# Releasing j2fix

## One-time setup

1. Push this project to the `main` branch of
   `https://github.com/AutoRocket/j2fix`.
2. Create a `pypi` environment under **GitHub repository settings →
   Environments**. Enable required reviewers if the repository belongs to an
   organization or your GitHub plan supports this protection.
3. Create and verify a PyPI account, enable two-factor authentication, and
   securely store the recovery codes.
4. In PyPI, create a pending Trusted Publisher with:

   - PyPI project name: `j2fix`
   - GitHub owner: `AutoRocket`
   - GitHub repository: `j2fix`
   - Workflow: `release.yml`
   - Environment: `pypi`

No PyPI API token or GitHub secret is required.

## Prepare a release

1. Update `__version__` in `src/j2fix/__init__.py`. This is the sole version
   source for both package metadata and `j2fix --version`.
2. Run the complete local validation:

   ```console
   python -m pip install --upgrade build twine
   python -m pip install --editable '.[dev]'
   ruff check .
   python -m unittest discover -s tests -v
   python -m build
   python -m twine check --strict dist/*
   ```

3. Commit and push the version change. Wait for CI to pass.
4. Create a GitHub release whose tag is exactly the version prefixed with `v`,
   for example `v0.1.0`.

Publishing the GitHub release starts `.github/workflows/release.yml`. It builds
and validates the wheel and source distribution in a job without publishing
credentials. A separate job downloads those exact artifacts and publishes them
to PyPI through a short-lived Trusted Publishing credential.

PyPI does not permit replacing files for an existing release. If a release is
wrong, increment the version and publish a new release.

## Verify the release

Install into a fresh virtual environment from PyPI:

```console
python -m venv /tmp/j2fix-release-check
/tmp/j2fix-release-check/bin/python -m pip install j2fix
/tmp/j2fix-release-check/bin/j2fix --version
```
