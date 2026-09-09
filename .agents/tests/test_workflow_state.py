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
    assert "Reviews: CEO —  Eng —" in out


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
    # adversarial "issues_found" counts (fixes in place); eng "issues_found" does not.
    R.log_review(repo, plan, "plan-adversarial-review", "issues_found", ts="2026-09-03T10:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "done", ts="2026-09-03T10:00:00Z")
    assert next_of(repo)["optional"] == []
    R.log_review(repo, plan, "plan-eng-review", "issues_found", ts="2026-09-04T10:00:00Z")
    assert next_of(repo)["next"]["skill"] == "/plan-eng-review"


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
    R.log_review(repo, plan, "qa", "issues_found")
    assert [o["skill"] for o in next_of(repo)["optional"]] == ["/design-review"]
    R.log_review(repo, plan, "final-review", "pass")
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
    assert [r["label"] for r in d["rows"]] == ["CEO", "Eng", "Adversarial", "Design", "Impl review", "QA", "Design audit", "Final", "Ship"]
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Verdict: NOT CLEARED — missing: plan-eng-review, plan-design-review" in text

    R.log_review(repo, plan, "plan-eng-review", "clean", issues=0, notes="ok")
    R.log_review(repo, plan, "plan-design-review", "done")
    text = R.run(repo, "workflow-state", "--dashboard").stdout
    assert "Eng          | clean ✓       | 2026-09-02 | issues=0,notes=ok" in text
    assert "Verdict: CLEARED FOR IMPLEMENTATION" in text
    assert "To ship: review-implementation, final-review" in text

    R.log_review(repo, plan, "review-implementation", "clean")
    R.log_review(repo, plan, "final-review", "issues_found")
    assert R.run_json(repo, "workflow-state", "--dashboard", "--json")["verdict"] == "CLEARED FOR IMPLEMENTATION"
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
