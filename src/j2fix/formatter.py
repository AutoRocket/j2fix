"""Formatting primitives for Arista-style Jinja2 templates."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from jinja2 import Environment, TemplateSyntaxError

from .limits import MAX_NESTING, MAX_TAB_SIZE, MAX_TOKENS, TemplateLimitError, check_size

OPENING = re.compile(r"{{|{%|{#")
ENDRAW = re.compile(r"{%[-+]?\s*endraw\s*[-+]?%}")
BLOCK_OPENERS = {"autoescape", "block", "call", "filter", "for", "if", "macro", "with"}
BLOCK_BRANCHES = {"elif", "else"}


@dataclass(frozen=True)
class FormatOptions:
    """Options controlling transformations that can affect rendered whitespace."""

    unsafe: bool = False
    tab_size: int = 4

    def __post_init__(self) -> None:
        if type(self.tab_size) is not int or not 1 <= self.tab_size <= MAX_TAB_SIZE:
            raise ValueError(f"tab_size must be an integer between 1 and {MAX_TAB_SIZE}")


def _tag_parts(tag: str) -> tuple[str, str, str]:
    opening, closing = tag[:2], tag[-2:]
    start, end = 2, len(tag) - 2
    if tag[start : start + 1] in {"-", "+"}:
        opening += tag[start]
        start += 1
    controls = {"-", "+"} if tag.startswith("{%") else {"-"}
    if tag[end - 1 : end] in controls:
        end -= 1
        closing = tag[end] + closing
    return opening, tag[start:end], closing


def _tags(text: str) -> Iterator[tuple[int, int, str]]:
    """Scan source offsets, respecting quotes, bracket nesting, comments and raw."""
    cursor = 0
    while match := OPENING.search(text, cursor):
        start = match.start()
        opening = match.group()
        closing = {"{{": "}}", "{%": "%}", "{#": "#}"}[opening]
        index = match.end()
        quote = None
        brackets: list[str] = []
        while index < len(text):
            char = text[index]
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
            elif not brackets and text.startswith(closing, index):
                break
            elif opening != "{#":
                if char in {"'", '"'}:
                    quote = char
                elif char in "([{":
                    brackets.append(char)
                elif char in ")]}":
                    if brackets:
                        brackets.pop()
            index += 1
        if index >= len(text):
            return
        cursor = index + 2
        tag = text[start:cursor]
        yield start, cursor, tag
        if opening == "{%" and _tag_parts(tag)[1].strip() == "raw":
            endraw = ENDRAW.search(text, cursor)
            if endraw is None:
                return
            yield endraw.start(), endraw.end(), endraw.group()
            cursor = endraw.end()


def _space_operators(body: str, environment: Environment) -> str:
    """Use Jinja tokens so quoted strings and scientific notation stay intact."""
    tokens = list(environment.lex("{{ " + body + " }}"))[1:-1]
    output: list[str] = []
    after_operator = False
    for _, kind, value in tokens:
        if kind == "operator" and value in {"|", "+", "=="}:
            while output and output[-1].isspace():
                output.pop()
            if output:
                output.append(" ")
            output.extend((value, " "))
            after_operator = True
        elif kind == "whitespace" and after_operator:
            continue
        else:
            output.append(value.replace("\t", " ") if kind == "whitespace" else value)
            after_operator = False
    return "".join(output).strip()


def _check_complexity(text: str, environment: Environment) -> None:
    """Use the non-recursive lexer before invoking Jinja's recursive parser."""
    brackets = blocks = 0
    statement: list[tuple[str, str]] | None = None
    for count, (_, kind, value) in enumerate(environment.lex(text), 1):
        if count > MAX_TOKENS:
            raise TemplateLimitError(f"template exceeds the {MAX_TOKENS}-token limit")
        if kind == "operator":
            if value in {"(", "[", "{"}:
                brackets += 1
            elif value in {")", "]", "}"}:
                brackets = max(0, brackets - 1)
        if kind == "block_begin":
            statement = []
        elif kind == "block_end" and statement:
            keyword = statement[0][1]
            if keyword in BLOCK_OPENERS:
                blocks += 1
            elif keyword == "set":
                # A filter's keyword arguments are not a set assignment.
                for token_kind, token_value in statement[1:]:
                    if token_kind == "operator" and token_value in {"=", "|"}:
                        blocks += token_value == "|"
                        break
                else:
                    blocks += 1
            elif keyword.startswith("end"):
                blocks = max(0, blocks - 1)
            statement = None
        elif statement is not None and kind != "whitespace":
            statement.append((kind, value))
        if brackets + blocks > MAX_NESTING:
            raise TemplateLimitError(f"template exceeds the {MAX_NESTING}-level nesting limit")


def format_text(text: str, options: FormatOptions | None = None) -> str:
    """Format valid templates without changing their literal text in safe mode.

    Comments, raw bodies, and multiline tags are preserved. Invalid syntax or
    unsupported extensions are left for the linter to report. Unsafe mode also
    removes statement whitespace controls and expands tabs before statements.
    """
    check_size(text)
    options = options or FormatOptions()
    environment = Environment(extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"])
    try:
        _check_complexity(text, environment)
        return _format_text(text, options, environment)
    except TemplateSyntaxError:
        return text
    except RecursionError as error:
        raise TemplateLimitError("template is too complex for the Jinja parser") from error


def _format_text(text: str, options: FormatOptions, environment: Environment) -> str:
    try:
        original_tree = environment.parse(text).dump()
    except TemplateSyntaxError:
        return text

    output: list[str] = []
    cursor = depth = 0
    for start, end, tag in _tags(text):
        literal = text[cursor:start]
        cursor = end
        if tag.startswith("{#"):
            output.extend((literal, tag))
            continue
        opening, body, closing = _tag_parts(tag)
        expression = tag.startswith("{{")
        keyword = body.split(maxsplit=1)[0] if body.strip() else ""
        closer = not expression and keyword.startswith("end")
        display_depth = max(0, depth - 1) if closer or keyword in BLOCK_BRANCHES else depth
        if not expression:
            if closer:
                depth = max(0, depth - 1)
            elif keyword in BLOCK_OPENERS or keyword == "raw":
                depth += 1
            elif keyword == "set":
                assignment = False
                for _, kind, value in environment.lex(tag):
                    if kind == "operator" and value == "|":
                        break
                    if kind == "operator" and value == "=":
                        assignment = True
                        break
                if not assignment:
                    depth += 1

        if "\n" in tag or "\r" in tag:
            output.extend((literal, tag))
            continue
        # The text before endraw is a raw body; never expand its tabs.
        if options.unsafe and not expression and keyword != "endraw":
            literal = re.sub(r"(?m)^[ \t]+$", lambda m: m.group().replace("\t", " " * options.tab_size), literal)
        if options.unsafe and not expression:
            opening, closing = "{%", "%}"
        body = _space_operators(body.strip(), environment)
        padding = " " if expression else " " * (1 + display_depth * 4)
        output.extend((literal, f"{opening}{padding}{body} {closing}"))
    output.append(text[cursor:])
    formatted = "".join(output)
    check_size(formatted)
    try:
        formatted_tree = environment.parse(formatted).dump()
    except TemplateSyntaxError:
        return text
    # ASTs include literal output and values, but ignore source indentation.
    if not options.unsafe and formatted_tree != original_tree:
        return text
    return formatted
