# How great engineering managers think

Loaded by plan-eng-review in the Posture section. These are not additional checklist items.
They are the instincts experienced engineering leaders develop over years: the pattern
recognition that separates "reviewed the plan" from "caught the landmine". Apply them
throughout the review; cite one when it drives a recommendation.

1. **State diagnosis.** Teams exist in four states: falling behind, treading water, repaying
   debt, innovating. Each demands a different intervention. (Larson, *An Elegant Puzzle*)
2. **Blast radius instinct.** Evaluate every decision through "what is the worst case, and how
   many systems and people does it affect?"
3. **Boring by default.** A company gets roughly three innovation tokens; everything else
   should be proven technology. (McKinley, *Choose Boring Technology*)
4. **Incremental over revolutionary.** Strangler fig, not big bang. Canary, not global rollout.
   Refactor, not rewrite. (Fowler)
5. **Systems over heroes.** Design for tired humans at 3am, not your best engineer on their
   best day.
6. **Reversibility preference.** Feature flags, A/B tests, incremental rollouts. Make the cost
   of being wrong low.
7. **Failure is information.** Blameless postmortems, error budgets, chaos engineering.
   Incidents are learning opportunities, not blame events. (Allspaw; Google SRE)
8. **Org structure is architecture.** Conway's Law in practice. Design both intentionally.
   (Skelton and Pais, *Team Topologies*)
9. **DX is product quality.** Slow CI, bad local dev, and painful deploys produce worse
   software and higher attrition. Developer experience is a leading indicator.
10. **Essential versus accidental complexity.** Before adding anything: "Is this solving a
    real problem or one we created?" (Brooks, *No Silver Bullet*)
11. **Two-week smell test.** If a competent engineer cannot ship a small feature in two weeks,
    you have an onboarding problem disguised as architecture.
12. **Glue work awareness.** Recognize invisible coordination work. Value it, but do not let
    people get stuck doing only glue. (Reilly, *The Staff Engineer's Path*)
13. **Make the change easy, then make the easy change.** Refactor first, implement second.
    Never structural and behavioral changes in the same step. (Beck)
14. **Own your code in production.** No wall between development and operations: there are
    only engineers who write code and run it in production. (Majors)
15. **Error budgets over uptime targets.** An SLO of 99.9% is a 0.1% downtime budget to spend
    on shipping. Reliability is resource allocation. (Google SRE)

## Where each pattern bites

| When you are... | Think... |
|---|---|
| Evaluating architecture (Section 1) | Boring by default (3); blast radius (2); incremental (4); reversibility (6) |
| Reviewing new infrastructure or a new dependency | Is this spending an innovation token wisely? (3) |
| Assessing complexity (Step 0, Section 2) | Brooks's question (10); two-week smell test (11) |
| Reviewing tests (Section 3) | Systems over heroes (5); failure is information (7) |
| Reviewing rollout and failure modes | Reversibility (6); error budgets (15); own it in production (14) |
| Sequencing an epic's milestones | Make the change easy first (13); incremental (4); state diagnosis (1) |
| Noticing the plan needs three teams to agree | Org structure is architecture (8); glue work (12) |
| Seeing a slow suite or painful local setup in the way | DX is product quality (9) |
