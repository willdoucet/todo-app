"""Tests for infra/release-smoke.py (M8 item 4; Eng review 2.3, 2.4, 3A).

Every production read is answered by FakeRunner from fixtures; a command the
test did not answer fails the test, so "did not contact production" is checked
rather than assumed.
"""

import copy
import io
import json
from datetime import datetime, timezone

import pytest

from conftest import fixture_json, fixture_text

RELEASE = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
NOW = datetime(2026, 9, 21, 17, 3, tzinfo=timezone.utc)
API = "https://api.mealy.dev"
FRONT = "https://mealy.dev"
ASSET = "/assets/index-Bq3xY9aK.js"
VOLUME = "vol_4qlnz9q037wl2qwr"
ALL_GROUPS = "release,liveness,recoverability,edge"


def route_key(argv):
    if argv[0] == "curl":
        return f"curl {argv[-1]}" + (" @direct" if "--resolve" in argv else "")
    if argv[:3] == ["fly", "volumes", "snapshots"]:
        return f"fly volumes snapshots list {argv[4]}"
    if argv[0] == "fly":
        return "fly " + " ".join(argv[1:3])
    if argv[0] == "git" and "diff" in argv:
        return f"git diff {argv[-4]} {argv[-1]}"
    if argv[0] == "git":
        return "git rev-parse"
    raise AssertionError(f"unexpected command {argv[0]}")


class FakeRunner:
    def __init__(self, smoke, routes):
        self.smoke = smoke
        self.routes = dict(routes)
        self.calls = []

    def run(self, argv, timeout):
        key = route_key(argv)
        self.calls.append(key)
        if key not in self.routes:
            raise AssertionError(f"unexpected call: {key}")
        answer = self.routes[key]
        if isinstance(answer, Exception):
            raise answer
        return answer


def done(smoke, stdout="", returncode=0, stderr=""):
    return smoke.Completed(returncode, stdout, stderr)


def http(smoke, status, body="", headers=None):
    lines = [f"HTTP/2 {status}"] + [f"{k}: {v}" for k, v in (headers or {}).items()]
    return smoke.Completed(0, "\r\n".join(lines) + "\r\n\r\n" + body, "")


def index_html(sha=RELEASE, meta=True):
    tag = f'<meta name="build-commit" content="{sha}" />' if meta else ""
    return (
        f'<!doctype html><html lang="en"><head><meta charset="UTF-8" />{tag}'
        f'<script type="module" crossorigin src="{ASSET}"></script></head>'
        '<body><div id="root"></div></body></html>'
    )


def healthy_routes(smoke, healthz=None):
    body = json.dumps(healthz if healthz is not None else fixture_json("healthz_healthy.json"))
    revalidate = {"cache-control": "public, max-age=0, must-revalidate"}
    return {
        "git rev-parse": done(smoke, RELEASE + "\n"),
        f"git diff {RELEASE} frontend/": done(smoke),
        f"git diff {RELEASE} backend/": done(smoke),
        "fly machines list": done(smoke, fixture_text("fly_machines_list.json")),
        "fly ssh console": done(smoke, 'SMOKE_ROUNDTRIP {"status": "ok"}\n'),
        f"curl {API}/healthz": http(smoke, 200, body, {"content-type": "application/json"}),
        "curl https://mealy-app-prod.fly.dev/healthz": http(smoke, 200, body),
        "fly volumes list": done(smoke, fixture_text("fly_volumes_list.json")),
        f"fly volumes snapshots list {VOLUME}": done(smoke, fixture_text("fly_volumes_snapshots_list.json")),
        "fly pg backup": done(smoke, fixture_text("fly_pg_backup_list.txt")),
        "fly ips list": done(smoke, fixture_text("fly_ips_list.json")),
        f"curl {API}/tasks/ @direct": http(smoke, 421, '{"detail":"host_not_allowed"}'),
        f"curl {API}/tasks/": http(smoke, 401, '{"detail":"unauthorized"}'),
        f"curl {FRONT}/index.html": http(smoke, 200, index_html(), revalidate),
        f"curl {FRONT}/mealboard": http(smoke, 200, index_html(), revalidate),
        f"curl {FRONT}{ASSET}": http(smoke, 200, "export{}", {"cache-control": "public, max-age=31536000, immutable"}),
        f"curl {API}/uploads/stock_icons/release-smoke.png": http(
            smoke, 401, '{"detail":"unauthorized"}',
            {"cache-control": "private, no-store", "cf-cache-status": "DYNAMIC"},
        ),
    }


def run(smoke, routes, *args):
    out = io.StringIO()
    runner = FakeRunner(smoke, routes)
    code = smoke.main(list(args), runner=runner, now=NOW, out=out)
    return code, out.getvalue(), runner


def line_for(output, label):
    return next(line for line in output.splitlines() if f"{label}:" in line)


# --- the whole run ---------------------------------------------------------


