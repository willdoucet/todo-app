"""design-sync-check / design-sync-mark against a temp git repo."""

from __future__ import annotations

import json

import _repo as R

WATCHED = [".agents/docs/FRONTEND_GUIDELINES.md", "frontend/src/index.css"]


def enabled_repo(tmp_path):
    repo = R.make_repo(tmp_path, modules={"learning": False, "design_sync": True, "learning_summaries": False}, design_watched_files=WATCHED)
    R.write(repo, WATCHED[1], "a{}\n")
    R.commit(repo, "style: css")
    return repo


def marker(repo):
    return json.loads((repo / ".agents/state/design-system-synced.json").read_text())


def test_module_disabled(tmp_path):
    repo = R.make_repo(tmp_path)  # config.example.json ships with design_sync: false
    for helper in ("design-sync-check", "design-sync-mark"):
        proc = R.run(repo, helper)
        assert (proc.returncode, proc.stdout.strip()) == (0, "design-sync: module disabled"), helper
    assert not (repo / ".agents/state/design-system-synced.json").exists()


def test_missing_and_malformed_marker(tmp_path):
    repo = enabled_repo(tmp_path)
    proc = R.run(repo, "design-sync-check")
    assert proc.returncode == 2
    assert "marker missing at .agents/state/design-system-synced.json" in proc.stdout
    assert "design-sync-mark" in proc.stdout
    R.write(repo, ".agents/state/design-system-synced.json", '{"synced_at": "x"}')
    proc = R.run(repo, "design-sync-check")
    assert proc.returncode == 2 and "malformed" in proc.stderr
    R.write(repo, ".agents/state/design-system-synced.json", "{nope")
    assert R.run(repo, "design-sync-check").returncode == 2


def test_mark_then_check_then_drift(tmp_path):
    repo = enabled_repo(tmp_path)
    design_sha = R.git(repo, "rev-parse", "HEAD")
    R.write(repo, "README.md", "# unrelated\n")
    repo_sha = R.commit(repo, "docs: readme")
    assert repo_sha != design_sha

    proc = R.run(repo, "design-sync-mark", "--org-url", "https://example.test/org/1")
    assert proc.returncode == 0 and "marked synced at" in proc.stdout
    m = marker(repo)
    assert m["schema_version"] == 1
    assert m["synced_repo_sha"] == repo_sha and m["synced_design_sha"] == design_sha
    assert m["watched_files"] == WATCHED and m["claude_design_org_url"] == "https://example.test/org/1"
    assert m["synced_at"].endswith("Z")

    proc = R.run(repo, "design-sync-check")
    assert proc.returncode == 0 and proc.stdout.startswith("design-sync-check: CLEAN")
    assert design_sha in proc.stdout

    R.write(repo, WATCHED[0], "# guidelines\n")
    new_design_sha = R.commit(repo, "docs: guidelines")
    proc = R.run(repo, "design-sync-check")
    assert proc.returncode == 1
    lines = proc.stdout.splitlines()
    assert lines[0].startswith("design-sync-check: DRIFT — 1 commit(s)")
    assert lines[1].strip() == f"synced_design_sha:  {design_sha}"
    assert lines[2].strip() == f"current_design_sha: {new_design_sha}"
    assert "https://example.test/org/1" in lines[3] and "design-sync-mark" in lines[3]

    # re-marking without --org-url preserves the URL and clears the drift
    R.run(repo, "design-sync-mark")
    assert marker(repo)["claude_design_org_url"] == "https://example.test/org/1"
    assert marker(repo)["synced_design_sha"] == new_design_sha
    assert R.run(repo, "design-sync-check").returncode == 0


def test_design_sha_falls_back_to_head_when_no_watched_history(tmp_path):
    repo = R.make_repo(tmp_path, modules={"design_sync": True}, design_watched_files=["frontend/src/nothing.css"])
    head = R.git(repo, "rev-parse", "HEAD")
    assert R.run(repo, "design-sync-mark").returncode == 0
    assert marker(repo)["synced_design_sha"] == head
    assert R.run(repo, "design-sync-check").returncode == 0


def test_empty_watch_list_is_an_error(tmp_path):
    repo = R.make_repo(tmp_path, modules={"design_sync": True}, design_watched_files=[])
    proc = R.run(repo, "design-sync-mark")
    assert proc.returncode == 2 and json.loads(proc.stdout)["status"] == "error"
