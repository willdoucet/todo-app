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
