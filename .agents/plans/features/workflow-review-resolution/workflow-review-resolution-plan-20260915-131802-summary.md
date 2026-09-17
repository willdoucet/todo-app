# Optional to run, not optional to resolve — one review-status vocabulary and a resolution gate — execution summary

- Plan: .agents/plans/features/workflow-review-resolution/workflow-review-resolution-plan-20260915-131802.md
- Branch: workflow-review-resolution
- Started: 20260915-211855
- Metadata: {"implementation_status": "implementing", "plan_kind": "feature", "plan_mode": "feature", "reason": "Eng review 2026-09-16 clean (FULL_REVIEW): OQ1-3 decided (accepted limitation = clean; reject legacy words; no operator flag); 1 critical gap closed in-plan (same-second resolver ts -> >=); 4 warnings folded (handoff logs at completion, tier invoke field, execute-plan --next guard, unreadable log lines fail closed); 1 TODO added (leaked M7 boto3 checksum finding).", "registry_key": "plan:workflow-review-resolution", "review_status": ["eng-reviewed", "adversarial-reviewed"], "risk_tags": ["infra", "security"], "ui_scope": false, "updated_at": "2026-09-16T04:17:12Z", "workflow_status": "implementing"}
- Test artifact: .agents/plans/testing/workflow-review-resolution-test-artifact.md
- Design source of truth: none (framework helpers and skill text; no UI)

## Steps
- [✓] Step 1 — `payload/bin/_lib.py`: vocabulary, legacy map, `review_disposition`, `REVIEW_TIERS` (dicts with `gates`/`invoke`), summary-name normalization, `review_log_read -> (entries, unreadable)` (plan §2) (2026-09-15 21:24)
- [✓] Step 2 — `payload/bin/review-log`: validate the merged entry; four words; `done` only for `ship`; the `resolved` rules; refuse on unreadable lines (§3) (2026-09-15 21:36)
- [✓] Step 3 — `payload/bin/review-read`: `disposition` in text and JSON; exit 2 on unreadable lines (§4) (2026-09-15 21:36)
- [✓] Step 4 — `payload/bin/workflow-state`: `gate_state`, Open list, failed reasons, verdicts, dashboard and banner marks, `unreadable` (§5) (2026-09-15 21:36)
- [✓] Step 5 — shared docs: `obsidian-sync.md` vocabulary table, `dashboard.md` procedure + verdicts + OPEN line, `plan-footer.md` mirroring + Adv subagent row, `WORKFLOW.md` pointer (§1, §6a, §7) (2026-09-15 21:36)
- [✓] Step 6 — skills: status wording, the §6a handoff (read at grounding, log at completion), `critical_gaps` split, subagent re-run/resolve line, ship sentences, execute-plan guard (§6, §6a–§6e) (2026-09-15 21:47)
- [✓] Step 7 — `bin/framework` `copy_payload`: the four review-gate helpers upgrade all-or-nothing (§11.2, Adversarial review) (2026-09-15 21:47)
- [✓] Step 8 — tests: `payload/tests/test_lib.py`, `test_review_log.py`, `test_workflow_state.py`, `tests/test_skill_lint.py`, `tests/test_cli.py` (§8, §9) (2026-09-15 21:49)
- [✓] Step 9 — release: `VERSION` 1.1.0, `CHANGELOG.md`, `README.md`; framework suite green (§10) (2026-09-15 21:49)
- [✓] Step 10 — PR-T: `framework upgrade` into this branch, `.gitattributes` merge=union, host suite, §11.5 audit, LESSONS check (§11) (2026-09-15 21:52)

Not boxes: plan §12 (the M8 resolution on `prod-launch-release`) runs after PR-T merges and is an
operator step on another branch; the framework commit and PR-F are outside `/ship`'s scope and
are decided in the assumptions below.

## Step notes

