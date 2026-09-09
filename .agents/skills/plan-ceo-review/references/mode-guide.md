# Mode guide

Loaded by plan-ceo-review at Step 0D. One block per mode: the posture, the 0D analysis to run
before recommending it, the additions it makes to the ten review sections, and the rules that
keep the review from drifting once the mode is chosen.

## Quick reference

| Mode | Posture | Default for | Step 0 parts | Section additions |
|---|---|---|---|---|
| SCOPE EXPANSION | Build the cathedral. Push scope up. | Greenfield features; "go big", "ambitious", "cathedral" (chosen without asking) | 0A to 0F | 1, 8, 9, 10; delight step runs |
| SELECTIVE EXPANSION | Hold the core; cherry-pick adjacencies one at a time | A sound core with a few tempting adjacencies | 0A to 0F, plus the candidate list | 1, 8, 9, 10 for accepted candidates; declined ones become TODOs |
| HOLD SCOPE | Rigorous reviewer. Scope accepted; make it bulletproof. | Bug fix, hotfix, refactor, epic children | 0A to 0F | none |
| SCOPE REDUCTION | Surgeon. The minimum that ships value; cut the rest. | More than 15 files touched, unless the user pushes back | 0A to 0D, 0F (skip 0E) | none |

Commit rule, every mode: once selected, execute it faithfully. Raise concerns once, in Step 0.
EXPANSION never argues for less work in a later section; REDUCTION never sneaks scope back in;
HOLD SCOPE neither reduces nor expands silently; SELECTIVE EXPANSION fixes the scope before
Section 1 and does not reopen it.

## SCOPE EXPANSION

Posture: you are building a cathedral. Envision the platonic ideal. The answer to "should we
also build X?" is "yes, if it serves the vision." You have permission to dream.

0D analysis, all three:

1. **10x check.** What is the version that is 10x more ambitious and delivers 10x more value
   for 2x the effort? Describe it concretely: what the user can do that they cannot today.
2. **Platonic ideal.** If the best engineer in the world had unlimited time and perfect taste,
   what would this system look like? What would the user feel using it? Start from the
   experience, not the architecture.
3. **Delight opportunities.** At least three adjacent improvements under thirty minutes each
   that make the feature sing; things a user notices and thinks "oh nice, they thought of
   that". These feed step 9 (delight), where each becomes its own question.

Section additions (raise them inside the section, not as a separate pass):

- Section 1: what would make this architecture beautiful, not just correct? Is there a design
  a new engineer in six months would call clever and obvious at the same time? What
  infrastructure would make this feature a platform other features build on?
- Section 8: what observability would make this feature a joy to operate?
- Section 9: what deploy infrastructure would make shipping this feature routine?
- Section 10: what comes after this ships, phase 2 and phase 3, and does the architecture
  support that trajectory? What capabilities does this create that other features can use?

Taste calibration (step 2 of the skill) is mandatory in this mode.

## SELECTIVE EXPANSION

Posture: the core is right. Hold it, then decide, one adjacency at a time, what else joins.
This is HOLD SCOPE with a controlled front door for expansion, not EXPANSION with brakes.

0D analysis:

1. Run the HOLD SCOPE analysis below (complexity check and minimum set) against the core.
2. Build the **expansion candidate list**: every adjacency the plan, the audit, the PRD, or
   TODOS.md suggests. One row per candidate:

```
  CANDIDATE                 | VALUE (1-5) | EFFORT (human / AI-assisted) | CHANGES ARCHITECTURE?
  --------------------------|-------------|------------------------------|----------------------
  Bulk edit from list view  | 4           | ~2 days / ~40 min            | no
  Undo for destructive ops  | 5           | ~3 days / ~1.5 hours         | yes: needs an event log
```

Cherry-pick rules:

- Ask about candidates one at a time, in descending value, before Section 1. Each is one
  question: A) add to this plan, B) defer to TODOS.md, C) drop.
- Candidates that change the architecture come first; an accepted one changes what Sections
  1 through 10 review.
- Accepted candidates are folded into the plan's scope and success criteria immediately, with
  a `CEO review 0: accepted expansion` breadcrumb.
- Declined candidates go through step 8 (TODOS) as vision items; dropped ones are listed under
  NOT in scope with the reason.
- After the last candidate, the scope is fixed. Do not reopen it in later sections.

Section additions: the same as EXPANSION for Sections 1, 8, 9, and 10, scoped to the accepted
candidates. The delight step (step 9) does not run; delight-class ideas belong on the
candidate list.

Taste calibration (step 2 of the skill) is mandatory in this mode.

## HOLD SCOPE

Posture: rigorous reviewer. The scope is accepted. Catch every failure mode, test every edge
case, ensure observability, map every error path. Do not silently reduce or expand.

0D analysis:

1. **Complexity check.** More than 8 files touched, or more than 2 new classes or services, is
   a smell. Challenge whether the same goal can be met with fewer moving parts. When it
   triggers, that is one question: say what looks overbuilt, propose the leaner shape, and ask
   whether to simplify or proceed. Once answered, commit.
2. **Minimum set.** What is the minimum set of changes that achieves the stated goal? Flag any
   work that could be deferred without blocking the core objective, as candidates for NOT in
   scope, never as silent cuts.

No section additions. Every section runs at full rigor.

Epic children default here: the epic already set the ambition, and the child's "Inherited
constraints" section is locked. Step 0 may challenge how the child meets a constraint, never
whether the constraint applies.

## SCOPE REDUCTION

Posture: surgeon. Find the minimum viable version that achieves the core outcome. Cut
everything else. Be ruthless.

0D analysis:

1. **Ruthless cut.** What is the absolute minimum that ships value to a user? Everything else
   is deferred. No exceptions.
2. **Follow-up split.** Separate "must ship together" (one is useless or unsafe without the
   other) from "nice to ship together" (convenient, not required). The second group becomes
   follow-up work with TODOS.md entries.

Present the minimal version as a concrete list of what stays and what goes, then review the
minimal version. Skip 0E (temporal interrogation); the cut list replaces it.

No section additions. Everything cut is written under NOT in scope with its rationale, or it
does not exist.
