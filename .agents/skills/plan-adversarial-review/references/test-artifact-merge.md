# Test artifact merge discipline

Loaded by `plan-adversarial-review` at step 9. The test artifact at `$TEST_ARTIFACT` is a
downstream execution contract consumed by execute-plan and QA. It is not scratch space.

## Discovery

Use `$TEST_ARTIFACT` from `ctx`. Read that exact path. Do not conclude the artifact is absent
because a search tool or the harness's file index returns nothing under the testing directory;
that directory is often ignored while a direct read still works.

## Editing

1. Read the existing artifact in full before editing anything.
2. Prefer surgical edits and an additive adversarial section over wholesale replacement.
3. When an expectation is stale, update only that expectation and keep the surrounding still-
   valid coverage.
4. When duplicate-looking sections exist, reconcile by content, not by heading:
   - preserve high-signal completion gates, numbered end-to-end flows, operational invariants,
     log-hygiene requirements, deployment guards, and critical paths
   - rewrite stale bullets in place so they match the adversarial decision
   - remove only content that is genuinely superseded, contradictory, or repeated with
     equal-or-better specificity elsewhere
5. Before deleting any block ask: "Is this invariant still valid even if one detail is stale?"
   If yes, migrate the invariant into the updated artifact instead of deleting it.
6. After editing, reread the whole artifact and verify:
   - no duplicate top-level artifact bodies remain
   - no stale expectation contradicts the reviewed plan
   - every removed critical gate is represented with equal or clearer specificity somewhere in
     the final artifact

## Never collapse a critical path

Never collapse a specific numbered critical path into a vague summary bullet unless the
numbered path is also preserved or replaced with an equally explicit flow. In particular, do not
remove completion gates of the form "milestone N is not done unless ...", credential-
verification invariants, or log-hygiene invariants merely because a nearby expectation changed.

## Scope

Keep the artifact focused on what a tester needs: affected pages and routes, key interactions,
edge cases, critical paths. Do not dump implementation details into it.

## Marking additions

Add one line under each adversarial addition naming this skill, `$HARNESS`, and the model, so
QA can tell which expectations came from the red-team pass:

```markdown
<!-- plan-adversarial-review · harness: <HARNESS> · model: <model> · <TIMESTAMP> -->
```
