## GitHub Actions

### Operations
- `doc-guard` runs on every pull request with `fetch-depth: 0` so the base range resolves.
- Every job runs the same command as development-commands.md; there is no CI-only code path.
- A `concurrency` group cancels superseded runs; every job has `timeout-minutes`.
- Actions are pinned to a major version or a SHA; `permissions` is minimal (`contents: read` unless a job needs more).
- Required checks have stable job names; new suites stay informational until they have soaked flake-free.
- Test artifacts are uploaded on failure only.

### Secrets & config
- Secrets are referenced as `${{ secrets.NAME }}` and never echoed; no step runs `env` or `printenv` bare.
- One-time CI secrets (a test encryption key) are documented with their generation command in development-commands.md.
- Forked pull requests do not receive secrets; jobs that need them are skipped or gated, not failed.

### Testing
- The matrix is limited to versions the project actually supports.
