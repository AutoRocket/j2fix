"""Fixed resource budgets for processing potentially untrusted templates."""

MAX_INPUT_BYTES = 1024 * 1024
MAX_TOKENS = 50_000
MAX_NESTING = 50
MAX_TAB_SIZE = 16


class TemplateLimitError(ValueError):
    """A template cannot be processed within the supported resource budgets."""


def check_size(text: str) -> None:
    if len(text) > MAX_INPUT_BYTES or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise TemplateLimitError(f"template exceeds the {MAX_INPUT_BYTES}-byte limit")
