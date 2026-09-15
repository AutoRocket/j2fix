"""Formatting primitives for Arista-style Jinja2 templates."""

from __future__ import annotations

import re
from dataclasses import dataclass

TAG_PATTERN = re.compile(r"({{[-+]?.*?[-+]?}}|{%[-+]?.*?[-+]?%}|{#.*?#})", re.DOTALL)
RAW_TAG_PATTERN = re.compile(r"{%[-+]?\s*(raw|endraw)\s*[-+]?%}")

BLOCK_OPENERS = {
    "autoescape",
    "block",
    "call",
    "filter",
    "for",
    "if",
    "macro",
    "raw",
    "trans",
    "with",
}
BLOCK_BRANCHES = {"elif", "else"}


@dataclass(frozen=True)
class FormatOptions:
    """Options controlling transformations that can affect rendered whitespace."""

    unsafe: bool = False
    tab_size: int = 4


def _space_operators(value: str) -> str:
    """Give j2lint's S2 operators one space without touching quoted strings."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(value):
        char = value[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(value):
                index += 1
                output.append(value[index])
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue

        operator = "==" if value[index : index + 2] == "==" else char if char in {"|", "+"} else None
        if operator:
            while output and output[-1].isspace():
                output.pop()
            if output:
                output.append(" ")
            output.append(operator)
            index += len(operator)
            while index < len(value) and value[index].isspace():
                index += 1
            if index < len(value):
                output.append(" ")
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _format_tag(tag: str, options: FormatOptions, statement_depth: int | None = None) -> str:
    if tag.startswith("{#"):
        return tag

    expression = tag.startswith("{{")
    opening, closing = ("{{", "}}") if expression else ("{%", "%}")
    prefix_control = tag[len(opening) : len(opening) + 1] if tag[len(opening) :].startswith(("-", "+")) else ""
    suffix_control = tag[-len(closing) - 1 : -len(closing)] if tag[: -len(closing)].endswith(("-", "+")) else ""
    body_start = len(opening) + len(prefix_control)
    body_end = len(tag) - len(closing) - len(suffix_control)
    body = _space_operators(tag[body_start:body_end].strip())

    if options.unsafe and not expression:
        prefix_control = ""
        suffix_control = ""

    padding = " " if expression or statement_depth is None else " " * (1 + statement_depth * 4)
    return f"{opening}{prefix_control}{padding}{body} {suffix_control}{closing}"


def _format_non_raw_segment(text: str, options: FormatOptions) -> str:
    parts: list[str] = []
    cursor = 0
    for match in TAG_PATTERN.finditer(text):
        parts.append(text[cursor : match.start()])
        parts.append(_format_tag(match.group(), options))
        cursor = match.end()
    parts.append(text[cursor:])
    return "".join(parts)


def _format_tags_outside_raw(text: str, options: FormatOptions) -> str:
    """Format tags while preserving literal contents of raw blocks."""
    parts: list[str] = []
    cursor = 0
    raw = False
    for match in RAW_TAG_PATTERN.finditer(text):
        segment = text[cursor : match.start()]
        parts.append(segment if raw else _format_non_raw_segment(segment, options))
        parts.append(_format_tag(match.group(), options))
        raw = match.group(1) == "raw"
        cursor = match.end()
    tail = text[cursor:]
    parts.append(tail if raw else _format_non_raw_segment(tail, options))
    return "".join(parts)


def _indent_standalone_statements(text: str, options: FormatOptions) -> str:
    """Apply AVD's four-space nesting inside standalone statement delimiters."""
    lines = text.splitlines(keepends=True)
    depth = 0
    raw = False
    result: list[str] = []
    for line in lines:
        newline = "\n" if line.endswith("\n") else ""
        content = line[:-1] if newline else line
        stripped = content.strip()
        tags = list(TAG_PATTERN.finditer(stripped))
        if len(tags) != 1 or tags[0].span() != (0, len(stripped)) or not stripped.startswith("{%"):
            result.append(line)
            for tag_match in TAG_PATTERN.finditer(content):
                tag = tag_match.group()
                if not tag.startswith("{%"):
                    continue
                tag_body = re.sub(r"^{%[-+]?|[-+]?%}$", "", tag).strip()
                tag_keyword = tag_body.split(maxsplit=1)[0] if tag_body else ""
                if raw:
                    if tag_keyword == "endraw":
                        raw = False
                        depth = max(0, depth - 1)
                    continue
                if tag_keyword.startswith("end"):
                    depth = max(0, depth - 1)
                elif tag_keyword in BLOCK_OPENERS:
                    depth += 1
                    raw = tag_keyword == "raw"
            continue

        leading = content[: len(content) - len(content.lstrip())]
        trailing = content[len(content.rstrip()) :]
        tag = stripped
        body = re.sub(r"^{%[-+]?|[-+]?%}$", "", tag).strip()
        keyword = body.split(maxsplit=1)[0] if body else ""
        is_closer = keyword.startswith("end")
        display_depth = max(0, depth - 1) if is_closer or keyword in BLOCK_BRANCHES else depth
        formatted = _format_tag(tag, options, display_depth)
        result.append(f"{leading}{formatted}{trailing}{newline}")

        if is_closer:
            depth = max(0, depth - 1)
            raw = False if keyword == "endraw" else raw
        elif keyword in BLOCK_OPENERS:
            depth += 1
            raw = keyword == "raw"
    return "".join(result)


def _replace_indentation_tabs(text: str, tab_size: int) -> str:
    return re.sub(
        r"(?m)^[ \t]+",
        lambda match: match.group().replace("\t", " " * tab_size),
        text,
    )


def format_text(text: str, options: FormatOptions | None = None) -> str:
    """Return a deterministically formatted Jinja2 template.

    Safe mode fixes S1, S2, S3, S4, and indentation tabs from S5. Unsafe mode
    additionally removes S6 whitespace-control markers, which may alter output.
    S0, S7, V1, and V2 require author intent and are left to j2lint.
    """
    options = options or FormatOptions()
    formatted = _replace_indentation_tabs(text, options.tab_size)
    formatted = _format_tags_outside_raw(formatted, options)
    return _indent_standalone_statements(formatted, options)
