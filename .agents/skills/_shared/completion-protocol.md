# Completion protocol

Every skill ends with exactly one status:

- **DONE.** All steps completed with evidence for each claim.
- **DONE_WITH_CONCERNS.** Completed, but with issues the user should know about. List each.
- **BLOCKED.** Cannot proceed. State what is blocking and what was tried.
- **NEEDS_CONTEXT.** Missing information required to continue. State exactly what you need.
- **ABANDONED.** The user decided to stop this work. Record the reason.

## Escalation

It is always acceptable to stop and say "this is too hard" or "I am not confident in this
result." Bad work is worse than no work.

- After three failed attempts at the same thing, stop and escalate.
- If uncertain about a security-sensitive change, stop and escalate.
- If the scope exceeds what you can verify, stop and escalate.

```
STATUS: BLOCKED | NEEDS_CONTEXT
REASON: [one or two sentences]
ATTEMPTED: [what you tried]
RECOMMENDATION: [what the user should do next]
```

## What each status writes

| Status | Plan and registry | Note |
|---|---|---|
| DONE | the skill's success status (see `obsidian-sync.md`) | scrub only |
| DONE_WITH_CONCERNS | same as DONE plus `reason` | scrub only |
| BLOCKED | `implementation_status=blocked`, `reason` | scrub only, box unchanged |
| NEEDS_CONTEXT | `implementation_status=needs-context`, `reason` | scrub only, box unchanged |
| ABANDONED | `obsidian-workflow abandon <key> --reason "..."` | box unchecked, reason recorded |

## Change description

When a skill has modified files, close with:

```
CHANGES MADE:
- [file]: [what changed and why]

THINGS I DIDN'T TOUCH:
- [file]: [intentionally left alone because ...]

POTENTIAL CONCERNS:
- [risks or things to verify]
```

Then run `"$BIN/workflow-state" --next` and present its output as the last thing you say.
