# j2fix

`j2fix` is an opinionated formatter for Jinja2 templates. It complements
[Arista Networks j2lint](https://github.com/aristanetworks/j2lint) in the same
way that `yamlfix` complements `yamllint`: `j2fix` makes deterministic edits,
then the official linter reports anything that still needs author intent.

> This is an independent project and is not an Arista Networks product.

## Rules

The formatter targets Arista j2lint 1.3's rules:

| Rule | Meaning | j2fix behavior |
| --- | --- | --- |
| S0 | Valid Jinja syntax | Validated by j2lint |
| S1 | One space inside expression delimiters | Fixed |
| S2 | Spaces around `\|`, `+`, and `==` | Fixed |
| S3 | Four-space nesting inside statement delimiters | Fixed for standalone statements |
| S4 | Spaces inside statement delimiters | Fixed |
| S5 | No tab indentation | Fixed |
| S6 | No statement whitespace-control delimiters | Fixed only with `--unsafe` |
| S7 | One statement per line | Reported by j2lint |
| V1 | Lowercase variable names | Reported by j2lint |
| V2 | Underscores in multi-word variables | Reported by j2lint |

S6 is opt-in because removing `{%-` or `-%}` can change rendered output. S7 and
variable renames are not automatic because a formatter cannot safely infer the
desired output or external data-model changes.

## Install and use

```console
python -m pip install -e .
j2fix templates/
j2fix --check templates/
j2fix --diff templates/
j2fix --unsafe templates/
cat template.j2 | j2fix -
```

By default files are rewritten and then checked with official `j2lint`. Exit
status is `1` when `--check`/`--diff` finds changes or when lint issues remain,
and `2` for usage or I/O errors. Use `--no-lint` to run formatting alone.

## Configuration

`j2fix` searches upward from the current directory for `pyproject.toml` with a
`[tool.j2fix]` table. Pass `-c` to select one explicitly.

```toml
[tool.j2fix]
extensions = ["j2", "jinja", "jinja2", "html"]
exclude = [".git", ".venv", "generated"]
unsafe = false
lint = true
tab_size = 4
```

Python API:

```python
from j2fix import format_text

formatted = format_text("{{value|upper}}")
```

## Pre-commit

Until the project has a release URL, use it as a local hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: j2fix
        name: j2fix
        entry: j2fix --check
        language: system
        files: '\\.(j2|jinja|jinja2)$'
```

## Development

```console
python -m pip install -e '.[dev]'
python -m unittest discover -s tests
pytest  # optional alternative
ruff check .
```

Release instructions, including PyPI Trusted Publishing setup, are in
[`RELEASING.md`](RELEASING.md).
