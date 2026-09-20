# Pull request

Loaded by ship step 7.

## Title

`<type>(<scope>): <plan title, imperative>`, the same style as the first commit subject. No
version prefix, no ticket prefix unless `AGENTS.md` requires one.

## Create or update

```bash
BODY_FILE=$(mktemp)                         # write the body below into it
EXISTING=$(gh pr view --json url -q .url 2>/dev/null || true)
if [ -z "$EXISTING" ]; then
  gh pr create --base "$BASE_BRANCH" --head "$BRANCH" --title "$TITLE" --body-file "$BODY_FILE"
else
  gh pr edit "$EXISTING" --body-file "$BODY_FILE"
fi
PR_URL=$(gh pr view --json url -q .url)
```

One pull request per branch. An existing one is updated in place; its number and reviewers
survive.

## Without `gh`

Print the compare URL and the body for the user to paste, and use the compare URL as
`PR_URL` until they hand back the real one:

```bash
REMOTE=$(git remote get-url origin | sed -E 's#^git@([^:]+):#https://\1/#; s#\.git$##')
echo "$REMOTE/compare/$BASE_BRANCH...$BRANCH?expand=1"
```

Ask for the pull request URL once the user has opened it, then update the registry with
`registry-upsert "$REGISTRY_KEY" --set pr="<url>"`. The completion status is
`DONE_WITH_CONCERNS` until then.

## Body

```markdown
## Summary
<what changed and why, three to six lines, for a reviewer who has not read the plan>

## Plan
- Plan: `<repo-relative _PLAN_FILE>`
- Summary: `<repo-relative SUMMARY_FILE>`
- Epic / milestone: `<slug> — M<n> <title>`            <!-- omit when not an epic child -->
- Intake: <note ref, note path, roadmap phase, epic milestone, or "free text">

## Review dashboard
<the `workflow-state --dashboard` output from step 1, verbatim>
Hotfix override: shipped without <skills>, approved by the user on <utc-date>   <!-- only when used -->

## Test evidence
| Suite | Command | Result |
|---|---|---|
| <name as development-commands.md calls it> | `<exact command>` | <N passed, M failed, wall time> |

Fixes made after review to get green: <what and where, or "none">

## Documentation
<the doc sync report from /update-docs, verbatim, ending with its DOC IMPACT line>

## TODOS
- Completed by this branch: <titles moved to Completed, or "none">
- Added during review: <titles, or "none">

## Deviations from the plan
<from the summary's step notes; "none" when there were none>
```

Rules:

- Paste, do not paraphrase, the dashboard and the doc sync report. They are the evidence; a
  summary of evidence is a claim.
- Every test row names a command a reviewer can run. "All tests pass" without a command is
  not evidence.
- No changelog section, no version line, no review-service badges. Those are not part of this
  workflow.
