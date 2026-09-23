"""Tests for infra/cloudflare-drift.py (M8 item 9; CEO review 3G).

The Transform Rule fixture carries a dummy X-Origin-Verify value and every test
greps stdout and stderr for it and for the token: presence-only is structural.
"""

import copy
import io
import json
import re

import pytest

from conftest import INFRA, fixture_text

TOKEN = "tok-SECRET-do-not-print-123"
HEADER_VALUE = "dummy-origin-verify-value-DO-NOT-PRINT"
ZONE = "/zones/f188a6cea2ead74660b191d435cb370b"
ACCOUNT = "/accounts/f7f2bff79b487f5d1552a1c5eebd3992"

ROUTES = {
    f"{ZONE}/rulesets/phases/http_ratelimit/entrypoint": "cloudflare_ratelimit.json",
    f"{ZONE}/rulesets/phases/http_request_late_transform/entrypoint": "cloudflare_transform_rules.json",
    f"{ZONE}/settings/browser_cache_ttl": "cloudflare_browser_cache_ttl.json",
    f"{ACCOUNT}/access/apps": "cloudflare_access_apps.json",
    f"{ZONE}/bot_management": "cloudflare_bot_management.json",
}


class FakeFetch:
    def __init__(self, overrides=None):
        self.answers = {path: (200, fixture_text(name)) for path, name in ROUTES.items()}
        self.answers.update(overrides or {})
        self.calls = []

    def __call__(self, url, token):
        assert token == TOKEN
        self.calls.append(url)
        for path, answer in self.answers.items():
            if url.endswith(path):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected request {url}")


def edited(name, change):
    payload = json.loads(fixture_text(name))
    change(payload)
    return (200, json.dumps(payload))


def run(drift, fetch=None, environ=None, state_file=None):
    out, err = io.StringIO(), io.StringIO()
    kwargs = {"state_file": state_file} if state_file else {}
    code = drift.main(
        [], fetch=fetch or FakeFetch(), environ={"CLOUDFLARE_API_TOKEN": TOKEN} if environ is None else environ,
        out=out, err=err, **kwargs,
    )
    text = out.getvalue() + err.getvalue()
    assert HEADER_VALUE not in text, "the origin-lock header value reached the output"
    assert TOKEN not in text, "the API token reached the output"
    return code, text


def test_no_drift_against_the_committed_state_file(drift):
    code, text = run(drift)
    assert code == 0, text
    assert text.splitlines()[-1] == "exit 0: no drift"
    assert "'Mealy api-auth burst limit' 5 requests / 10 s / IP, block 10 s, active" in text
    assert "'Mealy origin lock' present, enabled, sets X-Origin-Verify (value not read)" in text
    assert "OK     browser-cache-ttl: Respect Existing Headers" in text
    assert "OK     access-apps: 0 Access application(s)" in text


def test_intent_is_read_from_the_committed_state_file(drift):
    intent = drift.parse_intent((INFRA / "cloudflare-state.md").read_text())
    assert (intent.waf_requests, intent.waf_period, intent.waf_timeout) == (5, 10, 10)
    assert intent.waf_action == "block" and intent.waf_enabled
    assert intent.waf_expression == '(starts_with(http.request.uri.path, "/auth/"))'
    assert intent.lock_name == "Mealy origin lock" and intent.lock_enabled
    assert intent.lock_expression == '(http.host eq "api.mealy.dev")'
    assert intent.lock_header == "X-Origin-Verify"
    assert intent.cache_ttl == 0
    assert intent.access_apps == ()  # both applications are recorded as REMOVED


def test_sanitize_drops_header_values_whatever_the_shape(drift):
    rule = json.loads(fixture_text("cloudflare_transform_rules.json"))["result"]["rules"][0]
    rule["action_parameters"]["headers"]["X-Other"] = {"operation": "set", "expression": HEADER_VALUE}
    assert HEADER_VALUE not in json.dumps(drift.sanitize_transform_rule(rule))


@pytest.mark.parametrize(
    "change,expected",
    [
        (lambda p: p["result"]["rules"][0].update(enabled=False), "enabled is False"),
        (lambda p: p["result"]["rules"][0]["action_parameters"]["headers"]["X-Origin-Verify"].update(operation="remove"),
         "operation is 'remove'"),
        (lambda p: p["result"]["rules"][0].update(expression='(http.host eq "mealy.dev")'), "expression is"),
        (lambda p: p["result"]["rules"][0]["action_parameters"].update(headers={}), "does not set X-Origin-Verify"),
    ],
)
def test_origin_lock_drift_never_prints_the_header_value(drift, change, expected):
    fetch = FakeFetch({ROUTE_TRANSFORM: edited("cloudflare_transform_rules.json", change)})
    code, text = run(drift, fetch)
    assert code == 1 and expected in text and "DRIFT  origin-lock" in text