### Step 1 — `_lib.py` (2026-09-15 21:24)
- Files: `../framework/payload/bin/_lib.py` (branch `review-resolution`, cut from `main` 104b79b). The review-log section is rewritten: `REVIEW_STATUSES`, `REVIEW_TIERS` as dicts (`label`, `short`, `skill`, `invoke`, `gates`) with `office-hours` first (`gates=False`) and `adversarial-subagent` after `Impl review` (`invoke=/review-implementation`), `PLAN_STAGE_SKILLS`, `SHIP_GATE_SKILLS`, `tier_for`, `gating_tiers`, `LEGACY_STATUS_MAP`, `review_disposition`, `review_ok(entry)`, `review_plan_name` (summary-name normalization), `review_log_scan -> (entries, bad_line_numbers)`, `review_log_read -> (entries, unreadable)`, `unreadable_message`, and `reviews_for_plan` reading through the normalization. Two inline diagrams added (state machine above the legacy map; the read contract above `review_log_scan`).
- Decisions: `review_log_scan` is the one parser and returns 1-based line numbers so the CLIs can name them; `[0]` means the file itself failed to decode. `review_disposition` lowercases on read (belt and braces; no uppercase status exists in the log). `review_ok(entry)` is a convenience over the disposition so callers never compare words.
- Deviations: none.
- Verification: import and fixture run (19 disposition cases incl. `resolved` without `resolved_by`, missing status, uppercase; scan on blank lines, conflict marker, `1`, `[]`, `"x"`, bad UTF-8, trailing newline; summary-name attach with tie-break). Suite: 297 passed, 1 failed — `test_review_read_all_newest_first_with_plan_column`, because `review-read` still does `sorted(review_log_read(...))` on the new tuple; Step 3 fixes it.
- Test-artifact gap: none for this step.

