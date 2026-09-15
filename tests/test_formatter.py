import unittest

from j2fix import FormatOptions, format_text


class FormatterTests(unittest.TestCase):
    def test_fixes_spacing_operators_and_statement_indentation(self) -> None:
        source = """{%if enabled%}\n{{name|upper}}\n{%for item in items%}\n{{ item+suffix }}\n{%endfor%}\n{%endif%}\n"""
        expected = (
            "{% if enabled %}\n{{ name | upper }}\n{%     for item in items %}\n"
            "{{ item + suffix }}\n{%     endfor %}\n{% endif %}\n"
        )
        self.assertEqual(format_text(source), expected)

    def test_preserves_quoted_operators(self) -> None:
        self.assertEqual(format_text('{{ "a+b|c==d" }}'), '{{ "a+b|c==d" }}')

    def test_raw_block_body_is_untouched(self) -> None:
        source = "{%raw%}{{bad|spacing}}{%endraw%}"
        self.assertEqual(format_text(source), "{% raw %}{{bad|spacing}}{% endraw %}")

    def test_whitespace_control_is_only_removed_in_unsafe_mode(self) -> None:
        source = "{%- if thing -%}\n{{- value -}}\n{%- endif -%}\n"
        self.assertIn("{%- if thing -%}", format_text(source))
        self.assertEqual(format_text(source, FormatOptions(unsafe=True)).splitlines()[0], "{% if thing %}")
        self.assertIn("{{- value -}}", format_text(source, FormatOptions(unsafe=True)))

    def test_idempotent(self) -> None:
        source = "{% if enabled %}\n{%     set value = thing | upper %}\n{% endif %}\n"
        self.assertEqual(format_text(format_text(source)), format_text(source))

    def test_inline_closer_updates_following_branch_depth(self) -> None:
        source = "{% if one %}\n{% for item in items %}\n{{ item }}{% endfor %}\n{% elif two %}\n{% endif %}\n"
        expected = "{% if one %}\n{%     for item in items %}\n{{ item }}{% endfor %}\n{% elif two %}\n{% endif %}\n"
        self.assertEqual(format_text(source), expected)
