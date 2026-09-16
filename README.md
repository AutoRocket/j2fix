# j2fix

**Consistent Jinja2 templates. Less manual cleanup.**

[![Version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/AutoRocket/j2fix/tree/v0.2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#installation)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/AutoRocket/j2fix/blob/main/LICENSE)

Format Jinja2 templates using the conventions checked by
[Arista Networks’ j2lint](https://github.com/aristanetworks/j2lint).

`j2fix` fixes spacing and statement indentation, then reports anything that needs
manual attention. Use it for network configuration templates, Ansible projects,
or other Jinja templates. No Arista hardware is required.

An independent AutoRocket project—not affiliated with or endorsed by Arista Networks.

[Usage guide](docs/usage.md) · [Security policy](SECURITY.MD) ·
[Report a bug](https://github.com/AutoRocket/j2fix/issues)

## Install

Requires **Python 3.10 or newer**. Jinja2 and j2lint are installed automatically;
Node.js is not needed.

```bash
pip install j2fix
j2fix --version
```

## Get started

Preview changes without editing your files:

```bash
j2fix --diff templates/
```

Apply the changes:

```bash
j2fix templates/
```

Check files without changing them—useful in CI:

```bash
j2fix --check templates/
```

Replace `templates/` with your own file or folder. You can pass multiple paths.
By default, j2fix finds `.j2`, `.jinja`, and `.jinja2` files.

## Before and after

Before:

```jinja
{%for interface in interfaces%}
{%if interface.enabled%}
interface {{interface.name}}
 description {{interface.description|default("Managed by automation")}}
{%endif%}
{%endfor%}
```

After: j2fix 

```jinja
{% for interface in interfaces %}
{%     if interface.enabled %}
interface {{ interface.name }}
 description {{ interface.description | default("Managed by automation") }}
{%     endif %}
{% endfor %}
```

Normal formatting preserves the text outside Jinja tags, including the indentation
of your generated configuration. Nested statement indentation goes inside the
`{% … %}` tags.

## Useful commands

| What you want to do | Command |
| --- | --- |
| Format one file | `j2fix router.j2` |
| Preview changes | `j2fix --diff templates/` |
| Check formatting and lint | `j2fix --check templates/` |
| Format without linting | `j2fix --no-lint templates/` |
| Read from standard input | `j2fix - < router.j2` |
| See all options | `j2fix --help` |

Exit codes: `0` means success; `1` means lint issues or changes found in check/diff
mode; `2` means a processing error or no matching files. Files may already have
been changed in write mode even when the command returns an error.

## What to expect

- Spacing and statement indentation are fixed automatically.
- Invalid syntax, variable naming, and other unsupported fixes need manual attention.
- j2fix does not render templates or validate the resulting device configuration.
- `--unsafe` can change rendered whitespace. Preview it with
  `j2fix --unsafe --diff templates/` and run your rendering tests before applying it.

Keep templates in version control and review your diffs. Do not run j2fix with
administrator privileges or assume it is a sandbox for untrusted input.

The current source also adds symlink protection, atomic file replacement, and
input limits. These changes are not yet included in the published v0.2.0 release.
See [file safety and limits](docs/usage.md#file-safety-and-untrusted-input).

## Configuration

Optional settings go in your project's `pyproject.toml`:

```toml
[tool.j2fix]
extensions = ["j2", "jinja", "jinja2"]
exclude = [".git", ".venv", "venv", "build", "dist"]
unsafe = false
lint = true
tab_size = 4
```

j2fix searches upward from your current working directory for these settings.
`exclude` replaces the default exclusions. Keep `unsafe = false` unless you
intend to allow whitespace changes.

See the [configuration guide](docs/usage.md#configuration) for overrides and limits.

## Use with pre-commit

Add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/AutoRocket/j2fix
    rev: v0.2.0
    hooks:
      - id: j2fix
```

Then run:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The hook edits files. Add `args: [--check]` to check without editing.
This example uses the released tag, not unreleased changes on `main`.

## Help and development

For bugs, [open an issue](https://github.com/AutoRocket/j2fix/issues) with a small,
sanitized template, expected output, and your `j2fix --version`.
For security concerns, follow the [security policy](SECURITY.MD) instead.

See the [usage guide](docs/usage.md) for rule coverage, the Python API, and development setup.

## License

[MIT](LICENSE). 

## Acknowledgments

This project is based on j2lint [Arista Networks’ j2lint](https://github.com/aristanetworks/j2lint).