def test_all_groups_green_exits_0(smoke):
    code, out, _ = run(smoke, healthy_routes(smoke), f"--release-commit={RELEASE}")
    assert code == 0, out
    assert out.splitlines()[-1] == "exit 0: 12 passed, 0 skipped"
    assert "FAIL" not in out and "ERROR" not in out and "SKIP" not in out


def test_pr1a_skip_list_prints_skipped_and_check_1_still_runs(smoke):
    """PR1a's /healthz is only {"status": "ok"}: the three PR1b keys are skipped,
    printed as skipped (never pass), and check 1 still runs (Adversarial review)."""
    routes = healthy_routes(smoke, healthz={"status": "ok"})
    code, out, _ = run(
        smoke, routes, f"--only={ALL_GROUPS}",
        "--skip=healthz_jobs,healthz_version,healthz_gate_break_glass", f"--release-commit={RELEASE}",
    )
    assert code == 0, out
    assert line_for(out, "[1] healthz").startswith("PASS")
    for label in ("[jobs] jobs-fresh", "[8] commit-backend", "[glass] break-glass-off"):
        line = line_for(out, label)
        assert line.startswith("SKIP") and "skipped" in line and "PASS" not in line
    assert out.splitlines()[-1] == "exit 0: 9 passed, 3 skipped"


@pytest.mark.parametrize(
    "key,label",
    [("jobs", "[jobs] jobs-fresh"), ("version", "[8] commit-backend"), ("gate_break_glass", "[glass] break-glass-off")],
)
def test_missing_pr1b_key_without_skip_is_exit_1_naming_it(smoke, key, label):
    body = fixture_json("healthz_healthy.json")
    del body[key]
    code, out, _ = run(smoke, healthy_routes(smoke, healthz=body), f"--release-commit={RELEASE}")
    assert code == 1
    assert line_for(out, label).startswith("FAIL") and f"`{key}`" in line_for(out, label)


def test_self_test_default_fails_check_3_without_contacting_production(smoke):
    code, out, runner = run(smoke, {}, "--self-test")
    assert code == 1
    assert runner.calls == []
    assert line_for(out, "[3] scale-reconciled").startswith("FAIL")
    assert "web: expected 1, found 2" in out
    assert out.splitlines()[-1].startswith("exit 1 production: [3] scale-reconciled")


def test_self_test_of_the_cron_groups_fails_a_check_in_that_set(smoke):
    code, out, runner = run(smoke, {}, "--only=liveness,recoverability,edge", "--self-test")
    assert code == 1
    assert runner.calls == []
    assert "[jobs] jobs-fresh" in out and "[3]" not in out
    assert out.splitlines()[-1].startswith("exit 1 production: [jobs] jobs-fresh")


@pytest.mark.parametrize("group,label", [("recoverability", "[9] restore-point"), ("edge", "[glass] break-glass-off")])
def test_self_test_of_one_group(smoke, group, label):
    code, out, runner = run(smoke, {}, f"--only={group}", "--self-test")
    assert (code, runner.calls) == (1, [])
    assert line_for(out, label).startswith("FAIL")


# --- usage and tooling (exit 2) ---------------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ["--only=release"],  # no --release-commit
        ["--only=liveness,bogus"],
        ["--only=liveness", "--skip=healthz_everything"],
    ],
)
def test_usage_errors_exit_2(smoke, args):
    code, out, runner = run(smoke, {}, *args)
    assert code == 2 and out.startswith("exit 2 tooling:")
    assert runner.calls == []


def test_release_commit_that_does_not_resolve_is_exit_2(smoke):
    routes = {"git rev-parse": done(smoke, "", returncode=1)}
    code, out, _ = run(smoke, routes, "--only=release", "--release-commit=nope")
    assert code == 2 and "not a commit" in out


def test_fly_missing_is_exit_2(smoke):
    routes = {"fly volumes list": smoke.Tooling("`fly` is not on PATH"), "fly pg backup": smoke.Tooling("`fly` is not on PATH")}
    code, out, _ = run(smoke, routes, "--only=recoverability")
    assert code == 2
    assert line_for(out, "[9] restore-point").startswith("ERROR")
    assert "#tooling-failures-exit-2" in out


def test_rejected_token_is_exit_2_with_the_cause_named(smoke):
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, "", 1, "Error: You must be authenticated to view this.")
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 2
    assert "authenticated" in line_for(out, "[3] scale-reconciled")


def test_no_network_is_exit_2(smoke):
    routes = {f"curl {API}/healthz": done(smoke, "", 6, "curl: (6) Could not resolve host: api.mealy.dev"),
              "curl https://mealy-app-prod.fly.dev/healthz": done(smoke, "", 6, "curl: (6) Could not resolve host")}
    code, out, _ = run(smoke, routes, "--only=liveness", "--skip=healthz_jobs")
    assert code == 2 and "Could not resolve host" in out


