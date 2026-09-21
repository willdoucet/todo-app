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


def test_ctx_timestamp_is_utc_whatever_tz_the_shell_has(tmp_path):
    """UTC+14 shares its calendar date with UTC for 10 hours of every day, so a date-only
    check passes against local-time code 42% of the time. Compare the whole timestamp with
    the UTC clock: under local-time code the gap is 14 hours at every hour of the day. TZ is
    set in the subprocess that runs the helper; os.environ in-process does nothing without
    time.tzset(), which would leak into every later test."""
    from datetime import datetime, timezone
    repo = R.make_repo(tmp_path)
    proc = R.run(repo, "ctx", "--json", env={"TZ": "Pacific/Kiritimati"})
    assert proc.returncode == 0, proc.stderr
    slug = json.loads(proc.stdout)["TIMESTAMP"]
    stamped = datetime.strptime(slug, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - stamped).total_seconds()) < 60
    own = datetime.strptime(_lib.timestamp_slug(), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - own).total_seconds()) < 60


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


# ---------------------------------------------------------------- re-review demands: stale

T = {n: f"2026-09-{n:02d}T00:00:00Z" for n in range(1, 28)}


def _repo_and_cfg(tmp_path):
    repo = R.make_repo(tmp_path)
    return repo, _lib.load_config(repo)


def _adder(repo, cfg, plan_name):
    return lambda skill, status, ts, **kw: _lib.review_log_append(repo, cfg, {"skill": skill, "status": status, "plan": plan_name, "ts": ts, **kw})


def disp(repo, cfg, plan_name, skill):
    return _lib.review_disposition(_lib.reviews_for_plan(repo, cfg, plan_name)[skill])


def test_can_demand_same_stage_gating_not_self_not_ship():
    assert _lib.can_demand("plan-design-review", "plan-eng-review") and _lib.can_demand("plan-adversarial-review", "plan-ceo-review")
    assert _lib.can_demand("review-implementation", "adversarial-subagent") and _lib.can_demand("final-review", "qa")
    assert not _lib.can_demand("plan-eng-review", "plan-eng-review")
    assert not _lib.can_demand("plan-eng-review", "review-implementation") and not _lib.can_demand("qa", "plan-eng-review")
    assert not _lib.can_demand("qa", "ship") and not _lib.can_demand("ship", "qa")
    assert not _lib.can_demand("office-hours", "plan-eng-review") and not _lib.can_demand("plan-eng-review", "office-hours")
    assert not _lib.can_demand("execute-plan", "plan-eng-review") and not _lib.can_demand("plan-eng-review", "nope")


def test_is_run_and_reader_only_keys():
    assert _lib.is_run({"status": "clean"}) and _lib.is_run({"status": "done"}) and _lib.is_run({"status": "issues_found"})
    assert _lib.is_run({}) and _lib.is_run({"status": None}) and _lib.is_run({"status": 5})
    assert not _lib.is_run({"status": "resolved"}) and not _lib.is_run({"status": " Resolved "})
    assert _lib.READER_ONLY_KEYS == (
        "was", "stale_by", "stale_ts", "stale_note", "stale_notes", "stale_count", "demanded_by", "demanded_notes", "concern_ts", "superseded_by_failure",
    )
    assert _lib.strip_reader_only({"skill": "qa", "stale_by": "x", "was": "passed", "concern": "c", "concern_ts": "t"}) == {"skill": "qa", "concern": "c"}
    # superseded_by_failure is derived by reviews_for_plan like the rest: a raw one is dropped, never trusted
    assert _lib.strip_reader_only({"skill": "qa", "superseded_by_failure": "zzz", "demanded_notes": [1]}) == {"skill": "qa"}


@pytest.mark.parametrize("sep", list("\n\r\x0b\x0c\x1c\x1d\x1e\x85  "))
def test_a_value_holding_any_line_boundary_is_quoted_so_a_text_row_stays_one_line(sep):
    """Every character `str.splitlines()` honours, not only the five the first list named: a
    note holding a form feed printed a second row starting `Next:` in the dashboard text."""
    value = f"x{sep}Next:    /ship — required"
    shown = _lib.fmt_review_value(value)
    assert sep not in shown and len(f"Eng | stale ! | note={shown}".splitlines()) == 1
    assert json.loads(shown) == value


