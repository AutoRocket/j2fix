# j2fix

**Consistent Jinja2 templates. Less manual cleanup.**

[![Version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/AutoRocket/j2fix/tree/v0.2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#installation)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/AutoRocket/j2fix/blob/main/LICENSE)

`j2fix` is a command-line formatter for Jinja2 templates, designed around the
[Arista AVD style guide](https://avd.arista.com/5.3/docs/contribution/style-guide.html)
and the rules enforced by [Arista Networks' `j2lint`](https://github.com/aristanetworks/j2lint).
It fixes spacing and statement indentation, then runs `j2lint` to report anything
that still needs your attention.

If you use `yamllint` to check YAML and `yamlfix` to tidy it, think of `j2fix` as
the formatting companion to `j2lint`. It is useful for network configuration
templates, Ansible projects, and other Jinja templates that follow Arista's style.
You do not need Arista devices or the AVD collection to use it.

> An independent AutoRocket project. Not affiliated with or endorsed by Arista Networks.

[Quick start](#quick-start) · [Configuration](#configuration) · [Rule coverage](#rule-coverage) ·
[Pre-commit](#pre-commit) · [Python API](#python-api)

## See the difference

Before:

```jinja
{%for interface in interfaces%}
{%if interface.enabled%}
interface {{interface.name}}
 description {{interface.description|default("Managed by automation")}}
{%endif%}
{%endfor%}
```

After `j2fix interfaces.j2`:

```jinja
{% for interface in interfaces %}
{%     if interface.enabled %}
interface {{ interface.name }}
 description {{ interface.description | default("Managed by automation") }}
{%     endif %}
{% endfor %}
```

Arista-style nesting goes **inside** the `{% … %}` delimiters. The indentation
of the configuration text itself stays intact in default mode.

## Installation

Requires **Python 3.10 or newer**. Jinja2 and `j2lint` are installed automatically.

Install the tagged version directly from GitHub:

```bash
python -m pip install "git+https://github.com/AutoRocket/j2fix.git@v0.2.0"
j2fix --version
```

Git must be installed for this method. While the repository is private, you need
access to it and GitHub authentication configured for Git.

Once `0.2.0` has been published to PyPI, you can install it with:

```bash
python -m pip install "j2fix==0.2.0"
```

Expected version output:

```text
j2fix 0.2.0
```

## Quick start

Preview the changes, then apply them:

```bash
j2fix --diff templates/
j2fix templates/
```

Check formatting and lint results without editing files:

```bash
j2fix --check templates/
```

You can pass several files or directories. With no path, `j2fix` searches the
current directory. Directory searches include `.j2`, `.jinja`, and `.jinja2`
files by default.

```bash
j2fix router.j2 switch.j2 templates/
j2fix --check .
j2fix --extensions j2,jinja,jinja2,html templates/
```

### Command reference

| Option | What it does |
| --- | --- |
| `--check` | Report files needing formatting without writing changes. |
| `--diff` | Show a unified diff without writing changes. |
| `--unsafe` | Also allow changes to statement whitespace controls and indentation tabs before statements. |
| `--no-lint` | Format without running the final `j2lint` checks. |
| `-c`, `--config-file` | Use a specific `pyproject.toml`. |
| `-e`, `--extensions` | Select file extensions using a comma-separated list. |
| `--version` | Print the installed version. |
| `--help` | Show command help. |

For editor integrations and shell pipelines, use `-` to read from standard input.
Formatted text goes to standard output; lint diagnostics go to standard error.

```bash
j2fix - < template.j2
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success; no remaining lint issues when linting is enabled. |
| `1` | Lint issues remain, or `--check`/`--diff` found changes. |
| `2` | A usage, configuration, or file error occurred, or no matching templates were found. |

In write mode, fixes may already have been saved even if the command exits with
`1`. Read the remaining diagnostics to see what needs manual attention.

## Formatting behavior

Default formatting preserves literal text, quoted strings, comments, raw block
contents, and file line endings. Before accepting a safe edit, `j2fix` compares
Jinja's parsed representation of the original and formatted template.

There are deliberate limits:

- Templates with invalid syntax are left unchanged and reported by `j2lint`.
- Multiline tags are preserved; other supported tags in the same file can still be formatted.
- Variable names are not renamed, because those names may belong to an external data model.
- Multiple statements on one line are not split automatically.
- Custom Jinja extensions and delimiters are not configurable. Standard Jinja syntax,
  plus the `do` and loop-control extensions, is supported.
- `j2fix` checks template syntax and style; it does not validate rendered device
  configuration, inventory data, or whether application-specific filters exist.

### When to use `--unsafe`

Whitespace controls such as `{%-` and `-%}` affect rendered output. Arista's S6
rule discourages those markers, but removing them can add whitespace to a generated
configuration. Tabs before statements can also be part of the output.

Preview these changes explicitly:

```bash
j2fix --unsafe --diff templates/
```

Apply them when they match your intended output, and run your template rendering tests:

```bash
j2fix --unsafe templates/
```

`--unsafe` does not rename variables or split statements. Expression whitespace
controls such as `{{- value -}}` are preserved.

## Rule coverage

`j2fix` targets the rules in `j2lint` 1.3. Arista's wider style guide also includes
recommendations that are not automated by these tools.

| Rule | Convention | Behavior |
| --- | --- | --- |
| S0 | Valid Jinja syntax | Checked by `j2lint`; invalid templates are not rewritten. |
| S1 | Spaces inside expression delimiters | Fixed for single-line tags. |
| S2 | Spaces around `\|`, `+`, and `==` | Fixed without changing string contents or numeric literals. |
| S3 | Four-space nesting inside statement delimiters | Fixed for single-line tags. |
| S4 | Spaces inside statement delimiters | Fixed for single-line tags. |
| S5 | No tab indentation | Fixed within single-line tags; tabs before statements require `--unsafe`. |
| S6 | No statement whitespace-control markers | Fixed for single-line tags with `--unsafe`. |
| S7 | One statement per line | Reported for manual correction. |
| V1 | Lowercase variable names | Reported for manual correction. |
| V2 | Underscores between words in variable names | Reported for manual correction. |

## Configuration

Add a `[tool.j2fix]` table to your project's `pyproject.toml`. These are the defaults:

```toml
[tool.j2fix]
extensions = ["j2", "jinja", "jinja2"]
exclude = [".git", ".venv", "venv", "build", "dist"]
unsafe = false
lint = true
tab_size = 4
```

`j2fix` searches upward from the **current working directory** and uses the first
`pyproject.toml` containing this table. To select a file explicitly:

```bash
j2fix --config-file path/to/pyproject.toml templates/
```

`extensions` and `exclude` replace their default lists. Exclusions apply during
directory discovery; explicitly supplied files are still processed. `tab_size`
controls expansion of tabs before statements in unsafe mode; Arista's nesting
width inside statement tags remains four spaces.

The command-line `--extensions` setting overrides the configured extensions.
`--unsafe` enables unsafe formatting, and `--no-lint` disables linting, regardless
of their corresponding configuration values.

## Pre-commit

Add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/AutoRocket/j2fix
    rev: v0.2.0
    hooks:
      - id: j2fix
```

Then install and run the hook:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The hook applies fixes. Review and stage the changes, then commit again. Add
`args: [--check]` under the hook if you want it to report changes without editing.
Private repositories require Git authentication wherever the hook runs.

## Python API

Use the formatter directly in Python:

```python
from j2fix import FormatOptions, format_text

formatted = format_text("{{value|upper}}")
assert formatted == "{{ value | upper }}"

formatted = format_text(
    "{%- if enabled -%}yes{%- endif -%}",
    FormatOptions(unsafe=True),
)
```

`format_text()` returns a string. It does not write files or run the final `j2lint`
checks; those are part of the command-line interface.

## Contributing

Bug reports and pull requests are welcome at
[AutoRocket/j2fix](https://github.com/AutoRocket/j2fix). For a formatting issue,
include a small template, expected output, actual output, and `j2fix --version`.

Set up a development environment from a clone:

```bash
git clone https://github.com/AutoRocket/j2fix.git
cd j2fix
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
python -m pytest
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
CI is configured to test Python 3.10–3.14 and validate the built distributions.

## License

Released under the [MIT license](https://github.com/AutoRocket/j2fix/blob/main/LICENSE).