def test_cloudflare_challenge_page_is_exit_2_not_1(smoke):
    routes = healthy_routes(smoke)
    routes[f"curl {API}/healthz"] = http(smoke, 403, "<html><title>Just a moment...</title></html>",
                                         {"cf-mitigated": "challenge"})
    code, out, _ = run(smoke, routes, "--only=liveness", "--skip=healthz_jobs")
    assert code == 2
    assert "challenge" in line_for(out, "[1] healthz")


def test_remote_error_text_masks_credentials_in_urls(smoke):
    assert smoke.first_line("\n  Error 111 connecting to rediss://default:hunter2@host:6379\n") == (
        "Error 111 connecting to rediss://***@host:6379"
    )


# --- check 1 and check 2 ----------------------------------------------------


def test_healthz_down_by_one_path_is_exit_1(smoke):
    routes = healthy_routes(smoke)
    routes["curl https://mealy-app-prod.fly.dev/healthz"] = http(smoke, 502, "bad gateway")
    code, out, _ = run(smoke, routes, "--only=liveness")
    assert code == 1 and "502" in line_for(out, "[1] healthz")


def test_healthz_status_other_than_ok_is_exit_1(smoke):
    code, out, _ = run(smoke, healthy_routes(smoke, healthz={"status": "degraded"}), "--only=liveness",
                       "--skip=healthz_jobs")
    assert code == 1 and "status is 'degraded', expected 'ok'" in line_for(out, "[1] healthz")


def test_stopped_worker_fails_check_2_naming_the_machine(smoke):
    machines = fixture_json("fly_machines_list.json")
    machines[1]["state"] = "stopped"
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    assert "worker d8d2e06fed20d8 is stopped" in line_for(out, "[2] groups-started")


def test_a_process_group_with_no_machine_fails_check_2(smoke):
    """A destroyed worker is not "stopped": it is absent, and absence must fail too."""
    machines = [m for m in fixture_json("fly_machines_list.json") if smoke.machine_group(m) != "worker"]
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and "worker: no machine" in line_for(out, "[2] groups-started")


def test_a_standby_is_neither_required_started_nor_counted(smoke):
    """A Fly standby is stopped by design. Starting a beat standby by hand runs two beats."""
    machines = fixture_json("fly_machines_list.json")
    standby = copy.deepcopy(machines[2])
    standby.update(id="d894036cstandby", state="stopped")
    standby["config"]["standbys"] = [machines[2]["id"]]
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines + [standby]))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 0, out
    assert "standby, not counted: beat=1" in line_for(out, "[2] groups-started")
    assert "beat=1" in line_for(out, "[3] scale-reconciled")


def test_a_started_standby_is_counted_by_check_3(smoke):
    """A started beat standby beside its primary is two beats, the invariant check 3 exists for."""
    machines = fixture_json("fly_machines_list.json")
    standby = copy.deepcopy(machines[2])
    standby.update(id="d894036cstandby", state="started")
    standby["config"]["standbys"] = [machines[2]["id"]]
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines + [standby]))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    line = line_for(out, "[3] scale-reconciled")
    assert "beat: expected 1, found 2" in line and "started standby" in line


def test_self_test_fails_whatever_count_the_file_pins(smoke, monkeypatch):
    """The forced failure is one more than the pin, so a future web=2 cannot turn it green."""
    monkeypatch.setattr(smoke.Context, "scale", lambda self: {"web": 2, "worker": 1, "beat": 1})
    code, out, runner = run(smoke, {}, "--self-test")
    assert (code, runner.calls) == (1, [])
    assert "web: expected 2, found 3" in line_for(out, "[3] scale-reconciled")


def test_an_unexpected_error_in_a_check_is_exit_2_and_the_rest_still_run(smoke):
    machines = fixture_json("fly_machines_list.json") + [{"id": "odd", "state": "started", "config": "not-an-object"}]
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 2, out
    assert line_for(out, "[2] groups-started").startswith("ERROR") and "unexpected AttributeError" in out
    assert line_for(out, "[4] worker-roundtrip").startswith("PASS")
    assert out.splitlines()[-1].startswith("exit 2 tooling:")


def test_git_missing_while_resolving_the_release_commit_is_exit_2(smoke):
    code, out, _ = run(smoke, {"git rev-parse": smoke.Tooling("`git` is not on PATH")},
                       "--only=release", f"--release-commit={RELEASE}")
    assert code == 2 and "git" in out


def test_curl_parser_skips_continue_and_proxy_connect_blocks(smoke):
    continued = "HTTP/1.1 100 Continue\r\n\r\nHTTP/2 200\r\ncache-control: no-store\r\n\r\n{}"
    assert (smoke.parse_curl_include(continued).status, smoke.parse_curl_include(continued).body) == (200, "{}")
    proxied = "HTTP/1.1 200 Connection established\r\n\r\nHTTP/2 401\r\ncontent-type: application/json\r\n\r\nx"
    assert smoke.parse_curl_include(proxied).status == 401


