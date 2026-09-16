# Security policy

This policy covers the j2fix formatter, command-line interface, and this
repository's build and release workflows.

## Supported versions

Security fixes target the latest release and the `main` development branch.
Older releases are not maintained as separate security-update branches; upgrade
to the latest release when a fix becomes available. Development changes on
`main` are not necessarily included in a published package yet.

j2fix is an early-stage project. Security reports are handled on a best-effort
basis, with no guaranteed response or resolution time.

## Report a vulnerability

Please do not post exploit details, credentials, private templates, or sensitive
logs in public issues or pull requests.

1. Open the repository's [Security page](https://github.com/AutoRocket/j2fix/security).
2. If **Report a vulnerability** is available, use it to send a private report
   to the maintainers.

In your private report, include:

- The j2fix version or commit, Python version, and operating system.
- A clear description of the issue and its possible impact.
- Minimal steps to reproduce it, using sanitized input.
- The command and relevant settings you used, including `--unsafe` if applicable.
- Any known workaround or suggested fix.

Only test against files and systems you own or are authorized to assess. Do not
access other users' data or disrupt shared services to demonstrate an issue.

## Handling and disclosure

Maintainers will review reports, request clarification where needed, and assess
whether the issue affects j2fix. Confirmed issues may be addressed through a fix,
a dependency update, or documented mitigation.

Please coordinate public disclosure with the maintainers so users can receive
a fix or mitigation first. Reporter credit can be discussed during coordination.
This policy does not promise a bounty, a CVE assignment, or a fixed disclosure
deadline.

For ordinary formatting bugs and feature requests, use
[GitHub issues](https://github.com/AutoRocket/j2fix/issues). If you are unsure
whether an issue has security impact, use the private reporting process above.

## Safe use

- Keep j2fix and its dependencies updated, and review release notes before upgrading.
- Keep templates in version control and preview changes with `j2fix --diff`.
- Avoid elevated privileges and directories writable by untrusted users.
- Treat `--unsafe` and `unsafe = true` in configuration as permission to change
  rendered whitespace; validate the result with your own rendering tests.
- j2fix parses templates but does not render them. It is not a sandbox or a
  validator for generated device configurations.
- If you offer hosted processing of untrusted input, use isolated workers with
  CPU, memory, and time limits. Formatter input limits alone are not sufficient.

See the [usage guide](docs/usage.md#file-safety-and-untrusted-input) for the current
source's file handling, resource limits, and platform limitations. Those
protections must not be assumed to exist in older releases.
