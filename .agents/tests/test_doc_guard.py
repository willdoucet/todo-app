"""doc-guard: --explain, --commit-msg (strict / pr-strict / ci-only), --staged --dry-run, --range, and the hook."""

from __future__ import annotations

import shutil
import subprocess

import _repo as R

ROUTE = "backend/app/routes/items.py"
DOC = ".agents/docs/BACKEND_STRUCTURE.md"

EXPECTED_FAILURE = f"""doc-guard: staged changes touch documented areas whose docs are not staged

  {ROUTE}  -> {DOC}  (API Endpoints)

Fix one of:
  - run /update-docs and stage the doc changes
  - add a trailer:  Docs: n/a - <reason>      (no doc impact, recorded in history)
  - add a trailer:  Docs: later               (feature branch only; CI requires the PR to resolve it)
"""


def guard(repo, *args):
    return R.run(repo, "doc-guard", *args)


def stage(repo, *rels):
    for rel in rels:
        R.write(repo, rel, f"{rel}\n")
    R.git(repo, "add", "-A")


def msgfile(repo, text):
    path = repo / ".git" / "COMMIT_EDITMSG_TEST"
    path.write_text(text)
    return str(path)


def commit_msg(repo, text="feat: change"):
    return guard(repo, "--commit-msg", msgfile(repo, text))


# ---------------------------------------------------------------- explain


def test_explain(tmp_path):
    repo = R.make_repo(tmp_path)
    assert guard(repo, "--explain", ROUTE).stdout.strip() == f"{ROUTE} -> {DOC}  (API Endpoints)"
    assert guard(repo, "--explain", "backend/tests/test_x.py").stdout.strip() == "backend/tests/test_x.py: exempt"
    assert guard(repo, "--explain", "scripts/x.sh").stdout.strip() == "scripts/x.sh: unmapped (no doc_map rule)"
    both = guard(repo, "--explain", "backend/app/models.py").stdout
    assert "Data Model" in both


# ---------------------------------------------------------------- commit-msg: strict


