# Git hooks

`framework init` points git at this directory with `git config core.hooksPath .agents/hooks`,
so every hook here runs for every clone that has run init (no copying into `.git/hooks`).

- `commit-msg` — runs `.agents/bin/doc-guard --commit-msg` against the staged files and the
  commit message; skips itself with a one-line warning when the helper or `python3` is missing.

Bypass a single commit with `git commit --no-verify`; CI still checks the PR range with `doc-guard --range`.