def test_healthz_unreachable_by_one_path_while_the_other_answers_is_exit_1(smoke):
    """This laptop reached one path in the same run, so the other path's timeout is production."""
    routes = healthy_routes(smoke)
    routes[f"curl {API}/healthz"] = done(smoke, "", 28, "curl: (28) Operation timed out after 20001 milliseconds")
    code, out, _ = run(smoke, routes, "--only=liveness", "--skip=healthz_jobs")
    assert code == 1 and "unreachable while the other path answered" in line_for(out, "[1] healthz")


# --- check 3 ----------------------------------------------------------------


def test_scale_disagreement_fails_check_3_naming_the_group(smoke):
    machines = fixture_json("fly_machines_list.json")
    second_web = copy.deepcopy(machines[0])
    second_web["id"] = "2869e6dae306d8"
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines + [second_web]))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    assert "web: expected 1, found 2" in line_for(out, "[3] scale-reconciled")


def test_scale_file_keys_must_equal_fly_toml_processes_before_any_diff(smoke, tmp_path):
    scale = tmp_path / "fly-scale.json"
    scale.write_text('{"web": 1, "wroker": 1, "beat": 1}')
    runner = FakeRunner(smoke, {})
    ctx = smoke.Context(runner, now=NOW, scale_file=scale)
    check = next(c for c in smoke.CHECKS if c.name == "scale-reconciled")
    result = smoke.run_check(check, ctx, set())
    assert result.outcome == "fail" and "fly.toml [processes]" in result.detail
    assert runner.calls == []  # failed before `fly machines list`


def test_the_committed_scale_file_matches_fly_toml(smoke):
    assert smoke.Context(FakeRunner(smoke, {})).scale() == {"web": 1, "worker": 1, "beat": 1}


def test_a_machine_in_an_unlisted_group_fails_check_3(smoke):
    machines = fixture_json("fly_machines_list.json")
    stray = copy.deepcopy(machines[0])
    stray["config"]["metadata"]["fly_process_group"] = "app"
    routes = healthy_routes(smoke)
    routes["fly machines list"] = done(smoke, json.dumps(machines + [stray]))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and "app: 1 machine(s)" in out


# --- check 4 ----------------------------------------------------------------


def test_worker_round_trip_timeout_is_exit_1_unverified(smoke):
    routes = healthy_routes(smoke)
    routes["fly ssh console"] = done(smoke, "", 1, "celery.exceptions.TimeoutError: The operation timed out.")
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    assert "worker round-trip unverified" in line_for(out, "[4] worker-roundtrip")


def test_an_exception_raised_on_the_machine_is_production_not_tooling(smoke):
    """The probe ran in the app's environment and failed there (broker down, broken
    import): that is evidence about production, so exit 1, with credentials masked."""
    routes = healthy_routes(smoke)
    routes["fly ssh console"] = done(smoke, "", 1, (
        "Traceback (most recent call last):\n  File \"<string>\", line 1, in <module>\n"
        "kombu.exceptions.OperationalError: Error 111 connecting to rediss://default:hunter2@upstash:6379\n"
    ))
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    line = line_for(out, "[4] worker-roundtrip")
    assert "OperationalError" in line and "hunter2" not in line and "rediss://***@" in line


def test_a_worker_round_trip_with_the_wrong_result_is_exit_1(smoke):
    routes = healthy_routes(smoke)
    routes["fly ssh console"] = done(smoke, 'SMOKE_ROUNDTRIP {"status": "degraded"}\n')
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and "health_check returned" in line_for(out, "[4] worker-roundtrip")


def test_ssh_failure_is_exit_2(smoke):
    routes = healthy_routes(smoke)
    routes["fly ssh console"] = done(smoke, "", 1, "Error: tunnel unavailable: failed probing")
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 2 and "tunnel unavailable" in out


def test_worker_probe_spells_the_interpreter_absolutely_and_targets_web(smoke):
    runner = FakeRunner(smoke, {"fly ssh console": done(smoke, 'SMOKE_ROUNDTRIP {"status": "ok"}')})
    seen = []
    runner.run = lambda argv, timeout: (seen.append(argv), done(smoke, 'SMOKE_ROUNDTRIP {"status": "ok"}'))[1]
    smoke.check_worker(smoke.Context(runner))
    argv = seen[0]
    assert argv[argv.index("-g") + 1] == "web"
    command = argv[argv.index("-C") + 1]
    assert command.startswith("/app/.venv/bin/python -c ")
    assert '"' not in command[len('/app/.venv/bin/python -c "'):-1]  # one double-quoted argument


# --- check 5 ----------------------------------------------------------------


def test_origin_lock_429_is_exit_1_rate_limited_never_0(smoke):
    routes = healthy_routes(smoke, healthz={"status": "ok", "gate_break_glass": False})
    routes[f"curl {API}/tasks/"] = http(smoke, 429, "rate limited")
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1
    assert "rate-limited, unverified" in line_for(out, "[5] origin-lock")


