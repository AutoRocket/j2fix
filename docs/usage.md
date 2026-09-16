# Usage guide

[Back to the README](../README.md) · [Security policy](../SECURITY.MD)

This guide describes the current source. The file-safety protections, resource
limits, and `TemplateLimitError` API described below are unreleased changes and
are not included in the published v0.2.0 package or tag.

## Command reference

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

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success; no remaining lint issues when linting is enabled. |
| `1` | Lint issues remain, or `--check`/`--diff` found changes. |
| `2` | A usage, configuration, file, or resource-limit error occurred, or no matching templates were found. |

In write mode, fixes may already have been saved even if the command exits with
`1`. Read the remaining diagnostics to see what needs manual attention.
If one file fails during processing, other files are still processed and the
command exits with `2`. A multi-file run is not a single transaction.

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

### File safety and untrusted input

Directory searches skip symbolic links and excluded directories. Explicitly
passing a symbolic link, a path through a linked directory, or a Windows reparse
point is an error. Pass the real path if you intend to format its target.

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
width inside statement tags remains four spaces. `tab_size` must be an integer
from 1 to 16.

The command-line `--extensions` setting overrides the configured extensions.
`--unsafe` enables unsafe formatting, and `--no-lint` disables linting, regardless
of their corresponding configuration values.

## Pre-commit

Add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/AutoRocket/j2fix
    rev: v0.3.0
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
It raises `j2fix.TemplateLimitError` when a resource limit or parser recursion
limit is reached. Callers processing untrusted templates should handle that error.

## Development setup

From a local clone:

```bash
git clone https://github.com/AutoRocket/j2fix.git
cd j2fix
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade 'pip>=26.2' 'setuptools>=83'
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
python -m pytest
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
Installing from a clone uses that checkout's source, including any local changes.

CI is configured to test Python 3.10–3.14 and validate built distributions.
The current workflow configuration also adds `pip-audit` checks for installed
third-party packages; the project's own package is excluded from the dependency
lookup. `pip check` checks dependency compatibility, not known vulnerabilities.

Workflow actions are pinned to commit hashes. JavaScript actions use Node.js 24,
and Dependabot is configured to propose weekly action and Python dependency updates.
OpenSSF Scorecard provides a separate supply-chain review. Local workflow changes
take effect on GitHub only after they are committed and pushed.
