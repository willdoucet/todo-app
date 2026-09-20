# Dashboard and next step

Do not compute review readiness or the next step in prose. Both are derived from the registry,
the review log, and the plan's frontmatter by one function, so every skill and the session
banner agree.

## At the end of every skill

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```

Present the dashboard table verbatim, then the next step in this shape:

```
NEXT: /plan-eng-review — required (shipping gate)
OPTIONAL: /plan-adversarial-review — risk tags: auth, infra
OPEN: /plan-ceo-review — ran with issues open: re-run it, or confirm each open item is closed and log resolved
CONCERN: /plan-adversarial-review (2026-09-17): rollback fails open; capture the stale rows before reverting
REASON: /plan-eng-review (2026-09-17): Eng review 2 clean; two operator gates remain before merge
```

`CONCERN:` and `REASON:` are display only: a review's own `concern` field, shown with the
review that wrote it and when, and the plan's frontmatter `reason`, shown with its `reason_by`
and the date of its `reason_at` when it has them. Nothing reads them to decide anything.

Add one line reminding the user that the invocation syntax depends on the harness (`/name` in
Claude Code, Grok Build, and Cursor; `$name` in Codex).

## When the next step names a review that ran with issues open

`--next` names a review whose latest entry is `issues_open`; every other such review is an
`Open:` line. A review that ran and did not pass blocks its stage; "optional" governs only a
review that never ran. There are two ways to clear it, and only two.

1. **Confirm each open item is closed, then log a resolution.** Find the review's open items: a
   plan review's REVIEW REPORT row and the plan; `/qa`'s QA report; `/design-review`'s audit
   report; `/review-implementation`'s and `/final-review`'s findings in their REVIEW REPORT rows
   and the summary file. For each item, find where it is closed: a plan section, a report entry,
   or a commit. If every item is closed:

   ```bash
   "$BIN/review-log" --skill <that review> --status resolved \
     --field resolved_by=<the later review that verified the closure> \
     --field note="<where each item is closed>"
   ```

   The resolver is a review tier that ran after the failure and passed: never the skill that
   wrote the fix (`/execute-plan` and `/quickfix` are not review tiers) and never the failed
   review itself; `review-log` checks both. A failure at the ship stage (implementation review,
   adversarial subagent, QA, design audit, final review) takes a ship-stage resolver or
   `operator`, never a plan review and never `ship`. A resolution clears only the failure it
   names: a later failure of the same review, even one merged in from another branch, reopens
   it (`superseded_by_failure` in the row). At the plan stage the resolver is usually the next
   plan review; when the `--next` reason says a later review already passed, prefer logging
   `resolved` by that review over re-running. At the ship stage no later review runs before the
   gate, so a failed `/qa`, `/design-review`, implementation or final review clears in practice
   by re-running it after the fix, or by `operator`. Use `resolved_by=operator` only when the
   user said in this session that they decided the item; the dashboard row shows who resolved.
2. **Re-run the review** when any item is not closed. A re-run that fails again blocks again.

Never log `clean` under another skill's name. A review that closes an earlier failed review's
items logs its **own** entry first, then the resolution: `review-log` requires the resolver's
latest entry to be passed and not earlier than the failure. A review that reads `stale` is
not failed, and neither way applies to it; the next section does.

## When your review changes what an earlier review approved

Reviews edit the plan by design, so the one who changed what an earlier review approved is the
one who knows it. Declare it; nothing infers it from a diff.

**What counts.** Reversing or replacing a decision an earlier review recorded, or adding or
changing a contract in that review's domain: for eng, data flow, schema, API, failure modes and
tests; for design, what a user sees; for the CEO review, scope; for the adversarial review,
abuse and rollback. Counts: a design review adding a backend contract that supersedes an eng
rule; an adversarial review replacing the handling an eng review had accepted as out of scope;
an adversarial review changing the outcome of a case an eng review had specified a test for.

**What does not count.** Working inside your own domain on material the earlier review left to
you: pinning an ambiguity it left (a return type it never stated); adding a parameter, a test,
or a third caller to a rule without contradicting it; extending a fix to a side the earlier
review did not cover; an eng review replacing cells in a CEO review's failure-mode table, which
is eng working in its own domain. The test: could the earlier reviewer read your change and
say "that is not what I approved"?

**How to declare.** On your own completion entry, once per review that must run again:

```bash
"$BIN/review-log" --skill <your review> --status "$STATUS" \
  --rereview <the review you overtook> --rereview-note "<what you changed that it approved>"