def test_origin_lock_open_is_exit_1(smoke):
    routes = healthy_routes(smoke)
    routes[f"curl {API}/tasks/ @direct"] = http(smoke, 401, '{"detail":"unauthorized"}')
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and "origin lock OPEN" in out


def test_cloudflare_path_421_points_at_the_transform_rule(smoke):
    routes = healthy_routes(smoke)
    routes[f"curl {API}/tasks/"] = http(smoke, 421, '{"detail":"host_not_allowed"}')
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and "Transform Rule" in line_for(out, "[5] origin-lock")


def test_origin_ip_comes_from_fly_ips_list_v4_first(smoke):
    ctx = smoke.Context(FakeRunner(smoke, {"fly ips list": done(smoke, fixture_text("fly_ips_list.json"))}))
    assert ctx.fly_ip() == "66.241.124.153"


def test_origin_ip_falls_back_to_v6_when_the_app_has_no_v4(smoke):
    v6_only = json.dumps([e for e in fixture_json("fly_ips_list.json") if e["Type"] == "v6"])
    ctx = smoke.Context(FakeRunner(smoke, {"fly ips list": done(smoke, v6_only)}))
    assert ctx.fly_ip() == "2a09:8280:1::6c:1a2b:0"


def test_a_v6_origin_is_bracketed_for_curl_resolve(smoke):
    seen = []

    class Capture(smoke.Runner):
        def run(self, argv, timeout):
            seen.append(argv)
            return http(smoke, 421, '{"detail":"host_not_allowed"}')

    smoke.Context(Capture()).http_get(f"{API}/tasks/", resolve_ip="2a09:8280:1::6c:1a2b:0")
    assert seen[0][seen[0].index("--resolve") + 1] == "api.mealy.dev:443:[2a09:8280:1::6c:1a2b:0]"


def test_break_glass_on_fails_the_edge_group(smoke):
    body = fixture_json("healthz_healthy.json")
    body["gate_break_glass"] = True
    code, out, _ = run(smoke, healthy_routes(smoke, healthz=body), "--only=edge")
    assert code == 1 and "GATE_BREAK_GLASS is ON" in out


# --- checks 6 and 7 ---------------------------------------------------------


@pytest.mark.parametrize(
    "status,headers,expected",
    [
        (401, {"cache-control": "private, max-age=14400, no-store"}, "Browser Cache TTL rewrote"),
        (401, {"cache-control": "max-age=14400"}, "expected 'private, no-store'"),
        (401, {"cache-control": "private, no-store", "cf-cache-status": "HIT"}, "cf-cache-status HIT"),
        (200, {"cache-control": "private, no-cache"}, "expected 401"),
    ],
)
def test_private_media_header_failures(smoke, status, headers, expected):
    routes = healthy_routes(smoke)
    routes[f"curl {API}/uploads/stock_icons/release-smoke.png"] = http(smoke, status, "", headers)
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and expected in line_for(out, "[6] private-media-headers")


def test_spa_route_without_revalidation_fails_check_7(smoke):
    routes = healthy_routes(smoke)
    routes[f"curl {FRONT}/mealboard"] = http(smoke, 200, index_html(), {"cache-control": "public, max-age=3600"})
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and "/mealboard cache-control" in line_for(out, "[7] vercel-cache-headers")


def test_index_without_an_asset_reference_fails_check_7(smoke):
    routes = healthy_routes(smoke)
    bare = f'<!doctype html><html><head><meta name="build-commit" content="{RELEASE}" /></head><body></body></html>'
    routes[f"curl {FRONT}/index.html"] = http(smoke, 200, bare, {"cache-control": "public, max-age=0, must-revalidate"})
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and "references no /assets/*.js" in line_for(out, "[7] vercel-cache-headers")


def test_mutable_asset_fails_check_7(smoke):
    routes = healthy_routes(smoke)
    routes[f"curl {FRONT}{ASSET}"] = http(smoke, 200, "", {"cache-control": "public, max-age=0"})
    code, out, _ = run(smoke, routes, "--only=edge")
    assert code == 1 and "expected immutable" in out


# --- check 8 ----------------------------------------------------------------


def test_a_deployed_build_whose_tier_differs_from_the_release_fails(smoke):
    routes = healthy_routes(smoke)
    routes[f"git diff {RELEASE} frontend/"] = done(smoke, "", 1)
    routes[f"git diff {RELEASE} backend/"] = done(smoke, "", 1)
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    assert "differs from release" in line_for(out, "[8] commit-frontend") and "promote" in line_for(out, "[8] commit-frontend")
    assert "differs from release" in line_for(out, "[8] commit-backend")


def test_commit_missing_from_local_history_fails_not_errors(smoke):
    routes = healthy_routes(smoke)
    for tier in ("frontend/", "backend/"):
        routes[f"git diff {RELEASE} {tier}"] = done(smoke, "", 128, f"fatal: bad object {RELEASE}")
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and "not in local history" in out


