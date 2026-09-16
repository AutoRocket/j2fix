# j2fix

**Consistent Jinja2 templates. Less manual cleanup.**

[![Version](https://img.shields.io/badge/version-0.3.0-blue)](https://github.com/AutoRocket/j2fix/tree/v0.3.0)
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

> An independent project. Not affiliated with or endorsed by Arista Networks.

[Usage guide](docs/usage.md) · [Security policy](SECURITY.MD) ·
[Report a bug](https://github.com/AutoRocket/j2fix/issues)

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

Install with pip

```bash
pip install j2fix
j2fix --version
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

The current source also adds symlink protection, atomic file replacement, and
input limits. See [file safety and limits](docs/usage.md#file-safety-and-untrusted-input).

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
    rev: v0.3.0
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
