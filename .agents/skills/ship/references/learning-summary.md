# Plain-English summary

Written by ship step 8 when `modules.learning_summaries` is `true` in
`$REPO_ROOT/.agents/config.json`. One file per shipped plan:

```
$VAULT_DIR/Learning/<plan-name> - Plain English Summary.md      # plan-name = basename of _PLAN_FILE without .md
```

Create the `Learning` directory if it is missing. The audience is the builder six months from
now, or a friend who does not code: no function names, no acronyms without a one-line
definition, no jargon that needs the code open to follow. Say what things do, not what they
are called. The reason behind each decision is the point of the file; the what is in the pull
request already.

```markdown
# <plan title> — plain English summary

Shipped <utc-date> on `<branch>` · Pull request: <PR_URL> · Plan: `<repo-relative _PLAN_FILE>`

## What we built
<two or three sentences a non-programmer can follow>

## Why
<the problem and who had it, in the user's own words from the plan's problem statement>

## How it works, in one analogy
<one concrete everyday analogy for the mechanism; then one sentence on where the analogy breaks>

## What changed for the user
- <something they can do now that they could not before>
- <something that stopped going wrong>

## Decisions and trade-offs
- <what we chose> instead of <what we did not>, because <the reason>; we gave up <the cost>
- <repeat for every decision the plan or the reviews locked>

## What this taught
- <two to four things worth remembering; link the matching `## Decisions` entries in LESSONS.md>

## Where to look
- `<path>` — <one line on what this file is responsible for>
- <three to five files that carry the idea; not a full inventory>
```

Rules:

- One screen. If it runs long, the decisions section is doing the plan's job; cut it back to
  the why.
- Nothing is copied from the plan or the pull request; this is a retelling, not an excerpt.
- Never skip the why, and never skip the trade-off. A decision without a cost is not a
  decision.