ROUTE_TRANSFORM = f"{ZONE}/rulesets/phases/http_request_late_transform/entrypoint"
ROUTE_RATELIMIT = f"{ZONE}/rulesets/phases/http_ratelimit/entrypoint"


def test_missing_transform_rule_is_drift(drift):
    fetch = FakeFetch({ROUTE_TRANSFORM: (404, '{"success": false, "errors": [{"code": 10003}]}')})
    code, text = run(drift, fetch)
    assert code == 1 and "every request will 421" in text


def test_missing_waf_rule_is_exit_1_naming_it(drift):
    fetch = FakeFetch({ROUTE_RATELIMIT: edited("cloudflare_ratelimit.json", lambda p: p["result"].update(rules=[]))})
    code, text = run(drift, fetch)
    assert code == 1
    assert "rate-limit rule 'Mealy api-auth burst limit' is missing" in text
    assert text.splitlines()[-1].startswith("exit 1 drift: waf-rate-limit")


def test_waf_threshold_drift(drift):
    def loosen(p):
        p["result"]["rules"][0]["ratelimit"].update(requests_per_period=10, period=60)
    code, text = run(drift, FakeFetch({ROUTE_RATELIMIT: edited("cloudflare_ratelimit.json", loosen)}))
    assert code == 1 and "threshold is 10 / 60 s, intent 5 / 10 s" in text


@pytest.mark.parametrize(
    "change,expected",
    [
        (lambda r: r["ratelimit"].update(characteristics=["cf.colo.id"]), "not counted per IP"),
        (lambda r: r.update(action="log"), "action is 'log', intent 'block'"),
        (lambda r: r["ratelimit"].update(mitigation_timeout=60), "block duration is 60 s, intent 10 s"),
        (lambda r: r.update(enabled=False), "enabled is False, intent True"),
        (lambda r: r.update(expression='(starts_with(http.request.uri.path, "/"))'), "expression is"),
    ],
)
def test_waf_rule_drift_names_the_field(drift, change, expected):
    fetch = FakeFetch({ROUTE_RATELIMIT: edited("cloudflare_ratelimit.json", lambda p: change(p["result"]["rules"][0]))})
    code, text = run(drift, fetch)
    assert code == 1 and expected in text and "DRIFT  waf-rate-limit" in text


def test_a_recorded_browser_cache_ttl_duration_is_read_in_seconds(drift):
    original = (INFRA / "cloudflare-state.md").read_text()
    four_hours = re.sub(r"(Browser Cache TTL\): \*\*)Respect Existing\s+Headers(\*\*)", r"\g<1>4 hours\2", original)
    assert four_hours != original
    assert drift.parse_intent(four_hours).cache_ttl == 14400
    with pytest.raises(drift.Tooling, match="is not a duration"):
        drift.parse_intent(four_hours.replace("**4 hours**", "**a while**"))


def test_browser_cache_ttl_drift(drift):
    fetch = FakeFetch({f"{ZONE}/settings/browser_cache_ttl": edited(
        "cloudflare_browser_cache_ttl.json", lambda p: p["result"].update(value=14400))})
    code, text = run(drift, fetch)
    assert code == 1 and "Browser Cache TTL is 14400 s, intent Respect Existing Headers" in text


def test_a_live_access_application_is_drift(drift):
    fetch = FakeFetch({f"{ACCOUNT}/access/apps": (200, json.dumps(
        {"success": True, "result": [{"name": "Mealy Edge Gate", "domain": "api.mealy.dev"}]}))})
    code, text = run(drift, fetch)
    assert code == 1 and "Mealy Edge Gate" in text


def _access(apps):
    return FakeFetch({f"{ACCOUNT}/access/apps": (200, json.dumps({"success": True, "result": apps}))})


def test_an_access_application_on_another_zone_is_not_drift(drift):
    """The API lists the whole account; an old williamdoucet.dev gate is not this zone's."""
    code, text = run(drift, _access([{"name": "Old todo gate", "domain": "api.todo.williamdoucet.dev"}]))
    assert code == 0, text
    assert "0 Access application(s) on mealy.dev, as recorded (1 on other zones, not compared)" in text


