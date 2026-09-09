"""Shared library for every helper in .agents/bin.

Standard library only. Python 3.10+.

Every helper imports this module for: repo and config discovery, path
resolution, git queries, plan discovery, plan frontmatter, the Obsidian
registry (one JSON file per entry), the review log (JSONL), and the JSON
output envelope used on stdout.

Nothing in this file may hardcode a project-specific path, branch name,
vault name, or directory layout. Everything comes from .agents/config.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
CONFIG_REL = ".agents/config.json"

# --------------------------------------------------------------------------
# Errors and output envelope
# --------------------------------------------------------------------------


class FrameworkError(Exception):
    """Raised for any user-facing failure. `payload` is merged into the JSON error."""

    def __init__(self, message: str, code: int = 1, **payload: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.payload = payload


def print_json(obj: Any, code: int = 0) -> int:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))
    return code


def fail(message: str, code: int = 1, **extra: Any) -> int:
    payload = {"status": "error", "error": message}
    payload.update(extra)
    return print_json(payload, code)


def run_main(fn) -> None:
    """Wrap a helper's main() so FrameworkError becomes a JSON error envelope."""
    try:
        sys.exit(fn())
    except FrameworkError as exc:
        sys.exit(fail(exc.message, exc.code, **exc.payload))


# --------------------------------------------------------------------------
# Time, text, files
# --------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def timestamp_slug() -> str:
    """YYYYMMDD-HHMMSS in local time, used in plan filenames."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(text: str, max_len: int = 80) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].rstrip("-")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj: Any) -> None:
    atomic_write(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def short_hash(text: str, n: int = 8) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


# --------------------------------------------------------------------------
# Repo, config, paths
# --------------------------------------------------------------------------


def git(root: Path | None, *args: str, check: bool = True) -> str:
    cmd = ["git"] + (["-C", str(root)] if root else []) + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise FrameworkError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root(start: Path | None = None) -> Path:
    """Locate the repo root. Prefer git; fall back to walking up for .git or .agents."""
    start = (start or Path.cwd()).resolve()
    try:
        out = git(start if start.is_dir() else start.parent, "rev-parse", "--show-toplevel")
        if out:
            return Path(out).resolve()
    except FrameworkError:
        pass
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists() or (candidate / ".agents").is_dir():
            return candidate
    raise FrameworkError("not inside a git repository or framework project", code=2)


def config_path(root: Path) -> Path:
    return root / CONFIG_REL


REQUIRED_CONFIG_KEYS = ("schema_version", "project_name", "default_branch", "vault_path", "paths", "doc_map", "doc_guard_mode")


def load_config(root: Path) -> dict:
    path = config_path(root)
    if not path.exists():
        raise FrameworkError(f"missing {CONFIG_REL}; run `framework init` first", code=2)
    try:
        cfg = read_json(path)
    except json.JSONDecodeError as exc:
        raise FrameworkError(f"{CONFIG_REL} is not valid JSON: {exc}", code=2)
    missing = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg]
    if missing:
        raise FrameworkError(f"{CONFIG_REL} missing keys: {', '.join(missing)}", code=2)
    for k in ("docs", "plans", "state"):
        if k not in cfg["paths"]:
            raise FrameworkError(f"{CONFIG_REL} paths.{k} missing", code=2)
    if cfg["schema_version"] != SCHEMA_VERSION:
        raise FrameworkError(
            f"{CONFIG_REL} schema_version {cfg['schema_version']} != {SCHEMA_VERSION}; run `framework upgrade`",
            code=2,
        )
    if cfg["doc_guard_mode"] not in ("strict", "pr-strict", "ci-only"):
        raise FrameworkError(f"{CONFIG_REL} doc_guard_mode must be strict, pr-strict, or ci-only", code=2)
    return cfg


def save_config(root: Path, cfg: dict) -> None:
    write_json(config_path(root), cfg)


def _resolve(root: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (root / p)


def docs_dir(root: Path, cfg: dict) -> Path:
    return _resolve(root, cfg["paths"]["docs"])


def plans_dir(root: Path, cfg: dict) -> Path:
    return _resolve(root, cfg["paths"]["plans"])


def state_dir(root: Path, cfg: dict) -> Path:
    return _resolve(root, cfg["paths"]["state"])


def vault_dir(root: Path, cfg: dict) -> Path:
    return _resolve(root, cfg["vault_path"])


def agents_dir(root: Path) -> Path:
    return root / ".agents"


def repo_relpath(root: Path, path: Path) -> str:
    """POSIX path relative to the repo root; absolute if outside the repo."""
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def vault_relpath(root: Path, cfg: dict, path: Path) -> str:
    """POSIX path relative to the vault root. Raises if the path is outside the vault."""
    vault = vault_dir(root, cfg).resolve()
    try:
        return Path(path).resolve().relative_to(vault).as_posix()
    except ValueError:
        raise FrameworkError(f"{path} is not inside the vault at {vault}", code=2)


def resolve_note_path(root: Path, cfg: dict, given: str) -> Path:
    """Accept a vault-relative, repo-relative, or absolute note path and return the absolute path."""
    given_path = Path(given).expanduser()
    candidates = []
    if given_path.is_absolute():
        candidates.append(given_path)
    else:
        candidates.append(vault_dir(root, cfg) / given_path)
        candidates.append(root / given_path)
        candidates.append(Path.cwd() / given_path)
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FrameworkError(f"note not found: {given}", code=2, tried=[str(c) for c in candidates])


# --------------------------------------------------------------------------
# Git and branch helpers
# --------------------------------------------------------------------------


def current_branch(root: Path) -> str | None:
    try:
        out = git(root, "branch", "--show-current")
        return out or None
    except FrameworkError:
        return None


def safe_branch(branch: str) -> str:
    return branch.replace("/", "-")


def base_branch(root: Path, cfg: dict) -> str:
    configured = cfg.get("default_branch")
    if configured:
        return configured
    try:
        ref = git(root, "symbolic-ref", "refs/remotes/origin/HEAD")
        return ref.rsplit("/", 1)[-1]
    except FrameworkError:
        pass
    for name in ("main", "master"):
        try:
            git(root, "rev-parse", "--verify", "--quiet", name)
            return name
        except FrameworkError:
            continue
    return "main"


def on_base_branch(root: Path, cfg: dict) -> bool:
    return current_branch(root) == base_branch(root, cfg)


def head_sha(root: Path, short: bool = True) -> str | None:
    try:
        return git(root, "rev-parse", "--short" if short else "--verify", "HEAD")
    except FrameworkError:
        return None


def detect_harness() -> str:
    env = os.environ
    if env.get("CLAUDE_PROJECT_DIR") or env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude-code"
    if any(k.startswith("CURSOR") for k in env):
        return "cursor"
    if any(k.startswith("CODEX") for k in env):
        return "codex"
    if any(k.startswith("GROK") for k in env):
        return "grok"
    return "unknown"


# --------------------------------------------------------------------------
# Glob matching (supports ** and matches against POSIX repo-relative paths)
# --------------------------------------------------------------------------


def glob_to_regex(pattern: str) -> re.Pattern:
    out = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
            continue
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(path: str, patterns: Iterable[str]) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


# --------------------------------------------------------------------------
# Plan discovery
# --------------------------------------------------------------------------

PLAN_TS_RE = re.compile(r"-(plan|epic)-(\d{8}-\d{6})")


def plan_timestamp(path: Path) -> str:
    m = PLAN_TS_RE.search(path.name)
    return m.group(2) if m else ""


def is_summary(path: Path) -> bool:
    return path.name.endswith("-summary.md")


def feature_plan_dir(root: Path, cfg: dict, branch: str) -> Path:
    return plans_dir(root, cfg) / "features" / safe_branch(branch)


def epics_dir(root: Path, cfg: dict) -> Path:
    return plans_dir(root, cfg) / "epics"


def epic_dir(root: Path, cfg: dict, slug: str) -> Path:
    return epics_dir(root, cfg) / slug


def testing_dir(root: Path, cfg: dict) -> Path:
    return plans_dir(root, cfg) / "testing"


def quickfix_log_path(root: Path, cfg: dict) -> Path:
    return plans_dir(root, cfg) / "quickfixes" / "LOG.md"


def find_plan_files(directory: Path, kind: str = "plan") -> list[Path]:
    """Plan files in a directory, newest first by the timestamp in the filename."""
    if not directory.is_dir():
        return []
    files = [p for p in directory.glob(f"*-{kind}-*.md") if not is_summary(p)]
    files.sort(key=lambda p: (plan_timestamp(p), p.name), reverse=True)
    return files


def latest_plan(root: Path, cfg: dict, branch: str) -> Path | None:
    files = find_plan_files(feature_plan_dir(root, cfg, branch))
    return files[0] if files else None


def latest_epic(root: Path, cfg: dict, slug: str) -> Path | None:
    files = find_plan_files(epic_dir(root, cfg, slug), kind="epic")
    return files[0] if files else None


def all_epics(root: Path, cfg: dict) -> list[Path]:
    out = []
    base = epics_dir(root, cfg)
    if base.is_dir():
        for d in sorted(base.iterdir()):
            if d.is_dir():
                latest = latest_epic(root, cfg, d.name)
                if latest:
                    out.append(latest)
    return out


def summary_path_for(plan: Path) -> Path:
    return plan.with_name(plan.stem + "-summary.md")


def test_artifact_path(root: Path, cfg: dict, branch: str) -> Path:
    return testing_dir(root, cfg) / f"{safe_branch(branch)}-test-artifact.md"


# --------------------------------------------------------------------------
# Frontmatter (flat keys; values are JSON scalars or JSON collections)
# --------------------------------------------------------------------------

FRONTMATTER_ORDER = [
    "plan_kind",
    "obsidian_workflow",
    "plan_mode",
    "source_note_path",
    "source_task_id",
    "source_note_ref",
    "source_tasks",
    "task_count",
    "source_heading",
    "source_task_text",
    "registry_key",
    "parent_epic",
    "milestone",
    "ui_scope",
    "risk_tags",
    "supersedes",
    "workflow_status",
    "review_status",
    "implementation_status",
    "completed",
    "reason",
    "updated_at",
]

_FM_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*):\s*(.*)$")


def parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == "":
        return ""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def serialize_scalar(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Body keeps its original text if there is no frontmatter."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    rest = text[end + 4 :]
    if rest.startswith("\n"):
        rest = rest[1:]
    meta: dict = {}
    for line in block.splitlines():
        m = _FM_KEY_RE.match(line)
        if m:
            meta[m.group(1)] = parse_scalar(m.group(2))
    return meta, rest


def read_frontmatter(path: Path) -> dict:
    return split_frontmatter(read_text(path))[0]


def render_frontmatter(meta: dict, order: list[str] | None = None) -> str:
    order = order or FRONTMATTER_ORDER
    keys = [k for k in order if k in meta] + sorted(k for k in meta if k not in order)
    lines = ["---"] + [f"{k}: {serialize_scalar(meta[k])}" for k in keys] + ["---", ""]
    return "\n".join(lines)


def write_frontmatter(path: Path, meta: dict, order: list[str] | None = None) -> None:
    _, body = split_frontmatter(read_text(path))
    atomic_write(path, render_frontmatter(meta, order) + body)


def update_frontmatter(path: Path, updates: dict, appends: dict | None = None) -> dict:
    """Merge updates into a plan's frontmatter. `appends` adds to list-valued keys without duplicates."""
    meta = read_frontmatter(path)
    meta.update(updates)
    for key, values in (appends or {}).items():
        current = meta.get(key)
        if current in (None, "", "not-started", "pending"):
            current = []
        elif isinstance(current, str):
            current = [current]
        for v in values if isinstance(values, list) else [values]:
            if v not in current:
                current.append(v)
        meta[key] = current
    meta["updated_at"] = now_iso()
    write_frontmatter(path, meta)
    return meta


