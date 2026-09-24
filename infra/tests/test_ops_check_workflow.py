"""ops-check.yml must give the smoke script a `fly` to run.

`superfly/flyctl-actions/setup-flyctl` puts only a `flyctl` binary on the runner's PATH,
while `release-smoke.py` runs `fly`, as every operator command does. The workflow's first
dispatch (run 36009722470, M8 PR1b release) failed `[9]` and `[5]` with "`fly` is not on
PATH". A laptop never shows it: Homebrew installs both names. These tests run the
workflow's own step on a PATH shaped like the runner's.
"""

import os
import shutil
import subprocess
import textwrap

import pytest

from conftest import INFRA

WORKFLOW = INFRA.parent / ".github" / "workflows" / "ops-check.yml"
STEP = "Expose flyctl as fly"
SYSTEM_PATH = os.pathsep.join(["/usr/bin", "/bin"])


def step_run_block(text: str, name: str) -> str | None:
    """The `run: |` body of the step called `name`, dedented. Standard library only, so this
    reads the block by indentation rather than parsing YAML."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != f"- name: {name}":
            continue
        step_indent = len(line) - len(line.lstrip())
        for j in range(i + 1, len(lines)):
            here = lines[j]
            indent = len(here) - len(here.lstrip())
            if here.strip().startswith("- ") and indent <= step_indent:
                return None  # reached the next step without a run block
            if here.strip() == "run: |":
                body = []
                for k in range(j + 1, len(lines)):
                    nxt = lines[k]
                    if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                        break
                    body.append(nxt)
                return textwrap.dedent("\n".join(body))
    return None


@pytest.fixture
def toolcache(tmp_path):
    """What setup-flyctl leaves on PATH: one directory holding `flyctl`, and no `fly`."""
    cache = tmp_path / "hostedtoolcache" / "flyctl" / "0.4.102" / "x86_64"
    cache.mkdir(parents=True)
    fake = cache / "flyctl"
    fake.write_text('#!/bin/sh\necho "flyctl v0.4.102 (fake)"\n')
    fake.chmod(0o755)
    return cache


def test_the_runner_path_has_flyctl_but_no_fly(smoke, toolcache, monkeypatch):
    """The reproduction: the smoke script's own runner, on the runner's PATH."""
    monkeypatch.setenv("PATH", os.pathsep.join([str(toolcache), SYSTEM_PATH]))
    with pytest.raises(smoke.Tooling, match="`fly` is not on PATH"):
        smoke.Runner().run(["fly", "version"], 5)


def run_step(tmp_path, path: str) -> subprocess.CompletedProcess:
    """Run the workflow's step as GitHub does (`bash -e {0}`) and return the process."""
    snippet = step_run_block(WORKFLOW.read_text(), STEP)
    assert snippet, f"ops-check.yml has no `{STEP}` step with a run block"
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir(exist_ok=True)
    (tmp_path / "github_path").write_text("")
    env = {"PATH": path, "RUNNER_TEMP": str(runner_temp),
           "GITHUB_PATH": str(tmp_path / "github_path")}
    return subprocess.run([shutil.which("bash"), "-e", "-c", snippet], env=env,
                          capture_output=True, text=True)


def test_the_step_fails_when_flyctl_is_missing(tmp_path):
    """Setup quietly broken must fail here, not reappear as exit 2 two steps later."""
    assert run_step(tmp_path, SYSTEM_PATH).returncode != 0
    assert (tmp_path / "github_path").read_text() == ""


def test_the_workflow_step_puts_fly_on_path(smoke, toolcache, tmp_path, monkeypatch):
    step = run_step(tmp_path, os.pathsep.join([str(toolcache), SYSTEM_PATH]))
    assert step.returncode == 0, step.stderr
    github_path = tmp_path / "github_path"

    # The runner prepends each GITHUB_PATH line to PATH for the steps that follow.
    added = [line for line in github_path.read_text().splitlines() if line]
    assert added, "the step wrote nothing to GITHUB_PATH"
    monkeypatch.setenv("PATH", os.pathsep.join([*reversed(added), str(toolcache), SYSTEM_PATH]))
    completed = smoke.Runner().run(["fly", "version"], 5)
    assert completed.returncode == 0 and "flyctl v0.4.102 (fake)" in completed.stdout


def test_the_step_runs_after_setup_flyctl_and_before_every_smoke_step():
    lines = WORKFLOW.read_text().splitlines()
    setup = next(i for i, line in enumerate(lines) if "setup-flyctl@" in line)
    expose = next((i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP}"), None)
    smoke_runs = [i for i, line in enumerate(lines)
                  if "infra/release-smoke.py" in line and not line.lstrip().startswith("#")]
    assert expose is not None, f"ops-check.yml has no `{STEP}` step"
    assert smoke_runs, "ops-check.yml no longer runs infra/release-smoke.py"
    assert setup < expose < min(smoke_runs)
