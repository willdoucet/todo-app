"""workflow-state: banner, --next decision table, --dashboard, --history, --epics."""

from __future__ import annotations

import json

import _repo as R


def next_of(repo):
    return R.run_json(repo, "workflow-state", "--next", "--json")


def banner(repo) -> str:
    proc = R.run(repo, "workflow-state")
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


# ---------------------------------------------------------------- banner


def test_banner_on_base_without_epics(tmp_path):
    repo = R.make_repo(tmp_path)
    out = banner(repo)
    assert out.startswith("━━━ Workflow Status ━━━\nBranch:  main\n")
    assert "Plan:    none" in out
    assert "Stage:   IDLE — on base branch" in out
    assert "Next:    /office-hours — required" in out
    assert "Optional: /quickfix" in out
    assert "/name or $name" in out


def test_banner_json_is_sessionstart_envelope(tmp_path):
    repo = R.make_repo(tmp_path)
    proc = R.run(repo, "workflow-state", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    hook = payload["hookSpecificOutput"]
    assert hook["hookEventName"] == "SessionStart"
    assert hook["additionalContext"] == banner(repo).rstrip("\n")


def test_banner_is_fail_silent(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    for args in ([], ["--json"]):
        proc = R.run(outside, "workflow-state", *args, cwd=outside)
        assert proc.returncode == 0
        assert proc.stdout == ""
    repo = R.make_repo(tmp_path)
    (repo / ".agents/config.json").write_text("{not json")
    proc = R.run(repo, "workflow-state")
    assert (proc.returncode, proc.stdout) == (0, "")
    # explicit modes are NOT fail-silent
    proc = R.run(repo, "workflow-state", "--next", "--json")
    assert proc.returncode != 0
    assert json.loads(proc.stdout)["status"] == "error"


def test_banner_feature_branch_no_plan(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    out = banner(repo)
    assert "Branch:  feat/x" in out
    assert "Stage:   IDLE\n" in out
    d = next_of(repo)
    assert d["next"] == {"skill": "/office-hours", "args": None, "required": True, "reason": "no plan on this branch — draft one"}
    assert [o["skill"] for o in d["optional"]] == ["/quickfix"]


# ---------------------------------------------------------------- --next on a feature plan


def test_not_started_requires_eng_review_first(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "not-started"})
    d = next_of(repo)
    assert d["stage"] == "PLANNING"
    assert d["next"] == {"skill": "/plan-eng-review", "args": None, "required": True, "reason": "shipping gate"}
    assert [o["skill"] for o in d["optional"]] == ["/plan-ceo-review"]
    out = banner(repo)
    assert f"Plan:    {plan.name}" in out
    assert "Next:    /plan-eng-review — required (shipping gate)" in out
    assert "Reviews: OH —  CEO —  Eng —  Adv —  Design —  Impl —  AdvSub —  QA —  Audit —  Final —  Ship —" in out
    assert d["open"] == [] and d["unreadable"] == 0


def test_ui_scope_requires_design_review_after_eng(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"ui_scope": True})
    R.log_review(repo, plan, "plan-eng-review", "clean")
    assert next_of(repo)["next"]["skill"] == "/plan-design-review"
    R.log_review(repo, plan, "plan-design-review", "done")
    assert next_of(repo)["next"]["skill"] == "/execute-plan"


def test_execute_plan_with_optionals(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"risk_tags": ["auth", "infra"]})
    R.log_review(repo, plan, "plan-eng-review", "clean")
    d = next_of(repo)
    assert d["next"]["skill"] == "/execute-plan" and d["next"]["required"] is True
    assert d["optional"] == [
        {"skill": "/plan-adversarial-review", "reason": "risk tags: auth,infra"},
        {"skill": "/plan-ceo-review", "reason": "not yet run"},
    ]
    assert "Optional: /plan-adversarial-review — risk tags: auth,infra" in banner(repo)
    # legacy adversarial "issues_found" reads as passed (it meant "hardened"); legacy eng
    # "issues_found" reads as failed and blocks with the failed reason, never "not yet run".
    R.log_review(repo, plan, "plan-adversarial-review", "issues_found", ts="2026-09-03T10:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "done", ts="2026-09-03T10:00:00Z")
    assert next_of(repo)["optional"] == []
    R.log_review(repo, plan, "plan-eng-review", "issues_found", ts="2026-09-04T10:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-eng-review" and d["next"]["reason"].startswith("ran with issues open")
    assert "not yet run" not in json.dumps(d)


def test_reviews_are_scoped_to_this_plan_file(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    old = R.write_plan(repo, "feat/x", {}, ts="20260801-120000")
    R.log_review(repo, old, "plan-eng-review", "clean", ts="2020-01-01T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/execute-plan"  # old ts still counts: no age window
    R.write_plan(repo, "feat/x", {}, ts="20260901-120000")  # newer plan supersedes
    assert next_of(repo)["next"]["skill"] == "/plan-eng-review"


def test_implementing_shows_summary_progress(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "implementing"})
    R.write(repo, f".agents/plans/features/feat-x/{plan.stem}-summary.md", "- [✓] a\n- [x] b\n- [ ] c\n- [✗] d\n")
    d = next_of(repo)
    assert d["stage"] == "IMPLEMENTING (2/4 steps)"
    assert d["next"]["skill"] == "/execute-plan"


def test_ready_for_review_chain(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review", "ui_scope": "yes"})
    assert next_of(repo)["next"]["skill"] == "/review-implementation"
    R.log_review(repo, plan, "review-implementation", "clean")
    d = next_of(repo)
    assert d["stage"] == "READY FOR REVIEW"
    assert d["next"]["skill"] == "/final-review"
    assert [o["skill"] for o in d["optional"]] == ["/qa", "/design-review"]
    # legacy qa "issues_found" meant "not every issue fixed": it is failed, and blocks.
    R.log_review(repo, plan, "qa", "issues_found", ts="2026-09-03T10:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/qa" and d["next"]["reason"].startswith("ran with issues open") and d["optional"] == []
    dash = R.run_json(repo, "workflow-state", "--dashboard", "--json")
    assert "qa" in dash["missing_to_ship"] and dash["verdict"] != "CLEARED TO SHIP"
    R.log_review(repo, plan, "qa", "clean", ts="2026-09-03T11:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/final-review" and [o["skill"] for o in d["optional"]] == ["/design-review"]
    R.log_review(repo, plan, "final-review", "pass", ts="2026-09-03T12:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/ship"


def test_terminal_and_blocked_states(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    R.write_plan(repo, "feat/x", {"implementation_status": "shipped"})
    d = next_of(repo)
    assert d["stage"] == "SHIPPED" and d["next"]["skill"] is None and d["next"]["reason"] == "merge the PR"
    assert "Next:    merge the PR" in banner(repo)

    R.write_plan(repo, "feat/x", {"implementation_status": "abandoned"})
    d = next_of(repo)
    assert d["stage"] == "ABANDONED" and d["next"]["skill"] == "/office-hours"

    R.write_plan(repo, "feat/x", {"implementation_status": "blocked", "reason": "waiting on API key"})
    d = next_of(repo)
    assert d["stage"] == "BLOCKED"
    assert d["next"]["skill"] == "/execute-plan" and "waiting on API key" in d["next"]["reason"]

    R.write_plan(repo, "feat/x", {"implementation_status": "needs-context"})
    assert next_of(repo)["stage"] == "BLOCKED (needs-context)"


def test_status_falls_back_to_registry_entry(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    R.write_plan(repo, "feat/x", {})
    R.registry_put(repo, "plan:feat-x", {"implementation_status": "implementing", "branch": "feat/x"})
    assert next_of(repo)["stage"] == "IMPLEMENTING"


# ---------------------------------------------------------------- epics


def seed_epic(repo, slug="v1", milestones=None):
    epic_file = R.write_epic(repo, slug, {"title": "V1 launch"})
    R.registry_put(
        repo,
        f"epic:{slug}",
        {
            "kind": "epic",
            "title": "V1 launch",
            "milestones": milestones
            or [
                {"id": "M1", "title": "Auth", "size": "feature"},
                {"id": "M2", "title": "Logging", "size": "feature", "status": "subsumed"},
                {"id": "M3", "title": "Tidy", "size": "quickfix"},
                {"id": "M4", "title": "Launch", "size": "feature"},
            ],
        },
    )
    R.registry_put(repo, "plan:feat-m1", {"kind": "feature", "parent_epic": slug, "milestone": "M1", "implementation_status": "shipped", "branch": "feat/m1", "completed": "2026-09-01"})
    return epic_file


def test_epic_progress_derivation(tmp_path):
    repo = R.make_repo(tmp_path)
    seed_epic(repo)
    cfg = R.load_cfg(repo)
    ep = R._lib.epic_progress(repo, cfg, "v1")
    assert [m["status"] for m in ep["milestones"]] == ["shipped", "subsumed", "not-started", "not-started"]
    assert (ep["total"], ep["shipped"], ep["subsumed"], ep["in_progress"], ep["not_started"]) == (4, 1, 1, 0, 2)
    assert ep["next"]["id"] == "M3" and ep["next"]["size"] == "quickfix"
    assert ep["milestones"][0]["branch"] == "feat/m1" and ep["done"] is False
    # a child naming an unlisted milestone is appended; an unknown epic is empty, not an error
    R.registry_put(repo, "quickfix:extra", {"kind": "quickfix", "parent_epic": "v1", "milestone": "M9", "implementation_status": "implementing"})
    ep = R._lib.epic_progress(repo, cfg, "v1")
    assert ep["milestones"][-1]["id"] == "M9" and ep["in_progress"] == 1
    assert R._lib.epic_progress(repo, cfg, "nope")["total"] == 0


def test_epic_milestones_fallback_to_epic_frontmatter(tmp_path):
    repo = R.make_repo(tmp_path)
    R.write_epic(repo, "v2", {"title": "V2", "milestones": [{"id": "M1", "title": "One"}, "M2"]})
    ep = R._lib.epic_progress(repo, R.load_cfg(repo), "v2")
    assert [m["id"] for m in ep["milestones"]] == ["M1", "M2"]
    assert ep["title"] == "V2" and ep["next"]["id"] == "M1"


def test_milestone_plan_banner_epic_line(tmp_path):
    repo = R.make_repo(tmp_path)
    seed_epic(repo)
    R.checkout(repo, "feat/m3")
    R.write_plan(repo, "feat/m3", {"parent_epic": "v1", "milestone": "M3"})
    out = banner(repo)
    assert "Epic:    v1 — M3 of 4 (1 shipped, 1 subsumed)" in out
    d = next_of(repo)
    assert d["epic"]["index"] == 3 and d["epic"]["milestone"] == "M3" and d["epic"]["next"]["id"] == "M3"


def test_base_branch_suggests_next_milestone(tmp_path):
    repo = R.make_repo(tmp_path)
    epic_file = seed_epic(repo)
    d = next_of(repo)
    assert d["stage"] == "IDLE"
    assert d["next"]["skill"] == "/quickfix"  # M3 is a quickfix-sized milestone
    assert d["next"]["args"] == f".agents/plans/epics/v1/{epic_file.name}#M3"
    assert d["epic"]["slug"] == "v1"
    out = banner(repo)
    assert "Epic:    v1  2/4 done (1 shipped, 1 subsumed)  next: M3 (quickfix) Tidy" in out
    assert "Next:    /quickfix .agents/plans/epics/v1/" in out
    # once M3 ships, M4 (feature) → /office-hours
    R.registry_put(repo, "quickfix:tidy", {"kind": "quickfix", "parent_epic": "v1", "milestone": "M3", "implementation_status": "shipped"})
    d = next_of(repo)
    assert d["next"]["skill"] == "/office-hours" and d["next"]["args"].endswith("#M4")


def test_base_branch_milestone_in_progress_elsewhere(tmp_path):
    repo = R.make_repo(tmp_path)
    seed_epic(repo)
    R.registry_put(repo, "quickfix:tidy", {"kind": "quickfix", "parent_epic": "v1", "milestone": "M3", "implementation_status": "implementing", "branch": "fix/tidy"})
    d = next_of(repo)
    assert d["next"]["skill"] is None
    assert "M3 Tidy is implementing on branch fix/tidy" in d["next"]["reason"]


def test_base_branch_warns_about_stuck_entries(tmp_path):
    repo = R.make_repo(tmp_path)
    R.registry_put(repo, "plan:feat-a", {"implementation_status": "ready-for-review", "branch": "feat/a"})
    R.registry_put(repo, "plan:feat-b", {"implementation_status": "implementing", "branch": "feat/b"})
    R.registry_put(repo, "plan:feat-c", {"implementation_status": "shipped", "branch": "feat/c"})
    out = banner(repo)
    assert "Warn:    2 plan(s) stuck on other branches: feat/a (ready-for-review), feat/b (implementing)" in out


def test_epic_branch_stage(tmp_path):
    repo = R.make_repo(tmp_path)
    epic_file = seed_epic(repo)
    R.checkout(repo, "v1")  # the epic's own branch is named after its slug
    d = next_of(repo)
    assert d["stage"] == "EPIC"
    assert d["next"]["skill"] == "/plan-ceo-review" and d["next"]["required"] is True
    R.log_review(repo, epic_file, "plan-ceo-review", "done")
    d = next_of(repo)
    assert d["next"]["skill"] == "/quickfix" and d["next"]["args"].endswith("#M3")
    assert "Epic:    v1 — 4 milestones (1 shipped, 1 subsumed)" in banner(repo)
    # all done → complete
    for mid, key in (("M3", "quickfix:tidy"), ("M4", "plan:feat-m4")):
        R.registry_put(repo, key, {"parent_epic": "v1", "milestone": mid, "implementation_status": "shipped"})
    d = next_of(repo)
    assert d["stage"] == "EPIC (complete)" and d["next"]["skill"] is None


def test_epics_listing(tmp_path):
    repo = R.make_repo(tmp_path)
    assert R.run(repo, "workflow-state", "--epics").stdout.strip() == "(no epics)"
    seed_epic(repo)
    out = R.run(repo, "workflow-state", "--epics").stdout
    assert out.startswith("v1  2/4 done (1 shipped, 1 subsumed)  next: M3 (quickfix) Tidy")
    epics = R.run_json(repo, "workflow-state", "--epics", "--json")
    assert [e["slug"] for e in epics] == ["v1"] and epics[0]["next"]["id"] == "M3"


# ---------------------------------------------------------------- dashboard


def test_dashboard_verdicts(tmp_path):
    repo = R.make_repo(tmp_path)
    assert R.run(repo, "workflow-state", "--dashboard").stdout.strip() == "no plan on this branch"
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"ui_scope": True})
    d = R.run_json(repo, "workflow-state", "--dashboard", "--json")
    assert d["plan"] == plan.name and d["verdict"] == "NOT CLEARED"
    assert d["missing"] == ["plan-eng-review", "plan-design-review"]
    assert [r["label"] for r in d["rows"]] == ["Office hours", "CEO", "Eng", "Adversarial", "Design", "Impl review", "Adv subagent", "QA", "Design audit", "Final", "Ship"]
    assert d["unreadable"] == 0 and all(r["disposition"] == "missing" and r["gates"] is (r["skill"] != "office-hours") for r in d["rows"])
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Verdict: NOT CLEARED — missing: plan-eng-review, plan-design-review" in text

    R.log_review(repo, plan, "plan-eng-review", "clean", issues=0, notes="ok")
    R.log_review(repo, plan, "plan-design-review", "done")
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Eng          | clean ✓       | 2026-09-02 | issues=0,notes=ok" in text
    assert "Verdict: CLEARED FOR IMPLEMENTATION" in text
    assert "To ship: review-implementation, final-review" in text

    R.log_review(repo, plan, "review-implementation", "clean")
    R.log_review(repo, plan, "final-review", "issues_found")  # legacy word, never defined by final-review: failed
    d = R.run_json(repo, "workflow-state", "--dashboard", "--json")
    assert d["verdict"] == "CLEARED FOR IMPLEMENTATION" and d["missing_to_ship"] == ["final-review"]
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Final        | issues_found !" in text  # a 14-character legacy word fills the column exactly
    assert "To ship: final-review (issues open)" in text
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-05T00:00:00Z")
    assert "Verdict: CLEARED TO SHIP" in R.run(repo, "workflow-state", "--dashboard").stdout


# ---------------------------------------------------------------- history


def test_history(tmp_path):
    repo = R.make_repo(tmp_path)
    assert R.run(repo, "workflow-state", "--history").stdout.strip() == "(no completions recorded)"
    R.registry_put(repo, "plan:feat-a", {"kind": "feature", "title": "A", "implementation_status": "shipped", "completed": "2026-08-01", "branch": "feat/a", "plan": "feat-a-plan-1.md"})
    R.registry_put(repo, "plan:feat-m1", {"parent_epic": "v1", "milestone": "M1", "implementation_status": "shipped", "completed": "2026-09-01", "branch": "feat/m1", "plan": "m1.md"})
    R.registry_put(repo, "quickfix:typo", {"kind": "quickfix", "title": "Typo", "completed": "2026-08-15", "commit": "abc1234", "branch": "main"})
    R.registry_put(repo, "plan:feat-open", {"implementation_status": "implementing", "branch": "feat/open"})
    rows = R.run_json(repo, "workflow-state", "--history", "--json")
    assert [(r["date"], r["kind"], r["key"]) for r in rows] == [
        ("2026-09-01", "milestone", "plan:feat-m1"),
        ("2026-08-15", "quickfix", "quickfix:typo"),
        ("2026-08-01", "feature", "plan:feat-a"),
    ]
    assert rows[1]["ref"] == "abc1234" and rows[0]["ref"] == "m1.md"
    assert len(R.run_json(repo, "workflow-state", "--history", "2", "--json")) == 2
    text = R.run(repo, "workflow-state", "--history", "1").stdout
    assert text.startswith("2026-09-01  milestone  plan:feat-m1  [feat/m1]  m1.md")


# ---------------------------------------------------------------- the gate: failed reviews and resolutions


def dashboard_of(repo):
    return R.run_json(repo, "workflow-state", "--dashboard", "--json")


def test_m8_sequence_failed_ceo_blocks_until_resolved(tmp_path):
    """CEO issues_open (T0) → eng clean (T1 >= T0) → NOT CLEARED, next names CEO with the failed
    reason → resolved by eng → CLEARED FOR IMPLEMENTATION, next is /execute-plan."""
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "office-hours", "issues_open", ts="2026-09-11T23:22:30Z", concerns=6)
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-12T05:27:06Z", critical_gaps=5)
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-12T21:41:42Z")
    d = dashboard_of(repo)
    assert d["verdict"] == "NOT CLEARED" and d["missing"] == ["plan-ceo-review"] and d["missing_to_ship"][:1] == ["plan-ceo-review"]
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Verdict: NOT CLEARED — missing: plan-ceo-review (issues open)" in text
    assert "Office hours | issues_open   | 2026-09-11 | concerns=6" in text  # display only: no mark
    assert "CEO          | issues_open ! | 2026-09-12 | critical_gaps=5" in text
    n = next_of(repo)
    assert n["next"]["skill"] == "/plan-ceo-review" and n["next"]["required"] is True
    assert n["next"]["reason"] == (
        "ran with issues open: /plan-eng-review already passed after this failure; "
        "confirm each open item is closed and log resolved by plan-eng-review, or re-run this review"
    )
    assert "not yet run" not in json.dumps(n) and n["open"] == [] and n["optional"] == [] and n["unreadable"] == 0
    out = banner(repo)
    assert "Reviews: OH ·  CEO !  Eng ✓" in out and "Next:    /plan-ceo-review — required (ran with issues open" in out

    stored = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=item 2 break-glass entry; Failure modes note", "--field", "ts=2026-09-16T00:00:00Z")
    assert stored["resolves_ts"] == "2026-09-12T05:27:06Z"
    d = dashboard_of(repo)
    assert d["verdict"] == "CLEARED FOR IMPLEMENTATION" and d["missing"] == [] and d["missing_to_ship"] == ["review-implementation", "final-review"]
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "CEO          | resolved ✓    | 2026-09-16 | note=item 2 break-glass entry; Failure modes note,resolved_by=plan-eng-review,resolves_ts=2026-09-12T05:27:06Z" in text
    n = next_of(repo)
    assert n["next"]["skill"] == "/execute-plan" and n["open"] == [] and [o["skill"] for o in n["optional"]] == []
    assert "Reviews: OH ·  CEO ✓  Eng ✓" in banner(repo)
    # a re-run that fails again blocks again, and the older eng entry can no longer vouch
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-17T00:00:00Z")
    n = next_of(repo)
    assert n["next"]["skill"] == "/plan-ceo-review"
    assert n["next"]["reason"] == "ran with issues open: re-run it, or confirm each open item is closed and log resolved"
    assert dashboard_of(repo)["verdict"] == "NOT CLEARED"


def test_plan_stage_failure_does_not_block_other_plan_reviews(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"ui_scope": True, "risk_tags": ["auth"]})
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z")
    d = next_of(repo)
    assert d["next"] == {"skill": "/plan-eng-review", "args": None, "required": True, "reason": "shipping gate"}
    assert d["optional"] == []  # a failed CEO review is not "optional: not yet run"
    assert d["open"] == [{"skill": "plan-ceo-review", "invoke": "/plan-ceo-review", "reason": "ran with issues open: re-run it, or confirm each open item is closed and log resolved"}]
    assert "Open:    /plan-ceo-review — ran with issues open: re-run it" in banner(repo)
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-adversarial-review", "issues_open", ts="2026-09-03T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-design-review" and d["next"]["reason"] == "ui_scope is set"
    assert [o["skill"] for o in d["open"]] == ["plan-ceo-review", "plan-adversarial-review"] and d["optional"] == []
    R.log_review(repo, plan, "plan-design-review", "clean", ts="2026-09-04T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-ceo-review" and "/plan-eng-review already passed after this failure" in d["next"]["reason"]
    assert [o["skill"] for o in d["open"]] == ["plan-adversarial-review"]
    assert dashboard_of(repo)["missing"] == ["plan-ceo-review", "plan-adversarial-review"]


def test_failed_design_review_blocks_even_without_ui_scope(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "issues_open", ts="2026-09-03T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/plan-design-review"
    assert dashboard_of(repo)["verdict"] == "NOT CLEARED"  # --next and the verdict agree


def test_open_lines_while_implementing_and_none_when_shipped(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "implementing"})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-03T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/execute-plan" and d["next"]["reason"] == "continue implementation"
    assert [o["skill"] for o in d["open"]] == ["plan-ceo-review"]
    assert "Open:    /plan-ceo-review — " in banner(repo)
    for status in ("blocked", "needs-context"):
        R.write_plan(repo, "feat/x", {"implementation_status": status})
        d = next_of(repo)
        assert d["next"]["skill"] == "/execute-plan" and [o["skill"] for o in d["open"]] == ["plan-ceo-review"]
    for status in ("shipped", "abandoned"):
        R.write_plan(repo, "feat/x", {"implementation_status": status})
        d = next_of(repo)
        assert d["open"] == [] and "Open:" not in banner(repo)


def test_adversarial_subagent_gates_and_routes_to_review_implementation(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review"})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-01T00:00:00Z")
    # the same second: one skill step logs the subagent's failure and its own passing entry
    R.log_review(repo, plan, "adversarial-subagent", "issues_open", ts="2026-09-11T16:19:20Z", issues_found=4, tier="large")
    R.log_review(repo, plan, "review-implementation", "clean", ts="2026-09-11T16:19:20Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/review-implementation" and d["next"]["required"] is True
    assert d["next"]["reason"] == (
        "adversarial subagent ran with issues open: /review-implementation already passed after this failure; "
        "confirm each open item is closed and log resolved by review-implementation, or re-run this review"
    )
    assert d["open"] == []  # already the next step; not repeated
    assert "AdvSub !" in banner(repo)
    dash = dashboard_of(repo)
    assert dash["missing_to_ship"] == ["adversarial-subagent", "final-review"]
    assert "Adv subagent | issues_open ! | 2026-09-11 | issues_found=4,tier=large" in R.run(repo, "workflow-state", "--dashboard").stdout
    R.run_json(repo, "review-log", "--skill", "adversarial-subagent", "--status", "resolved", "--field", "resolved_by=review-implementation", "--field", "note=all four fixed in 7beceb3")
    d = next_of(repo)
    assert d["next"]["skill"] == "/final-review" and d["open"] == []
    assert "Adv subagent | resolved ✓    |" in R.run(repo, "workflow-state", "--dashboard").stdout
    assert "AdvSub ✓" in banner(repo)
    # without a later passing tier the reason is the plain re-run one
    (tmp_path / "two").mkdir()
    repo2 = R.make_repo(tmp_path / "two")
    R.checkout(repo2, "feat/x")
    plan2 = R.write_plan(repo2, "feat/x", {"implementation_status": "ready-for-review"})
    R.log_review(repo2, plan2, "review-implementation", "clean", ts="2026-09-11T16:19:19Z")
    R.log_review(repo2, plan2, "adversarial-subagent", "issues_open", ts="2026-09-11T16:19:20Z")
    assert next_of(repo2)["next"]["reason"] == "adversarial subagent ran with issues open: re-run /review-implementation, or confirm each finding is closed and log resolved"


def test_failure_after_final_review_stops_short_of_ship(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review", "ui_scope": True})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-08-01T00:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "clean", ts="2026-08-02T00:00:00Z")
    R.log_review(repo, plan, "review-implementation", "clean", ts="2026-09-01T00:00:00Z")
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-04T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/ship" and dashboard_of(repo)["verdict"] == "CLEARED TO SHIP"
    R.log_review(repo, plan, "design-review", "issues_open", ts="2026-09-05T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/design-review"
    # final review passed BEFORE the failure, so it cannot be offered as the resolver
    assert d["next"]["reason"] == "ran with issues open: re-run it, or confirm each open item is closed and log resolved"
    dash = dashboard_of(repo)
    assert dash["verdict"] == "CLEARED FOR IMPLEMENTATION" and dash["missing_to_ship"] == ["design-review"]
    assert "To ship: design-review (issues open)" in R.run(repo, "workflow-state", "--dashboard").stdout
    R.log_review(repo, plan, "design-review", "clean", ts="2026-09-06T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/ship" and dashboard_of(repo)["verdict"] == "CLEARED TO SHIP"


def test_ready_for_review_with_failed_implementation_review(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review"})
    R.log_review(repo, plan, "review-implementation", "issues_open", ts="2026-09-01T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/review-implementation" and d["next"]["reason"].startswith("ran with issues open")
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-02T00:00:00Z")
    d = next_of(repo)
    assert "/final-review already passed after this failure" in d["next"]["reason"]


def test_failed_reason_suggests_only_an_eligible_resolver(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review"})
    R.log_review(repo, plan, "review-implementation", "issues_open", ts="2026-09-01T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "clean", ts="2026-09-02T00:00:00Z")  # a plan review cannot resolve a code review
    assert next_of(repo)["next"]["reason"] == "ran with issues open: re-run it, or confirm each open item is closed and log resolved"
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-03T00:00:00Z")
    assert "/final-review already passed after this failure" in next_of(repo)["next"]["reason"]


def test_dashboard_shows_a_superseded_resolution_as_failed(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-05T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "resolved", ts="2026-09-03T00:00:00Z", resolved_by="operator", note="n", resolves_ts="2026-09-01T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/execute-plan"
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-02T00:00:00Z")  # union-merged in later
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-ceo-review" and dashboard_of(repo)["verdict"] == "NOT CLEARED"
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "CEO          | resolved !" in text and "superseded_by_failure=2026-09-02T00:00:00Z" in text


def test_epic_branch_failed_ceo_review_reason(tmp_path):
    repo = R.make_repo(tmp_path)
    epic_file = seed_epic(repo)
    R.checkout(repo, "v1")
    R.log_review(repo, epic_file, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z")
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-ceo-review" and d["next"]["reason"].startswith("ran with issues open")
    assert d["open"] == []
    R.log_review(repo, epic_file, "plan-ceo-review", "clean", ts="2026-09-02T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/quickfix"


def test_office_hours_row_is_display_only(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "office-hours", "issues_open", ts="2026-09-01T00:00:00Z", concerns=3)
    d = next_of(repo)
    assert d["next"]["skill"] == "/plan-eng-review" and d["open"] == []
    assert "Reviews: OH ·  CEO —" in banner(repo)
    dash = dashboard_of(repo)
    assert dash["missing"] == ["plan-eng-review"] and dash["missing_to_ship"] == ["review-implementation", "final-review"]
    row = next(r for r in dash["rows"] if r["skill"] == "office-hours")
    assert row["gates"] is False and row["disposition"] == "failed" and row["extra"] == {"concerns": 3}
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Office hours | issues_open   | 2026-09-01 | concerns=3" in text and "issues_open !" not in text.split("\n")[2]
    R.log_review(repo, plan, "office-hours", "clean", ts="2026-09-02T00:00:00Z")
    assert "Reviews: OH ·  CEO —" in banner(repo)  # never ✓ either


def test_summary_named_legacy_entries_attach_to_the_plan(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"implementation_status": "ready-for-review"})
    cfg = R.load_cfg(repo)
    summary = plan.stem + "-summary.md"
    R._lib.review_log_append(repo, cfg, {"skill": "adversarial-subagent", "status": "issues_found", "plan": summary, "ts": "2026-04-17T05:53:53Z"})
    R._lib.review_log_append(repo, cfg, {"skill": "review-implementation", "status": "clean", "plan": summary, "ts": "2026-04-17T05:53:53Z"})
    dash = dashboard_of(repo)
    rows = {r["skill"]: r for r in dash["rows"]}
    assert rows["review-implementation"]["disposition"] == "passed" and rows["adversarial-subagent"]["disposition"] == "failed"
    assert next_of(repo)["next"]["skill"] == "/review-implementation"


def test_unreadable_log_fails_closed_everywhere(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-03T00:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/execute-plan"
    path = R._lib.review_log_path(repo, R.load_cfg(repo))
    good = path.read_text()
    path.write_text(good + "<<<<<<< HEAD\n" + good)
    d = next_of(repo)
    assert d["next"]["skill"] is None and d["next"]["required"] is True and d["unreadable"] == 1
    assert d["next"]["reason"] == "review log has 1 unreadable line(s); resolve the conflict (keep both sides) before any review command"
    assert d["open"] == [] and d["optional"] == [] and "execute-plan" not in json.dumps(d["next"])
    text = R.run(repo, "workflow-state", "--next").stdout
    assert text.startswith("Warn:    1 unreadable review-log line(s)") and "Next:    review log has 1 unreadable" in text
    dash = dashboard_of(repo)
    assert dash["verdict"] == "NOT CLEARED — review log unreadable" and dash["unreadable"] == 1 and dash["missing"] == [] and dash["missing_to_ship"] == []
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert text.splitlines()[0] == "Warn: 1 unreadable review-log line(s)" and "Verdict: NOT CLEARED — review log unreadable" in text
    # the banner still prints, and its JSON envelope carries the warning
    out = banner(repo)
    assert out.splitlines()[1].startswith("Warn:    1 unreadable review-log line(s)")
    envelope = json.loads(R.run(repo, "workflow-state", "--json").stdout)
    assert "Warn:    1 unreadable" in envelope["hookSpecificOutput"]["additionalContext"]
    path.write_text(good)
    assert next_of(repo)["next"]["skill"] == "/execute-plan" and next_of(repo)["unreadable"] == 0
    # a trailing newline alone is not unreadable; a non-dict line is
    path.write_text(good.rstrip("\n") + "\n\n")
    assert next_of(repo)["unreadable"] == 0
    path.write_text(good + "1\n")
    assert next_of(repo)["unreadable"] == 1


def guard_program() -> str:
    """The python one-liner from execute-plan's grounding gate, exactly as the skill ships it."""
    text = (R.PAYLOAD / "skills" / "execute-plan" / "SKILL.md").read_text(encoding="utf-8")
    block = text[text.index("--next --json"):]
    program = block[block.index("python3 -c '") + len("python3 -c '"):]
    return program[: program.index("'\n")]


def _guard(next_json: dict) -> tuple[int, str]:
    import subprocess
    import sys as _sys
    proc = subprocess.run([_sys.executable, "-c", guard_program()], input=json.dumps(next_json), capture_output=True, text=True)
    return proc.returncode, proc.stdout


def test_execute_plan_guard_refuses_on_an_open_review(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z")
    rc, out = _guard(next_of(repo))
    assert (rc, out.strip()) == (0, "cleared for implementation")
    R.log_review(repo, plan, "plan-adversarial-review", "issues_open", ts="2026-09-03T00:00:00Z")
    rc, out = _guard(next_of(repo))
    assert rc == 1 and out.startswith("NOT CLEARED: /plan-adversarial-review — ran with issues open")
    # a reason that merely mentions execute-plan cannot pass the guard: it reads next.skill
    rc, out = _guard({"next": {"skill": "/plan-ceo-review", "reason": "then run /execute-plan"}, "unreadable": 0})
    assert rc == 1
    rc, out = _guard({"next": {"skill": None, "reason": "review log has 1 unreadable line(s)"}, "unreadable": 1})
    assert rc == 1 and "unreadable" in out
    rc, out = _guard({"next": {"skill": "/execute-plan", "reason": "continue implementation"}, "unreadable": 1})
    assert rc == 1
    # a missing unreadable key is not treated as 0 (plan: key present, integer)
    rc, out = _guard({"next": {"skill": "/execute-plan", "reason": "continue implementation"}})
    assert rc == 1