def truthy(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in ("true", "yes", "1"))


# --------------------------------------------------------------------------
# Registry: one JSON file per entry under state/registry/
# --------------------------------------------------------------------------

REGISTRY_VERSION = 3


def registry_dir(root: Path, cfg: dict) -> Path:
    return state_dir(root, cfg) / "registry"


def entries_dir(root: Path, cfg: dict) -> Path:
    return registry_dir(root, cfg) / "entries"


def task_ids_dir(root: Path, cfg: dict) -> Path:
    return registry_dir(root, cfg) / "task-ids"


def entry_filename(key: str) -> str:
    """Readable, unique filename for a registry key."""
    slug = key.replace("#^", "--").replace("#batch", "--batch").replace("/", "__").replace(":", "--")
    slug = re.sub(r"[^A-Za-z0-9._\-]+", "_", slug).strip("_")[:120]
    return f"{slug}--{short_hash(key)}.json"


def registry_get(root: Path, cfg: dict, key: str) -> dict | None:
    path = entries_dir(root, cfg) / entry_filename(key)
    return read_json(path) if path.exists() else None


def registry_put(root: Path, cfg: dict, key: str, entry: dict) -> dict:
    entry = dict(entry)
    entry["key"] = key
    entry.setdefault("created_at", now_iso())
    entry["updated_at"] = now_iso()
    entry["registry_version"] = REGISTRY_VERSION
    write_json(entries_dir(root, cfg) / entry_filename(key), entry)
    return entry