def _git(repo, *args):
    import subprocess
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(repo)}
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env, check=True).stdout.strip()


def _commit(repo, path, text, message):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def test_check_8_compares_code_not_ancestry_against_real_git(smoke, tmp_path, monkeypatch):
    """/review-implementation (M8 PR1a): the ancestor rule passed a forgotten promote and
    failed RUNBOOK §4's deploy-before-merge path. Real git, no fakes, for all three cases."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    _commit(repo, "frontend/app.js", "v1", "base frontend")
    previous = _commit(repo, "backend/app.py", "v1", "base backend")

    def verdict(tier, deployed, release):
        ctx = smoke.Context(smoke.Runner(), release_commit=release, now=NOW)
        try:
            return "pass", smoke.assert_deployed_matches(ctx, tier, deployed)
        except smoke.CheckFailed as exc:
            return "fail", str(exc)

    monkeypatch.setattr(smoke, "REPO_ROOT", repo)
    # A release that changed the frontend, and the promote was forgotten: production is on
    # the previous build, which IS an ancestor. The old rule passed this.
    frontend_release = _commit(repo, "frontend/app.js", "v2", "frontend change")
    assert verdict("frontend", previous, frontend_release)[0] == "fail"
    # A backend-only release: the previous frontend build is still the right one.
    backend_release = _commit(repo, "backend/app.py", "v2", "backend change")
    assert verdict("frontend", frontend_release, backend_release)[0] == "pass"
    # RUNBOOK §4: the backend is deployed from the pull request's head, then squash-merged.
    _git(repo, "checkout", "-q", "-b", "feature")
    pr_head = _commit(repo, "backend/app.py", "v3", "feature")
    _git(repo, "checkout", "-q", "master")
    _git(repo, "merge", "--squash", "-q", "feature")
    _git(repo, "commit", "-q", "-m", "squash")
    squash = _git(repo, "rev-parse", "HEAD")
    import subprocess
    not_ancestor = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", pr_head, squash])
    assert not_ancestor.returncode == 1  # negative control: the ancestor rule would fail this release
    assert verdict("backend", pr_head, squash)[0] == "pass"
    assert verdict("backend", previous, squash)[0] == "fail"  # an old backend is still caught


def test_a_deployed_commit_missing_from_local_history_fails_against_real_git(smoke, tmp_path, monkeypatch):
    """The "not in local history" markers are git's own wording, so real git decides them: a
    full sha git has never seen (`bad object`) and a short one (`bad revision`)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    release = _commit(repo, "frontend/app.js", "v1", "base")
    monkeypatch.setattr(smoke, "REPO_ROOT", repo)
    ctx = smoke.Context(smoke.Runner(), release_commit=release, now=NOW)
    for unknown in ("deadbeef" * 5, "deadbee"):
        with pytest.raises(smoke.CheckFailed, match="not in local history"):
            smoke.assert_deployed_matches(ctx, "frontend", unknown)


def test_an_unexpected_git_error_in_check_8_is_exit_2(smoke):
    routes = healthy_routes(smoke)
    for tier in ("frontend/", "backend/"):
        routes[f"git diff {RELEASE} {tier}"] = done(
            smoke, "", 128, "fatal: not a git repository (or any of the parent directories): .git")
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 2
    assert line_for(out, "[8] commit-frontend").startswith("ERROR") and "not a git repository" in out


def test_an_empty_frontend_stamp_names_the_vercel_setting(smoke):
    """Vercel's buildCommand sets VITE_GIT_COMMIT from an unexposed VERCEL_GIT_COMMIT_SHA as
    an empty string, and Vite writes "" (not the placeholder): the empty case needs the hint."""
    routes = healthy_routes(smoke)
    routes[f"curl {FRONT}/index.html"] = http(smoke, 200, index_html(sha=""), {"cache-control": "public, max-age=0, must-revalidate"})
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and "System Environment Variables" in line_for(out, "[8] commit-frontend")


@pytest.mark.parametrize(
    "html,expected",
    [
        (index_html(meta=False), "no commit reported"),
        (index_html(sha=""), "empty"),
        (index_html(sha="%VITE_GIT_COMMIT%"), "placeholder was never substituted"),
        (index_html(sha="unknown"), "version unknown"),
    ],
)
def test_frontend_commit_absent_empty_or_placeholder_fails_that_tier(smoke, html, expected):
    routes = healthy_routes(smoke)
    routes[f"curl {FRONT}/index.html"] = http(smoke, 200, html, {"cache-control": "public, max-age=0, must-revalidate"})
    code, out, _ = run(smoke, routes, "--only=release", f"--release-commit={RELEASE}")
    assert code == 1
    assert line_for(out, "[8] commit-frontend").startswith("FAIL") and expected in line_for(out, "[8] commit-frontend")
    assert line_for(out, "[8] commit-backend").startswith("PASS")


