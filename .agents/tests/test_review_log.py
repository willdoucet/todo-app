"""review-log (append) and review-read (query) against state/review-log.jsonl."""

from __future__ import annotations

import json

import _repo as R


def entries(repo) -> list[dict]:
    path = R._lib.review_log_path(repo, R.load_cfg(repo))
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_json_form_autofills_context(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    out = R.run_json(repo, "review-log", '{"skill":"plan-eng-review","status":"clean","issues":2}')
    assert out["skill"] == "plan-eng-review" and out["status"] == "clean" and out["issues"] == 2
    assert out["branch"] == "feat/x" and out["plan"] == plan.name
    assert out["commit"] == R.git(repo, "rev-parse", "--short", "HEAD")
    assert out["ts"].endswith("Z") and out["harness"] == "unknown"
    assert entries(repo) == [out]


def test_flag_form_fields_and_plan_override(tmp_path):
    repo = R.make_repo(tmp_path)
    out = R.run_json(
        repo, "review-log", "--skill", "qa", "--status", "issues_found",
        "--field", "issues=3", "--field", "notes=fixed in place", "--field", "tags=[\"a\"]", "--plan", "other-plan.md",
    )
    assert out["issues"] == 3 and out["notes"] == "fixed in place" and out["tags"] == ["a"]
    assert out["plan"] == "other-plan.md" and out["branch"] == "main"
    # explicit fields in JSON win over auto-fill
    out2 = R.run_json(repo, "review-log", '{"skill":"ship","status":"done","ts":"2026-01-01T00:00:00Z","branch":"b"}')
    assert out2["ts"] == "2026-01-01T00:00:00Z" and out2["branch"] == "b"
    assert len(entries(repo)) == 2


def test_errors_are_json(tmp_path):
    repo = R.make_repo(tmp_path)
    proc = R.run(repo, "review-log", "--skill", "qa")
    assert proc.returncode == 1 and json.loads(proc.stdout)["status"] == "error"
    proc = R.run(repo, "review-log", "{not json")
    assert proc.returncode == 1 and "valid JSON" in json.loads(proc.stdout)["error"]
    proc = R.run(repo, "review-log", "--skill", "qa", "--status", "x", "--field", "novalue")
    assert proc.returncode == 1
    assert entries(repo) == [] if R._lib.review_log_path(repo, R.load_cfg(repo)).exists() else True


def test_review_read_default_latest_per_skill(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    other = R.write_plan(repo, "feat/x", {}, ts="20260701-000000")  # older plan file on the same branch
    R.log_review(repo, plan, "plan-eng-review", "issues_found", ts="2026-09-01T00:00:00Z", issues=2)
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z", issues=0)
    R.log_review(repo, plan, "qa", "pass", ts="2026-09-03T00:00:00Z")
    R.log_review(repo, other, "final-review", "clean", ts="2026-09-04T00:00:00Z")
    proc = R.run(repo, "review-read")
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [
        "plan-eng-review|2026-09-02T00:00:00Z|clean|issues=0",
        "qa|2026-09-03T00:00:00Z|pass|",
    ]
    data = R.run_json(repo, "review-read", "--json")
    assert data["plan"] == plan.name and set(data["reviews"]) == {"plan-eng-review", "qa"}
    assert data["reviews"]["plan-eng-review"]["issues"] == 0
    # --plan overrides auto-detection
    assert R.run(repo, "review-read", "--plan", other.name).stdout.splitlines() == ["final-review|2026-09-04T00:00:00Z|clean|"]
    assert R.run_json(repo, "review-read", "--plan", "missing.md", "--json")["reviews"] == {}
    assert R.run(repo, "review-read", "--plan", "missing.md").stdout.strip() == "(no reviews for plan: missing.md)"


def test_review_read_all_newest_first_with_plan_column(tmp_path):
    repo = R.make_repo(tmp_path)
    assert R.run(repo, "review-read", "--all").stdout.strip() == "(no reviews logged)"
    assert R.run(repo, "review-read").stdout.strip() == "(no plan on this branch)"
    assert R.run_json(repo, "review-read", "--json") == {"plan": None, "reviews": {}}
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-01T00:00:00Z")
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z", issues=1)
    R._lib.review_log_append(repo, R.load_cfg(repo), {"skill": "ship", "status": "done", "ts": "2026-09-03T00:00:00Z", "plan": "z.md"})
    lines = R.run(repo, "review-read", "--all").stdout.splitlines()
    assert lines == [
        "z.md|ship|2026-09-03T00:00:00Z|done|",
        f"{plan.name}|plan-eng-review|2026-09-02T00:00:00Z|clean|issues=1",
        f"{plan.name}|plan-eng-review|2026-09-01T00:00:00Z|clean|",
    ]
    data = R.run_json(repo, "review-read", "--all", "--json")
    assert [e["ts"] for e in data["entries"]] == ["2026-09-03T00:00:00Z", "2026-09-02T00:00:00Z", "2026-09-01T00:00:00Z"]
