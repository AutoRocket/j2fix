import unittest

from jinja2 import Environment

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
        expected = (
            "{% if one %}\n{%     for item in items %}\n{{ item }}{%     endfor %}\n{% elif two %}\n{% endif %}\n"
        )
        self.assertEqual(format_text(source), expected)

    def test_render_preservation_and_idempotence(self) -> None:
        sources = [
            "{% raw %}\n\t{% if foo %}\n{{bar|upper}}\n{% endraw %}",
            '{{ "}}a+b" }}',
            '{{ "a\\"}}|b" }}',
            '{{ {"name": {"value": 2}}}}',
            "{{ 1e+3 }}",
            "{{ 2+3 }}",
            "\tinterface {{name}}\n",
            "{# {%raw%}\n{{foo}} #}\n{{name|upper}}",
            "{% set capture %}\n{% if true %}ok{% endif %}\n{% endset %}{{capture}}",
            '{% set value = "=" %}\n{% if true %}{{value}}{% endif %}',
            "{% if\ntrue %}\n{{name}}\n{% endif %}",
            "{%- if true +%}\n{{- name -}}\n{% endif -%}",
            "{{name}}\r\n{% if true %}\r\n{{name}}\r\n{% endif %}\r\n",
            "{% for item in [] %}{{item}}{% else %}empty{% endfor %}",
        ]
        for source in sources:
            with self.subTest(source=source):
                result = format_text(source)
                self.assertEqual(format_text(result), result)
                for trim in (False, True):
                    for lstrip in (False, True):
                        env = Environment(trim_blocks=trim, lstrip_blocks=lstrip, keep_trailing_newline=True)
                        self.assertEqual(
                            env.from_string(source).render(name="test"),
                            env.from_string(result).render(name="test"),
                        )

    def test_quoted_delimiter_does_not_prevent_formatting(self) -> None:
        self.assertEqual(format_text('{{"}}a+b"|upper}}'), '{{ "}}a+b" | upper }}')

    def test_capture_set_indentation(self) -> None:
        self.assertEqual(
            format_text("{%set capture%}\n{%if true%}ok{%endif%}\n{%endset%}"),
            "{% set capture %}\n{%     if true %}ok{%     endif %}\n{% endset %}",
        )

    def test_invalid_syntax_is_never_rewritten(self) -> None:
        source = "{%if broken%}\n{{name}}"
        for unsafe in (False, True):
            self.assertEqual(format_text(source, FormatOptions(unsafe=unsafe)), source)

    def test_raw_body_is_preserved_in_unsafe_mode(self) -> None:
        source = "{%raw%}\n\t{%if ignored%}\n{{foo}}\n{%endraw%}"
        self.assertEqual(
            format_text(source, FormatOptions(unsafe=True)),
            "{% raw %}\n\t{%if ignored%}\n{{foo}}\n{% endraw %}",
        )

    def test_tabs_inside_tags_are_fixed_without_changing_strings(self) -> None:
        self.assertEqual(format_text('{{value\t~\t"a\tb"}}'), '{{ value ~ "a\tb" }}')

    def test_capture_filter_keyword_arguments_keep_block_depth(self) -> None:
        source = '{% set capture | replace(old="x", new="y") %}\n{% if true %}x{% endif %}\n{% endset %}'
        self.assertIn("{%     if true %}x{%     endif %}", format_text(source))
