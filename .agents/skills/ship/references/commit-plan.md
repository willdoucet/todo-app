# Commit plan

Loaded by ship step 6. Decides how the working tree becomes commits, what each message says,
and how the doc guard is satisfied per commit.

## Grouping

- **Default: one commit.** A plan is one logical unit; most branches land as one commit plus
  the merge commit from the sync.
- **Split only when the layers read independently**, and order them so every commit builds
  and its own tests pass on its own:
  1. infrastructure, configuration, migrations;
  2. models, services, background jobs;
  3. routes, pages, components;
  4. tests ride with the code they test, never in a separate "tests" commit;
  5. each doc change rides in the commit whose code it describes. The guard checks per commit,
     so a code commit whose doc lands two commits later is blocked by the hook.
- Never squash commits that already exist on the branch unless they are your own
  work-in-progress from an interrupted ship and the user agrees. Never rewrite the merge
  commit.
- Workflow files (`$PLANS_DIR`, `$STATE_DIR`) that changed before ship go into the last work
  commit. Step 9 makes the `chore(workflow): record ship` commit for what ship itself changes.

## Message

```
<type>(<scope>): <subject, imperative, at most 72 characters>

<why, in a few lines: the problem, the approach, what a reader of the log needs>
Plan: <repo-relative _PLAN_FILE>

Docs: n/a - <reason from DOC IMPACT>        # only when DOC IMPACT was none
```

- Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `build`, `ci`. Scope is
  the feature or directory; omit it when it adds nothing.
- The subject says what changed for the reader, not which files moved.
- Write the message to a file (`MSG_FILE=$(mktemp)`) and commit with `-F`; multi-line
  messages through `-m` lose their trailers in some shells.
- Add the attribution trailer the project's `AGENTS.md` or your harness requires, if any.
  This skill adds none of its own.

## The trailer rule

`Docs: n/a - <reason>` goes on a commit only when `/update-docs` concluded
`DOC IMPACT: none - <reason>` and the commit touches a mapped path. The reason is the one
`/update-docs` gave, verbatim; the guard requires it to be non-empty, and the git log is where
it is read later. Never invent a reason to get past the hook. `Docs: later` is never written by
ship.

## The guard loop, per commit

```bash
git add <paths of this group>
git diff --cached --stat
"$BIN/doc-guard" --staged --dry-run
git commit -F "$MSG_FILE"                   # never --no-verify
git log --oneline "$BASE_BRANCH"..HEAD
```

| Dry-run says | Do |
|---|---|
| `would pass` or `touch no documented areas` | commit |
| `would block` naming a doc staged for a later group | move that doc's changes into this commit |
| `would block` and `DOC IMPACT` was `none` | add the trailer, re-run the dry run, commit |
| `would block` and the doc was never updated | back to step 4; this is a gap, not a formality |
| the hook still rejects the commit | read its message; fix the cause; never bypass |

Before each commit, scan the staged diff for things that must not land: private keys
(`-----BEGIN`), tokens and secrets in config or example env files, local paths, debug output
left on. `git diff --cached | grep -nE 'BEGIN (RSA|OPENSSH|EC) PRIVATE|secret|token=' ` is a
first pass, not the whole check; read the diff.

## Re-running after an interruption

Commits that already exist are kept. Stage only what is still uncommitted, run the same loop,
and show the full `git log --oneline "$BASE_BRANCH"..HEAD` before pushing so the user sees the
whole set.