def registry_delete(root: Path, cfg: dict, key: str) -> bool:
    path = entries_dir(root, cfg) / entry_filename(key)
    if path.exists():
        path.unlink()
        return True
    return False


def registry_all(root: Path, cfg: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    d = entries_dir(root, cfg)
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                entry = read_json(p)
            except json.JSONDecodeError:
                continue
            key = entry.get("key")
            if key:
                out[key] = entry
    return out


def task_id_get(root: Path, cfg: dict, task_id: str) -> dict | None:
    path = task_ids_dir(root, cfg) / f"{task_id}.json"
    return read_json(path) if path.exists() else None


def task_id_put(root: Path, cfg: dict, task_id: str, record: dict) -> dict:
    record = dict(record)
    record["task_id"] = task_id
    record["updated_at"] = now_iso()
    write_json(task_ids_dir(root, cfg) / f"{task_id}.json", record)
    return record


def task_ids_all(root: Path, cfg: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    d = task_ids_dir(root, cfg)
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                rec = read_json(p)
            except json.JSONDecodeError:
                continue
            if rec.get("task_id"):
                out[rec["task_id"]] = rec
    return out


# Registry key conventions
def plan_key(branch: str) -> str:
    return f"plan:{safe_branch(branch)}"


def epic_key(slug: str) -> str:
    return f"epic:{slug}"


def quickfix_key(slug: str) -> str:
    return f"quickfix:{slug}"


def note_key(note_rel: str, task_id: str | None) -> str:
    return f"{note_rel}#^{task_id}" if task_id else f"{note_rel}#batch"


# --------------------------------------------------------------------------
# Review log (JSONL)
# --------------------------------------------------------------------------


def review_log_path(root: Path, cfg: dict) -> Path:
    return state_dir(root, cfg) / "review-log.jsonl"


def review_log_append(root: Path, cfg: dict, entry: dict) -> dict:
    entry = dict(entry)
    entry.setdefault("ts", now_iso())
    entry.setdefault("harness", detect_harness())
    branch = current_branch(root)
    if branch:
        entry.setdefault("branch", branch)
        if "plan" not in entry:
            plan = latest_plan(root, cfg, branch)
            if plan:
                entry["plan"] = plan.name
    entry.setdefault("commit", head_sha(root))
    path = review_log_path(root, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def review_log_read(root: Path, cfg: dict) -> list[dict]:
    path = review_log_path(root, cfg)
    if not path.exists():
        return []
    out = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


REVIEW_STD_FIELDS = ("skill", "ts", "status", "branch", "plan", "commit", "harness")


def review_extra(entry: dict) -> dict:
    """Fields of a review-log entry beyond the standard envelope (skill/ts/status/branch/plan/commit/harness)."""
    return {k: v for k, v in entry.items() if k not in REVIEW_STD_FIELDS}


def reviews_for_plan(root: Path, cfg: dict, plan_name: str) -> dict[str, dict]:
    """Latest entry per skill logged against this plan file. Age is not a factor."""
    latest: dict[str, dict] = {}
    for e in review_log_read(root, cfg):
        if e.get("plan") != plan_name:
            continue
        skill = e.get("skill")
        if not skill:
            continue
        if skill not in latest or e.get("ts", "") >= latest[skill].get("ts", ""):
            latest[skill] = e
    return latest


# --------------------------------------------------------------------------
# Epics: milestone progress derived from the registry
# --------------------------------------------------------------------------

MILESTONE_DONE_STATUSES = ("shipped", "subsumed")
MILESTONE_ACTIVE_STATUSES = ("implementing", "ready-for-review", "blocked", "needs-context")


def epic_slug_from_path(path: Path) -> str:
    """Epic slug for an epic plan file: the directory it lives in under plans/epics/."""
    return path.parent.name


def epic_progress(root: Path, cfg: dict, slug: str) -> dict:
    """Derive an epic's milestone progress. Pure: reads the registry and the epic file only.

    Milestone list comes from the epic registry record (`epic:<slug>`, key `milestones`)
    or, failing that, the epic file's frontmatter `milestones`. Each milestone is
    `{"id": "M1", "title": "...", "size": "plan"|"quickfix", "status": ...}` (a bare
    string is treated as an id). A milestone's status is taken from the most recently
    updated child registry entry with `parent_epic == slug` and `milestone == id`
    (`implementation_status`, else `status`); otherwise the milestone's own `status`
    in the epic record (how `subsumed` is recorded); otherwise `not-started`.
    Children that name a milestone missing from the list are appended.

    Returns {slug, key, title, epic_file, status, milestones, total, shipped, subsumed,
    in_progress, not_started, next, done}. `next` is the first milestone whose status is
    not shipped/subsumed, or None.
    """
    record = registry_get(root, cfg, epic_key(slug)) or {}
    epic_file = latest_epic(root, cfg, slug)
    meta = read_frontmatter(epic_file) if epic_file else {}
    listed = record.get("milestones") or meta.get("milestones") or []
    if not isinstance(listed, list):
        listed = []

    children: dict[str, list[dict]] = {}
    for entry in registry_all(root, cfg).values():
        if entry.get("parent_epic") == slug and entry.get("milestone"):
            children.setdefault(str(entry["milestone"]), []).append(entry)

    milestones: list[dict] = []
    seen: set[str] = set()

    def build(mid: str, spec: dict) -> dict:
        matches = sorted(children.get(mid, []), key=lambda e: e.get("updated_at", ""))
        child = matches[-1] if matches else None
        status = None
        if child:
            status = child.get("implementation_status") or child.get("status")
        status = status or spec.get("status") or "not-started"
        return {
            "id": mid,
            "title": spec.get("title") or (child or {}).get("title") or "",
            "size": spec.get("size") or ("quickfix" if (child or {}).get("kind") == "quickfix" else "plan"),
            "status": status,
            "branch": (child or {}).get("branch") or spec.get("branch"),
            "plan": (child or {}).get("plan") or (child or {}).get("plan_path") or spec.get("plan") or spec.get("plan_path"),
            "key": (child or {}).get("key"),
            "completed": (child or {}).get("completed") or spec.get("completed"),
        }

    for i, spec in enumerate(listed, 1):
        if isinstance(spec, str):
            spec = {"id": spec}
        if not isinstance(spec, dict):
            continue
        mid = str(spec.get("id") or f"M{i}")
        if mid in seen:
            continue
        seen.add(mid)
        milestones.append(build(mid, spec))
    for mid in sorted(children, key=_milestone_sort_key):
        if mid not in seen:
            seen.add(mid)
            milestones.append(build(mid, {}))

    shipped = sum(1 for m in milestones if m["status"] == "shipped")
    subsumed = sum(1 for m in milestones if m["status"] == "subsumed")
    in_progress = sum(1 for m in milestones if m["status"] in MILESTONE_ACTIVE_STATUSES)
    total = len(milestones)
    done = total > 0 and shipped + subsumed == total
    next_ms = next((m for m in milestones if m["status"] not in MILESTONE_DONE_STATUSES), None)
    status = record.get("status") or meta.get("implementation_status") or ("shipped" if done else "active")
    return {
        "slug": slug,
        "key": epic_key(slug),
        "title": record.get("title") or meta.get("title") or slug,
        "epic_file": repo_relpath(root, epic_file) if epic_file else record.get("epic_file"),
        "status": status,
        "milestones": milestones,
        "total": total,
        "shipped": shipped,
        "subsumed": subsumed,
        "in_progress": in_progress,
        "not_started": total - shipped - subsumed - in_progress,
        "next": next_ms,
        "done": done,
    }


def _milestone_sort_key(mid: str) -> tuple:
    m = re.match(r"^[A-Za-z]*(\d+)", mid)
    return (0, int(m.group(1)), mid) if m else (1, 0, mid)


def all_epic_slugs(root: Path, cfg: dict) -> list[str]:
    """Union of epic directories under plans/epics/ and `epic:` registry keys, sorted."""
    slugs = {epic_slug_from_path(p) for p in all_epics(root, cfg)}
    slugs.update(k.split(":", 1)[1] for k in registry_all(root, cfg) if k.startswith("epic:"))
    return sorted(slugs)


# --------------------------------------------------------------------------
# Doc map
# --------------------------------------------------------------------------


def doc_owners(cfg: dict, path: str) -> list[dict]:
    """Doc-map rules that own a repo-relative path. Empty if exempt or unmapped."""
    dm = cfg.get("doc_map", {})
    if glob_match(path, dm.get("exempt", [])):
        return []
    return [rule for rule in dm.get("rules", []) if glob_match(path, rule.get("paths", []))]


def doc_rel(cfg: dict, doc_name: str) -> str:
    """Repo-relative path of a doc named in the doc map."""
    docs = cfg["paths"]["docs"].rstrip("/")
    return f"{docs}/{doc_name}"


# --------------------------------------------------------------------------
# Context bundle used by `ctx` and the SessionStart banner
# --------------------------------------------------------------------------


def context(root: Path | None = None) -> dict:
    root = root or repo_root()
    cfg = load_config(root)
    branch = current_branch(root)
    base = base_branch(root, cfg)
    plan = latest_plan(root, cfg, branch) if branch else None
    return {
        "REPO_ROOT": str(root),
        "PROJECT": cfg["project_name"],
        "BRANCH": branch or "",
        "SAFE_BRANCH": safe_branch(branch) if branch else "",
        "BASE_BRANCH": base,
        "ON_BASE": "1" if branch == base else "0",
        # Absolute paths: skills run shell from wherever the harness left the cwd.
        # Helpers normalize to repo-relative when they store a path.
        "DOCS_DIR": str(docs_dir(root, cfg)),
        "PLANS_DIR": str(plans_dir(root, cfg)),
        "STATE_DIR": str(state_dir(root, cfg)),
        "VAULT_DIR": str(vault_dir(root, cfg)),
        "PLAN_DIR": str(feature_plan_dir(root, cfg, branch)) if branch else "",
        "PLAN_FILE": str(plan) if plan else "",
        "SUMMARY_FILE": str(summary_path_for(plan)) if plan else "",
        "TEST_ARTIFACT": str(test_artifact_path(root, cfg, branch)) if branch else "",
        "HARNESS": detect_harness(),
        "TIMESTAMP": timestamp_slug(),
    }
