"""Every diagnostics link the operator is handed must land on a real heading.

`release-smoke.py` prints `infra/incident-diagnostics.md#<anchor>` on each FAIL and ERROR
line, and the runbooks link each other by anchor. A renamed heading would silently turn
those into links to the top of the file, at the moment the reader needs the entry.
"""

import re

import pytest

from conftest import INFRA


def github_slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces become hyphens."""
    kept = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return kept.replace(" ", "-")


def anchors(filename: str) -> set[str]:
    text = (INFRA / filename).read_text()
    return {github_slug(m) for m in re.findall(r"^#{1,6} (.+?)\s*$", text, re.M)}


def test_slug_matches_githubs_rules():
    assert github_slug("Break-glass: the origin gate during a Cloudflare outage") == (
        "break-glass-the-origin-gate-during-a-cloudflare-outage"
    )
    assert github_slug("Transform Rules — origin lock (Modify Request Header)") == (
        "transform-rules--origin-lock-modify-request-header"
    )
    assert github_slug("5.2 Backend: roll back the code, never the schema") == (
        "52-backend-roll-back-the-code-never-the-schema"
    )


def test_every_smoke_check_links_an_existing_diagnostics_entry(smoke):
    targets = {c.diagnostics for c in smoke.CHECKS} | {smoke.TOOLING_DIAGNOSTICS}
    missing = targets - anchors("incident-diagnostics.md")
    assert not missing, f"release-smoke.py links headings that do not exist: {sorted(missing)}"


LINK = re.compile(r"\]\(\./([\w.-]+\.md)#([^)]+)\)|\]\(#([^)]+)\)")


@pytest.mark.parametrize(
    "source", ["RUNBOOK.md", "incident-diagnostics.md", "backup-restore-drill.md", "cloudflare-state.md"]
)
def test_every_anchor_link_between_the_runbooks_resolves(source):
    path = INFRA / source
    if not path.exists():
        pytest.skip(f"{source} not written yet")
    broken = []
    for other_file, other_anchor, local_anchor in LINK.findall(path.read_text()):
        target, anchor = (other_file, other_anchor) if other_file else (source, local_anchor)
        if not (INFRA / target).exists() or anchor not in anchors(target):
            broken.append(f"{target}#{anchor}")
    assert not broken, f"{source} links anchors that do not exist: {broken}"