```

or `--rereview none` when every answer is no. The four plan reviews must declare; ship-stage
reviews may. A demand names a gating review of the same stage that has a run on this plan,
never yourself and never `ship`; `review-log` refuses anything else, and the reader ignores a
hand-written one. Then add `· re-review demanded by /<your review>, <utc-date>: <note>` to the
demanded review's REVIEW REPORT row (`_shared/plan-footer.md`).

**How it clears.** The demanded review reads `stale` on the dashboard (`stale !`, with who
demanded it and why), blocks its stage, and is what `--next` names. Only that review running
again clears it: another review cannot vouch for it, `review-log --status resolved` is refused
for it, and re-running the declarer while saying `none` does not withdraw the demand. The
re-run may be scoped: a review that starts while it is `stale` reads the demand's note
(`stale_note`, and every demand in `stale_notes` when `stale_count` is more than one; a review
that is failed and also demanded carries the same list as `demanded_notes`), reviews
the named change and what it touches, and writes `scoped re-review of <what>` in its REVIEW
REPORT row. It runs the full review instead when the change touches the data model, an API or
CLI contract, or rollout and rollback, or when it cannot bound what the change touches. The
gate does not distinguish the two: any new run clears the demand, and the scoped run still
logs through the normal completion call with its own declaration.

One limit, accepted: "a new run" is decided by `ts` alone, so a run of the same review made
on another branch against the same plan file, and merged in later, clears a demand it never
saw. A plan is reviewed on one branch; when two branches did review one plan file, run that
review again after the merge.

```
                    logs clean / done
   missing ───────────────────────────────▶ passed ─────────(D)────────┐
      │                                      ▲   ▲                     ▼
      │ logs issues_open       re-run passes │   └── X re-runs, ──── stale
      ▼                                      │       logs clean        ▲ │
   failed ── review-log --status resolved ─▶ resolved ──────(D)────────┘ │
      ▲        resolved_by = another gating tier                         │
      └───────────────── X re-runs, logs issues_open ◀───────────────────┘

   (D)  a later run of another same-stage gating review declares rereview=[X]
        with a ts at or after X's last run (a tie fails closed)
   ok = passed | resolved · blocking = failed | stale · every transition is an appended log line
   stale ends only with a newer run of X; failed + demanded reads failed and resolving it yields stale
```

## Verdicts

A review's latest entry has one disposition: `missing` (never ran), `passed`, `failed` (ran
and did not pass), `resolved`, or `stale` (a later review declared it must run again; only its
own re-run clears it). **ok** is `passed` or `resolved`; **blocking** is `failed` or `stale`.
`office-hours` is shown on the dashboard but never gates.

- `CLEARED FOR IMPLEMENTATION`: eng review ok, design review ok when the plan has UI scope, and
  no plan-stage review (CEO, eng, adversarial, design) is `failed` or `stale`.
- `CLEARED TO SHIP`: implementation review and final review ok, and no review of any gating
  tier is `failed` or `stale`.
- `NOT CLEARED`: the missing items are listed; a failed one carries ` (issues open)`, a stale
  one ` (re-review demanded)`. Say which one you recommend doing first.
- `NOT CLEARED — review log unreadable`: the log holds a line that is not a JSON object,
  usually a merge-conflict marker. Resolve it by keeping both sides; every review command
  refuses until the log is whole.

A review counts only when it was logged against the current plan file. Superseding a plan resets
the dashboard, by design.