def test_strict_blocks_with_exact_message(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    R.checkout(repo, "feat/x")
    stage(repo, ROUTE)
    proc = commit_msg(repo)
    assert proc.returncode == 1
    assert proc.stdout == EXPECTED_FAILURE
    assert proc.stderr == ""


def test_strict_passes_when_doc_is_staged(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    stage(repo, ROUTE, DOC)
    proc = commit_msg(repo)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


def test_strict_trailers(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    R.checkout(repo, "feat/x")
    stage(repo, ROUTE)
    assert commit_msg(repo, "feat: x\n\nDocs: n/a - endpoint is internal only\n").returncode == 0
    assert commit_msg(repo, "feat: x\n\ndocs: N/A - case insensitive\n").returncode == 0
    proc = commit_msg(repo, "feat: x\n\nDocs: n/a\n")  # reason required
    assert proc.returncode == 1 and "without a reason" in proc.stdout
    proc = commit_msg(repo, "feat: x\n\nDocs: later\n")  # later never satisfies strict
    assert proc.returncode == 1 and "not accepted in strict mode" in proc.stdout
    assert commit_msg(repo, "feat: x\n\n# Docs: n/a - commented out\n").returncode == 1


def test_no_documented_areas_passes_silently(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    stage(repo, "backend/tests/test_items.py", "README.md")
    proc = commit_msg(repo)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


# ---------------------------------------------------------------- commit-msg: pr-strict / ci-only


def test_pr_strict_accepts_later_on_feature_branch_only(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="pr-strict")
    stage(repo, ROUTE)
    proc = commit_msg(repo, "feat: x\n\nDocs: later\n")
    assert proc.returncode == 1 and "only accepted on a feature branch" in proc.stdout
    assert commit_msg(repo).returncode == 1
    R.checkout(repo, "feat/x")
    assert commit_msg(repo, "feat: x\n\nDocs: later\n").returncode == 0
    assert commit_msg(repo).returncode == 1
    assert commit_msg(repo, "feat: x\n\nDocs: n/a - reason\n").returncode == 0


def test_ci_only_always_passes_silently(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="ci-only")
    stage(repo, ROUTE, "newarea/thing.py")
    proc = commit_msg(repo)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


# ---------------------------------------------------------------- unmapped note, deletions, dry-run


def test_unmapped_area_note_never_blocks(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    stage(repo, "scripts/deploy.sh", "scripts/other.sh", "toplevel.txt", "backend/app/unknown_thing.py")
    proc = commit_msg(repo)
    assert proc.returncode == 0 and proc.stdout == ""
    assert proc.stderr.splitlines() == ["doc-guard: note: unmapped area 'scripts/' — add it to doc_map.rules or doc_map.exempt"]


def test_deleted_paths_are_exempt(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    R.write(repo, ROUTE)
    R.commit(repo, "add route\n\nDocs: n/a - seed")
    (repo / ROUTE).unlink()
    R.git(repo, "add", "-A")
    assert commit_msg(repo).returncode == 0
    # renames count under the new path
    R.write(repo, ROUTE)
    R.commit(repo, "restore\n\nDocs: n/a - seed")
    R.git(repo, "mv", ROUTE, "backend/app/routes/items2.py")
    proc = commit_msg(repo)
    assert proc.returncode == 1 and "backend/app/routes/items2.py" in proc.stdout


def test_staged_dry_run(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    proc = guard(repo, "--staged", "--dry-run")
    assert proc.returncode == 0 and "touch no documented areas" in proc.stdout
    stage(repo, ROUTE)
    proc = guard(repo, "--staged", "--dry-run")
    assert proc.returncode == 0
    assert "mode=strict branch=main base=main" in proc.stdout
    assert "would block without a `Docs:` trailer" in proc.stdout and DOC in proc.stdout
    stage(repo, DOC)
    proc = guard(repo, "--staged", "--dry-run")
    assert proc.returncode == 0 and "would pass" in proc.stdout and f"docs staged: {DOC}" in proc.stdout


# ---------------------------------------------------------------- range mode


def test_range_passes_when_doc_updated_anywhere_in_range(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="pr-strict")
    base = R.git(repo, "rev-parse", "HEAD")
    R.checkout(repo, "feat/x")
    R.write(repo, ROUTE)
    R.commit(repo, "feat: route\n\nDocs: later")
    R.write(repo, "backend/app/models.py")
    R.commit(repo, "feat: model")
    R.write(repo, DOC, "# updated\n")
    R.commit(repo, "docs: update")
    proc = guard(repo, "--range", f"{base}..HEAD")
    assert (proc.returncode, proc.stdout) == (0, "")


def test_range_fails_per_commit_and_later_does_not_satisfy(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="pr-strict")
    base = R.git(repo, "rev-parse", "HEAD")
    R.checkout(repo, "feat/x")
    R.write(repo, ROUTE)
    c1 = R.commit(repo, "feat: route\n\nDocs: later")
    R.write(repo, "frontend/package.json", "{}\n")
    c2 = R.commit(repo, "chore: deps\n\nDocs: n/a - lockstep bump")
    R.write(repo, "frontend/src/index.css", "a{}\n")
    c3 = R.commit(repo, "style: css")
    proc = guard(repo, "--range", f"{base}..HEAD")
    assert proc.returncode == 1
    out = proc.stdout
    assert out.startswith(f"doc-guard: 2 commit(s) in {base}..HEAD touch documented areas")
    assert f"{c3[:7]}  style: css" in out and f"{c1[:7]}  feat: route" in out and c2[:7] not in out
    assert f"{ROUTE}  -> {DOC}  (API Endpoints)" in out
    assert "frontend/src/index.css  -> .agents/docs/FRONTEND_GUIDELINES.md  (Color Palette)" in out
    assert "`Docs: later` does not satisfy CI" in out
    assert "Docs: n/a - <reason>" in out
    # fixing one doc in a follow-up commit clears only that commit
    R.write(repo, ".agents/docs/FRONTEND_GUIDELINES.md", "# palette\n")
    R.commit(repo, "docs: palette")
    proc = guard(repo, "--range", f"{base}..HEAD")
    assert proc.returncode == 1 and "1 commit(s)" in proc.stdout and c3[:7] not in proc.stdout


def test_range_empty_and_ci_only_still_enforces(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="ci-only")
    base = R.git(repo, "rev-parse", "HEAD")
    proc = guard(repo, "--range", f"{base}..HEAD")
    assert proc.returncode == 0 and "no commits" in proc.stdout
    R.write(repo, ROUTE)
    R.commit(repo, "feat: route")
    assert guard(repo, "--range", f"{base}..HEAD").returncode == 1


# ---------------------------------------------------------------- hook script


def install_payload(repo):
    shutil.copytree(R.BIN, repo / ".agents/bin", ignore=shutil.ignore_patterns("__pycache__"))


def run_hook(repo, text):
    return subprocess.run(["sh", str(R.HOOKS / "commit-msg"), msgfile(repo, text)], cwd=repo, capture_output=True, text=True)


def test_commit_msg_hook_delegates_to_doc_guard(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    stage(repo, ROUTE)
    proc = run_hook(repo, "feat: x")
    assert proc.returncode == 0 and "doc-guard skipped" in proc.stderr  # helper not installed yet
    install_payload(repo)
    proc = run_hook(repo, "feat: x")
    assert proc.returncode == 1 and proc.stdout == EXPECTED_FAILURE
    assert run_hook(repo, "feat: x\n\nDocs: n/a - internal").returncode == 0


def test_hook_wired_through_git_commit(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="strict")
    install_payload(repo)
    shutil.copytree(R.HOOKS, repo / ".agents/hooks")
    R.git(repo, "config", "core.hooksPath", ".agents/hooks")
    stage(repo, ROUTE)
    proc = subprocess.run(["git", "-C", str(repo), *R.GIT_IDENTITY, "commit", "-q", "-m", "feat: x"], capture_output=True, text=True)
    # git forwards commit-msg hook output on stderr
    assert proc.returncode != 0 and "doc-guard: staged changes touch documented areas" in (proc.stdout + proc.stderr)
    proc = subprocess.run(["git", "-C", str(repo), *R.GIT_IDENTITY, "commit", "-q", "-m", "feat: x\n\nDocs: n/a - internal"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------- worktree


def test_worktree_sees_commits_and_uncommitted_changes(tmp_path):
    repo = R.make_repo(tmp_path, doc_guard_mode="pr-strict")
    R.checkout(repo, "feat/x")
    # committed on the branch without docs, no trailer
    R.write(repo, ROUTE, "one\n")
    R.commit(repo, "feat: route", ROUTE)
    proc = guard(repo, "--worktree")
    assert proc.returncode == 1 and ROUTE in proc.stdout and "untouched" in proc.stdout
    # dry-run never fails
    assert guard(repo, "--worktree", "--dry-run").returncode == 0
    # an uncommitted doc edit satisfies it
    R.write(repo, DOC, "updated\n")
    proc = guard(repo, "--worktree")
    assert proc.returncode == 0 and "doc-guard: pass" in proc.stdout
    # a commit justified with n/a is not counted
    (repo / DOC).unlink()
    R.git(repo, "add", "-A")
    R.git(repo, "commit", "-q", "--amend", "-m", "feat: route\n\nDocs: n/a - internal only")
    R.write(repo, "backend/app/services/x.py", "svc\n")  # uncommitted, mapped
    proc = guard(repo, "--worktree")
    assert proc.returncode == 1 and "backend/app/services/x.py" in proc.stdout and ROUTE not in proc.stdout
