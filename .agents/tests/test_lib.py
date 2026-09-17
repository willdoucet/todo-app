"""Unit tests for the shared library (_lib.py)."""

from __future__ import annotations

import json

import pytest

import _repo as R

_lib = R._lib


# ---------------------------------------------------------------- config and paths


def test_load_config_validates(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    assert cfg["project_name"] == "t"
    bad = R.load_cfg(repo)
    bad["doc_guard_mode"] = "nope"
    R.save_cfg(repo, bad)
    with pytest.raises(_lib.FrameworkError):
        _lib.load_config(repo)
    bad["doc_guard_mode"] = "strict"
    bad["schema_version"] = 99
    R.save_cfg(repo, bad)
    with pytest.raises(_lib.FrameworkError) as exc:
        _lib.load_config(repo)
    assert "upgrade" in exc.value.message


def test_vault_and_repo_relpaths(tmp_path):
    repo = R.make_repo(tmp_path, vault_path="My Notes")
    cfg = _lib.load_config(repo)
    note = repo / "My Notes" / "Ideas" / "Todo.md"
    note.parent.mkdir(parents=True)
    note.write_text("- [ ] x\n")
    assert _lib.vault_relpath(repo, cfg, note) == "Ideas/Todo.md"
    assert _lib.repo_relpath(repo, note) == "My Notes/Ideas/Todo.md"
    assert _lib.resolve_note_path(repo, cfg, "Ideas/Todo.md") == note.resolve()
    assert _lib.resolve_note_path(repo, cfg, "My Notes/Ideas/Todo.md") == note.resolve()
    with pytest.raises(_lib.FrameworkError):
        _lib.vault_relpath(repo, cfg, repo / "README.md")
    with pytest.raises(_lib.FrameworkError):
        _lib.resolve_note_path(repo, cfg, "Nope.md")


def test_absolute_vault_path_outside_repo(tmp_path):
    vault = tmp_path / "elsewhere"
    vault.mkdir()
    repo = R.make_repo(tmp_path, vault_path=str(vault))
    cfg = _lib.load_config(repo)
    assert _lib.vault_dir(repo, cfg) == vault


# ---------------------------------------------------------------- git


def test_branch_helpers(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    assert _lib.current_branch(repo) == "main"
    assert _lib.on_base_branch(repo, cfg)
    R.checkout(repo, "feat/one")
    assert _lib.safe_branch("feat/one") == "feat-one"
    assert not _lib.on_base_branch(repo, cfg)
    assert _lib.head_sha(repo)


# ---------------------------------------------------------------- globs and doc map


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("backend/app/routes/items.py", "backend/app/routes/**", True),
        ("backend/app/routes/v2/items.py", "backend/app/routes/**", True),
        ("backend/app/routes.py", "backend/app/routes/**", False),
        ("frontend/src/App.jsx", "frontend/src/App.*", True),
        ("a/b/c/test_x.py", "**/test_*.py", True),
        ("test_x.py", "**/test_*.py", True),
        ("uv.lock", "**/*.lock", True),
        ("backend/uv.lock", "**/uv.lock", True),
        ("src/x.js", "*.js", False),
    ],
)
def test_glob_match(path, pattern, expected):
    assert _lib.glob_match(path, [pattern]) is expected


