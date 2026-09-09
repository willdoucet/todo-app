# Adversarial passes

Loaded by `plan-adversarial-review` at step 5. Run the framing first, then the seven passes in
order. The output of every pass is an edit to the plan or the test artifact, not a note.

## Framing, before any edit

Answer privately:

1. If I wanted this plan to fail in production, where would I attack first?
2. What assumption is doing the most work in this plan?
3. What would a tired engineer misunderstand at six on a Friday evening?
4. What breaks during a mixed-version deploy, a rollback, stale client state, or duplicate
   processing?
5. What part of this plan could pass review and still create user pain?

Assume the plan is smart and still wrong in a few expensive ways. You are looking for:

- assumptions that fail under real-world pressure
- contradictions between sections
- hidden coupling and mixed-version rollout traps
- happy-path specs with vague failure behavior
- silent failure modes
- places where two competent engineers would implement the same section differently
- tests that are missing even though the plan feels complete
- cheap ways this could still hurt users or operators

## Inherited coverage from eng review

Everything in the eng review's architecture and code-quality sections is minimum coverage.

Architecture, evaluated explicitly:

- overall system design and component boundaries
- dependency graph and coupling
- data flow patterns and potential bottlenecks
- scaling characteristics and single points of failure
- security architecture: auth, data access, API boundaries
- whether key flows deserve diagrams in the plan or in later code comments
- for each new codepath or integration point, one realistic production failure scenario and
  whether the plan accounts for it

Push past "is the design plausible?" to "how does this fail under pressure, mixed versions,
stale state, partial rollout, or operator error?"

Code quality, evaluated explicitly:

- code organization and module structure
- DRY violations, aggressively
- error handling patterns and missing edge cases
- technical debt hotspots
- over-engineering or under-engineering relative to the eng review's stated preferences
- whether existing diagrams in likely-touched files go stale, and whether the plan calls out
  their maintenance

Assume a rushed implementer takes the narrowest defensible path. Look for where weak
structure, repetition, vague error handling, or diagram drift makes the result brittle.

## Pass 1: Premise inversion

Take the three to five most important assumptions in the plan and invert each one.

| Stated | Inverted |
|---|---|
| The upstream system is reliable | It is flaky and slow |
| The data is present | It is partial, stale, or duplicated |
| Users follow the intended flow | They jump in midstream, double-submit, use two tabs |
| Rollout is atomic | Old and new code coexist for hours |
| The team will remember the follow-up cleanup | They will not |
| The feature flag defaults are right | The flag is flipped in the wrong environment |

For each inversion, decide whether the plan already handles it. If not, update the plan in the
smallest correct place. On an epic, the strongest inversion is "milestone N ships and N+1 never
does"; the plan must survive that.

## Pass 2: Hostile implementer

Read the plan as someone who wants to be done by five and will take the narrowest defensible
interpretation. Flag and fix:

- ambiguous nouns: `sync`, `ready`, `processed`, `status`, `cache`, `complete`, `done`,
  `valid`, `active`
- vague directives: "handle errors", "add validation", "make it robust", "clean up"
- missing ownership boundaries: which layer is responsible for which invariant
- intent described but behavior not: "the user should not lose work" without saying how
- a test implied but never stated

If two competent engineers could implement a section differently, it is underspecified. Write
the behavior down.

## Pass 3: Silent-failure hunt

For each major flow ask:

- how could this fail without an obvious crash?
- would the user see stale, partial, duplicated, or misleading state?
- would logs or metrics reveal it quickly, and to whom?
- would QA catch it before ship, given the test artifact as written?

Where the answer is no, add to the plan: explicit failure handling, explicit user-visible
behavior for the failure, explicit observability (what is logged, at what level, with what
correlation), and explicit tests.

## Pass 4: Rollout and reversal attack

Treat deploy and rollback as hostile environments. Check:

- mixed old and new code compatibility, in both directions
- schema transition safety: additive first, backfill, then constrain; never a single-step
  destructive change
- background jobs still holding old payloads, and jobs enqueued twice
- stale or cached clients, including a browser tab left open across the deploy
- replay and idempotency of every mutation that can be retried
- duplicate processing under at-least-once delivery
- a rollback story that is a sentence rather than a sequence
- reversibility that is poor with no feature flag in front of it

If rollback is vague, it is a gap. Add a concrete, ordered rollback sequence: what to flip,
what to revert, what data must be reconciled, and how you know it worked.

On an epic, do this per milestone boundary. For each seam write: what is live, what is
half-live, which milestone can be reverted alone, and which cannot be reverted once the next
one lands. A milestone that cannot be reverted alone needs a flag, a documented forward-fix
path, or a resequencing; pick one and write it into the epic.

## Pass 5: Test escape analysis

Assume a bug is trying to slip past the proposed tests. Look for:

- new branches with no direct test
- nil, empty, malformed, duplicate, stale, and retry paths with no test
- integration points covered only by unit tests
- user-visible regressions with no high-level test
- background work with no failure-path test
- concurrency and double-submit paths with no test
- migrations with no test against production-shaped data

Add the missing tests to the plan. When the eng-review test artifact exists, update it too, so
downstream implementation and QA use the hardened scope. Follow
`references/test-artifact-merge.md`.

## Pass 6: Trust boundary and abuse cases

Find the version of the feature that works for good users and fails under messy or adversarial
input. Check:

- authorization assumptions: who is assumed to have checked, and did anyone
- object scoping: can an id from one scope be used in another
- duplicate requests and replay
- malformed data at every boundary that accepts input
- race conditions between two legitimate actions
- privacy leaks in responses, logs, and error messages
- auditability of sensitive mutations

Add only the fixes that materially reduce risk. Stay minimal-diff.

## Pass 7: Future regret

Ask:

- what will the team hate maintaining in three months?
- what follow-up work is being silently assumed?
- what complexity was added for convenience rather than necessity?
- is there a simpler shape that achieves the same safety?

If the plan is overbuilt, recommend the smaller shape. If it is underbuilt, fill in the missing
operational and test detail. The bar for both is the same: two engineers reading it build the
same thing.

## Success bar

The review succeeded if the plan is now:

- harder to misimplement
- harder to break silently
- easier to test
- easier to roll back
- clearer off the happy path
- explicitly marked as adversarially reviewed, with the harness and model recorded
