"""Hermetic temp-repo helpers shared by the helper tests (not a conftest: keeps ownership explicit)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parents[1]
BIN = PAYLOAD / "bin"
HOOKS = PAYLOAD / "hooks"
sys.path.insert(0, str(BIN))
import _lib  # noqa: E402

GIT_IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@t"]


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *GIT_IDENTITY, *args], check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def load_cfg(repo: Path) -> dict:
    return json.loads((repo / _lib.CONFIG_REL).read_text())


def save_cfg(repo: Path, cfg: dict) -> None:
    (repo / _lib.CONFIG_REL).write_text(json.dumps(cfg, indent=2))


def make_repo(tmp_path: Path, **cfg_overrides) -> Path:
    """git init -b main, write .agents/config.json from config.example.json, one initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    cfg = json.loads((PAYLOAD / "config.example.json").read_text())
    cfg["project_name"] = "t"
    cfg.update(cfg_overrides)
    (repo / ".agents").mkdir()
    save_cfg(repo, cfg)
    (repo / ".agents" / "docs").mkdir()
    (repo / ".agents" / "docs" / "PRD.md").write_text("# PRD\n")
    (repo / "README.md").write_text("# t\n")
    commit(repo, "init")
    return repo


def commit(repo: Path, message: str, *paths: str) -> str:
    git(repo, "add", "-A", *paths) if paths else git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def write(repo: Path, rel: str, text: str = "x\n") -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def checkout(repo: Path, branch: str, create: bool = True) -> None:
    git(repo, "checkout", "-q", *(["-b"] if create else []), branch)


def run(repo: Path, helper: str, *args: str, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a payload/bin helper via the current interpreter from inside the temp repo."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "CURSOR", "CODEX", "GROK"))}
    clean.update(env or {})
    return subprocess.run([sys.executable, str(BIN / helper), *args], cwd=cwd or repo, capture_output=True, text=True, env=clean)


def run_json(repo: Path, helper: str, *args: str):
    proc = run(repo, helper, *args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def write_plan(repo: Path, branch: str, meta: dict, body: str = "# Plan\n", ts: str = "20260901-120000") -> Path:
    cfg = load_cfg(repo)
    d = _lib.feature_plan_dir(repo, cfg, branch)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{_lib.safe_branch(branch)}-plan-{ts}.md"
    path.write_text(_lib.render_frontmatter(meta) + body)
    return path


def write_epic(repo: Path, slug: str, meta: dict, body: str = "# Epic\n", ts: str = "20260901-100000") -> Path:
    cfg = load_cfg(repo)
    d = _lib.epic_dir(repo, cfg, slug)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{slug}-epic-{ts}.md"
    path.write_text(_lib.render_frontmatter(dict(meta, plan_kind="epic")) + body)
    return path


def registry_put(repo: Path, key: str, entry: dict) -> dict:
    return _lib.registry_put(repo, load_cfg(repo), key, entry)


def log_review(repo: Path, plan: Path, skill: str, status: str, ts: str = "2026-09-02T10:00:00Z", **extra) -> dict:
    entry = {"skill": skill, "status": status, "plan": plan.name, "ts": ts, **extra}
    return _lib.review_log_append(repo, load_cfg(repo), entry)


def load_helper(name: str):
    """Import a bin helper in-process (they carry no .py suffix), for a test that must count calls
    into `_lib`; the helper's `import _lib` resolves to the same module object as `_repo._lib`."""
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(BIN / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