def test_doc_owners_and_exempt(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    owners = _lib.doc_owners(cfg, "backend/app/routes/items.py")
    assert [(o["doc"], o["section"]) for o in owners] == [("BACKEND_STRUCTURE.md", "API Endpoints")]
    assert _lib.doc_owners(cfg, "backend/tests/test_items.py") == []
    assert _lib.doc_owners(cfg, "unmapped/thing.txt") == []
    assert _lib.doc_rel(cfg, "PRD.md") == ".agents/docs/PRD.md"


# ---------------------------------------------------------------- plans


def test_plan_discovery_by_filename_timestamp(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    old = R.write_plan(repo, "feat/x", {"plan_kind": "feature"}, ts="20260101-000000")
    new = R.write_plan(repo, "feat/x", {"plan_kind": "feature"}, ts="20260301-000000")
    # touch the old one so mtime would mislead
    old.write_text(old.read_text() + "\n")
    summary = _lib.summary_path_for(new)
    summary.write_text("# summary\n")
    assert _lib.latest_plan(repo, cfg, "feat/x") == new
    assert summary not in _lib.find_plan_files(new.parent)
    assert _lib.is_summary(summary) and not _lib.is_summary(new)
    assert _lib.plan_timestamp(new) == "20260301-000000"
    assert _lib.test_artifact_path(repo, cfg, "feat/x").name == "feat-x-test-artifact.md"


def test_epic_discovery(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    e = R.write_epic(repo, "v1", {"milestones": [{"id": "M1", "title": "one"}]})
    assert _lib.latest_epic(repo, cfg, "v1") == e
    assert [p.name for p in _lib.all_epics(repo, cfg)] == [e.name]
    assert _lib.epic_slug_from_path(e) == "v1"


# ---------------------------------------------------------------- frontmatter


def test_frontmatter_roundtrip_and_types(tmp_path):
    repo = R.make_repo(tmp_path)
    plan = R.write_plan(repo, "feat/x", {"plan_kind": "feature", "ui_scope": True, "task_count": 3, "risk_tags": ["auth", "data"], "note": 'say "hi"'}, body="# Body\n\ntext\n")
    meta = _lib.read_frontmatter(plan)
    assert meta["ui_scope"] is True and meta["task_count"] == 3 and meta["risk_tags"] == ["auth", "data"] and meta["note"] == 'say "hi"'
    assert _lib.truthy(meta["ui_scope"]) and _lib.truthy("true") and not _lib.truthy("false") and not _lib.truthy(None)
    _lib.update_frontmatter(plan, {"workflow_status": "eng-reviewed"}, {"review_status": ["eng-reviewed"]})
    _lib.update_frontmatter(plan, {}, {"review_status": ["eng-reviewed", "ceo-reviewed"]})
    meta = _lib.read_frontmatter(plan)
    assert meta["review_status"] == ["eng-reviewed", "ceo-reviewed"]
    assert "updated_at" in meta
    text = plan.read_text()
    assert text.endswith("# Body\n\ntext\n")
    # key order follows FRONTMATTER_ORDER, unknown keys sorted after
    keys = [l.split(":")[0] for l in text.split("---")[1].strip().splitlines()]
    assert keys.index("plan_kind") < keys.index("workflow_status") < keys.index("updated_at")
    assert keys[-1] in ("updated_at", "note") or keys.index("note") > keys.index("updated_at")


def test_frontmatter_absent_body_untouched(tmp_path):
    p = tmp_path / "plain.md"
    p.write_text("# No frontmatter\n")
    assert _lib.read_frontmatter(p) == {}
    _lib.update_frontmatter(p, {"plan_kind": "feature"})
    assert p.read_text().startswith("---\nplan_kind: \"feature\"\n") and p.read_text().endswith("# No frontmatter\n")


def test_parse_scalar():
    assert _lib.parse_scalar('"x"') == "x"
    assert _lib.parse_scalar("true") is True
    assert _lib.parse_scalar("7") == 7
    assert _lib.parse_scalar("[1, 2]") == [1, 2]
    assert _lib.parse_scalar("2026-04-22T00:00:00Z") == "2026-04-22T00:00:00Z"
    assert _lib.parse_scalar("") == ""


# ---------------------------------------------------------------- registry


def test_registry_per_entry_files(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    key = "Ideas/Todo List.md#^ideas-thing"
    _lib.registry_put(repo, cfg, key, {"kind": "note-task", "task_id": "ideas-thing"})
    files = list(_lib.entries_dir(repo, cfg).glob("*.json"))
    assert len(files) == 1 and files[0].name == _lib.entry_filename(key)
    assert "__" in files[0].name and files[0].name.endswith(".json") and " " not in files[0].name
    got = _lib.registry_get(repo, cfg, key)
    assert got["key"] == key and got["registry_version"] == _lib.REGISTRY_VERSION and got["created_at"]
    _lib.registry_put(repo, cfg, key, dict(got, workflow_status="shipped"))
    assert len(list(_lib.entries_dir(repo, cfg).glob("*.json"))) == 1
    assert _lib.registry_all(repo, cfg)[key]["workflow_status"] == "shipped"
    assert _lib.registry_delete(repo, cfg, key) and _lib.registry_get(repo, cfg, key) is None
    _lib.task_id_put(repo, cfg, "ideas-thing", {"state": "shipped"})
    assert _lib.task_ids_all(repo, cfg)["ideas-thing"]["state"] == "shipped"
    assert _lib.entry_filename("a#^b") != _lib.entry_filename("a#batch")


def test_registry_key_conventions():
    assert _lib.plan_key("feat/x") == "plan:feat-x"
    assert _lib.epic_key("v1") == "epic:v1"
    assert _lib.quickfix_key("fix-thing") == "quickfix:fix-thing"
    assert _lib.note_key("Ideas/Todo.md", "x") == "Ideas/Todo.md#^x"
    assert _lib.note_key("Ideas/Todo.md", None) == "Ideas/Todo.md#batch"


# ---------------------------------------------------------------- review log


def test_review_log_append_and_plan_scoping(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"plan_kind": "feature"})
    e = _lib.review_log_append(repo, cfg, {"skill": "plan-eng-review", "status": "issues_open"})
    assert e["plan"] == plan.name and e["branch"] == "feat/x" and e["commit"] and e["harness"] and e["ts"]
    _lib.review_log_append(repo, cfg, {"skill": "plan-eng-review", "status": "clean", "ts": "2099-01-01T00:00:00Z"})
    _lib.review_log_append(repo, cfg, {"skill": "plan-eng-review", "status": "clean", "plan": "other-plan.md"})
    latest = _lib.reviews_for_plan(repo, cfg, plan.name)
    assert latest["plan-eng-review"]["status"] == "clean" and latest["plan-eng-review"]["ts"].startswith("2099")
    lines = _lib.review_log_path(repo, cfg).read_text().splitlines()
    assert len(lines) == 3 and all(json.loads(l) for l in lines)


# ---------------------------------------------------------------- epics


def test_epic_progress_derives_from_children(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    R.write_epic(repo, "v1", {})
    R.registry_put(repo, "epic:v1", {
        "kind": "epic",
        "milestones": [
            {"id": "M1", "title": "freeze", "size": "quickfix"},
            {"id": "M2", "title": "deploy", "size": "feature"},
            {"id": "M3", "title": "config", "size": "feature", "status": "subsumed", "reason": "empty"},
            {"id": "M4", "title": "launch", "size": "feature"},
        ],
    })
    R.registry_put(repo, "quickfix:v1-m1", {"kind": "quickfix", "parent_epic": "v1", "milestone": "M1", "implementation_status": "shipped", "completed": "2026-01-02"})
    R.registry_put(repo, "plan:m2-branch", {"kind": "plan", "parent_epic": "v1", "milestone": "M2", "implementation_status": "implementing", "branch": "m2-branch"})
    prog = _lib.epic_progress(repo, cfg, "v1")
    by_id = {m["id"]: m for m in prog["milestones"]}
    assert by_id["M1"]["status"] == "shipped" and by_id["M1"]["completed"] == "2026-01-02"
    assert by_id["M2"]["status"] == "implementing" and by_id["M2"]["branch"] == "m2-branch"
    assert by_id["M3"]["status"] == "subsumed"
    assert by_id["M4"]["status"] == "not-started"
    assert prog["total"] == 4 and prog["shipped"] == 1 and prog["subsumed"] == 1
    assert prog["next"]["id"] == "M2" and prog["done"] is False


# ---------------------------------------------------------------- context


def test_context_bundle(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {"plan_kind": "feature"})
    ctx = _lib.context(repo)
    assert ctx["PROJECT"] == "t" and ctx["BRANCH"] == "feat/x" and ctx["SAFE_BRANCH"] == "feat-x" and ctx["ON_BASE"] == "0"
    assert ctx["PLAN_FILE"].endswith(plan.name) and ctx["SUMMARY_FILE"].endswith("-summary.md")
    assert ctx["DOCS_DIR"].endswith("/.agents/docs") and ctx["TEST_ARTIFACT"].endswith("/.agents/plans/testing/feat-x-test-artifact.md")
    assert ctx["PLAN_FILE"].startswith("/") and ctx["DOCS_DIR"].startswith("/")


# ---------------------------------------------------------------- review vocabulary and dispositions


def test_review_statuses_match_the_shared_definition():
    text = (R.PAYLOAD / "skills" / "_shared" / "obsidian-sync.md").read_text(encoding="utf-8")
    header = "| Status | Meaning | Disposition | Written by |"
    assert header in text
    table = text[text.index(header):]
    rows = []
    for line in table.splitlines()[2:]:
        if not line.startswith("| `"):
            break
        rows.append(line)
    words = tuple(line.split("`")[1] for line in rows)
    assert words == _lib.REVIEW_STATUSES == ("clean", "issues_open", "resolved", "done")
    dispositions = tuple(line.split("|")[3].strip() for line in rows)
    assert dispositions == ("passed", "failed", "resolved", "passed")


@pytest.mark.parametrize(
    "entry,expected",
    [
        (None, "missing"),
        ({}, "failed"),
        ({"status": None}, "failed"),
        ({"status": "   "}, "failed"),
        ({"status": "clean"}, "passed"),
        ({"status": "Clean"}, "passed"),  # legacy read lowercases; the CLI never writes it
        ({"status": "issues_open"}, "failed"),
        ({"status": "resolved", "resolved_by": "plan-eng-review"}, "failed"),  # no target skill
        ({"status": "resolved", "resolved_by": "operator"}, "failed"),  # no target skill
        ({"status": "resolved", "resolved_by": "operator", "skill": "qa"}, "resolved"),
        ({"status": "resolved", "resolved_by": "plan-eng-review", "skill": "plan-ceo-review"}, "resolved"),
        ({"status": "resolved"}, "failed"),
        ({"status": "resolved", "resolved_by": ""}, "failed"),
        ({"status": "resolved", "resolved_by": 1}, "failed"),
        ({"status": "resolved", "resolved_by": "execute-plan"}, "failed"),
        ({"status": "resolved", "resolved_by": "office-hours"}, "failed"),
        ({"status": "resolved", "resolved_by": "qa", "skill": "qa"}, "failed"),
        ({"status": "resolved", "resolved_by": "ship", "skill": "qa"}, "failed"),
        ({"status": "resolved", "resolved_by": "plan-ceo-review", "skill": "qa"}, "failed"),
        ({"status": "resolved", "resolved_by": "plan-eng-review", "skill": "review-implementation"}, "failed"),
        ({"status": "resolved", "resolved_by": "final-review", "skill": "qa"}, "resolved"),
        ({"status": "resolved", "resolved_by": "plan-eng-review", "skill": "plan-ceo-review", "superseded_by_failure": "2026-01-01T00:00:00Z"}, "failed"),
        ({"status": "done", "skill": "ship"}, "passed"),
        ({"status": "done", "skill": "qa"}, "passed"),
        ({"status": "done", "skill": "plan-design-review"}, "passed"),
        ({"status": "issues_found", "skill": "plan-adversarial-review"}, "passed"),
        ({"status": "issues_found", "skill": "qa"}, "failed"),
        ({"status": "issues_found", "skill": "design-review"}, "failed"),
        ({"status": "issues_found", "skill": "review-implementation"}, "failed"),
        ({"status": "issues_found", "skill": "final-review"}, "failed"),
        ({"status": "issues_found", "skill": "adversarial-subagent"}, "failed"),
        ({"status": "issues_found"}, "failed"),
        ({"status": "cleared"}, "passed"),
        ({"status": "pass"}, "passed"),
        ({"status": "bogus"}, "failed"),
        ({"status": "skipped"}, "failed"),
        ({"status": "neutral"}, "failed"),
    ],
)
def test_review_disposition(entry, expected):
    assert _lib.review_disposition(entry) == expected
    assert _lib.review_ok(entry) is (expected in ("passed", "resolved"))


def test_review_tiers_shape():
    skills = [t["skill"] for t in _lib.REVIEW_TIERS]
    assert skills == [
        "office-hours", "plan-ceo-review", "plan-eng-review", "plan-adversarial-review", "plan-design-review",
        "review-implementation", "adversarial-subagent", "qa", "design-review", "final-review", "ship",
    ]
    assert len(set(skills)) == len(skills)
    assert len({t["label"] for t in _lib.REVIEW_TIERS}) == len(skills)
    for tier in _lib.REVIEW_TIERS:
        assert set(tier) == {"label", "short", "skill", "invoke", "gates"}
        assert tier["invoke"].startswith("/") and isinstance(tier["gates"], bool)
    assert _lib.tier_for("office-hours")["gates"] is False
    assert all(t["gates"] for t in _lib.REVIEW_TIERS if t["skill"] != "office-hours")
    assert _lib.tier_for("adversarial-subagent")["invoke"] == "/review-implementation"
    assert skills.index("adversarial-subagent") == skills.index("review-implementation") + 1
    assert _lib.tier_for("nope") is None
    assert [t["skill"] for t in _lib.gating_tiers()] == skills[1:]
    assert set(_lib.PLAN_STAGE_SKILLS) < set(skills) and set(_lib.SHIP_GATE_SKILLS) < set(skills)


def test_can_resolve_stage_rule():
    assert _lib.can_resolve("plan-ceo-review", "plan-eng-review") and _lib.can_resolve("plan-ceo-review", "final-review")
    assert _lib.can_resolve("review-implementation", "final-review") and _lib.can_resolve("qa", "operator")
    assert not _lib.can_resolve("review-implementation", "plan-ceo-review") and not _lib.can_resolve("qa", "plan-adversarial-review")
    assert not _lib.can_resolve("qa", "ship") and not _lib.can_resolve("plan-ceo-review", "ship")
    assert not _lib.can_resolve("qa", "qa") and not _lib.can_resolve("qa", "office-hours") and not _lib.can_resolve("qa", "execute-plan")
    assert set(_lib.SHIP_STAGE_SKILLS) < {t["skill"] for t in _lib.gating_tiers()}


def test_resolution_covers_only_the_failure_it_names(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    T0, T1, T2 = "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z", "2026-09-03T00:00:00Z"
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_open", "plan": "p.md", "ts": T0})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "resolved", "plan": "p.md", "ts": T2, "resolved_by": "operator", "note": "n", "resolves_ts": T0})
    assert _lib.review_disposition(_lib.reviews_for_plan(repo, cfg, "p.md")["qa"]) == "resolved"
    # a second failure between the named one and the resolution merges in later (union merge): not covered
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_open", "plan": "p.md", "ts": T1})
    latest = _lib.reviews_for_plan(repo, cfg, "p.md")["qa"]
    assert latest["status"] == "resolved" and latest["superseded_by_failure"] == T1
    assert _lib.review_disposition(latest) == "failed"
    # the same-second failure on an earlier line is not covered either; on a later line it is simply newest
    _lib.review_log_append(repo, cfg, {"skill": "design-review", "status": "issues_open", "plan": "p.md", "ts": T2})
    _lib.review_log_append(repo, cfg, {"skill": "design-review", "status": "resolved", "plan": "p.md", "ts": T2, "resolved_by": "operator", "note": "n", "resolves_ts": T0})
    assert _lib.reviews_for_plan(repo, cfg, "p.md")["design-review"]["superseded_by_failure"] == T2
    # a resolution that names no failure never counts once any failure precedes it
    _lib.review_log_append(repo, cfg, {"skill": "final-review", "status": "issues_open", "plan": "p.md", "ts": T0})
    _lib.review_log_append(repo, cfg, {"skill": "final-review", "status": "resolved", "plan": "p.md", "ts": T2, "resolved_by": "operator", "note": "n"})
    assert _lib.review_disposition(_lib.reviews_for_plan(repo, cfg, "p.md")["final-review"]) == "failed"
    # a resolved line with no prior failure at all (hand-appended) is not ok
    _lib.review_log_append(repo, cfg, {"skill": "plan-eng-review", "status": "resolved", "plan": "p.md", "ts": T2, "resolved_by": "operator", "note": "n"})
    latest = _lib.reviews_for_plan(repo, cfg, "p.md")["plan-eng-review"]
    assert latest["superseded_by_failure"] == "unmatched" and _lib.review_disposition(latest) == "failed"
    # two failures at the named ts: fail closed, do not pick one
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_open", "plan": "q.md", "ts": T0})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_open", "plan": "q.md", "ts": T0})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "resolved", "plan": "q.md", "ts": T2, "resolved_by": "operator", "note": "n", "resolves_ts": T0})
    latest = _lib.reviews_for_plan(repo, cfg, "q.md")["qa"]
    assert latest["superseded_by_failure"] == T0 and _lib.review_disposition(latest) == "failed"


def test_review_plan_name_normalizes_summary_names():
    assert _lib.review_plan_name({"plan": "x-plan-20260101-120000-summary.md"}) == "x-plan-20260101-120000.md"
    assert _lib.review_plan_name({"plan": "x-plan-20260101-120000.md"}) == "x-plan-20260101-120000.md"
    assert _lib.review_plan_name({"plan": None}) is None and _lib.review_plan_name({}) is None
    assert _lib.review_plan_name({"plan": 3}) == 3


def test_review_log_scan_contract(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    path = _lib.review_log_path(repo, cfg)
    assert _lib.review_log_scan(repo, cfg) == ([], [])
    assert _lib.review_log_read(repo, cfg) == ([], 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    one = json.dumps({"skill": "qa", "status": "clean", "plan": "p.md", "ts": "2026-01-01T00:00:00Z"})
    path.write_text(one + "\n")  # a trailing newline is not a record
    entries, unreadable = _lib.review_log_read(repo, cfg)
    assert isinstance(entries, list) and isinstance(unreadable, int) and (len(entries), unreadable) == (1, 0)
    path.write_text(one + "\n\n   \n" + one)  # blank lines are skipped, not unreadable
    assert _lib.review_log_read(repo, cfg) == ([json.loads(one)] * 2, 0)
    path.write_text(one + "\n<<<<<<< HEAD\n" + one + "\n=======\n1\n[]\n\"x\"\n>>>>>>> theirs\n" + one)
    entries, bad = _lib.review_log_scan(repo, cfg)
    assert len(entries) == 3 and bad == [2, 4, 5, 6, 7, 8]
    assert _lib.review_log_read(repo, cfg)[1] == 6
    path.write_bytes(b"\xff\xfe" + one.encode())
    assert _lib.review_log_scan(repo, cfg) == ([], [0])
    assert _lib.review_log_read(repo, cfg) == ([], 1)
    assert "not valid UTF-8" in _lib.unreadable_message([0])
    assert _lib.unreadable_message([2, 4]).startswith("review log has 2 unreadable line(s): 2, 4")


def test_line_separators_in_a_field_never_split_the_record(tmp_path):
    # U+2028, U+2029 and U+0085 are line boundaries for str.splitlines() but json.dumps
    # leaves them raw; unescaped, one note would make the whole log unreadable.
    note = "closed in \u00a73\u2028item 2\u2029item 3\x85item 4"
    line = _lib.review_log_line({"note": note, "skill": "qa"})
    assert len(line.splitlines()) == 1 and "\u00a7" in line  # other non-ASCII stays raw
    assert json.loads(line)["note"] == note
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-03T00:00:00Z")
    stored = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", f"note={note}")
    assert stored["note"] == note
    cfg = _lib.load_config(repo)
    entries, bad = _lib.review_log_scan(repo, cfg)
    assert bad == [] and len(entries) == 3 and entries[-1]["note"] == note
    assert R.run_json(repo, "review-read", "--json")["reviews"]["plan-ceo-review"]["disposition"] == "resolved"
    text = R.run(repo, "review-read").stdout
    assert len(text.splitlines()) == 2  # ceo + eng; U+2028 is \\u2028 so it does not split the row
    assert "\\u2028" in text


def test_readers_tolerate_a_null_or_numeric_ts_from_a_raw_append(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "clean", "plan": "p.md", "ts": None})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_open", "plan": "p.md", "ts": "2026-01-01T00:00:00Z"})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "clean", "plan": "p.md", "ts": 5})
    assert _lib.review_ts({"ts": None}) == "" and _lib.review_ts({"ts": 5}) == "" and _lib.review_ts(None) == ""
    assert _lib.review_ts({"ts": "2026-01-01T00:00:00Z"}) == "2026-01-01T00:00:00Z"
    # a real timestamp outranks a missing one; a non-string never becomes the latest entry
    assert _lib.reviews_for_plan(repo, cfg, "p.md")["qa"]["status"] == "issues_open"
    for argv in (["review-read", "--all"], ["review-read", "--all", "--json"], ["review-read", "--plan", "p.md"]):
        proc = R.run(repo, *argv)
        assert proc.returncode == 0, (argv, proc.stdout, proc.stderr)


def test_reviews_for_plan_attaches_summary_named_entries_and_ignores_unreadable(tmp_path):
    repo = R.make_repo(tmp_path)
    cfg = _lib.load_config(repo)
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "issues_found", "plan": "p-plan-1-summary.md", "ts": "2026-01-02T00:00:00Z"})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "clean", "plan": "p-plan-1.md", "ts": "2026-01-01T00:00:00Z"})
    _lib.review_log_append(repo, cfg, {"skill": "qa", "status": "clean", "plan": "other-plan-1-summary.md", "ts": "2026-01-03T00:00:00Z"})
    latest = _lib.reviews_for_plan(repo, cfg, "p-plan-1.md")
    assert latest["qa"]["status"] == "issues_found" and latest["qa"]["plan"] == "p-plan-1-summary.md"
    path = _lib.review_log_path(repo, cfg)
    path.write_text(path.read_text() + "{broken\n")
    assert _lib.reviews_for_plan(repo, cfg, "p-plan-1.md")["qa"]["status"] == "issues_found"
    assert _lib.review_log_read(repo, cfg)[1] == 1