@pytest.mark.parametrize(
    "app",
    [
        {"name": "No hostname at all"},  # unreadable: counts, so a shape change is loud
        {"name": "Wildcard", "domain": "*.mealy.dev"},
        {"name": "Destinations", "destinations": [{"type": "public", "uri": "mealy.dev/admin"}]},
        {"name": "Legacy list", "self_hosted_domains": ["other.example", "api.mealy.dev/x"]},
    ],
)
def test_an_access_application_on_the_zone_or_unreadable_is_drift(drift, app):
    code, text = run(drift, _access([app]))
    assert code == 1 and app["name"] in text and "DRIFT  access-apps" in text


def test_access_apps_that_are_not_a_list_is_exit_2(drift):
    code, text = run(drift, _access({"name": "not a list"}))
    assert code == 2 and "not a list" in text


def test_the_zone_name_is_read_from_the_state_file(drift):
    assert drift.parse_intent((INFRA / "cloudflare-state.md").read_text()).zone_name == "mealy.dev"


def test_token_unset_is_exit_2_naming_the_variable_and_calls_nothing(drift):
    fetch = FakeFetch()
    code, text = run(drift, fetch, environ={})
    assert code == 2 and "CLOUDFLARE_API_TOKEN is not set" in text
    assert fetch.calls == []


def test_rejected_token_is_exit_2_and_never_echoed(drift):
    fetch = FakeFetch({path: (401, '{"success": false, "errors": [{"code": 10000}]}') for path in ROUTES})
    code, text = run(drift, fetch)
    assert code == 2
    assert "CLOUDFLARE_API_TOKEN was rejected" in text and "(value not shown)" in text


def test_one_missing_permission_is_exit_2_naming_the_scope(drift):
    fetch = FakeFetch({f"{ZONE}/bot_management": (403, '{"success": false}')})
    code, text = run(drift, fetch)
    assert code == 2 and "Bot Management: Read" in text
    assert "OK     waf-rate-limit" in text


def test_an_error_body_is_never_printed(drift):
    fetch = FakeFetch({ROUTE_TRANSFORM: (500, json.dumps(
        {"success": False, "errors": [{"code": 10000, "message": HEADER_VALUE}], "result": HEADER_VALUE}))})
    code, text = run(drift, fetch)
    assert code == 2 and "error codes [10000]" in text


def test_network_failure_is_exit_2(drift):
    fetch = FakeFetch({path: drift.Tooling("cannot reach the Cloudflare API: timed out") for path in ROUTES})
    code, text = run(drift, fetch)
    assert code == 2 and "cannot reach the Cloudflare API" in text


def test_state_file_shape_change_is_exit_2(drift, tmp_path):
    state = tmp_path / "cloudflare-state.md"
    state.write_text((INFRA / "cloudflare-state.md").read_text().replace("Threshold:", "Limit:"))
    code, text = run(drift, state_file=state)
    assert code == 2 and "cannot find the WAF threshold" in text


def test_bot_fight_mode_is_drift_only_once_recorded(drift, tmp_path):
    fetch_on = lambda: FakeFetch({f"{ZONE}/bot_management": edited(
        "cloudflare_bot_management.json", lambda p: p["result"].update(fight_mode=True))})
    code, text = run(drift, fetch_on())
    assert code == 0 and "live on; not yet recorded" in text
    state = tmp_path / "cloudflare-state.md"
    original = (INFRA / "cloudflare-state.md").read_text()
    assert "Bot Fight Mode): **not yet recorded**" in original
    state.write_text(original.replace("Bot Fight Mode): **not yet recorded**", "Bot Fight Mode): **Off**", 1))
    code, text = run(drift, fetch_on(), state_file=state)
    assert code == 1 and "Bot Fight Mode is on, intent off" in text


def test_an_unexpected_api_shape_is_exit_2_and_prints_no_value(drift):
    """Headers as a list is a shape sanitize() does not expect; the error must be exit 2
    (Python's crash exit is 1, "drift") and must not quote the response."""
    def change(payload):
        payload["result"]["rules"][0]["action_parameters"]["headers"] = [HEADER_VALUE]
    fetch = FakeFetch({ROUTE_TRANSFORM: edited("cloudflare_transform_rules.json", change)})
    code, text = run(drift, fetch)  # run() asserts the header value never reaches the output
    assert code == 2 and "ERROR  origin-lock: unexpected AttributeError" in text
    assert "OK     browser-cache-ttl" in text  # the other comparisons still ran


def test_an_unreadable_state_file_is_exit_2(drift, tmp_path):
    code, text = run(drift, state_file=tmp_path / "missing.md")
    assert code == 2 and "cannot read missing.md" in text


def test_extra_arguments_are_a_usage_error(drift):
    assert drift.main(["--fix"], fetch=FakeFetch(), environ={"CLOUDFLARE_API_TOKEN": TOKEN},
                      out=io.StringIO(), err=io.StringIO()) == 2
