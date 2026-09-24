"""Shared helpers for the host-side operator-script tests.

Run on the host, never in a container: `python3 -m pytest infra/tests -q`.
Standard library plus pytest only. Nothing here reaches the network: every
`fly`, `curl` and `git` call goes through FakeRunner, which fails the test on
any command it was not given an answer for.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_script(filename: str, module_name: str):
    """Import a hyphenated script (`release-smoke.py`) as a module."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, INFRA / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def fixture_json(name: str):
    return json.loads(fixture_text(name))


@pytest.fixture(scope="session")
def smoke():
    return load_script("release-smoke.py", "release_smoke")


@pytest.fixture(scope="session")
def drift():
    return load_script("cloudflare-drift.py", "cloudflare_drift")


@pytest.fixture(autouse=True)
def no_declared_pause(smoke, tmp_path, monkeypatch):
    """Every test starts from `{}`. The committed infra/paused.json declares a real pause
    (TODOS.md P1), which would otherwise change checks 2, 4 and jobs-fresh in every test. The
    pause tests write their own file; one structural test reads the committed one."""
    empty = tmp_path / "paused-none.json"
    empty.write_text("{}")
    monkeypatch.setattr(smoke, "PAUSE_FILE", empty)
