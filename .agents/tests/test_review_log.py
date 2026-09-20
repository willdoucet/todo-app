"""review-log (validated append) and review-read (query) against state/review-log.jsonl."""

from __future__ import annotations

import json

import pytest

import _repo as R


def entries(repo) -> list[dict]:
    path = R._lib.review_log_path(repo, R.load_cfg(repo))
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def log_bytes(repo) -> bytes:
    path = R._lib.review_log_path(repo, R.load_cfg(repo))
    return path.read_bytes() if path.exists() else b""


def error(proc) -> dict:
    assert proc.returncode != 0, proc.stdout
    data = json.loads(proc.stdout)
    assert data["status"] == "error"
    return data


def test_json_form_autofills_context(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    out = R.run_json(repo, "review-log", '{"skill":"plan-eng-review","status":"clean","rereview":[],"issues":2}')
    assert out["skill"] == "plan-eng-review" and out["status"] == "clean" and out["issues"] == 2 and out["rereview"] == []
    assert out["branch"] == "feat/x" and out["plan"] == plan.name
    assert out["commit"] == R.git(repo, "rev-parse", "--short", "HEAD")
    assert out["ts"].endswith("Z") and out["harness"] == "unknown"
    assert entries(repo) == [out]


def test_flag_form_fields_and_plan_override(tmp_path):
    repo = R.make_repo(tmp_path)
    out = R.run_json(
        repo, "review-log", "--skill", "qa", "--status", "issues_open",
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
    proc = R.run(repo, "review-log", "--skill", "qa", "--status", "clean", "--field", "novalue")
    assert proc.returncode == 1
    assert entries(repo) == [] if R._lib.review_log_path(repo, R.load_cfg(repo)).exists() else True


# ---------------------------------------------------------------- vocabulary


@pytest.mark.parametrize("word", ["issues_found", "fixed", "pass", "cleared", "skipped", "neutral", "Clean", "CLEAN", " clean"])
def test_unknown_status_rejected_in_both_forms(tmp_path, word):
    repo = R.make_repo(tmp_path)
    for argv in (["--skill", "qa", "--status", word], [json.dumps({"skill": "qa", "status": word})]):
        err = error(R.run(repo, "review-log", *argv))
        assert f"unknown status {word!r}" in err["error"]
        assert "use one of: clean, issues_open, resolved, done" in err["error"]
    assert log_bytes(repo) == b""


def test_done_is_ships_word(tmp_path):
    repo = R.make_repo(tmp_path)
    err = error(R.run(repo, "review-log", "--skill", "qa", "--status", "done"))
    assert "'done' is written by 'ship' only" in err["error"]
    err = error(R.run(repo, "review-log", '{"skill":"final-review","status":"done"}'))
    assert "'done' is written by 'ship' only" in err["error"]
    assert log_bytes(repo) == b""
    assert R.run_json(repo, "review-log", "--skill", "ship", "--status", "done")["status"] == "done"
    assert R.run_json(repo, "review-log", "--skill", "qa", "--status", "clean")["status"] == "clean"
    assert R.run_json(repo, "review-log", "--skill", "qa", "--status", "issues_open")["status"] == "issues_open"


def test_field_cannot_smuggle_status_or_skill(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-03T00:00:00Z")
    before = log_bytes(repo)
    for argv in (
        ["--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x", "--field", "status=clean"],
        ['{"skill":"plan-ceo-review","status":"resolved","resolved_by":"plan-eng-review","note":"x"}', "--field", "status=clean"],
        ["--skill", "qa", "--status", "issues_open", "--field", "skill=ship"],
        ["--skill", "qa", "--status", "done", "--field", "skill=ship"],
    ):
        err = error(R.run(repo, "review-log", *argv))
        assert "--field cannot set" in err["error"]
    assert log_bytes(repo) == before


@pytest.mark.parametrize(
    "argv",
    [
        [json.dumps({"skill": "plan-eng-review", "status": "clean", "rereview": [], "ts": None})],
        [json.dumps({"skill": "plan-eng-review", "status": "clean", "rereview": [], "ts": 123})],
        ["--skill", "plan-eng-review", "--status", "clean", "--rereview", "none", "--field", "ts=123"],
        ["--skill", "plan-eng-review", "--status", "clean", "--rereview", "none", "--field", "ts="],
    ],
)
def test_ts_must_be_a_non_empty_string_when_supplied(tmp_path, argv):
    # readers order entries by ts with string comparison; a null or number would raise inside them
    repo = R.make_repo(tmp_path)
    err = error(R.run(repo, "review-log", *argv))
    assert "ts must be UTC" in err["error"]
    assert log_bytes(repo) == b""
    assert R.run_json(repo, "review-log", "--skill", "plan-eng-review", "--status", "clean", "--rereview", "none", "--field", "ts=2026-09-01T00:00:00Z")["ts"] == "2026-09-01T00:00:00Z"


def test_ts_is_stamped_before_the_rules_run_and_never_in_the_future(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    import re
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", R.run_json(repo, "review-log", "--skill", "qa", "--status", "clean")["ts"])
    for value, needle in (("2099-01-01T00:00:00Z", "later than now"), ("2026-09-01", "ts must be UTC"), ("2026-09-01 00:00:00", "ts must be UTC"), ("2026-02-30T00:99:00Z", "real UTC datetime")):
        err = error(R.run(repo, "review-log", "--skill", "qa", "--status", "clean", "--field", f"ts={value}"))
        assert needle in err["error"], err["error"]
    # a failure dated ahead of this clock cannot be resolved silently: the stamped ts is compared too
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2099-01-01T00:00:00Z")
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2099-01-02T00:00:00Z")
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "earlier than the failed entry" in err["error"]
    assert log_bytes(repo) == before


def test_ship_logs_done_only_and_computed_fields_are_refused(tmp_path):
    repo = R.make_repo(tmp_path)
    for status in ("clean", "issues_open"):
        err = error(R.run(repo, "review-log", "--skill", "ship", "--status", status))
        assert "'ship' logs done only" in err["error"]
    for argv in (
        ["--skill", "qa", "--status", "clean", "--field", "disposition=passed"],
        ['{"skill":"qa","status":"clean","disposition":"passed"}'],
    ):
        assert "disposition is computed" in error(R.run(repo, "review-log", *argv))["error"]
    err = error(R.run(repo, "review-log", "--skill", "qa", "--status", "clean", "--field", "resolves_ts=2026-01-01T00:00:00Z"))
    assert "resolves_ts is filled" in err["error"]
    assert log_bytes(repo) == b""


def test_plan_override_normalizes_a_summary_name(tmp_path):
    repo = R.make_repo(tmp_path)
    out = R.run_json(repo, "review-log", "--skill", "qa", "--status", "clean", "--plan", "x-plan-20260101-120000-summary.md")
    assert out["plan"] == "x-plan-20260101-120000.md"
    out = R.run_json(repo, "review-log", '{"skill":"qa","status":"clean","plan":"y-plan-20260101-120000-summary.md"}')
    assert out["plan"] == "y-plan-20260101-120000.md"


def test_text_rows_quote_values_that_carry_separators(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "qa", "clean", ts="2026-09-01T00:00:00Z", note="a|b, c", plain="ok")
    assert R.run(repo, "review-read").stdout.strip() == 'qa|2026-09-01T00:00:00Z|clean|passed|note="a|b, c",plain=ok'
    assert 'note="a|b, c",plain=ok' in R.run(repo, "workflow-state", "--dashboard").stdout


# ---------------------------------------------------------------- resolved


def seeded(tmp_path, ceo_ts="2026-09-02T05:27:06Z", eng_ts="2026-09-02T21:41:42Z"):
    """A plan whose CEO review failed and whose eng review passed later (the M8 shape)."""
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts=ceo_ts, critical_gaps=1)
    R.log_review(repo, plan, "plan-eng-review", "clean", ts=eng_ts)
    return repo, plan


def test_resolved_accepted_and_fills_resolves_ts(tmp_path):
    repo, plan = seeded(tmp_path)
    out = R.run_json(
        repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved",
        "--field", "resolved_by=plan-eng-review", "--field", "note=item 2: break-glass entry",
    )
    assert out["status"] == "resolved" and out["skill"] == "plan-ceo-review" and out["plan"] == plan.name
    assert out["resolves_ts"] == "2026-09-02T05:27:06Z" and out["resolved_by"] == "plan-eng-review"
    latest = R._lib.reviews_for_plan(repo, R.load_cfg(repo), plan.name)["plan-ceo-review"]
    assert R._lib.review_disposition(latest) == "resolved"
    # a second resolution of the same review is refused
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=again"))
    assert "latest is resolved" in err["error"]


def test_resolved_accepts_same_second_resolver_and_rejects_earlier(tmp_path):
    # one skill step writes the failed subagent entry and its own passing entry in the same second
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "adversarial-subagent", "issues_open", ts="2026-09-11T16:19:20Z", issues_found=4)
    R.log_review(repo, plan, "review-implementation", "clean", ts="2026-09-11T16:19:20Z")
    out = R.run_json(repo, "review-log", "--skill", "adversarial-subagent", "--status", "resolved", "--field", "resolved_by=review-implementation", "--field", "note=all four fixed in 7beceb3")
    assert out["resolves_ts"] == "2026-09-11T16:19:20Z"

    (tmp_path / "two").mkdir()
    repo2 = R.make_repo(tmp_path / "two")
    R.checkout(repo2, "feat/x")
    plan2 = R.write_plan(repo2, "feat/x", {})
    R.log_review(repo2, plan2, "review-implementation", "clean", ts="2026-09-11T16:19:19Z")
    R.log_review(repo2, plan2, "adversarial-subagent", "issues_open", ts="2026-09-11T16:19:20Z")
    err = error(R.run(repo2, "review-log", "--skill", "adversarial-subagent", "--status", "resolved", "--field", "resolved_by=review-implementation", "--field", "note=x"))
    assert "before the failure" in err["error"]
    assert len(entries(repo2)) == 2


def test_resolved_by_operator_needs_no_flag(tmp_path):
    repo, _plan = seeded(tmp_path)
    out = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=operator", "--field", "note=user decided in session: accept")
    assert out["resolved_by"] == "operator" and out["resolves_ts"] == "2026-09-02T05:27:06Z"


def test_resolved_note_keeps_equals_sign(tmp_path):
    repo, _plan = seeded(tmp_path)
    out = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=operator", "--field", "note=closed in §3 = item 2")
    assert out["note"] == "closed in §3 = item 2"


REJECTIONS = [
    (["--field", "note=x"], "resolved_by"),
    (["--field", "resolved_by=plan-eng-review"], "note"),
    (["--field", "resolved_by=plan-eng-review", "--field", "note="], "note"),
    (["--field", "resolved_by=plan-eng-review", "--field", "note=true"], "note"),
    (["--field", "resolved_by=plan-eng-review", "--field", "note=1"], "note"),
    (["--field", "resolved_by=true", "--field", "note=x"], "resolved_by"),
    (["--field", "resolved_by=1", "--field", "note=x"], "resolved_by"),
    (["--field", "resolved_by=plan-ceo-review", "--field", "note=x"], "cannot resolve its own"),
    (["--field", "resolved_by=/plan-eng-review", "--field", "note=x"], "leading slash"),
    (["--field", "resolved_by=Operator", "--field", "note=x"], "'operator' or a gating review tier"),
    (["--field", "resolved_by=office-hours", "--field", "note=x"], "'operator' or a gating review tier"),
    (["--field", "resolved_by=execute-plan", "--field", "note=x"], "'operator' or a gating review tier"),
    (["--field", "resolved_by=plan-eng-review", "--field", "note=x", "--field", "resolves_ts=2026-01-01T00:00:00Z"], "resolves_ts is filled"),
    (["--field", "resolved_by=plan-eng-review", "--field", "note=x", "--field", "ts=2026-09-01T00:00:00Z"], "earlier than the failed entry"),
    (["--field", "resolved_by=qa", "--field", "note=x"], "latest entry on"),  # resolver never ran
    (["--field", "resolved_by=plan-design-review", "--field", "note=x"], "is resolved; the resolver"),  # resolver itself resolved
]


@pytest.mark.parametrize("extra,needle", REJECTIONS)
def test_resolved_rules_reject_in_flag_form(tmp_path, extra, needle):
    repo, plan = seeded(tmp_path)
    R.log_review(repo, plan, "plan-design-review", "issues_open", ts="2026-09-02T12:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "resolved", ts="2026-09-03T00:00:00Z", resolved_by="operator", note="n", resolves_ts="2026-09-02T12:00:00Z")
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", *extra))
    assert needle in err["error"], err["error"]
    assert log_bytes(repo) == before


@pytest.mark.parametrize("extra,needle", REJECTIONS)
def test_resolved_rules_reject_in_json_form(tmp_path, extra, needle):
    repo, plan = seeded(tmp_path)
    R.log_review(repo, plan, "plan-design-review", "issues_open", ts="2026-09-02T12:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "resolved", ts="2026-09-03T00:00:00Z", resolved_by="operator", note="n", resolves_ts="2026-09-02T12:00:00Z")
    fields = {}
    for item in extra[1::2]:
        k, v = item.split("=", 1)
        fields[k] = R._lib.parse_scalar(v)
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", json.dumps({"skill": "plan-ceo-review", "status": "resolved", **fields})))
    assert needle in err["error"], err["error"]
    assert log_bytes(repo) == before


def test_resolved_target_must_be_a_failed_gating_review(tmp_path):
    repo, plan = seeded(tmp_path)
    R.log_review(repo, plan, "execute-plan", "issues_open", ts="2026-09-04T00:00:00Z")
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", "--skill", "execute-plan", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "unknown skill 'execute-plan'" in err["error"]
    err = error(R.run(repo, "review-log", "--skill", "office-hours", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "nothing gates on 'office-hours'" in err["error"]
    err = error(R.run(repo, "review-log", "--skill", "plan-adversarial-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "no failed entry to resolve" in err["error"] and "latest is missing" in err["error"]
    err = error(R.run(repo, "review-log", "--skill", "plan-eng-review", "--status", "resolved", "--field", "resolved_by=plan-ceo-review", "--field", "note=x"))
    assert "latest is passed" in err["error"]
    assert log_bytes(repo) == before


def test_resolved_resolver_must_have_passed(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-eng-review", "issues_open", ts="2026-09-03T00:00:00Z")
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "is failed; the resolver must have run after the failure and passed" in err["error"]


def test_resolved_needs_a_plan(tmp_path):
    repo = R.make_repo(tmp_path)  # on main, no plan
    proc = R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=operator", "--field", "note=x")
    assert proc.returncode == 2 and "needs a plan" in json.loads(proc.stdout)["error"]
    assert log_bytes(repo) == b""


def test_unknown_skill_rejected_in_both_forms(tmp_path):
    repo = R.make_repo(tmp_path)
    for argv in (["--skill", "plan-eng-reveiw", "--status", "clean"], ['{"skill":"plan-eng-reveiw","status":"clean"}']):
        err = error(R.run(repo, "review-log", *argv))
        assert "unknown skill 'plan-eng-reveiw'" in err["error"] and "plan-eng-review" in err["error"]
    assert log_bytes(repo) == b""
    assert R.run_json(repo, "review-log", "--skill", "office-hours", "--status", "clean")["skill"] == "office-hours"


def test_resolver_must_share_the_failed_review_stage(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "review-implementation", "issues_open", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "qa", "issues_open", ts="2026-09-02T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "clean", ts="2026-09-03T00:00:00Z")
    R.log_review(repo, plan, "ship", "done", ts="2026-09-03T00:00:00Z")
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", "--skill", "review-implementation", "--status", "resolved", "--field", "resolved_by=plan-ceo-review", "--field", "note=x"))
    assert "ship stage" in err["error"]
    err = error(R.run(repo, "review-log", "--skill", "qa", "--status", "resolved", "--field", "resolved_by=ship", "--field", "note=x"))
    assert "'ship' cannot resolve" in err["error"]
    err = error(R.run(repo, "review-log", json.dumps({"skill": "qa", "status": "resolved", "resolved_by": "plan-ceo-review", "note": "x"})))
    assert "ship stage" in err["error"]
    err = error(R.run(repo, "review-log", json.dumps({"skill": "qa", "status": "resolved", "resolved_by": "ship", "note": "x"})))
    assert "'ship' cannot resolve" in err["error"]
    assert log_bytes(repo) == before
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-04T00:00:00Z")
    out = R.run_json(repo, "review-log", "--skill", "review-implementation", "--status", "resolved", "--field", "resolved_by=final-review", "--field", "note=x")
    assert out["resolves_ts"] == "2026-09-02T00:00:00Z"
    # a plan-stage failure takes any gating tier but ship
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-05T00:00:00Z")
    R.log_review(repo, plan, "final-review", "clean", ts="2026-09-06T00:00:00Z")
    assert R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=final-review", "--field", "note=x")["resolved_by"] == "final-review"


def test_superseded_resolution_is_resolved_again_naming_the_new_failure(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    T0, T1, T2, T3 = "2026-09-01T00:00:00Z", "2026-09-02T00:00:00Z", "2026-09-03T00:00:00Z", "2026-09-04T00:00:00Z"
    R.log_review(repo, plan, "qa", "issues_open", ts=T0)
    R.log_review(repo, plan, "qa", "resolved", ts=T2, resolved_by="operator", note="n", resolves_ts=T0)
    R.log_review(repo, plan, "qa", "issues_open", ts=T1)  # merged in later
    data = R.run_json(repo, "review-read", "--json")["reviews"]["qa"]
    assert data["disposition"] == "failed" and data["superseded_by_failure"] == T1
    R.log_review(repo, plan, "final-review", "clean", ts=T3)
    out = R.run_json(repo, "review-log", "--skill", "qa", "--status", "resolved", "--field", "resolved_by=final-review", "--field", "note=again")
    assert out["resolves_ts"] == T1
    assert R.run_json(repo, "review-read", "--json")["reviews"]["qa"]["disposition"] == "resolved"


# ---------------------------------------------------------------- unreadable log


def test_unreadable_log_refuses_append_and_read(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-03T00:00:00Z")
    path = R._lib.review_log_path(repo, R.load_cfg(repo))
    good = path.read_text()
    path.write_text(good + "<<<<<<< HEAD\n" + good + "\n" + good.replace("clean", "issues_open"))
    dirty = path.read_bytes()
    proc = R.run(repo, "review-log", "--skill", "qa", "--status", "clean")
    err = json.loads(proc.stdout)
    assert proc.returncode == 2 and err["unreadable"] == 1 and err["lines"] == [2]
    assert "unreadable line(s): 2" in err["error"] and "keep both sides" in err["error"]
    assert path.read_bytes() == dirty
    for argv in ([], ["--json"], ["--all"], ["--all", "--json"], ["--plan", plan.name]):
        proc = R.run(repo, "review-read", *argv)
        assert proc.returncode == 2, argv
        assert json.loads(proc.stdout)["unreadable"] == 1
    path.write_bytes(b"\xff\xfe" + dirty)
    proc = R.run(repo, "review-read")
    assert proc.returncode == 2 and "not valid UTF-8" in json.loads(proc.stdout)["error"]


# ---------------------------------------------------------------- review-read


def test_review_read_default_latest_per_skill(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    other = R.write_plan(repo, "feat/x", {}, ts="20260701-000000")  # older plan file on the same branch
    R.log_review(repo, plan, "plan-eng-review", "issues_found", ts="2026-09-01T00:00:00Z", issues=2)
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z", issues=0)
    R.log_review(repo, plan, "qa", "pass", ts="2026-09-03T00:00:00Z")
    R.log_review(repo, plan, "plan-ceo-review", "issues_found", ts="2026-09-04T00:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "issues_open", ts="2026-09-04T12:00:00Z")
    R.log_review(repo, plan, "plan-design-review", "resolved", ts="2026-09-05T00:00:00Z", resolved_by="operator", note="n", resolves_ts="2026-09-04T12:00:00Z")
    R.log_review(repo, other, "final-review", "clean", ts="2026-09-04T00:00:00Z")
    proc = R.run(repo, "review-read")
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [
        "plan-eng-review|2026-09-02T00:00:00Z|clean|passed|issues=0",
        "qa|2026-09-03T00:00:00Z|pass|passed|",
        "plan-ceo-review|2026-09-04T00:00:00Z|issues_found|failed|",
        "plan-design-review|2026-09-05T00:00:00Z|resolved|resolved|note=n,resolved_by=operator,resolves_ts=2026-09-04T12:00:00Z",
    ]
    data = R.run_json(repo, "review-read", "--json")
    assert data["plan"] == plan.name and set(data["reviews"]) == {"plan-eng-review", "qa", "plan-ceo-review", "plan-design-review"}
    assert data["reviews"]["plan-eng-review"]["issues"] == 0
    assert {k: v["disposition"] for k, v in data["reviews"].items()} == {
        "plan-eng-review": "passed", "qa": "passed", "plan-ceo-review": "failed", "plan-design-review": "resolved",
    }
    # --plan overrides auto-detection
    assert R.run(repo, "review-read", "--plan", other.name).stdout.splitlines() == ["final-review|2026-09-04T00:00:00Z|clean|passed|"]
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
        "z.md|ship|2026-09-03T00:00:00Z|done|passed|",
        f"{plan.name}|plan-eng-review|2026-09-02T00:00:00Z|clean|passed|issues=1",
        f"{plan.name}|plan-eng-review|2026-09-01T00:00:00Z|clean|passed|",
    ]
    data = R.run_json(repo, "review-read", "--all", "--json")
    assert [e["ts"] for e in data["entries"]] == ["2026-09-03T00:00:00Z", "2026-09-02T00:00:00Z", "2026-09-01T00:00:00Z"]
    assert [e["disposition"] for e in data["entries"]] == ["passed", "passed", "passed"]


def test_review_read_attaches_summary_named_legacy_entries(tmp_path):
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    cfg = R.load_cfg(repo)
    summary = plan.stem + "-summary.md"
    R._lib.review_log_append(repo, cfg, {"skill": "adversarial-subagent", "status": "issues_found", "plan": summary, "ts": "2026-04-17T05:53:53Z"})
    R._lib.review_log_append(repo, cfg, {"skill": "review-implementation", "status": "clean", "plan": summary, "ts": "2026-04-17T05:53:53Z"})
    R._lib.review_log_append(repo, cfg, {"skill": "review-implementation", "status": "issues_open", "plan": plan.name, "ts": "2026-04-18T00:00:00Z"})
    data = R.run_json(repo, "review-read", "--json")
    assert data["reviews"]["adversarial-subagent"]["disposition"] == "failed"
    # --plan <summary> normalizes the same way as write
    assert R.run_json(repo, "review-read", "--plan", summary, "--json")["plan"] == plan.name
    assert R.run_json(repo, "review-read", "--plan", summary, "--json")["reviews"]["adversarial-subagent"]["disposition"] == "failed"
    assert data["reviews"]["adversarial-subagent"]["plan"] == summary  # the raw value is kept
    assert data["reviews"]["review-implementation"]["ts"] == "2026-04-18T00:00:00Z"  # newest wins across both names
    lines = R.run(repo, "review-read").stdout.splitlines()
    assert lines[0].startswith("adversarial-subagent|2026-04-17T05:53:53Z|issues_found|failed|")


# ---------------------------------------------------------------- the declaration


def declared(tmp_path):
    """A feature-branch plan whose eng and adversarial reviews have run."""
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "clean", ts="2026-09-02T00:00:00Z", rereview=[])
    R.log_review(repo, plan, "plan-adversarial-review", "clean", ts="2026-09-03T00:00:00Z", rereview=[])
    return repo, plan


def test_plan_reviews_must_declare_in_both_forms(tmp_path):
    repo, plan = declared(tmp_path)
    before = log_bytes(repo)
    for skill in ("plan-ceo-review", "plan-eng-review", "plan-adversarial-review", "plan-design-review"):
        for status in ("clean", "issues_open"):
            for argv in (["--skill", skill, "--status", status], [json.dumps({"skill": skill, "status": status})]):
                err = error(R.run(repo, "review-log", *argv))
                assert f"{skill} must declare re-reviews" in err["error"] and "--rereview none" in err["error"] and "--rereview <skill>" in err["error"]
    assert log_bytes(repo) == before
    out = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "clean", "--rereview", "none")
    assert out["rereview"] == [] and "rereview_note" not in out
    assert R.run_json(repo, "review-log", '{"skill":"plan-ceo-review","status":"issues_open","rereview":[]}')["rereview"] == []
    # ship-stage reviews may declare and need not; office-hours and ship never must
    assert "rereview" not in R.run_json(repo, "review-log", "--skill", "qa", "--status", "clean")
    assert "rereview" not in R.run_json(repo, "review-log", "--skill", "office-hours", "--status", "issues_open", "--field", "concerns=3")
    assert R.run_json(repo, "review-log", "--skill", "ship", "--status", "done")["status"] == "done"


def test_a_demand_is_accepted_and_stored(tmp_path):
    repo, plan = declared(tmp_path)
    out = R.run_json(repo, "review-log", "--skill", "plan-design-review", "--status", "clean", "--rereview", "plan-eng-review", "--rereview", "plan-eng-review", "--rereview-note", "15a adds a backend contract")
    assert out["rereview"] == ["plan-eng-review"] and out["rereview_note"] == "15a adds a backend contract" and out["plan"] == plan.name
    assert entries(repo)[-1]["rereview"] == ["plan-eng-review"]
    # positional JSON, two targets deduplicated, a failed target accepted, design accepted whatever ui_scope says
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-04T00:00:00Z", rereview=[])
    out = R.run_json(repo, "review-log", json.dumps({"skill": "plan-adversarial-review", "status": "clean", "rereview": ["plan-ceo-review", "plan-design-review", "plan-ceo-review"], "rereview_note": "both"}))
    assert out["rereview"] == ["plan-ceo-review", "plan-design-review"]
    data = R.run_json(repo, "review-read", "--json")["reviews"]
    assert data["plan-eng-review"]["disposition"] == "stale" and data["plan-design-review"]["disposition"] == "stale"
    assert data["plan-ceo-review"]["disposition"] == "failed" and data["plan-ceo-review"]["demanded_by"] == "plan-adversarial-review"
    # ship stage: accepted, same stage only
    R.log_review(repo, plan, "qa", "clean", ts="2026-09-05T00:00:00Z")
    assert R.run_json(repo, "review-log", "--skill", "final-review", "--status", "clean", "--rereview", "qa", "--rereview-note", "the fix changed the flow QA passed")["rereview"] == ["qa"]


REREVIEW_REJECTIONS = [
    (["--rereview", "none", "--rereview", "plan-eng-review"], None, "none excludes names"),
    (["--rereview", "plan-eng-review"], {"rereview": ["plan-eng-review"]}, "needs --rereview-note"),
    (["--rereview", "plan-eng-review", "--rereview-note", ""], {"rereview": ["plan-eng-review"], "rereview_note": ""}, "needs --rereview-note"),
    (["--rereview", "none", "--rereview-note", "x"], {"rereview": [], "rereview_note": "x"}, "takes no note"),
    (["--rereview", "plan-design-review", "--rereview-note", "x"], {"rereview": ["plan-design-review"], "rereview_note": "x"}, "cannot demand its own"),
    (["--rereview", "ship", "--rereview-note", "x"], {"rereview": ["ship"], "rereview_note": "x"}, "never re-run"),
    (["--rereview", "qa", "--rereview-note", "x"], {"rereview": ["qa"], "rereview_note": "x"}, "stays in its stage"),
    (["--rereview", "office-hours", "--rereview-note", "x"], {"rereview": ["office-hours"], "rereview_note": "x"}, "not a gating review tier"),
    (["--rereview", "execute-plan", "--rereview-note", "x"], {"rereview": ["execute-plan"], "rereview_note": "x"}, "not a gating review tier"),
    (["--rereview", "plan-ceo-review", "--rereview-note", "x"], {"rereview": ["plan-ceo-review"], "rereview_note": "x"}, "has no run on"),
    (None, {"rereview": "plan-eng-review", "rereview_note": "x"}, "list of skill names"),
    (None, {"rereview": ["none"]}, "JSON spelling of none is []"),
    (None, {"rereview": ["plan-eng-review", 5], "rereview_note": "x"}, "list of skill names"),
    (None, {"rereview": ["plan-eng-review"], "rereview_note": 42}, "must be a string"),
    (None, {"rereview": {"plan-eng-review": True}, "rereview_note": "x"}, "list of skill names"),
    (["--field", "rereview=[]"], None, "--field cannot set 'rereview'"),
    (["--field", "rereview_note=x", "--rereview", "none"], None, "--field cannot set 'rereview_note'"),
    # dated before eng's run (2026-09-02): the reader would never count it, so the writer refuses it
    (
        ["--rereview", "plan-eng-review", "--rereview-note", "x", "--field", "ts=2026-09-01T00:00:00Z"],
        {"rereview": ["plan-eng-review"], "rereview_note": "x", "ts": "2026-09-01T00:00:00Z"},
        "a demand is dated at or after the run it overtakes",
    ),
]


@pytest.mark.parametrize("flags,fields,needle", REREVIEW_REJECTIONS)
def test_declaration_rules_reject_in_both_forms_and_leave_the_log_byte_identical(tmp_path, flags, fields, needle):
    repo, plan = declared(tmp_path)
    before = log_bytes(repo)
    if flags is not None:
        err = error(R.run(repo, "review-log", "--skill", "plan-design-review", "--status", "clean", *flags))
        assert needle in err["error"], err["error"]
    if fields is not None:
        err = error(R.run(repo, "review-log", json.dumps({"skill": "plan-design-review", "status": "clean", **fields})))
        assert needle in err["error"], err["error"]
    assert log_bytes(repo) == before


def test_declaration_refused_on_resolved_done_and_from_office_hours(tmp_path):
    repo, plan = declared(tmp_path)
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z", rereview=[])
    before = log_bytes(repo)
    cases = [
        (["--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x", "--rereview", "plan-adversarial-review", "--rereview-note", "x"],
         {"skill": "plan-ceo-review", "status": "resolved", "resolved_by": "plan-eng-review", "note": "x", "rereview": ["plan-adversarial-review"], "rereview_note": "x"},
         "a resolved entry cannot declare"),
        (["--skill", "ship", "--status", "done", "--rereview", "qa", "--rereview-note", "x"],
         {"skill": "ship", "status": "done", "rereview": ["qa"], "rereview_note": "x"},
         "a done entry cannot declare"),
        (["--skill", "office-hours", "--status", "clean", "--rereview", "plan-eng-review", "--rereview-note", "x"],
         {"skill": "office-hours", "status": "clean", "rereview": ["plan-eng-review"], "rereview_note": "x"},
         "never gates and cannot demand"),
    ]
    for flags, fields, needle in cases:
        assert needle in error(R.run(repo, "review-log", *flags))["error"]
        assert needle in error(R.run(repo, "review-log", json.dumps(fields)))["error"]
    assert log_bytes(repo) == before


def test_a_rereview_note_without_a_declaration_is_refused_in_both_forms(tmp_path):
    """The note rules sit under "rereview, when present", so a note with no declaration used to
    slip past them in any type, on any skill, even on a resolution record."""
    repo, plan = declared(tmp_path)
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z", rereview=[])
    before = log_bytes(repo)
    cases = [
        (["--skill", "qa", "--status", "clean", "--rereview-note", "orphan"], {"skill": "qa", "status": "clean", "rereview_note": "orphan"}),
        (None, {"skill": "qa", "status": "clean", "rereview_note": ["a", 1]}),
        (None, {"skill": "office-hours", "status": "issues_open", "rereview_note": 42}),
        (["--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x", "--rereview-note", "orphan"],
         {"skill": "plan-ceo-review", "status": "resolved", "resolved_by": "plan-eng-review", "note": "x", "rereview_note": "orphan"}),
    ]
    for flags, fields in cases:
        if flags is not None:
            assert "rereview_note belongs to a declaration" in error(R.run(repo, "review-log", *flags))["error"]
        assert "rereview_note belongs to a declaration" in error(R.run(repo, "review-log", json.dumps(fields)))["error"]
    assert log_bytes(repo) == before


def test_a_demand_dated_in_the_same_second_as_the_run_is_accepted_and_reads_stale(tmp_path):
    """The refusal is `<`, never `<=`: one step can write a run and a demand in one second, and the
    reader's `>=` reads that tie as demanded (it fails closed)."""
    repo, plan = declared(tmp_path)
    out = R.run_json(repo, "review-log", "--skill", "plan-design-review", "--status", "clean", "--rereview", "plan-eng-review", "--rereview-note", "tie", "--field", "ts=2026-09-02T00:00:00Z")
    assert out["ts"] == "2026-09-02T00:00:00Z"
    assert R.run_json(repo, "review-read", "--json")["reviews"]["plan-eng-review"]["disposition"] == "stale"


def test_reader_only_keys_and_concern_are_validated_in_both_forms(tmp_path):
    repo, plan = declared(tmp_path)
    before = log_bytes(repo)
    for key in R._lib.READER_ONLY_KEYS:
        err = error(R.run(repo, "review-log", "--skill", "qa", "--status", "clean", "--field", f"{key}=x"))
        assert f"'{key}' is derived on read" in err["error"]
        err = error(R.run(repo, "review-log", json.dumps({"skill": "qa", "status": "clean", key: "x"})))
        assert f"'{key}' is derived on read" in err["error"]
    for argv in (["--skill", "qa", "--status", "clean", "--field", "concern=42"], ['{"skill":"qa","status":"clean","concern":true}'], ["--skill", "qa", "--status", "clean", "--field", "concern="]):
        err = error(R.run(repo, "review-log", *argv))
        assert "concern must be a non-empty string" in err["error"] and "quote it" in err["error"]
    assert log_bytes(repo) == before
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z", rereview=[])
    before = log_bytes(repo)
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x", "--field", "concern=c"))
    assert "concern belongs on a run entry" in err["error"]
    assert log_bytes(repo) == before
    assert R.run_json(repo, "review-log", "--skill", "qa", "--status", "clean", "--field", "concern=flaky on retry")["concern"] == "flaky on retry"
    assert R.run_json(repo, "review-log", "--skill", "ship", "--status", "done", "--field", "concern=merge after the outage")["concern"] == "merge after the outage"


def test_resolved_is_refused_for_a_stale_review_by_every_resolver(tmp_path):
    repo, plan = declared(tmp_path)
    R.log_review(repo, plan, "plan-design-review", "clean", ts="2026-09-04T00:00:00Z", rereview=["plan-eng-review"], rereview_note="15a")
    before = log_bytes(repo)
    for by in ("operator", "plan-adversarial-review", "plan-design-review"):
        for argv in (["--skill", "plan-eng-review", "--status", "resolved", "--field", f"resolved_by={by}", "--field", "note=x"], [json.dumps({"skill": "plan-eng-review", "status": "resolved", "resolved_by": by, "note": "x"})]):
            err = error(R.run(repo, "review-log", *argv))
            assert err["error"].startswith("a re-review demand clears only when plan-eng-review runs again"), err["error"]
            assert "has no failed entry to resolve" not in err["error"]
    assert log_bytes(repo) == before
    # the subagent wording, and a stale review refused as a resolver
    R.log_review(repo, plan, "adversarial-subagent", "clean", ts="2026-09-05T00:00:00Z")
    R.log_review(repo, plan, "review-implementation", "clean", ts="2026-09-06T00:00:00Z", rereview=["adversarial-subagent"], rereview_note="the fix changed the diff")
    err = error(R.run(repo, "review-log", "--skill", "adversarial-subagent", "--status", "resolved", "--field", "resolved_by=final-review", "--field", "note=x"))
    assert "clears only when /review-implementation runs again" in err["error"]
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z", rereview=[])
    err = error(R.run(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x"))
    assert "is stale; the resolver must have run after the failure and passed" in err["error"]


def test_resolving_a_failed_and_demanded_review_writes_resolves_ts_and_leaves_it_stale(tmp_path):
    repo, plan = declared(tmp_path)
    R.log_review(repo, plan, "plan-ceo-review", "issues_open", ts="2026-09-01T00:00:00Z", rereview=[])
    R.log_review(repo, plan, "plan-design-review", "clean", ts="2026-09-04T00:00:00Z", rereview=["plan-ceo-review"], rereview_note="scope")
    out = R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "resolved", "--field", "resolved_by=plan-eng-review", "--field", "note=x")
    assert out["resolves_ts"] == "2026-09-01T00:00:00Z" and "waives_ts" not in out
    assert R.run_json(repo, "review-read", "--json")["reviews"]["plan-ceo-review"]["disposition"] == "stale"


def test_a_demand_needs_a_plan_but_none_does_not(tmp_path):
    repo = R.make_repo(tmp_path)  # on main, no plan
    for argv in (
        ["--skill", "plan-design-review", "--status", "clean", "--rereview", "plan-eng-review", "--rereview-note", "x"],
        [json.dumps({"skill": "plan-design-review", "status": "clean", "rereview": ["plan-eng-review"], "rereview_note": "x"})],
    ):
        proc = R.run(repo, "review-log", *argv)
        assert proc.returncode == 2 and "needs a plan to resolve against" in json.loads(proc.stdout)["error"]
    assert log_bytes(repo) == b""
    assert R.run_json(repo, "review-log", "--skill", "plan-design-review", "--status", "clean", "--rereview", "none")["rereview"] == []
    assert R.run_json(repo, "review-log", '{"skill":"plan-design-review","status":"clean","rereview":[]}')["rereview"] == []


def test_epic_branch_reviews_attach_to_the_epic_and_can_be_demanded(tmp_path):
    repo = R.make_repo(tmp_path)
    epic = R.write_epic(repo, "v1", {"milestones": [{"id": "M1", "title": "one"}]})
    R.checkout(repo, "v1")
    assert R.run_json(repo, "review-log", "--skill", "plan-ceo-review", "--status", "clean", "--rereview", "none")["plan"] == epic.name
    assert R.run(repo, "review-read").stdout.startswith("plan-ceo-review|")
    out = R.run_json(repo, "review-log", "--skill", "plan-eng-review", "--status", "clean", "--rereview", "plan-ceo-review", "--rereview-note", "sequencing changed")
    assert out["plan"] == epic.name and out["rereview"] == ["plan-ceo-review"]
    assert R.run_json(repo, "review-read", "--json")["reviews"]["plan-ceo-review"]["disposition"] == "stale"


# ---------------------------------------------------------------- review-read: stale


def test_review_read_shows_stale_in_plan_mode_and_never_in_all(tmp_path):
    repo, plan = declared(tmp_path)
    R.log_review(repo, plan, "plan-design-review", "clean", ts="2026-09-04T00:00:00Z", rereview=["plan-eng-review"], rereview_note="15a")
    eng = next(l for l in R.run(repo, "review-read").stdout.splitlines() if l.startswith("plan-eng-review|"))
    assert eng.startswith("plan-eng-review|2026-09-02T00:00:00Z|clean|stale|")
    assert "stale_by=plan-design-review" in eng and "was=passed" in eng and 'stale_notes="[{\\"declarer\\": \\"plan-design-review\\"' in eng
    data = R.run_json(repo, "review-read", "--json")["reviews"]
    assert data["plan-eng-review"]["disposition"] == "stale" and data["plan-eng-review"]["status"] == "clean" and data["plan-eng-review"]["stale_count"] == 1
    assert data["plan-eng-review"]["stale_notes"][0]["note"] == "15a" and "stale_by" not in data["plan-adversarial-review"]
    # --all: each entry's own disposition; a hand-appended stale_by is listed as written but never prints stale
    R.log_review(repo, plan, "qa", "clean", ts="2026-09-05T00:00:00Z", stale_by="forged", was="passed")
    lines = R.run(repo, "review-read", "--all").stdout.splitlines()
    assert lines and all("|stale|" not in l for l in lines)
    assert "stale" not in {e["disposition"] for e in R.run_json(repo, "review-read", "--all", "--json")["entries"]}
    qa = next(l for l in lines if "|qa|" in l)
    assert "|passed|" in qa and "stale_by=forged" in qa


def test_one_call_scans_the_log_once(tmp_path, monkeypatch, capsys):
    """`main` scans for unreadable lines and hands those entries to the validators. A resolution
    (pass 2) and a demand (pass 1) each used to read the whole file a second time."""
    repo = R.make_repo(tmp_path)
    R.checkout(repo, "feat/x")
    plan = R.write_plan(repo, "feat/x", {})
    R.log_review(repo, plan, "plan-eng-review", "issues_open", ts="2026-09-02T10:00:00Z", rereview=[])
    R.log_review(repo, plan, "plan-adversarial-review", "clean", ts="2026-09-03T10:00:00Z", rereview=[])
    review_log = R.load_helper("review-log")
    scans, real = [], R._lib.review_log_scan
    monkeypatch.setattr(R._lib, "review_log_scan", lambda root, cfg: scans.append(1) or real(root, cfg))
    monkeypatch.chdir(repo)
    for argv in (
        ["--skill", "plan-eng-review", "--status", "resolved", "--field", "resolved_by=plan-adversarial-review", "--field", "note=closed in section 2"],
        ["--skill", "plan-design-review", "--status", "clean", "--rereview", "plan-adversarial-review", "--rereview-note", "x"],
    ):
        scans.clear()
        monkeypatch.setattr("sys.argv", ["review-log", *argv])
        assert review_log.main() == 0
        assert len(scans) == 1, argv
    capsys.readouterr()
    assert [e["status"] for e in entries(repo)][-2:] == ["resolved", "clean"] and entries(repo)[-1]["rereview"] == ["plan-adversarial-review"]