@pytest.mark.parametrize("version,expected", [("unknown", "version unknown"), ("", "empty"), (None, "not a commit sha")])
def test_backend_commit_unknown_or_empty_fails_that_tier(smoke, version, expected):
    body = fixture_json("healthz_healthy.json")
    body["version"] = version
    code, out, _ = run(smoke, healthy_routes(smoke, healthz=body), "--only=release", f"--release-commit={RELEASE}")
    assert code == 1 and expected in line_for(out, "[8] commit-backend")


# --- check 9 ----------------------------------------------------------------


def recoverability(smoke, snapshots, wal):
    routes = healthy_routes(smoke)
    routes[f"fly volumes snapshots list {VOLUME}"] = done(smoke, json.dumps(snapshots))
    routes["fly pg backup"] = wal
    return run(smoke, routes, "--only=recoverability")


def test_snapshot_under_48h_passes_and_reports_both_mechanisms(smoke):
    code, out, _ = recoverability(
        smoke, [{"id": "vs_1", "status": "created", "created_at": "2026-09-21T08:00:00Z"}],
        done(smoke, fixture_text("fly_pg_backup_list.txt")),
    )
    assert code == 0
    line = line_for(out, "[9] restore-point")
    assert "volume snapshot 9 h old" in line and "WAL backup 13 h old" in line


def test_only_a_wal_point_under_48h_passes_with_both_reported(smoke):
    code, out, _ = recoverability(
        smoke, [{"id": "vs_1", "status": "created", "created_at": "2026-09-15T08:00:00Z"}],
        done(smoke, fixture_text("fly_pg_backup_list.txt")),
    )
    assert code == 0
    line = line_for(out, "[9] restore-point")
    assert "volume snapshot 6 days old" in line and "WAL backup 13 h old" in line


def test_neither_recent_is_exit_1(smoke):
    code, out, _ = recoverability(
        smoke, [{"id": "vs_1", "status": "created", "created_at": "2026-09-15T08:00:00Z"}],
        done(smoke, "ID  STATUS  START\n20260914T040000  completed  2026-09-14 04:00:00\n"),
    )
    assert code == 1 and "no restore point newer than 48 h" in out


def test_the_2026_09_12_state_no_snapshots_and_backups_disabled_is_exit_1(smoke):
    """What The Assignment found: a moved volume with zero snapshots, WAL backups off."""
    code, out, _ = recoverability(
        smoke, [], done(smoke, "", 1, "Error: backups are not enabled. Run `fly pg backup enable` to enable them"),
    )
    assert code == 1
    line = line_for(out, "[9] restore-point")
    assert "no volume snapshot" in line and "WAL backups disabled" in line


def test_snapshots_list_prints_no_snapshots_text(smoke):
    routes = healthy_routes(smoke)
    routes[f"fly volumes snapshots list {VOLUME}"] = done(smoke, "No snapshots available\n")
    code, out, _ = run(smoke, routes, "--only=recoverability")
    assert code == 0  # the WAL fixture is recent
    assert "no volume snapshot" in out


def test_restore_point_unverifiable_is_exit_2_never_pass(smoke):
    routes = healthy_routes(smoke)
    routes["fly volumes list"] = done(smoke, "", 1, "Error: unauthorized")
    routes["fly pg backup"] = done(smoke, "", 1, "Error: unauthorized")
    code, out, _ = run(smoke, routes, "--only=recoverability")
    assert code == 2 and "restore point unverified" in out


def test_a_failed_wal_backup_is_not_a_restore_point(smoke):
    table = ("ID                STATUS     START                 END\n"
             "20260921T040000   failed     2026-09-21 04:00:00   2026-09-21 04:00:41\n")
    code, out, _ = recoverability(smoke, [], done(smoke, table))
    assert code == 1 and "no WAL backup listed" in line_for(out, "[9] restore-point")


def test_an_outgoing_pending_destroy_volume_is_never_read(smoke):
    """The 2026-09-12 shape: the old volume still holds a fresh snapshot, the new one has
    none. Reading the old one would report a restore point that the database cannot use."""
    volumes = fixture_json("fly_volumes_list.json")
    outgoing = dict(volumes[0], id="vol_old_pending", state="pending_destroy", zone="76a8")
    routes = healthy_routes(smoke)
    routes["fly volumes list"] = done(smoke, json.dumps(volumes + [outgoing]))
    routes[f"fly volumes snapshots list {VOLUME}"] = done(smoke, "No snapshots available\n")
    routes["fly volumes snapshots list vol_old_pending"] = done(
        smoke, json.dumps([{"id": "vs_old", "status": "created", "created_at": "2026-09-21T08:00:00Z"}]))
    routes["fly pg backup"] = done(smoke, "", 1, "Error: backups are not enabled")
    code, out, runner = run(smoke, routes, "--only=recoverability")
    assert code == 1
    assert "fly volumes snapshots list vol_old_pending" not in runner.calls