### Steps 2–4 — `review-log`, `review-read`, `workflow-state` (2026-09-15 21:36)
- Files: `../framework/payload/bin/review-log` (rewritten: reserved `--field` keys `status`/`skill` rejected before the merge; validation on the merged entry; the four-word vocabulary, exact and lowercase; `done` for `ship` only; the `resolved` rules in plan §3 order with `>=` on the resolver's `ts`; `resolves_ts` filled from the failed entry; exit 2 on unreadable lines before anything else; validation-order diagram above the validator). `../framework/payload/bin/review-read` (rewritten: `disposition` column and key; exit 2 with `unreadable`/`lines` on a dirty log; docstring updated). `../framework/payload/bin/workflow-state` (rewritten in place: `OK_STATUSES`/`FIX_IN_PLACE`/`REVIEW_TIERS`/`review_ok` removed; `gate_state(reviews, fm, status, unreadable)` is the one source for `decide()`, `dashboard()`, and the banner; `failed_reason` with the "already passed" variant; Open lines (`Open:    <invoke> — <reason>`, aligned like `Next:`); `Warn:` line first in the banner and dashboard; `unreadable` in both JSON outputs; `gates=False` rows print no mark, banner `·`; decision-tree comment above `gate_state`; docstring updated).
- Decisions: a failed `plan-design-review` blocks at the plan stage even when `ui_scope` is false (otherwise `--next` said `/execute-plan` while the verdict said `NOT CLEARED`); `ship` is skipped when looking for a "later passed" resolver to suggest; `Open:` uses the banner's 4-space alignment.
- Deviations: none from the plan; the unreadable short-circuit applies before plan discovery (no plan, epic, or idle state escapes it), which the plan implies with "before any review command".
- Verification: fixture script over ~90 checks: critical paths 1 (M8 sequence), 2 (same-second subagent, and the strictly-earlier resolver rejected), 3 (QA inversion), 4 (failure after final), 7 and 13 (unreadable log: `review-log` and `review-read` exit 2 naming line 2, `--next.skill` null, verdict `NOT CLEARED — review log unreadable`, banner `Warn:` second line and carried in the `--json` envelope, recovery), the 28-case rejection matrix in both forms with the log byte-identical afterwards, `note` with `=`, operator and `ship done` accepted, summary-name attach, shipped plan prints no Open line, `implementing` prints one, plan-stage combinations, epic failed reason, optionals only when missing, legacy `issues_found` both ways. Suite: 292 passed, 6 failed — all six are the assertions plan §9 schedules for rewriting (`issues_found` in the CLI test, the review-read column, the `OH` tier in the banner, the QA chain, the row list); Step 8 rewrites them.
- Test-artifact gap: the artifact's key-interaction line for the subagent case expects the default reason ("re-run /review-implementation, or confirm…") while `review-implementation` is `clean` at the same second; plan §5 (adversarial addition) says the "already passed" variant applies then. The plan is the reviewed source, so the implementation follows it; the artifact line is corrected surgically in Step 8.

### Step 5 — shared docs (2026-09-15 21:36)
- Files: `payload/skills/_shared/obsidian-sync.md` (the vocabulary table replaces the old `STATUS` paragraph; header line `| Status | Meaning | Disposition | Written by |` is the lint's new shared signature), `payload/skills/_shared/dashboard.md` (`OPEN:` line in the template; the "When the next step names a review that ran with issues open" procedure with the state-machine diagram; Verdicts rewritten to §5 incl. the unreadable verdict), `payload/skills/_shared/plan-footer.md` (Status cell mirrors the logged word; a resolution adds to the row, never rewrites; `Adversarial subagent` placeholder row), `payload/WORKFLOW.md` (pointer beside the review-log paragraph).
- Deviations: none. Verification: anchors matched once each; lint run comes with Step 8.

### Step 6 — skills (2026-09-15 21:47)
- Files (all under `../framework/payload/skills/`): `qa/SKILL.md`, `design-review/SKILL.md` (status sentences: `clean` / `issues_open`, pointer to the shared definition, `deferred=N`); `plan-adversarial-review/SKILL.md` (provenance snippet reads `disposition`, unknown provenance on `resolved`; handoff after the provenance bullets; `--status "$STATUS"` with the `clean`/`issues_open` sentence; resolution at completion); `final-review/SKILL.md` (provenance snippet reads `disposition`; note on a resolved first review; resolution at completion); `ship/SKILL.md` (`CLEARED TO SHIP` means `missing_to_ship` is empty); `review-implementation/SKILL.md` (pointer; re-run-or-resolve the subagent with the exact `review-log` command); `office-hours/SKILL.md` (two lines replaced in place, still 499); `plan-ceo-review/SKILL.md`, `plan-eng-review/SKILL.md` (both gain `"$BIN/review-read"` at grounding with the handoff text; `critical_gaps_found` / `critical_gaps_open`; resolution at completion); `plan-design-review/SKILL.md` (handoff bullet in the system audit; resolution at completion); `execute-plan/SKILL.md` (the `--next --json` guard pinning `next.skill` and `unreadable`). References: `plan-ceo-review/references/output-templates.md` and `plan-eng-review/references/output-templates.md` name the two new fields.
- Decisions: the handoff paragraph is the same four lines in each plan review (the plan's §6a text); the shared *procedure* stays in `dashboard.md` and is referenced by its heading, never copied. The guard's python reads `next.skill` and `unreadable` from JSON, never a substring.
- Deviations: none. Line counts: 382 / 395 / 256 / 173 / 350 / 331 / 499 / 405 / 343 / 395 / 290, all under 500.
- Verification: `tests/test_skill_lint.py` (rewritten in Step 8) passes on the payload: vocabulary literals and sentences, `critical_gaps` field, handoff read-then-log order, `invoke` names, the execute-plan guard. The guard program itself is extracted from the skill text and executed in `test_execute_plan_guard_refuses_on_an_open_review`.

### Step 7 — `bin/framework` `copy_payload` (2026-09-15 21:47)
- Files: `../framework/bin/framework`: `classify_payload` (match / update / skip per file, before any write), `REVIEW_GATE_CLUSTER`, the all-or-nothing check raising `FrameworkError` (which `main()` prints as `error: …` and returns exit 1), diagram comment above the cluster constant.
- Verification: `tests/test_cli.py`: a mixed cluster is refused in both the dry run and the real run, none of the four files changes, the error names all four; `--force` updates all four; a consistent cluster updates while an unrelated local edit (`WORKFLOW.md`) is still skipped; a legacy review log survives `upgrade` byte-identical and reads with the new dispositions. 10 passed.

### Step 8 — tests (2026-09-15 21:49)
- Files: `payload/tests/test_lib.py` (+6 tests: vocabulary parity with the `obsidian-sync.md` table incl. the disposition column; 27 disposition cases; tier shape and order; summary-name rule; the scan contract — trailing newline, blank lines, conflict markers, `1`/`[]`/`"x"`, bad UTF-8, messages; attach + unreadable ignored by `reviews_for_plan`). `payload/tests/test_review_log.py` (rewritten: the three scheduled updates plus unknown words in both forms, `done` for ship only, `--field` cannot set `status`/`skill`, accepted resolutions with `resolves_ts`, same-second accepted / earlier rejected, operator, `note` with `=`, a 16-row rejection matrix run in both forms with the log byte-identical, non-gating targets, a resolver that failed, no plan, unreadable log for both CLIs, disposition columns, legacy attach). `payload/tests/test_workflow_state.py` (the three scheduled updates plus the M8 sequence, plan-stage combinations, failed design without `ui_scope`, Open lines by status, the subagent tier both variants, failure after final, failed implementation review, epic reason, display-only row, summary attach, unreadable log in every output, and the execute-plan guard program extracted from the skill text). `tests/test_skill_lint.py` (rewritten: `status_word_violations`, `critical_gaps_field_violations`, `handoff_violations` on whitespace-collapsed text, `SHARED_SIGNATURES` += the table header and the procedure's signature sentence, `invoke` names exist, the execute-plan guard; fixture tests for each). `tests/test_cli.py` (+3: legacy log byte-identical across `upgrade`; mixed cluster refused in dry run and real run; consistent cluster updates while another local edit still skips).
- Decisions: fixtures give explicit `ts` values throughout, because `review-log` stamps a real "now" and a fake earlier `ts` on a later entry would lose the latest-per-skill tie; the M8 sequence test passes `--field ts=` for the resolution for the same reason. The lint's handoff check collapses whitespace so a wrapped heading still matches.
- Verification: `python3 -m pytest tests payload/tests -q` → 401 passed (was 298 + 6 failures at Step 4).
- Test-artifact gaps: none beyond the subagent-reason reconciliation recorded under Steps 2–4 (artifact line corrected with a dated note).

### Step 9 — release (2026-09-15 21:49)
- Files: `VERSION` → `1.1.0`; `CHANGELOG.md` (`## Unreleased` folded into `## 1.1.0 — 2026-09-16` with the feature bullets, the zsh fix, and the upgrade note incl. the four-helper cluster and `merge=union`); `README.md` (dashboard example gains the `Office hours` and failed `CEO` rows; Verdict row rewritten to §5 incl. the unreadable verdict; `review-log` section documents the four words, the `resolved` form and its rules, the reserved `--field` keys; `review-read` section documents the disposition column and exit 2).
- Verification: `framework version` prints `1.1.0`; suite re-run after the doc edits → 401 passed.

### Step 10 — PR-T: upgrade into this branch (2026-09-15 21:52)
- Sequence (plan §11): 11.1 the branch was fast-forwarded to `origin/master` (f9564ef) before this run; 11.2 `framework upgrade <absolute worktree path> --dry-run` listed exactly this change's 24 payload files and no "modified locally" warning, then applied (the dry run's first header line named the main checkout once because the harness reset the shell's cwd between commands; every run with the absolute path, and the apply, targeted this worktree); 11.3 `.gitattributes` = `.agents/state/review-log.jsonl merge=union`, `git check-attr` confirms `merge: union`; 11.4 `python3 -m pytest .agents/tests -q` → 369 passed; 11.5 audit over every registry entry not shipped/abandoned/subsumed: `epic:v1-productionization` (no failed review) and `plan:workflow-review-resolution` (only `office-hours`, which never gates) — `plan:prod-launch-release` is not in this worktree's registry (its entry is uncommitted in the main checkout), so its failed CEO review is handled by §12 on that branch as planned; 11.6 LESSONS already carries the Decisions rows (office-hours 2026-09-15, eng review 2026-09-16, adversarial 2026-09-15) and the Corrections row, nothing added; 11.7 is `/ship`'s.
- Files in this repo: `.agents/**` (upgrade output only: 24 payload files, `manifest.json`, `config.json` `framework_version` 1.1.0), `.gitattributes` (new).
- Verification: `framework doctor --skip-tests` reports no modified payload file; its one FAIL (`core.hooksPath` is the absolute path, expected `.agents/hooks`) and two warnings (vault dir not in the worktree; this plan implementing) are pre-existing environment state, unrelated to this change. `git diff master -- .agents/state/review-log.jsonl`: 3 added lines, 0 removed (SC10). `workflow-state --dashboard` on this branch with the 1.1.0 helpers: `Office hours | issues_open` with no mark, `Adversarial | issues_found ✓` (legacy map), `CLEARED FOR IMPLEMENTATION`; `--next` names `/execute-plan` (`IMPLEMENTING (9/10 steps)` at that moment).
- Not in this run: plan §12 (the M8 resolution on `prod-launch-release`), which waits for PR-T to merge; PR-F is open at https://github.com/willdoucet/framework/pull/3 (commit 9e57152).

## Doc impact

- No mapped code area changed: every path under `.agents/**` is doc-map exempt, and the only
  file outside it, `.gitattributes`, is git configuration with no documented surface. Per
  `_shared/docs-contract.md`, nothing in PRD, APP_FLOW, TECH_STACK, FRONTEND_*, BACKEND_STRUCTURE,
  development-commands, or REVIEW_CHECKLIST describes the review helpers' status words; the
  framework's own `WORKFLOW.md`, README and CHANGELOG carry them and were updated in PR-F.
- `LESSONS.md`: the Decisions rows from office-hours, eng review, and adversarial review were
  already present; execute-plan added one test-isolation gotcha (fixture `ts` ordering).
- `TODOS.md`: the leaked M7 checksum finding was added by the eng review; nothing from execution.
- `IMPLEMENTATION_PLAN.md`: framework tooling has no roadmap row and none is added.

## Update-docs conclusion

```
DOC SYNC REPORT — default — workflow-review-resolution vs master — 2026-09-16

| Doc | Section | Action | Summary |
|---|---|---|---|
| AGENTS.md | Development Commands | no change | helper names under `.agents/bin/` and the host-side pointer are unchanged |
| development-commands.md | Framework Helper Tests | no change | `python3 -m pytest .agents/tests -q` still the command; no helper added or renamed |
| IMPLEMENTATION_PLAN.md | Phase 2 | no change | workflow tooling has no roadmap row; none added |
| LESSONS.md | Test isolation gotchas / Decisions | no change | rows from the reviews and execute-plan step 9 already present; nothing to reconcile |
| config.json | doc_map | asked (declined) | `.gitattributes` is unmapped; exempting it beside `.gitignore` was declined, file left as is |

Guard: doc-guard --staged --dry-run -> staged changes touch no documented areas
Questions: 1 asked, 0 applied, 1 declined
Unmapped: .gitattributes (root file; the guard prints no directory note for it)

DOC IMPACT: none - framework upgrade to 1.1.0; .agents is doc-map exempt and .gitattributes is git config
```

Status of the sync: DONE_WITH_CONCERNS (one declined question; `.gitattributes` stays unmapped). Base ref note: the local `master` ref is at 651ff27 while `origin/master` is f9564ef, so the local diff also lists the already-merged design-sync files from PRs #50–#52; all are `.agents/**` and exempt, so the verdict is unaffected. The pull request diffs against `origin/master`.

Ship-time run (`/ship` step 4, 2026-09-16). Differs from the run above: the declined
`.gitattributes` question was resolved on 2026-09-16 (exempted in `.agents/config.json`), so
nothing is unmapped and no question was asked.

```
DOC SYNC REPORT — default — workflow-review-resolution vs master — 2026-09-16

| Doc | Section | Action | Summary |
|---|---|---|---|
| AGENTS.md | Development Commands | no change | helper names under `.agents/bin/` and the host-side pointer are unchanged |
| development-commands.md | Framework Helper Tests | no change | `python3 -m pytest .agents/tests -q` is still the command; no helper added, removed or renamed |
| IMPLEMENTATION_PLAN.md | roadmap | no change | workflow tooling has no roadmap row; none added |
| LESSONS.md | Bug Log / Decisions / Test isolation gotchas | no change | rows from the reviews and execute-plan already present; nothing to reconcile |
| REVIEW_CHECKLIST.md | Framework helpers (Python CLIs) | no change | section added by /review-implementation already matches the helpers |
| TODOS.md | open items | no change | boto3 checksum item added by the eng review; nothing from ship |
| config.json | doc_map | no change | all 37 changed paths resolve to exempt (`.agents/**`, `.gitattributes`) |

Guard: doc-guard --staged --dry-run -> staged changes touch no documented areas
Questions: 0 asked, 0 applied, 0 declined
Unmapped: none

DOC IMPACT: none - framework upgrade to 1.1.0; .agents is doc-map exempt and .gitattributes is git config
```

## Completion

- Completed: 2026-09-16 02:04
- STATUS: DONE_WITH_CONCERNS

**What was built.** Framework 1.1.0 on `../framework` branch `review-resolution` (commit 9e57152, PR-F https://github.com/willdoucet/framework/pull/3): one review-status vocabulary (`clean`, `issues_open`, `resolved`, `done`) held in `_lib.REVIEW_STATUSES` and defined once in `_shared/obsidian-sync.md`; `review-log` validates the merged entry, accepts `done` from `ship` only, applies the `resolved` rules with `>=` on the resolver's timestamp, and refuses on an unreadable log; `review-read` shows dispositions; `workflow-state` gates from one `gate_state` (Open lines, failed reasons naming a later passed review, verdicts, `Office hours` display-only and `Adv subagent` gating rows, `Warn:` + `NOT CLEARED — review log unreadable` with `next.skill` null); legacy entries read through a compatibility map and summary-named entries attach to their plan; skills read earlier reviews at grounding and log resolutions at completion, `critical_gaps` is split, `execute-plan` refuses unless `--next --json` names it; `framework upgrade` moves the four review-gate helpers all-or-nothing; the skill lint enforces all of it. PR-T on this branch: the `framework upgrade` output (24 payload files, `manifest.json`, `config.json` `framework_version` 1.1.0) plus `.gitattributes` (`merge=union` for the review log).

**Test results.**
- Framework: `python3 -m pytest tests payload/tests -q` → 401 passed (last run after the release edits).
- todo-app host suite after the upgrade: `python3 -m pytest .agents/tests -q` → 369 passed.
- `doc-guard --worktree` → exit 0, no documented areas changed; `doc-guard --staged --dry-run` → staged changes touch no documented areas.
- Docker backend, frontend, and visual suites: not run. No file under `backend/` or `frontend/` changed; development-commands.md names the host-side helper suite for `.agents/` changes. Stated in the assumptions and not corrected.

**Test-artifact gaps.** One: the artifact's subagent key-interaction line expected the plain "re-run" reason while `review-implementation` was `clean` in the same second; plan §5 (adversarial addition) specifies the "already passed" variant there. The implementation follows the plan and the artifact line was corrected with a dated note. Both variants are tested.

**Deviations from the plan.** None in behavior. Choices the plan left open: `Open:` lines use the banner's `Next:` alignment (`Open:    …`); the unreadable-log short-circuit applies before plan discovery as well; a failed `plan-design-review` blocks at the plan stage even without `ui_scope` so `--next` and the verdict agree; the 14-character Status column is kept, so a 14-character legacy word (`issues_found !`) abuts the pipe.

**Concerns.**
1. PR-F is open, not merged. PR-T's upgrade was taken from the local `review-resolution` branch (identical bytes to what `main` will hold after a squash merge); if PR-F changes in review, re-run `framework upgrade` here before `/ship`.
2. `.gitattributes` stays unmapped in the doc map (exemption question declined); the guard does not block on it.
3. Plan §12 (the M8 CEO resolution on `prod-launch-release`) is an operator step after PR-T merges; not part of this run.
4. `framework doctor` reports a pre-existing `core.hooksPath` FAIL (absolute path in this repo's git config) and a missing vault directory in the worktree; neither is caused or fixed by this plan.

**Concerns addressed (2026-09-16, after execution, before `/review-implementation`).**
1. PR-F: head is now 230fde3 (adds the `.gitattributes` exemption to `config.example.json` and a clause in the upgrade note; framework suite 401 passed). `framework upgrade` re-run against this worktree by absolute path: only `config.example.json` changed, and a `--dry-run` afterwards lists nothing. PR-F is still open; merging is the operator's step. If it changes again, re-run the upgrade here before `/ship`.
2. `.gitattributes`: exempted in `.agents/config.json` beside `.gitignore` (`doc-guard --explain .gitattributes` → exempt) and in the framework's `config.example.json` so new projects carry it.
3. Plan §12: unchanged; still the operator step on `prod-launch-release` after PR-T merges.
4. Environment: `core.hooksPath` set to the relative `.agents/hooks` (`git rev-parse --git-path hooks` resolves per worktree; `git hook run commit-msg` exits 0 here). The vault is a relative symlink `todo-app-notes -> ../../../todo-app-notes` in this worktree, kept out of `git status` by a `todo-app-notes` line in the shared `.git/info/exclude`. `framework doctor --skip-tests` → 0 failures, 1 warning (this plan ready-for-review). Local `master` fast-forwarded to `origin/master` (f9564ef); the diff against `master` no longer lists the design-sync files.
- Re-verified afterwards: host suite 369 passed; `doc-guard --worktree` and `--staged --dry-run` clean; 35 files vs `master` in the index; `workflow-state --next` → `/review-implementation`.
- Gotcha hit once: one `framework upgrade "$PWD"` call ran against the main checkout because the harness reset the shell's cwd between commands. The 27 files it touched there were restored from HEAD with `git checkout --`, leaving that checkout's pre-existing edits intact. Pass the worktree's literal absolute path and check the tool's header line.

## Review-implementation (2026-09-16)

- Log: `adversarial-subagent issues_open` (large, 19) → `review-implementation clean` → `adversarial-subagent resolved` by review-implementation. Framework fixes: commit 0cda9ef on `review-resolution` (PR-F #3); this worktree re-upgraded (12 payload files, manifest); host suite 391 passed; framework suite 423 passed; doc-guard staged and worktree clean; doctor 0 failures.
- Structured pass, 4 findings, all fixed: (S1) a note carrying U+2028/U+2029/U+0085 split the record on read and locked every review command — `review_log_line` escapes them; (S2) a supplied `ts` was unvalidated — `review-log` requires UTC `YYYY-MM-DDTHH:MM:SSZ`, not later than now, and every comparison goes through `review_ts`; (S3) `plan-adversarial-review`'s handoff claimed the piped eng-only snippet listed every review — a plain `review-read` call added; (S4) this plan's REVIEW REPORT lacked the 1.1.0 `Adversarial subagent` row — added.
- Adversarial subagent, 19 findings: 1–2 = S1–S2. Fixed in 0cda9ef: 4 future `ts` refused; 5 `ts` stamped in `build_entry` so the ordering rule always runs; 6 a resolution clears only the failure it names (`superseded_by_failure`), hand-edited `resolved_by` reads failed; 8 `can_resolve` stage rule, `ship` never resolves, `failed_reason` suggests only eligible resolvers; 9 `ship` logs `done` only; 10 unknown `skill` refused; 11 `disposition`/`resolves_ts` refused; 12 `--plan <x>-summary.md` normalized; 13 subagent `resolved` snippet moved after the own entry; 14 `office-hours` `--status "$STATUS"`; 15 text rows JSON-quote values with `|`, `,`, newline; 16 exit-2 docstring. Decided, no change: 3 fail-silent banner (plan Failure modes; LESSONS Decisions 2026-09-15: fail-silent is reserved for unexpected crashes, and the crash it reproduced is now refused on write); 7 final-review's subagent logs under the same tier (plan Demand Evidence treats final-review as its resolver; the later-passed rule routes it there; a clean final-stage pass is a re-run of the same tier on the same diff); 19 a resume past `Open:` lines is plan §5 by design. Recorded: 17 the `.gitattributes` exemption was the user's 2026-09-16 decision (Concerns addressed above) and this review's sync refreshes the registry reason; 18 the payload now matches framework 0cda9ef — re-run `framework upgrade` here if PR-F changes again before `/ship`.
- New reviewer checks: `REVIEW_CHECKLIST.md` → Framework helpers (Python CLIs), offered back as the framework template `templates/checklists/framework-helpers.md`.
- Coverage: every changed code path has a test; gap tests written in the framework payload (`test_lib.py`, `test_review_log.py`, `test_workflow_state.py`) and upgraded here.