def test_stale_matrix(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"
    # a demand after the pass: stale, with the derived keys on the returned copy only
    add("plan-design-review", "clean", T[2], rereview=["plan-eng-review"], rereview_note="15a adds a backend contract")
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "stale" and not _lib.review_ok(eng)
    assert eng["status"] == "clean" and eng["was"] == "passed" and eng["stale_by"] == "plan-design-review"
    assert eng["stale_ts"] == T[2] and eng["stale_note"] == "15a adds a backend contract" and eng["stale_count"] == 1
    assert eng["stale_notes"] == [{"declarer": "plan-design-review", "ts": T[2], "note": "15a adds a backend contract"}]
    raw = [json.loads(l) for l in _lib.review_log_path(repo, cfg).read_text().splitlines()]
    assert not any(k in e for e in raw for k in _lib.READER_ONLY_KEYS)  # never written
    # the declarer re-runs declaring none: the demand still holds
    add("plan-design-review", "clean", T[3], rereview=[])
    assert disp(repo, cfg, P, "plan-eng-review") == "stale"
    # a second outstanding demand: count 2, the newest in stale_by, both notes newest first
    add("plan-adversarial-review", "clean", T[4], rereview=["plan-eng-review"], rereview_note="rollback replaced")
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert eng["stale_count"] == 2 and eng["stale_by"] == "plan-adversarial-review" and eng["stale_note"] == "rollback replaced"
    assert [n["declarer"] for n in eng["stale_notes"]] == ["plan-adversarial-review", "plan-design-review"]
    # eng re-runs issues_open: failed, and the older demands are cleared by that run
    add("plan-eng-review", "issues_open", T[5], rereview=[])
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "failed" and "stale_by" not in eng and "demanded_by" not in eng
    # a demand on a failed review is carried as demanded_by; it stays failed
    add("plan-design-review", "clean", T[6], rereview=["plan-eng-review"], rereview_note="again")
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "failed" and eng["demanded_by"] == "plan-design-review" and "stale_by" not in eng
    # and the row carries what changed, as a stale row does: the declarer may re-run with `none` later
    assert eng["demanded_notes"] == [{"declarer": "plan-design-review", "ts": T[6], "note": "again"}]
    # a third review resolves the failure: stale, not resolved (the demand is still outstanding)
    add("plan-eng-review", "resolved", T[7], resolved_by="plan-adversarial-review", note="n", resolves_ts=T[5])
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "stale" and eng["was"] == "resolved" and eng["status"] == "resolved"
    # eng re-runs clean after every demand: passed
    add("plan-eng-review", "clean", T[8], rereview=[])
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"


def test_equal_ts_between_run_and_demand_is_stale_in_both_file_orders(tmp_path):
    for order in ("run-first", "demand-first"):
        (tmp_path / order).mkdir()
        repo = R.make_repo(tmp_path / order)
        cfg = _lib.load_config(repo)
        run = {"skill": "plan-eng-review", "status": "clean", "plan": "p.md", "ts": T[2], "rereview": []}
        demand = {"skill": "plan-design-review", "status": "clean", "plan": "p.md", "ts": T[2], "rereview": ["plan-eng-review"], "rereview_note": "tie"}
        for entry in ((run, demand) if order == "run-first" else (demand, run)):
            _lib.review_log_append(repo, cfg, entry)
        assert disp(repo, cfg, "p.md", "plan-eng-review") == "stale", order
        _lib.review_log_append(repo, cfg, dict(run, ts=T[3]))  # only a run strictly after the demand clears it
        assert disp(repo, cfg, "p.md", "plan-eng-review") == "passed", order


def test_union_merged_failure_between_pass_and_demand_reads_failed_then_stale(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    add("plan-design-review", "clean", T[4], rereview=["plan-eng-review"], rereview_note="x")
    add("plan-eng-review", "issues_open", T[2], rereview=[])  # merged in later, dated between the pass and the demand
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "failed" and eng["demanded_by"] == "plan-design-review"
    add("plan-eng-review", "resolved", T[5], resolved_by="plan-adversarial-review", note="n", resolves_ts=T[2])
    assert disp(repo, cfg, P, "plan-eng-review") == "stale"


def test_hand_appended_lines_never_clear_or_invent_a_demand(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    add("plan-design-review", "clean", T[2], rereview=["plan-eng-review"], rereview_note="x")
    # a resolved entry by operator on a stale review, with or without a waives_ts key: failed (unmatched) and demanded
    add("plan-eng-review", "resolved", T[3], resolved_by="operator", note="n")
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "failed" and eng["superseded_by_failure"] == "unmatched" and eng["demanded_by"] == "plan-design-review"
    add("plan-eng-review", "resolved", T[4], resolved_by="operator", note="n", waives_ts=T[2])
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "failed" and eng["demanded_by"] == "plan-design-review"
    # an issues_open entry carrying a waives_ts key is an ordinary run: failed
    add("plan-eng-review", "issues_open", T[5], waives_ts=T[2], rereview=[])
    assert disp(repo, cfg, P, "plan-eng-review") == "failed"
    # only a hand-appended resolved entry and no run: demands naming it are dropped
    add("plan-ceo-review", "resolved", T[1], resolved_by="operator", note="n")
    add("plan-adversarial-review", "clean", T[6], rereview=["plan-ceo-review"], rereview_note="x")
    ceo = _lib.reviews_for_plan(repo, cfg, P)["plan-ceo-review"]
    assert _lib.review_disposition(ceo) == "failed" and "stale_by" not in ceo and "demanded_by" not in ceo
    history = _lib.plan_review_history(repo, cfg, P)
    assert _lib.last_run(history, "plan-ceo-review") is None and all(d[1] != "plan-ceo-review" for d in history["demands"])
    # legacy words, done and a missing status count as runs
    add("qa", "issues_found", T[1])
    add("design-review", "done", T[1])
    add("final-review", None, T[1])
    history = _lib.plan_review_history(repo, cfg, P)
    assert all(_lib.last_run(history, s) is not None for s in ("qa", "design-review", "final-review"))
    # lines that break can_demand are ignored on read: self, ship, cross-stage, a non-gating declarer, a resolved entry, a missing review
    add("plan-eng-review", "clean", T[7], rereview=[])
    add("plan-eng-review", "clean", T[8], rereview=["plan-eng-review"], rereview_note="self")
    add("ship", "done", T[8], rereview=["plan-eng-review"], rereview_note="ship")
    add("qa", "clean", T[8], rereview=["plan-eng-review"], rereview_note="cross-stage")
    add("office-hours", "clean", T[8], rereview=["plan-eng-review"], rereview_note="non-gating")
    add("plan-ceo-review", "resolved", T[8], resolved_by="operator", note="n", rereview=["plan-eng-review"], rereview_note="resolved")
    add("plan-design-review", "clean", T[8], rereview=["nope"], rereview_note="missing review")
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"
    # a demand logged against another plan is ignored
    _lib.review_log_append(repo, cfg, {"skill": "plan-design-review", "status": "clean", "plan": "q.md", "ts": T[9], "rereview": ["plan-eng-review"], "rereview_note": "other plan"})
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"


def test_reader_only_keys_are_stripped_first_even_inside_the_resolution_walk(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[], stale_by="plan-design-review", stale_ts=T[1], stale_note="forged", stale_notes=[], stale_count=9, was="passed", demanded_by="x")
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "passed" and not any(k in eng for k in _lib.READER_ONLY_KEYS)
    # a hand-appended stale_by on an older issues_open that a resolution later covers: the walk still sees the failure
    add("qa", "issues_open", T[2], stale_by="x")
    add("qa", "resolved", T[4], resolved_by="operator", note="n", resolves_ts=T[2])
    add("qa", "issues_open", T[3], stale_by="x")  # merged in later; strip-first keeps it a failure the walk sees
    qa = _lib.reviews_for_plan(repo, cfg, P)["qa"]
    assert _lib.review_disposition(qa) == "failed" and qa["superseded_by_failure"] == T[3]
    # a raw superseded_by_failure is the reader's own key: dropped, then derived. On a sound resolution it
    # used to read failed with a ts no later resolution could satisfy ("earlier than the failed entry's 'zzz'")
    add("final-review", "issues_open", T[2])
    add("final-review", "resolved", T[3], resolved_by="operator", note="n", resolves_ts=T[2], superseded_by_failure="zzz")
    final = _lib.reviews_for_plan(repo, cfg, P)["final-review"]
    assert _lib.review_disposition(final) == "resolved" and "superseded_by_failure" not in final
    # a raw concern_ts, and a raw concern on a resolved entry, are stripped; the run's concern travels with the row
    add("design-review", "issues_open", T[5], concern="from the run")
    add("design-review", "resolved", T[6], resolved_by="operator", note="n", resolves_ts=T[5], concern="on the record", concern_ts="forged")
    audit = _lib.reviews_for_plan(repo, cfg, P)["design-review"]
    assert audit["concern"] == "from the run" and audit["concern_ts"] == T[5] and _lib.review_disposition(audit) == "resolved"
    add("design-review", "clean", T[7])
    assert "concern" not in _lib.reviews_for_plan(repo, cfg, P)["design-review"]


def test_malformed_rereview_fields_never_raise_and_never_demand(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    for bad in (5, "plan-eng-review", {"a": 1}, [["plan-eng-review"]], [5], None, True):
        add("plan-design-review", "clean", T[2], rereview=bad, rereview_note=42)
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"
    assert _lib.plan_review_history(repo, cfg, P)["demands"] == []
    add("plan-design-review", "clean", T[3], rereview=["plan-eng-review"], rereview_note=42)
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert _lib.review_disposition(eng) == "stale" and eng["stale_note"] == "42"
    add("plan-design-review", "clean", T[4], rereview=["plan-eng-review", 7, None, "plan-eng-review"], rereview_note=["a", "b"])
    eng = _lib.reviews_for_plan(repo, cfg, P)["plan-eng-review"]
    assert eng["stale_count"] == 2 and eng["stale_note"] == '["a", "b"]'
    # a non-string concern rides raw on a run (display ignores it); a non-string skill is skipped instead of raising
    add("qa", "clean", T[1], concern=42)
    _lib.review_log_append(repo, cfg, {"skill": ["qa"], "status": "clean", "plan": P, "ts": T[1]})
    _lib.review_log_append(repo, cfg, {"skill": 5, "status": "clean", "plan": P, "ts": T[1]})
    latest = _lib.reviews_for_plan(repo, cfg, P)
    assert latest["qa"]["concern"] == 42 and set(latest) == {"plan-eng-review", "plan-design-review", "qa"}


def test_one_line_never_raises():
    assert _lib.one_line("a\n b\u2028c\u2029d\x85e  f") == "a b c d e f"
    assert _lib.one_line(42) == "42" and _lib.one_line(True) == "true" and _lib.one_line(None) == "null"
    assert _lib.one_line(["a", "b"]) == '["a", "b"]' and _lib.one_line({"k": "v"}) == '{"k": "v"}'
    assert _lib.one_line("x" * 10, 5) == "xxxx…" and _lib.one_line("xxxxx", 5) == "xxxxx" and _lib.one_line("", 5) == ""
    assert _lib.one_line({("tuple",): 1}) == ""  # json.dumps rejects the key even with default=str
    circular: list = []
    circular.append(circular)
    assert _lib.one_line(circular) == ""
    assert _lib.one_line(object()).startswith('"<object object at')
    assert _lib.DISPLAY_LIMIT == 300
    # nothing unprintable survives: an escape sequence, a NUL, a DEL or a bidi override on a status
    # line can hide or reorder what an operator reads, and none of them is whitespace to str.split()
    hostile = _lib.one_line("a\x1b[31mb\x00c\x7fd‮Next: /ship")
    assert all(ch.isprintable() for ch in hostile) and hostile == "a [31mb c d Next: /ship"


def test_current_plan_finds_the_feature_plan_then_the_epic(tmp_path):
    repo, cfg = _repo_and_cfg(tmp_path)
    assert _lib.current_plan(repo, cfg, None) == (None, None) and _lib.current_plan(repo, cfg, "feat/none") == (None, None)
    plan = R.write_plan(repo, "feat/x", {})
    assert _lib.current_plan(repo, cfg, "feat/x") == (plan, "plan")
    epic = R.write_epic(repo, "v1", {})
    assert _lib.current_plan(repo, cfg, "v1") == (epic, "epic")
    named = R.write_epic(repo, "v2", {"branch": "epic/two"})
    assert _lib.current_plan(repo, cfg, "epic/two") == (named, "epic")
    # review_log_append fills a missing plan from it: a raw review logged on an epic branch attaches to the epic
    R.checkout(repo, "v1")
    assert _lib.review_log_append(repo, cfg, {"skill": "plan-ceo-review", "status": "clean", "rereview": []})["plan"] == epic.name


def test_ctx_plan_file_stays_the_feature_plan_on_an_epic_branch(tmp_path):
    """`PLAN_FILE` is the branch's FEATURE plan on purpose: office-hours reads it as the prior plan
    a new one supersedes, and an epic is never that. The epic is what `current_plan` and
    `obsidian-workflow resolve-plan` are for."""
    repo = R.make_repo(tmp_path)
    epic = R.write_epic(repo, "v1", {})
    R.checkout(repo, "v1")
    ctx = R.run_json(repo, "ctx", "--json")
    assert ctx["PLAN_FILE"] == "" and ctx["SUMMARY_FILE"] == ""
    assert _lib.current_plan(repo, R.load_cfg(repo), "v1") == (epic, "epic")


def test_a_non_string_holding_a_row_separator_is_quoted_so_the_extra_cell_splits_on_bare_commas():
    """Extra is `k=v,k=v`. A string holding `,` or `|` was always JSON-quoted; a list was dumped
    raw, so `rereview` with two names, `stale_notes` and `demanded_notes` put top-level commas
    in the cell. A non-string whose JSON text holds a separator is now quoted as that text."""
    for bare, shown in (([], "[]"), (3, "3"), (True, "true"), (None, "null"), (["plan-eng-review"], '["plan-eng-review"]'), ({}, "{}")):
        assert _lib.fmt_review_value(bare) == shown
    notes = [{"declarer": "plan-design-review", "ts": "2026-09-02T10:00:00Z", "note": "a, b | c"}]
    for value in (notes, ["plan-eng-review", "plan-ceo-review"], {"a": 1, "b": 2}):
        shown = _lib.fmt_review_value(value)
        assert shown.startswith('"') and shown.endswith('"')
        assert json.loads(json.loads(shown)) == value  # one JSON string holding the value's JSON text
    cell = ",".join(f"{k}={_lib.fmt_review_value(v)}" for k, v in (("rereview", ["a", "b"]), ("stale_notes", notes), ("was", "passed")))
    assert [f.split("=", 1)[0] for f in _split_extra_cell(cell)] == ["rereview", "stale_notes", "was"]


def _split_extra_cell(cell: str) -> list[str]:
    """An Extra cell's fields, read the way `fmt_review_value` states them: a `"` opens a JSON
    string literal, which the real scanner consumes (`raw_decode` raises on text that is not
    one), and a comma outside a literal separates two fields. The 1.3.1 splitter looked one
    character back for a backslash, so a quoted value ENDING in one (`"C:\\\\"`) never closed."""
    scan, fields, start, i = json.JSONDecoder().raw_decode, [], 0, 0
    while i < len(cell):
        if cell[i] == '"':
            literal, i = scan(cell, i)
            assert isinstance(literal, str)
            continue
        if cell[i] == ",":
            fields.append(cell[start:i])
            start = i + 1
        i += 1
    fields.append(cell[start:])
    return fields


ROW_VALUES = [
    'see the 6" rule', '"', '""', 'a"b"c', '="', "C:\\temp\\", "\\", 'ends \\"', "\\u0041", "a, b | c", "k=v,k2=v2",
    "", "plain", "[]", "3", '["a", "b"]', "a\u2028b", "\ud800",
    ["plan-eng-review", "plan-ceo-review"], ["plan-eng-review"], [], 3, True, None, {"a": 1, "b": 2}, {"a": 'x"y'}, ['6" rule'], ["back\\slash"],
    [{"declarer": "plan-design-review", "ts": "2026-09-02T10:00:00Z", "note": 'a, b | c "quoted" \\'}],
]


def test_an_extra_cell_reads_back_field_by_field_with_a_real_json_string_scanner():
    """1.3.1 said every comma left outside a JSON string separates two fields, and it was false:
    a bare string holding `"` was not quoted, so `note=see the 6" rule` beside a two-name
    `rereview` opened a literal at the inch mark and swallowed the comma between the fields. A
    string holding `"` or a backslash is now quoted; every ordered pair of values reads back."""
    fmt = _lib.fmt_review_value
    assert fmt('see the 6" rule') == '"see the 6\\" rule"' and fmt("C:\\temp\\") == '"C:\\\\temp\\\\"' and fmt("\\") == '"\\\\"'
    inch, two_names = fmt('see the 6" rule'), fmt(["plan-eng-review", "plan-ceo-review"])
    assert [f.split("=", 1)[0] for f in _split_extra_cell(f"note={inch},rereview={two_names},was=passed")] == ["note", "rereview", "was"]
    for a in ROW_VALUES:
        for b in ROW_VALUES:
            fields = [f"left={fmt(a)}", f"right={fmt(b)}", "was=passed"]
            assert _split_extra_cell(",".join(fields)) == fields, (a, b)
    for value in ROW_VALUES:
        shown = fmt(value)
        if "|" in shown or "," in shown:
            assert isinstance(json.loads(shown), str)  # a delimiter only inside the one literal the value is
        if isinstance(value, str):
            assert shown == value or json.loads(shown) == value
        else:
            assert json.loads(shown) == value or json.loads(json.loads(shown)) == value
    # what the text row does not do, stated in the docstring: it does not carry the type
    assert fmt(["a", "b"]) == fmt('["a", "b"]') and fmt([]) == fmt("[]") and fmt(3) == fmt("3")


def test_an_undated_entry_is_the_oldest_entry_for_runs_and_demands_alike(tmp_path):
    """`review-log` stamps and validates its own `ts`; a hand-appended line can lack one, and so
    can history carried over by `framework migrate` (`"ts": ""`, pinned in tests/test_cli.py).
    The reader has one rule for it (`review_ts` -> ""): it is the OLDEST entry. An undated run
    never outranks a dated one; an undated demand is outstanding only against an undated run.
    Treating an undated demand as always outstanding would leave `--next` naming a review that no
    re-run can clear. A hand-appended line is fixed or deleted; migrated history is left alone."""
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    _lib.review_log_append(repo, cfg, {"skill": "plan-design-review", "status": "clean", "plan": P, "ts": None, "rereview": ["plan-eng-review"], "rereview_note": "undated"})
    assert disp(repo, cfg, P, "plan-eng-review") == "passed"  # the dated run is newer than an undated demand
    # against an undated run the same demand is outstanding (a tie fails closed), and a dated re-run clears it
    (tmp_path / "two").mkdir()
    repo2, cfg2 = _repo_and_cfg(tmp_path / "two")
    _lib.review_log_append(repo2, cfg2, {"skill": "plan-eng-review", "status": "clean", "plan": P, "ts": None, "rereview": []})
    _lib.review_log_append(repo2, cfg2, {"skill": "plan-design-review", "status": "clean", "plan": P, "ts": None, "rereview": ["plan-eng-review"], "rereview_note": "undated"})
    assert disp(repo2, cfg2, P, "plan-eng-review") == "stale"
    _adder(repo2, cfg2, P)("plan-eng-review", "clean", T[2], rereview=[])
    assert disp(repo2, cfg2, P, "plan-eng-review") == "passed"


def test_readers_take_entries_already_read_and_do_not_touch_the_file_again(tmp_path):
    """`review-log` and `workflow-state` scan the log once for the unreadable count and hand the
    entries on; pass 1 and pass 2 used to read the file again, each."""
    repo, cfg = _repo_and_cfg(tmp_path)
    P = "p.md"
    add = _adder(repo, cfg, P)
    add("plan-eng-review", "clean", T[1], rereview=[])
    add("plan-design-review", "clean", T[2], rereview=["plan-eng-review"], rereview_note="x")
    entries, bad = _lib.review_log_scan(repo, cfg)
    expected = _lib.reviews_for_plan(repo, cfg, P)
    history = _lib.plan_review_history(repo, cfg, P)
    _lib.review_log_path(repo, cfg).unlink()  # nothing left to read
    assert bad == [] and _lib.reviews_for_plan(repo, cfg, P, entries=entries) == expected
    assert _lib.plan_review_history(repo, cfg, P, entries=entries) == history
    assert _lib.reviews_for_plan(repo, cfg, P) == {}  # control: without `entries` it reads the file, now gone
    assert _lib.reviews_for_plan(repo, cfg, P, entries=[]) == {}  # an empty list is a read log, not "go read it"