def test_backup_table_times_are_read_as_utc(smoke):
    times = smoke.parse_backup_times(fixture_text("fly_pg_backup_list.txt"))
    assert max(times) == datetime(2026, 9, 21, 4, 0, 41, tzinfo=timezone.utc)


# --- the /healthz.jobs contract ---------------------------------------------


def jobs(**overrides):
    body = copy.deepcopy(fixture_json("healthz_healthy.json")["jobs"])
    body.update(overrides)
    return body


def verdict(smoke, body):
    try:
        return "pass", smoke.jobs_verdict(body)
    except smoke.CheckFailed as exc:
        return "fail", str(exc)


def test_healthy_contract_example_passes(smoke):
    assert verdict(smoke, jobs()) == ("pass", "4 background jobs fresh")


def test_null_row_the_server_has_not_marked_stale_passes(smoke):
    body = jobs()
    body["rows"][3]["last_success_at"] = None
    outcome, detail = verdict(smoke, body)
    assert outcome == "pass" and "1 not yet run" in detail


def test_stale_rows_are_named_by_label_with_cant_record_runs(smoke):
    body = jobs()
    body["rows"][0].update(stale=True, write_error=True)
    body["rows"][3].update(stale=True)
    outcome, detail = verdict(smoke, body)
    assert outcome == "fail"
    assert detail == "Background jobs behind schedule: iCloud calendar sync (can't record runs), Unused photo cleanup"


def test_critical_path_17_all_stale_three_flagged_names_all_four(smoke):
    body = jobs()
    for i, row in enumerate(body["rows"]):
        row.update(stale=True, write_error=i != 3)
    outcome, detail = verdict(smoke, body)
    assert outcome == "fail"
    assert detail.count("(can't record runs)") == 3
    for label in ("iCloud calendar sync", "iCloud reminders sync", "Deleted item cleanup", "Unused photo cleanup"):
        assert label in detail


def test_unavailable_reading_is_web_cannot_read(smoke):
    outcome, detail = verdict(smoke, jobs(read="unavailable", read_at=None, rows=[]))
    assert outcome == "fail" and "web cannot read job_heartbeats" in detail


def test_unusable_reading_is_checked_before_stale_rows(smoke):
    """read_at 5 min before serve time AND every row stale: one message, no label list
    (Eng review 5 pinned the order)."""
    body = jobs(read="stale", read_at="2026-09-21T16:57:40Z")
    for row in body["rows"]:
        row["stale"] = True
    outcome, detail = verdict(smoke, body)
    assert outcome == "fail" and "web cannot read job_heartbeats" in detail
    assert "iCloud" not in detail and "behind schedule" not in detail


def test_read_at_exactly_120_seconds_old_is_still_usable(smoke):
    assert verdict(smoke, jobs(read_at="2026-09-21T17:00:40Z"))[0] == "pass"
    assert "web cannot read" in verdict(smoke, jobs(read_at="2026-09-21T17:00:39Z"))[1]


def _drop_stale(body):
    del body["rows"][1]["stale"]
    return body


def _stale_as_string(body):
    body["rows"][1]["stale"] = "false"
    return body


@pytest.mark.parametrize(
    "body",
    [
        jobs(rows=[]),                       # read ok with no rows
        jobs(read_at=None),                  # read_at null while read is not unavailable
        jobs(now="yesterday"),               # now does not parse
        jobs(rows={"task": "x"}),            # rows not a list
        jobs(read="fine"),                   # read outside the enum
        _drop_stale(jobs()),                 # a row with no stale flag is never read as fresh
        _stale_as_string(jobs()),
        "not an object",
    ],
)
def test_malformed_jobs_is_exit_1_never_a_pass(smoke, body):
    outcome, detail = verdict(smoke, body)
    assert outcome == "fail" and "malformed jobs" in detail


def test_malformed_body_through_the_whole_script(smoke):
    body = fixture_json("healthz_healthy.json")
    body["jobs"]["rows"] = []
    code, out, _ = run(smoke, healthy_routes(smoke, healthz=body), "--only=liveness")
    assert code == 1 and "malformed jobs" in line_for(out, "[jobs] jobs-fresh")


# --- structure ----------------------------------------------------------------


def test_every_skip_key_belongs_to_exactly_one_check(smoke):
    keys = [c.skip_key for c in smoke.CHECKS if c.skip_key]
    assert sorted(keys) == sorted(smoke.SKIP_KEYS)


def test_every_check_is_in_a_known_group_and_the_release_group_is_release_relative(smoke):
    assert {c.group for c in smoke.CHECKS} == set(smoke.GROUPS)
    release = {c.number for c in smoke.CHECKS if c.group == "release"}
    assert release == {"2", "3", "4", "8"}  # never on the cron: release-relative, noise on a schedule
