"""Tests for bin/obsidian-workflow.

Every test runs twice: once with a vault named `notes` and once with `My Notes`
(a name with a space that matches no project). Repos come from tests/_repo.py's
make_repo (git init on `main`, `.agents/config.json` copied from config.example.json
with `vault_path` overridden); the vault lives inside the repo unless a test says otherwise.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import _repo as R

PAYLOAD = Path(__file__).resolve().parents[1]
MODULE_PATH = PAYLOAD / "bin" / "obsidian-workflow"
VAULT_NAMES = ["notes", "My Notes"]
TODO = "Mealboard/Todo List.md"
LOADING_TEXT = "Improve the meal planner loading state so quick loads feel intentional instead of broken."
TRANSITION_TEXT = "Add a short transition for the day and date bar so it does not pop in abruptly after loading."


def load_module():
    loader = importlib.machinery.SourceFileLoader("obsidian_workflow", str(MODULE_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


workflow = load_module()
_lib = workflow._lib


def run(*argv: str) -> tuple[int, dict]:
    """Run the CLI in-process and return (exit code, parsed JSON envelope)."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = workflow.run([str(a) for a in argv])
    return exit_code, json.loads(buffer.getvalue())


def make_repo(tmp_path: Path, vault_name: str) -> Path:
    """A git-backed repo (tests/_repo.py) with the vault inside it at <repo>/<vault_name>/."""
    root = R.make_repo(tmp_path, vault_path=vault_name)
    (root / vault_name / "Mealboard").mkdir(parents=True)
    return root


class Repo:
    def __init__(self, root: Path, vault_name: str) -> None:
        self.root = root
        self.vault_name = vault_name
        self.vault = root / vault_name

    @property
    def ctx(self) -> "workflow.Ctx":
        return workflow.Ctx.load(self.root)

    def note(self, rel: str, text: str) -> Path:
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def read(self, rel: str) -> str:
        return (self.vault / rel).read_text()

    def plan(self, rel: str, text: str = "# Plan\n\nBody\n") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def entry(self, key: str) -> dict | None:
        ctx = self.ctx
        return _lib.registry_get(ctx.root, ctx.cfg, key)

    def reservation(self, task_id: str) -> dict | None:
        ctx = self.ctx
        return _lib.task_id_get(ctx.root, ctx.cfg, task_id)


@pytest.fixture(params=VAULT_NAMES, ids=["vault-notes", "vault-with-space"], autouse=True)
def vault_name(request):
    return request.param


@pytest.fixture
def repo(tmp_path, vault_name, monkeypatch) -> Repo:
    root = make_repo(tmp_path, vault_name)
    monkeypatch.chdir(root)
    return Repo(root, vault_name)


def two_task_note(repo: Repo, with_ids: bool = True) -> Path:
    first_id = "  ^mealboard-loading-state\n" if with_ids else ""
    second_id = "  ^mealboard-date-bar\n" if with_ids else ""
    return repo.note(
        TODO,
        "## Meal Planner Board\n"
        f"- [ ] {LOADING_TEXT}\n"
        f"{first_id}"
        "  notes:: Keep this note.\n"
        f"- [ ] {TRANSITION_TEXT}\n"
        f"{second_id}",
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseTasks:
    def test_parse_tasks_extracts_headings_ids_and_metadata(self, repo):
        note = repo.note(
            TODO,
            "## Meal Planner Board\n"
            "\n"
            "- [ ] Improve loading state.\n"
            "  ^mealboard-loading-state\n"
            "  status:: idea\n"
            "  notes:: Research quick-loading page patterns.\n"
            "\n"
            "- [x] Add date bar transition.\n"
            "  ^mealboard-datebar-animation\n",
        )

        tasks = workflow.parse_tasks(note, TODO)

        assert len(tasks) == 2
        first = tasks[0]
        assert first.heading == "Meal Planner Board"
        assert first.task_id == "mealboard-loading-state"
        assert first.note_path == TODO
        assert first.note_ref == f"{TODO}#^mealboard-loading-state"
        assert first.checked is False
        assert first.metadata["status"] == ["idea"]
        assert first.metadata["notes"] == ["Research quick-loading page patterns."]
        assert tasks[1].task_id == "mealboard-datebar-animation"
        assert tasks[1].checked is True

    def test_select_task_requires_choice_when_multiple_unchecked(self, repo):
        note = repo.note(
            TODO,
            "- [ ] Improve loading state.\n"
            "  ^mealboard-loading-state\n"
            "- [ ] Add date bar transition.\n"
            "  ^mealboard-datebar-animation\n",
        )

        status, payload = workflow.select_task(workflow.parse_tasks(note, TODO), None)

        assert status == "needs_selection"
        assert len(payload["candidates"]) == 2

    def test_tab_indented_children_belong_to_their_task(self, repo):
        note = repo.note(TODO, "- [ ] Tabbed task.\n\t^tabbed-task\n\tnotes:: tabs here\n- [ ] Next.\n")

        tasks = workflow.parse_tasks(note, TODO)

        assert tasks[0].task_id == "tabbed-task"
        assert tasks[0].metadata["notes"] == ["tabs here"]
        assert tasks[0].end_line == 3

    def test_list_tasks_accepts_vault_repo_and_absolute_paths(self, repo):
        note = repo.note(TODO, "- [ ] Only task.\n  ^only-task\n")

        for given in (TODO, f"{repo.vault_name}/{TODO}", str(note)):
            exit_code, payload = run("list-tasks", given)
            assert exit_code == 0, given
            assert payload["note_path"] == TODO
            assert payload["tasks"][0]["note_ref"] == f"{TODO}#^only-task"

    def test_missing_note_is_exit_2(self, repo):
        exit_code, payload = run("list-tasks", "Mealboard/Nope.md")

        assert exit_code == 2
        assert payload["status"] == "error"
        assert "not found" in payload["error"]


class TestFencedCodeBlocks:
    def test_strip_fenced_code_blocks_preserves_line_count(self):
        source = ["Before", "```md", "- [ ] Example", "  ^example-id", "```", "After"]
        stripped = workflow.strip_fenced_code_blocks(source)
        assert len(stripped) == len(source)
        assert stripped == ["Before", "", "", "", "", "After"]

    def test_strip_fenced_code_blocks_handles_tilde_and_longer_fences(self):
        source = [
            "~~~python", "- [ ] tilde example", "  ^tilde-id", "~~~",
            "````", "- [ ] longer fence example", "  ^longer-id", "````",
        ]
        assert all(line == "" for line in workflow.strip_fenced_code_blocks(source))

    def test_strip_fenced_code_blocks_leaves_unfenced_content_untouched(self):
        source = ["# Heading", "- [ ] Real task", "  ^real-id"]
        assert workflow.strip_fenced_code_blocks(source) == source

    def test_parse_tasks_ignores_tasks_inside_fenced_examples(self, repo):
        note = repo.note(
            TODO,
            "# Docs\n\nExample task layout:\n\n```md\n- [ ] Example task from documentation\n"
            "  ^example-block-id\n  status:: idea\n```\n\n## Real Work\n\n- [ ] Actually do the thing.\n  ^real-task-id\n",
        )

        tasks = workflow.parse_tasks(note, TODO)

        assert [task.task_id for task in tasks] == ["real-task-id"]
        assert tasks[0].heading == "Docs / Real Work"

    def test_validate_vault_ignores_duplicate_ids_inside_fenced_blocks(self, repo):
        repo.note(
            "README.md",
            "# Vault Docs\n\nFirst example:\n\n```md\n- [ ] Example\n  ^shared-id\n```\n\n"
            "Second example:\n\n```md\n- [ ] Another example\n  ^shared-id\n```\n",
        )
        repo.note(TODO, "- [ ] Only real task.\n  ^shared-id\n")

        exit_code, payload = run("validate-vault")

        assert exit_code == 0
        assert payload["status"] == "ok"


# ---------------------------------------------------------------------------
# Task ID generation
# ---------------------------------------------------------------------------


class TestTaskIdGeneration:
    def test_build_task_id_base_prefers_readable_contextual_ids(self):
        assert workflow.build_task_id_base(TODO, "Meal Planner Board", LOADING_TEXT) == "mealboard-loading-state"

    def test_vault_dir_name_is_excluded_from_context_dynamically(self, repo, vault_name):
        vault_prefixed = f"{vault_name}/Todo List.md"

        excluded = workflow.build_task_id_base(vault_prefixed, "Meal Planner Board", LOADING_TEXT, exclude={vault_name.lower()})
        not_excluded = workflow.build_task_id_base(vault_prefixed, "Meal Planner Board", LOADING_TEXT)

        assert excluded == "meal-loading-state"
        assert not_excluded.startswith(workflow.slug_words(vault_name)[0])
        assert repo.ctx.id_base(vault_prefixed, "Meal Planner Board", LOADING_TEXT) == "meal-loading-state"
        assert repo.ctx.id_base("Todo List.md", "Meal Planner Board", LOADING_TEXT) == "meal-loading-state"

    def test_ensure_task_id_inserts_generated_id_only_once(self, repo):
        repo.note(TODO, f"## Meal Planner Board\n- [ ] {LOADING_TEXT}\n  notes:: Keep this note.\n")

        first_exit, first = run("ensure-task-id", TODO, "--line", "2")
        second_exit, second = run("ensure-task-id", first["note_ref"])

        contents = repo.read(TODO)
        assert first_exit == 0
        assert first["created"] is True
        assert first["task_id"] == "mealboard-loading-state"
        assert first["note_ref"] == f"{TODO}#^mealboard-loading-state"
        assert contents.count("^mealboard-loading-state") == 1
        assert "notes:: Keep this note." in contents
        assert second_exit == 0
        assert second["created"] is False
        assert second["task_id"] == "mealboard-loading-state"

    def test_ensure_task_id_never_mints_an_id_already_used_in_the_note(self, repo):
        repo.note(TODO, f"## Meal Planner Board\n- [x] {LOADING_TEXT}\n  ^mealboard-loading-state\n- [ ] {LOADING_TEXT}\n")

        exit_code, payload = run("ensure-task-id", TODO)

        assert exit_code == 0
        assert payload["task_id"] == "mealboard-loading-state-v2"
        assert repo.read(TODO).count("^mealboard-loading-state\n") == 1

    def test_suggest_task_id_suffixes_on_collision(self, repo):
        repo.note(TODO, f"- [ ] {LOADING_TEXT}\n  ^mealboard-loading-state\n")

        exit_code, payload = run("suggest-task-id", "--note-ref", TODO, "--task-text", LOADING_TEXT, "--heading", "Meal Planner Board")

        assert exit_code == 0
        assert payload["task_id"] == "mealboard-loading-state-v2"
        assert payload["note_path"] == TODO

    def test_suggest_task_id_gives_up_after_the_attempt_cap(self, repo, monkeypatch):
        repo.note(TODO, f"- [ ] a\n  ^mealboard-loading-state\n- [ ] b\n  ^mealboard-loading-state-v2\n")
        monkeypatch.setattr(workflow, "MAX_ID_ATTEMPTS", 2)

        exit_code, payload = run("suggest-task-id", "--note-ref", TODO, "--task-text", LOADING_TEXT, "--heading", "Meal Planner Board")

        assert exit_code == 1
        assert payload["status"] == "error"
        assert payload["error"] == "Could not generate a unique task ID"
        assert payload["base_task_id"] == "mealboard-loading-state"

    def test_parse_task_all_unchecked_returns_note_batch_payload(self, repo):
        repo.note(TODO, "## Meal Planner Board\n- [ ] Improve loading state.\n  notes:: Keep this note.\n- [ ] Add date bar transition.\n")

        exit_code, payload = run("parse-task", TODO, "--all-unchecked")

        assert exit_code == 0
        assert payload["status"] == "ok"
        assert payload["note_ref"] == f"{TODO}#batch"
        assert payload["task_count"] == 2
        assert [task["line"] for task in payload["tasks"]] == [2, 4]

    def test_ensure_task_id_all_unchecked_inserts_ids_for_entire_note(self, repo):
        two_task_note(repo, with_ids=False)

        exit_code, payload = run("ensure-task-id", TODO, "--all-unchecked")

        contents = repo.read(TODO)
        assert exit_code == 0
        assert payload["note_ref"] == f"{TODO}#batch"
        assert payload["task_count"] == 2
        assert payload["created_count"] == 2
        assert payload["task_ids"] == ["mealboard-loading-state", "mealboard-transition-day"]
        assert "^mealboard-loading-state" in contents
        assert "^mealboard-transition-day" in contents
        assert "notes:: Keep this note." in contents
        assert repo.reservation("mealboard-loading-state")["state"] == "planning"
        assert repo.reservation("mealboard-transition-day")["current_note_ref"] == f"{TODO}#^mealboard-transition-day"

    def test_inserted_block_id_matches_existing_child_indentation(self, repo):
        repo.note(TODO, "- [ ] Tabbed task.\n\tnotes:: tabs here\n- [ ] Plain task.\n")

        first_exit, _ = run("ensure-task-id", TODO, "--line", "1")
        second_exit, _ = run("ensure-task-id", TODO, "--line", "4")

        assert first_exit == 0 and second_exit == 0
        assert repo.read(TODO) == "- [ ] Tabbed task.\n\t^mealboard-tabbed-task\n\tnotes:: tabs here\n- [ ] Plain task.\n  ^mealboard-plain-task\n"


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestValidationFailures:
    def test_validate_vault_reports_duplicate_in_same_note(self, repo):
        repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n- [ ] Replace loading treatment.\n  ^mealboard-loading-state\n")

        exit_code, payload = run("validate-vault")

        assert exit_code == 1
        assert payload == {
            "status": "error",
            "error": "Duplicate task ID in note",
            "task_id": "mealboard-loading-state",
            "note_path": TODO,
            "locations": [1, 3],
            "recommendation": "Rename one of the duplicate task IDs before continuing.",
        }

    def test_validate_vault_reports_duplicate_across_notes(self, repo):
        repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n")
        repo.note("Archive/Mealboard Ideas.md", "- [ ] Revisit loading state.\n  ^mealboard-loading-state\n")

        exit_code, payload = run("validate-vault")

        assert exit_code == 1
        assert payload == {
            "status": "error",
            "error": "Duplicate task ID across notes",
            "task_id": "mealboard-loading-state",
            "locations": [
                "Archive/Mealboard Ideas.md#^mealboard-loading-state",
                f"{TODO}#^mealboard-loading-state",
            ],
            "recommendation": "Create a new unique task ID for the newer task.",
        }

    def test_validate_task_id_blocks_reserved_id_reuse(self, repo):
        repo.ctx.reserve("mealboard-loading-state", f"{TODO}#^mealboard-loading-state", "shipped")

        exit_code, payload = run(
            "validate-task-id", "--task-id", "mealboard-loading-state",
            "--note-ref", f"{repo.vault_name}/Mealboard/New Todo.md#^mealboard-loading-state",
        )

        assert exit_code == 1
        assert payload == {
            "status": "error",
            "error": "Task ID is already reserved",
            "task_id": "mealboard-loading-state",
            "existing_note_ref": f"{TODO}#^mealboard-loading-state",
            "existing_state": "shipped",
            "recommendation": "Create a new task ID, such as mealboard-loading-state-v2.",
        }

    def test_validate_task_id_allows_the_reserving_ref_itself(self, repo):
        repo.ctx.reserve("mealboard-loading-state", f"{TODO}#^mealboard-loading-state", "shipped")

        exit_code, payload = run("validate-task-id", "--task-id", "mealboard-loading-state", "--note-ref", f"{repo.vault_name}/{TODO}#^mealboard-loading-state")

        assert exit_code == 0
        assert payload["note_ref"] == f"{TODO}#^mealboard-loading-state"

    def test_ensure_task_id_reports_ambiguous_selection(self, repo):
        repo.note(TODO, f"- [ ] {LOADING_TEXT}\n- [ ] {TRANSITION_TEXT}\n")

        exit_code, payload = run("ensure-task-id", TODO)

        assert exit_code == 1
        assert payload == {
            "status": "error",
            "error": "Task selection is ambiguous",
            "note_path": TODO,
            "candidates": [{"line": 1, "task_text": LOADING_TEXT}, {"line": 2, "task_text": TRANSITION_TEXT}],
            "recommendation": "Select a single task explicitly before generating a block ID.",
        }

    def test_argparse_errors_use_the_json_envelope(self, repo):
        exit_code, payload = run("registry-get")

        assert exit_code == 2
        assert payload["status"] == "error"
        assert "usage" in payload


# ---------------------------------------------------------------------------
# Note updates
# ---------------------------------------------------------------------------


class TestNoteUpdate:
    def test_note_update_sets_fields_appends_review_status_and_checks_box(self, repo):
        note = repo.note(TODO, "## Meal Planner Board\n- [ ] Improve loading state.\n  ^mealboard-loading-state\n  status:: idea\n  notes:: Keep existing prose.\n")

        updated = workflow.update_note_file(
            note, "mealboard-loading-state", TODO,
            set_fields={"status": "shipped", "plan": ".agents/plans/features/x/plan.md"},
            append_fields={"review_status": ["ceo-reviewed", "eng-reviewed"]},
            check=True,
        )

        contents = repo.read(TODO)
        assert "- [x] Improve loading state." in contents
        assert "## Completed" in contents
        assert "status::" not in contents
        assert "plan::" not in contents
        assert "review_status::" not in contents
        assert "notes:: Keep existing prose." in contents
        assert updated.checked is True
        assert updated.heading == "Completed"

    def test_note_update_is_idempotent_for_multi_value_fields(self, repo):
        note = repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  review_status:: ceo-reviewed\n")

        workflow.update_note_file(note, "mealboard-loading-state", TODO, set_fields={}, append_fields={"review_status": ["ceo-reviewed", "eng-reviewed"]}, check=None)

        assert "review_status::" not in repo.read(TODO)

    def test_note_update_set_only_does_not_duplicate_multi_keys(self, repo):
        note = repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  review_status:: eng-reviewed\n  review_status:: design-reviewed\n")

        workflow.update_note_file(note, "mealboard-loading-state", TODO, set_fields={"status": "shipped"}, append_fields={}, check=True)

        contents = repo.read(TODO)
        assert "review_status::" not in contents
        assert "status::" not in contents
        assert "## Completed" in contents
        assert "- [x]" in contents

    def test_unmanaged_fields_are_written_and_appended_without_duplicates(self, repo):
        note = repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  tags:: ui\n")

        workflow.update_note_file(note, "mealboard-loading-state", TODO, set_fields={"owner": "will"}, append_fields={"tags": ["ui", "perf"]}, check=None)

        assert repo.read(TODO) == "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  owner:: will\n  tags:: ui\n  tags:: perf\n"

    def test_last_sync_error_is_no_longer_a_managed_key(self, repo):
        assert "last_sync_error" not in workflow.MANAGED_NOTE_KEYS
        note = repo.note(TODO, "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  last_sync_error:: keep me\n  status:: idea\n")

        workflow.update_note_file(note, "mealboard-loading-state", TODO, set_fields={}, append_fields={}, check=None)

        contents = repo.read(TODO)
        assert "last_sync_error:: keep me" in contents
        assert "status::" not in contents

    def test_note_update_can_target_multiple_tasks_by_task_ids(self, repo):
        repo.note(
            TODO,
            "- [ ] Improve loading state.\n  ^mealboard-loading-state\n  status:: idea\n"
            "- [ ] Add date bar transition.\n  ^mealboard-date-bar\n  review_status:: ceo-reviewed\n"
            "- [ ] Leave this alone.\n  ^mealboard-untouched\n  status:: blocked\n",
        )

        exit_code, payload = run(
            "note-update", f"{repo.vault_name}/{TODO}", "--task-ids-json", json.dumps(["mealboard-loading-state", "mealboard-date-bar"]),
            "--set", "status=planning", "--append", "review_status=ceo-reviewed",
        )

        contents = repo.read(TODO)
        assert exit_code == 0
        assert payload["note_path"] == TODO
        assert payload["task_count"] == 2
        assert "mealboard-loading-state\n  status::" not in contents
        assert "mealboard-date-bar\n  review_status::" not in contents
        assert "mealboard-untouched\n  status:: blocked" in contents

    def test_task_ids_json_accepts_objects_with_task_id(self, repo):
        two_task_note(repo)

        exit_code, payload = run("note-update", TODO, "--task-ids-json", json.dumps([{"task_id": "mealboard-loading-state", "note_ref": "x"}]), "--check")

        assert exit_code == 0
        assert payload["task_count"] == 1
        assert payload["tasks"][0]["task_id"] == "mealboard-loading-state"
        assert payload["tasks"][0]["checked"] is True

    @pytest.mark.parametrize("raw", ['{"task_id": "a"}', "[1]", '[{"note_ref": "x"}]', "not json"])
    def test_task_ids_json_rejects_bad_values_with_envelope(self, repo, raw):
        two_task_note(repo)

        exit_code, payload = run("note-update", TODO, "--task-ids-json", raw)

        assert exit_code == 1
        assert payload["status"] == "error"
        assert "--task-ids-json" in payload["error"]

    def test_note_update_check_creates_completed_section_and_preserves_notes(self, repo):
        note = repo.note(
            TODO,
            "## Meal Planner Board\n- [ ] Improve loading state.\n  ^mealboard-loading-state\n  status:: planning\n"
            "  notes:: Preserve this context.\n\n## Recipes\n- [ ] Leave this task alone.\n  ^leave-this-alone\n",
        )

        updated = workflow.update_note_file(
            note, "mealboard-loading-state", TODO,
            set_fields={"status": "shipped", "completed": "2026-04-12"}, append_fields={"review_status": ["eng-reviewed"]}, check=True,
        )

        contents = repo.read(TODO)
        completed_section = contents.split("## Completed", 1)[1]
        active_section = contents.split("## Meal Planner Board", 1)[1].split("## Recipes", 1)[0]
        assert "status::" not in contents
        assert "completed::" not in contents
        assert "review_status::" not in contents
        assert "notes:: Preserve this context." in completed_section
        assert "^mealboard-loading-state" in completed_section
        assert "mealboard-loading-state" not in active_section
        assert updated.heading == "Completed"

    def test_note_update_batch_appends_checked_tasks_to_existing_completed_section(self, repo):
        note = repo.note(
            TODO,
            "## General\n- [ ] First active task.\n  ^first-task\n  status:: planning\n  notes:: First note.\n\n"
            "## Recipes\n- [ ] Second active task.\n  ^second-task\n  review_status:: eng-reviewed\n  notes:: Second note.\n\n"
            "## Completed\n- [x] Existing completed task.\n  ^existing-task\n  notes:: Already done.\n",
        )

        updated = workflow.update_note_file_batch(
            note, TODO, set_fields={"status": "shipped"}, append_fields={"review_status": ["design-reviewed"]}, check=True,
            task_ids=["first-task", "second-task"],
        )

        contents = repo.read(TODO)
        completed_section = contents.split("## Completed", 1)[1]
        assert completed_section.index("^existing-task") < completed_section.index("^first-task") < completed_section.index("^second-task")
        assert "status::" not in contents
        assert "review_status::" not in contents
        assert "notes:: First note." in completed_section
        assert "notes:: Second note." in completed_section
        assert all(task.heading == "Completed" for task in updated)

    @pytest.mark.parametrize(
        "text",
        [
            "# Project\n## Active\n- [ ] Other.\n  ^other\n## Completed\n- [x] Done already.\n  ^done-already\n  status:: shipped\n",
            "# Completed\n### Old\n- [x] Done already.\n  ^done-already\n  status:: shipped\n- [x] Sibling.\n  ^sibling\n",
            "## completed\n- [x] Done already.\n  ^done-already\n  status:: shipped\n",
        ],
        ids=["nested-completed", "subsection-of-completed", "lowercase"],
    )
    def test_check_does_not_rearchive_tasks_already_under_completed(self, repo, text):
        note = repo.note(TODO, text)
        expected = text.replace("  status:: shipped\n", "")

        for _ in range(2):
            updated = workflow.update_note_file(note, "done-already", TODO, set_fields={"status": "shipped"}, append_fields={}, check=True)

        assert repo.read(TODO) == expected
        assert workflow.under_completed(updated.heading)

    def test_under_completed_requires_a_completed_segment(self):
        assert workflow.under_completed("Completed")
        assert workflow.under_completed("Project / completed")
        assert workflow.under_completed("Completed / Old")
        assert not workflow.under_completed("Completed Features / Old")
        assert not workflow.under_completed(None)

    def test_written_child_lines_follow_tab_indentation(self, repo):
        note = repo.note(TODO, "- [ ] Tabbed task.\n\t^tabbed-task\n\tstatus:: idea\n\tnotes:: keep\n")

        workflow.update_note_file(note, "tabbed-task", TODO, set_fields={"owner": "will"}, append_fields={"tags": ["ui"]}, check=None)

        assert repo.read(TODO) == "- [ ] Tabbed task.\n\t^tabbed-task\n\towner:: will\n\ttags:: ui\n\tnotes:: keep\n"

    def test_check_via_cli_uses_registry_bound_fields_only_for_filtering(self, repo):
        two_task_note(repo)

        exit_code, payload = run("note-update", f"{TODO}#^mealboard-loading-state", "--set", "status=shipped", "--set", "plan=x.md", "--append", "review_status=eng-reviewed", "--check")

        contents = repo.read(TODO)
        assert exit_code == 0
        assert payload["task"]["checked"] is True
        assert payload["task"]["heading"] == "Completed"
        assert "status::" not in contents and "plan::" not in contents and "review_status::" not in contents
        assert "notes:: Keep this note." in contents

    def test_uncheck_moves_nothing_and_clears_box(self, repo):
        repo.note(TODO, "## Completed\n- [x] Done.\n  ^done\n  status:: shipped\n")

        exit_code, payload = run("note-update", f"{TODO}#^done", "--uncheck")

        assert exit_code == 0
        assert payload["task"]["checked"] is False
        assert repo.read(TODO) == "## Completed\n- [ ] Done.\n  ^done\n"

    def test_check_and_uncheck_together_is_an_error(self, repo):
        two_task_note(repo)

        exit_code, payload = run("note-update", f"{TODO}#^mealboard-loading-state", "--check", "--uncheck")

        assert exit_code == 1
        assert payload["error"] == "Use either --check or --uncheck, not both"


# ---------------------------------------------------------------------------
# Registry and plan metadata
# ---------------------------------------------------------------------------

ENTRY_SHAPE = {"key", "kind", "note_path", "task_id", "plan_mode", "plan_path", "branch", "workflow_status",
               "implementation_status", "review_status", "created_at", "updated_at", "registry_version"}
RESERVATION_SHAPE = {"task_id", "first_note_ref", "current_note_ref", "state", "reserved_reason", "updated_at"}


class TestRegistry:
    def test_registry_upsert_round_trip_reserves_task_id_one_file_per_entry(self, repo):
        two_task_note(repo)
        key = f"{TODO}#^mealboard-loading-state"

        exit_code, payload = run(
            "registry-upsert", f"{repo.vault_name}/{key}", "--branch", "feat/loading",
            "--set", "source_heading=Meal Planner Board", "--set", "workflow_status=planning", "--set", "implementation_status=not-started",
            "--append", "review_status=ceo-reviewed", "--append", "review_status=ceo-reviewed",
        )

        entry = repo.entry(key)
        reserved = repo.reservation("mealboard-loading-state")
        entries_dir = repo.root / ".agents" / "state" / "registry" / "entries"
        assert exit_code == 0
        assert payload["key"] == key
        assert ENTRY_SHAPE <= set(entry)
        assert entry["kind"] == "note-task"
        assert entry["plan_mode"] == "single-task"
        assert entry["note_path"] == TODO
        assert entry["task_id"] == "mealboard-loading-state"
        assert entry["branch"] == "feat/loading"
        assert entry["review_status"] == ["ceo-reviewed"]
        assert entry["registry_version"] == _lib.REGISTRY_VERSION
        assert set(reserved) == RESERVATION_SHAPE
        assert reserved["first_note_ref"] == key
        assert reserved["state"] == "not-started"
        assert reserved["reserved_reason"] == "used-in-workflow"
        assert len(list(entries_dir.glob("*.json"))) == 1
        assert not (repo.root / ".claude" / "workflow-registry.json").exists()

    def test_registry_upsert_batch_uses_source_tasks_flag_and_reserves_each_task(self, repo):
        two_task_note(repo)
        source_tasks = [
            {"task_id": "mealboard-loading-state", "note_ref": f"{repo.vault_name}/{TODO}#^mealboard-loading-state",
             "note_path": "ignored", "heading": "Meal Planner Board", "task_text": LOADING_TEXT, "line": 2},
            {"task_id": "mealboard-date-bar", "heading": "Meal Planner Board", "task_text": TRANSITION_TEXT},
        ]

        exit_code, payload = run(
            "registry-upsert", TODO, "--batch", "--source-tasks-json", json.dumps(source_tasks),
            "--set", "workflow_status=planning", "--set", "implementation_status=not-started",
        )

        entry = repo.entry(f"{TODO}#batch")
        assert exit_code == 0
        assert payload["key"] == f"{TODO}#batch"
        assert entry["kind"] == "note-batch"
        assert entry["plan_mode"] == "batch-note"
        assert entry["task_count"] == 2
        assert entry["source_tasks"] == [
            {"task_id": "mealboard-loading-state", "note_ref": f"{TODO}#^mealboard-loading-state", "heading": "Meal Planner Board", "task_text": LOADING_TEXT},
            {"task_id": "mealboard-date-bar", "note_ref": f"{TODO}#^mealboard-date-bar", "heading": "Meal Planner Board", "task_text": TRANSITION_TEXT},
        ]
        assert repo.reservation("mealboard-loading-state")["state"] == "not-started"
        assert repo.reservation("mealboard-date-bar")["current_note_ref"] == f"{TODO}#^mealboard-date-bar"

    @pytest.mark.parametrize("raw", ["not json", '{"task_id": "a"}', "[1]", '[{"note_ref": "x"}]'])
    def test_bad_source_tasks_json_is_an_error_envelope(self, repo, raw):
        two_task_note(repo)

        exit_code, payload = run("registry-upsert", TODO, "--batch", "--source-tasks-json", raw)

        assert exit_code == 1
        assert payload["status"] == "error"
        assert "--source-tasks-json" in payload["error"]
        assert repo.entry(f"{TODO}#batch") is None

    def test_source_tasks_json_set_key_is_no_longer_magic(self, repo):
        two_task_note(repo)

        exit_code, _ = run("registry-upsert", TODO, "--batch", "--set", 'source_tasks_json=[{"task_id": "mealboard-loading-state"}]')

        assert exit_code == 0
        assert "source_tasks" not in repo.entry(f"{TODO}#batch")
        assert repo.reservation("mealboard-loading-state") is None

    def test_plan_path_is_normalized_to_repo_relative_on_write(self, repo):
        two_task_note(repo)
        plan = repo.plan(".agents/plans/features/feat/feat-plan-20260901-120000.md")

        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--set", f"plan_path={plan}")
        absolute = repo.entry(f"{TODO}#^mealboard-loading-state")["plan_path"]
        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--set", "plan_path=./.agents/plans/features/feat/feat-plan-20260901-120000.md")
        dotted = repo.entry(f"{TODO}#^mealboard-loading-state")["plan_path"]

        assert absolute == dotted == ".agents/plans/features/feat/feat-plan-20260901-120000.md"

    def test_registry_upsert_without_note_uses_plan_branch_key(self, repo):
        exit_code, payload = run("registry-upsert", "--branch", "feat/office-hours", "--plan-kind", "feature", "--set", "workflow_status=planning")

        entry = repo.entry("plan:feat-office-hours")
        assert exit_code == 0
        assert payload["key"] == "plan:feat-office-hours"
        assert entry["kind"] == "plan"
        assert entry["plan_mode"] == "feature"
        assert entry["plan_kind"] == "feature"
        assert entry["branch"] == "feat/office-hours"
        assert entry["note_path"] is None

    def test_registry_upsert_without_key_uses_current_branch_else_exit_2(self, repo):
        on_branch_code, on_branch = run("registry-upsert", "--set", "workflow_status=planning")
        R.git(repo.root, "checkout", "-q", "--detach")
        exit_code, payload = run("registry-upsert", "--set", "workflow_status=planning")

        assert on_branch_code == 0 and on_branch["key"] == "plan:main"
        assert on_branch["entry"]["branch"] == "main"
        assert exit_code == 2
        assert payload["status"] == "error"

    def test_registry_upsert_accepts_prefixed_keys_from_skills(self, repo):
        plan_code, plan = run(
            "registry-upsert", "plan:feat-office-hours", "--kind", "plan", "--branch", "feat/office-hours",
            "--set", "workflow_status=planning", "--set", "review_status=[]",
        )
        epic_code, epic = run("registry-upsert", "epic:storage", "--set", "workflow_status=ceo-reviewed", "--append", "review_status=ceo-reviewed")
        qf_code, qf = run("registry-upsert", "quickfix:typo", "--plan-kind", "feature")
        bad_code, bad = run("registry-upsert", "plan:feat-x", "--batch")

        assert plan_code == 0 and plan["key"] == "plan:feat-office-hours"
        assert (plan["entry"]["kind"], plan["entry"]["plan_mode"], plan["entry"]["branch"]) == ("plan", "feature", "feat/office-hours")
        assert plan["entry"]["review_status"] == []
        assert epic_code == 0
        assert (epic["entry"]["kind"], epic["entry"]["plan_mode"], epic["entry"]["review_status"]) == ("epic", "epic", ["ceo-reviewed"])
        assert qf_code == 0 and (qf["entry"]["kind"], qf["entry"]["plan_kind"]) == ("quickfix", "feature")
        assert bad_code == 1 and "note keys only" in bad["error"]
        assert repo.entry("plan:feat-x") is None

    def test_registry_upsert_batch_key_suffix_implies_batch(self, repo):
        two_task_note(repo)

        exit_code, payload = run("registry-upsert", f"{repo.vault_name}/{TODO}#batch", "--set", "plan_path=batch.md")

        assert exit_code == 0 and payload["key"] == f"{TODO}#batch"
        assert (payload["entry"]["kind"], payload["entry"]["plan_mode"], payload["entry"]["note_path"]) == ("note-batch", "batch-note", TODO)

    def test_plan_kind_is_validated(self, repo):
        exit_code, payload = run("registry-upsert", "plan:feat-x", "--plan-kind", "huge")

        assert exit_code == 2 and payload["status"] == "error" and "usage" in payload
        assert repo.entry("plan:feat-x") is None

    def test_registry_upsert_honours_explicit_kind(self, repo):
        two_task_note(repo)

        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--kind", "quickfix")

        entry = repo.entry(f"{TODO}#^mealboard-loading-state")
        assert entry["kind"] == "quickfix"
        assert entry["plan_mode"] == "quickfix"

    def test_registry_upsert_rejects_ids_reserved_by_another_note(self, repo):
        two_task_note(repo)
        repo.ctx.reserve("mealboard-loading-state", "Archive/Old.md#^mealboard-loading-state", "shipped")

        exit_code, payload = run("registry-upsert", f"{TODO}#^mealboard-loading-state")

        assert exit_code == 1
        assert payload["error"] == "Task ID is already reserved"

    def test_registry_get_normalizes_repo_relative_and_absolute_keys(self, repo):
        two_task_note(repo)
        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--set", "workflow_status=planning")
        key = f"{TODO}#^mealboard-loading-state"

        for given in (key, f"{repo.vault_name}/{key}", f"{repo.vault / key}"):
            exit_code, payload = run("registry-get", given)
            assert exit_code == 0, given
            assert payload["key"] == key
            assert payload["entry"]["workflow_status"] == "planning"
            assert payload["reserved"]["state"] == "planning"

    def test_registry_get_missing_is_exit_2(self, repo):
        exit_code, payload = run("registry-get", "quickfix:nope")

        assert exit_code == 2
        assert payload["error"] == "Registry entry not found"


class TestPlanMetadata:
    def test_plan_frontmatter_round_trips_real_values(self, repo):
        plan = repo.plan(".agents/plans/features/feat/feat-plan-20260901-120000.md")
        source_tasks = [{"task_id": "mealboard-loading-state", "note_ref": f"{TODO}#^mealboard-loading-state"}]

        exit_code, payload = run(
            "plan-metadata-set", ".agents/plans/features/feat/feat-plan-20260901-120000.md",
            "--set", "obsidian_workflow=true", "--set", "task_count=2", "--set", f"source_tasks={json.dumps(source_tasks)}",
            "--set", "plan_kind=feature", "--set", f"source_note_path={repo.vault_name}/{TODO}",
            "--set", f"source_note_ref={repo.vault_name}/{TODO}#batch",
            "--append", "review_status=ceo-reviewed", "--append", "review_status=ceo-reviewed",
        )
        _, fetched = run("plan-metadata-get", str(plan))

        text = plan.read_text()
        assert exit_code == 0
        assert payload["metadata"]["obsidian_workflow"] is True
        assert fetched["metadata"]["obsidian_workflow"] is True
        assert fetched["metadata"]["task_count"] == 2
        assert fetched["metadata"]["source_tasks"] == source_tasks
        assert fetched["metadata"]["review_status"] == ["ceo-reviewed"]
        assert fetched["metadata"]["source_note_path"] == TODO
        assert fetched["metadata"]["source_note_ref"] == f"{TODO}#batch"
        assert _lib.truthy(fetched["metadata"]["obsidian_workflow"])
        assert "obsidian_workflow: true\n" in text
        assert text.index("plan_kind:") < text.index("obsidian_workflow:") < text.index("updated_at:")
        assert text.endswith("# Plan\n\nBody\n")

    def test_plan_metadata_set_appends_to_a_second_run(self, repo):
        repo.plan(".agents/plans/features/feat/feat-plan-20260901-120000.md")
        run("plan-metadata-set", ".agents/plans/features/feat/feat-plan-20260901-120000.md", "--append", "review_status=ceo-reviewed")

        _, payload = run("plan-metadata-set", ".agents/plans/features/feat/feat-plan-20260901-120000.md", "--append", "review_status=eng-reviewed")

        assert payload["metadata"]["review_status"] == ["ceo-reviewed", "eng-reviewed"]

    def test_plan_metadata_get_on_summary_names_the_plan_file(self, repo):
        repo.plan(".agents/plans/features/feat/feat-plan-20260901-120000.md")
        repo.plan(".agents/plans/features/feat/feat-plan-20260901-120000-summary.md", "# Summary\n")

        exit_code, payload = run("plan-metadata-get", ".agents/plans/features/feat/feat-plan-20260901-120000-summary.md")

        assert exit_code == 2
        assert payload["status"] == "error"
        assert payload["plan_path"] == ".agents/plans/features/feat/feat-plan-20260901-120000.md"
        assert payload["plan_exists"] is True

    def test_plan_metadata_get_missing_plan_is_exit_2(self, repo):
        exit_code, payload = run("plan-metadata-get", ".agents/plans/features/feat/nope.md")

        assert exit_code == 2
        assert "plan not found" in payload["error"]


class TestResolvePlan:
    PLAN = ".agents/plans/features/feat-x/feat-x-plan-20260901-120000.md"

    def test_explicit_path_wins_and_summary_is_rejected(self, repo):
        repo.plan(self.PLAN)
        repo.plan(self.PLAN.replace(".md", "-summary.md"), "# Summary\n")
        run("registry-upsert", "--branch", "feat-x", "--set", "plan_path=other.md")

        ok_code, ok = run("resolve-plan", "--plan-path", self.PLAN, "--branch", "feat-x")
        bad_code, bad = run("resolve-plan", "--plan-path", self.PLAN.replace(".md", "-summary.md"))

        assert ok_code == 0 and ok["source"] == "explicit_path" and ok["plan_path"] == self.PLAN
        assert bad_code == 2 and bad["plan_path"] == self.PLAN

    def test_note_ref_registry_entry_beats_note_path_and_branch(self, repo):
        two_task_note(repo)
        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--set", "plan_path=single.md")
        run("registry-upsert", TODO, "--batch", "--set", "plan_path=batch.md")
        run("registry-upsert", "--branch", "feat-x", "--set", "plan_path=branch.md")

        _, by_ref = run("resolve-plan", "--note-ref", f"{repo.vault_name}/{TODO}#^mealboard-loading-state", "--note-path", TODO, "--branch", "feat-x")
        _, by_path = run("resolve-plan", "--note-path", f"{repo.vault_name}/{TODO}", "--branch", "feat-x")
        _, by_bare_ref = run("resolve-plan", "--note-ref", TODO, "--branch", "feat-x")
        _, by_branch = run("resolve-plan", "--branch", "feat-x")

        assert (by_ref["source"], by_ref["key"], by_ref["plan_path"]) == ("registry", f"{TODO}#^mealboard-loading-state", "single.md")
        assert (by_path["key"], by_path["plan_path"]) == (f"{TODO}#batch", "batch.md")
        assert by_bare_ref["plan_path"] == "batch.md"
        assert (by_branch["key"], by_branch["plan_path"]) == ("plan:feat-x", "branch.md")

    def test_branch_fallback_picks_newest_filename_timestamp_not_mtime(self, repo):
        newest = repo.plan(self.PLAN)
        older = repo.plan(".agents/plans/features/feat-x/feat-x-plan-20260101-120000.md")
        repo.plan(".agents/plans/features/feat-x/feat-x-plan-20261231-235959-summary.md", "# Summary\n")
        os.utime(older, (2_000_000_000, 2_000_000_000))
        os.utime(newest, (1_000_000_000, 1_000_000_000))

        exit_code, payload = run("resolve-plan", "--branch", "feat-x")

        assert exit_code == 0
        assert payload["source"] == "branch_fallback"
        assert payload["plan_path"] == self.PLAN

    def test_only_a_summary_on_branch_is_unresolved(self, repo):
        repo.plan(self.PLAN.replace(".md", "-summary.md"), "# Summary\n")

        exit_code, payload = run("resolve-plan", "--branch", "feat-x")

        assert exit_code == 2
        assert payload["error"] == "Could not resolve a plan path"
        assert payload["tried_keys"] == ["plan:feat-x"]


# ---------------------------------------------------------------------------
# Lifecycle: abandon, quickfixes, epics, parent links
# ---------------------------------------------------------------------------

EPIC_PLAN = ".agents/plans/epics/storage/storage-epic-20260901-120000.md"
MILESTONES = [
    {"id": "M1", "title": "Local storage", "size": "plan"},
    {"id": "M2", "title": "R2 storage", "size": "quickfix", "plan_path": "./.agents/plans/features/m2/m2-plan-20260901-120000.md"},
    {"id": "M3", "title": "Cleanup", "size": "plan"},
]


def register_epic(repo: Repo) -> dict:
    repo.plan(EPIC_PLAN)
    exit_code, payload = run("epic-register", "--slug", "storage", "--path", EPIC_PLAN, "--milestones-json", json.dumps(MILESTONES))
    assert exit_code == 0
    return payload["entry"]


class TestAbandon:
    PLAN = ".agents/plans/features/feat/feat-plan-20260901-120000.md"

    def test_abandon_by_key_updates_plan_registry_note_and_reservation(self, repo):
        repo.note(TODO, f"## Board\n- [x] {LOADING_TEXT}\n  ^mealboard-loading-state\n  status:: implementing\n  notes:: keep\n")
        repo.plan(self.PLAN)
        key = f"{TODO}#^mealboard-loading-state"
        run("registry-upsert", key, "--set", f"plan_path={self.PLAN}", "--set", "workflow_status=implementing")

        exit_code, payload = run("abandon", f"{repo.vault_name}/{key}", "--reason", "superseded by R2")

        entry = repo.entry(key)
        metadata = _lib.read_frontmatter(repo.root / self.PLAN)
        assert exit_code == 0
        assert payload["key"] == key and payload["plan_path"] == self.PLAN
        assert (entry["workflow_status"], entry["implementation_status"], entry["reason"]) == ("abandoned", "abandoned", "superseded by R2")
        assert (metadata["workflow_status"], metadata["implementation_status"], metadata["reason"]) == ("abandoned", "abandoned", "superseded by R2")
        assert repo.read(TODO) == f"## Board\n- [ ] {LOADING_TEXT}\n  ^mealboard-loading-state\n  notes:: keep\n"
        assert payload["tasks"][0]["checked"] is False
        assert repo.reservation("mealboard-loading-state")["state"] == "abandoned"

    def test_abandon_by_plan_path_finds_entry_or_creates_a_branch_entry(self, repo):
        repo.plan(self.PLAN)
        run("registry-upsert", "--branch", "feat", "--set", f"plan_path={self.PLAN}")
        orphan = repo.plan(".agents/plans/features/orphan/orphan-plan-20260901-120000.md")

        exit_code, payload = run("abandon", self.PLAN, "--reason", "nope")
        orphan_code, orphan_payload = run("abandon", str(orphan), "--reason", "nope")

        assert exit_code == 0 and payload["key"] == "plan:feat" and payload["entry"]["workflow_status"] == "abandoned"
        assert payload["tasks"] == []
        assert orphan_code == 0 and orphan_payload["key"] == "plan:main"
        orphan_entry = repo.entry("plan:main")
        assert (orphan_entry["kind"], orphan_entry["branch"], orphan_entry["workflow_status"], orphan_entry["reason"]) == ("plan", "main", "abandoned", "nope")
        assert orphan_entry["plan_path"] == ".agents/plans/features/orphan/orphan-plan-20260901-120000.md"
        assert _lib.read_frontmatter(orphan)["workflow_status"] == "abandoned"

    def test_abandon_plan_only_when_no_key_can_be_derived(self, repo):
        R.git(repo.root, "checkout", "-q", "--detach")
        loose = repo.plan(".agents/plans/features/loose/loose-plan-20260901-120000.md")

        exit_code, payload = run("abandon", str(loose), "--reason", "nope")

        assert exit_code == 0 and payload["key"] is None and "entry" not in payload
        assert _lib.read_frontmatter(loose)["implementation_status"] == "abandoned"
        assert repo.entry("plan:main") is None

    def test_abandon_batch_unchecks_every_source_task(self, repo):
        two_task_note(repo)
        run("ensure-task-id", TODO, "--all-unchecked")
        source_tasks = [{"task_id": "mealboard-loading-state"}, {"task_id": "mealboard-date-bar"}]
        run("registry-upsert", TODO, "--batch", "--source-tasks-json", json.dumps(source_tasks))
        run("note-update", TODO, "--all-unchecked", "--check")
        assert repo.read(TODO).count("- [x]") == 2

        exit_code, payload = run("abandon", f"{TODO}#batch", "--reason", "scope cut")

        assert exit_code == 0
        assert len(payload["tasks"]) == 2
        assert repo.read(TODO).count("- [ ]") == 2
        assert repo.reservation("mealboard-date-bar")["state"] == "abandoned"

    def test_abandon_unknown_target_is_exit_2(self, repo):
        exit_code, payload = run("abandon", "quickfix:nope", "--reason", "x")

        assert exit_code == 2


class TestQuickfix:
    def test_register_with_note_ref_mints_id_and_links_it(self, repo):
        repo.note(TODO, f"## Meal Planner Board\n- [ ] {LOADING_TEXT}\n  notes:: keep\n")

        exit_code, payload = run("quickfix-register", "--slug", "loading-flash", "--title", "Fix loading flash", "--note-ref", f"{repo.vault_name}/{TODO}", "--branch", "qf/loading")

        entry = repo.entry("quickfix:loading-flash")
        assert exit_code == 0
        assert payload["key"] == "quickfix:loading-flash"
        assert payload["task"]["created"] is True
        assert (entry["kind"], entry["plan_mode"], entry["workflow_status"]) == ("quickfix", "quickfix", "implementing")
        assert entry["title"] == "Fix loading flash"
        assert entry["branch"] == "qf/loading"
        assert (entry["note_path"], entry["task_id"]) == (TODO, "mealboard-loading-state")
        assert "^mealboard-loading-state" in repo.read(TODO)
        assert repo.reservation("mealboard-loading-state")["state"] == "implementing"

    def test_register_without_note_and_re_register_keeps_entry(self, repo):
        run("quickfix-register", "--slug", "typo", "--title", "Fix typo")
        first = repo.entry("quickfix:typo")

        exit_code, payload = run("quickfix-register", "--slug", "typo", "--title", "Fix the typo")

        assert exit_code == 0
        assert payload["task"] is None
        assert payload["entry"]["created_at"] == first["created_at"]
        assert payload["entry"]["title"] == "Fix the typo"
        assert payload["entry"]["note_path"] is None

    def test_register_parent_epic_requires_milestone_and_known_epic(self, repo):
        half_code, half = run("quickfix-register", "--slug", "x", "--title", "X", "--parent-epic", "storage")
        unknown_code, unknown = run("quickfix-register", "--slug", "x", "--title", "X", "--parent-epic", "storage", "--milestone", "M2")

        assert half_code == 1 and "together" in half["error"]
        assert unknown_code == 2 and unknown["error"] == "Registry entry not found"
        assert repo.entry("quickfix:x") is None

    def test_complete_checks_note_and_records_commit_and_pr(self, repo):
        repo.note(TODO, f"## Board\n- [ ] {LOADING_TEXT}\n  ^mealboard-loading-state\n  notes:: keep\n\n## Other\n- [ ] Stay.\n")
        run("quickfix-register", "--slug", "loading-flash", "--title", "Fix", "--note-ref", f"{TODO}#^mealboard-loading-state")

        exit_code, payload = run("quickfix-complete", "--slug", "loading-flash", "--commit", "abc1234", "--pr", "https://example.test/pr/1")

        entry = repo.entry("quickfix:loading-flash")
        contents = repo.read(TODO)
        assert exit_code == 0
        assert (entry["workflow_status"], entry["implementation_status"]) == ("shipped", "shipped")
        assert entry["completed"] == _lib.today()
        assert (entry["commit"], entry["pr"]) == ("abc1234", "https://example.test/pr/1")
        assert payload["tasks"][0]["checked"] is True and payload["tasks"][0]["heading"] == "Completed"
        assert f"## Completed\n- [x] {LOADING_TEXT}" in contents
        assert "- [ ] Stay." in contents
        assert repo.reservation("mealboard-loading-state")["state"] == "shipped"

    def test_complete_without_note_link_and_unknown_slug(self, repo):
        run("quickfix-register", "--slug", "typo", "--title", "Fix typo")

        ok_code, ok = run("quickfix-complete", "--slug", "typo")
        missing_code, _ = run("quickfix-complete", "--slug", "nope")

        assert ok_code == 0 and ok["tasks"] == [] and ok["entry"]["implementation_status"] == "shipped"
        assert missing_code == 2

    def test_escalate_marks_entry_and_prints_note_ref(self, repo):
        repo.note(TODO, f"## Meal Planner Board\n- [ ] {LOADING_TEXT}\n")
        run("quickfix-register", "--slug", "loading-flash", "--title", "Fix", "--note-ref", TODO)

        exit_code, payload = run("escalate", "--slug", "loading-flash")

        assert exit_code == 0
        assert payload["note_ref"] == f"{TODO}#^mealboard-loading-state"
        assert payload["entry"]["workflow_status"] == "escalated"
        assert payload["entry"]["implementation_status"] == "escalated"  # else workflow-state lists it as stuck
        assert repo.reservation("mealboard-loading-state")["state"] == "escalated"
        assert run("escalate", "--slug", "nope")[0] == 2


class TestEpic:
    def test_register_normalizes_milestones_and_paths(self, repo):
        entry = register_epic(repo)

        assert (entry["kind"], entry["plan_mode"], entry["plan_path"]) == ("epic", "epic", EPIC_PLAN)
        assert entry["workflow_status"] == "planning"
        assert [m["status"] for m in entry["milestones"]] == ["not-started"] * 3
        assert entry["milestones"][1]["plan_path"] == ".agents/plans/features/m2/m2-plan-20260901-120000.md"
        assert repo.entry("epic:storage")["milestones"] == entry["milestones"]
        metadata = _lib.read_frontmatter(repo.root / EPIC_PLAN)
        assert (metadata["plan_kind"], metadata["registry_key"]) == ("epic", "epic:storage")
        assert (entry["plan_kind"], entry["title"]) == ("epic", "storage")

    def test_register_takes_title_from_frontmatter_and_requires_the_file(self, repo):
        repo.plan(EPIC_PLAN, _lib.render_frontmatter({"title": "Storage epic"}) + "# Epic\n")

        ok_code, ok = run("epic-register", "--slug", "storage", "--path", EPIC_PLAN, "--milestones-json", json.dumps(MILESTONES))
        missing_code, _ = run("epic-register", "--slug", "nope", "--path", ".agents/plans/epics/nope/nope-epic-20260901-120000.md", "--milestones-json", json.dumps(MILESTONES))

        assert ok_code == 0 and ok["entry"]["title"] == "Storage epic" and ok["metadata"]["title"] == "Storage epic"
        assert ok["plan_path"] == EPIC_PLAN
        assert missing_code == 2 and repo.entry("epic:nope") is None

    @pytest.mark.parametrize(
        "milestones",
        ['{"id": "M1"}', '[{"id": "M1", "title": "x", "size": "huge"}]', '[{"title": "x", "size": "plan"}]',
         '[{"id": "M1", "title": "x", "size": "plan"}, {"id": "M1", "title": "y", "size": "plan"}]', "nope"],
    )
    def test_register_rejects_bad_milestones(self, repo, milestones):
        repo.plan(EPIC_PLAN)

        exit_code, payload = run("epic-register", "--slug", "storage", "--path", EPIC_PLAN, "--milestones-json", milestones)

        assert exit_code == 1 and payload["status"] == "error"
        assert repo.entry("epic:storage") is None

    def test_re_register_preserves_subsumed_markers(self, repo):
        register_epic(repo)
        run("milestone-set", "--slug", "storage", "--milestone", "M3", "--set", "status=subsumed", "--set", "reason=folded into M2")

        _, payload = run("epic-register", "--slug", "storage", "--path", EPIC_PLAN, "--milestones-json", json.dumps(MILESTONES))

        assert payload["entry"]["milestones"][2]["status"] == "subsumed"
        assert payload["entry"]["milestones"][2]["reason"] == "folded into M2"
        assert payload["entry"]["workflow_status"] == "planning"

    def test_get_derives_status_from_children_and_computes_progress(self, repo):
        register_epic(repo)
        two_task_note(repo)
        plan = repo.plan(".agents/plans/features/m1/m1-plan-20260901-120000.md")
        run("registry-upsert", f"{TODO}#^mealboard-loading-state", "--set", f"plan_path={plan}", "--set", "implementation_status=shipped", "--set", "completed=2026-09-01", "--set", "pr=https://example.test/pr/9", "--branch", "m1")
        run("link-parent", f"{TODO}#^mealboard-loading-state", "--parent-epic", "storage", "--milestone", "M1")
        run("quickfix-register", "--slug", "m2-fix", "--title", "M2", "--parent-epic", "storage", "--milestone", "M2", "--branch", "qf/m2")
        run("milestone-set", "--slug", "storage", "--milestone", "M3", "--set", "status=subsumed", "--set", "reason=folded")

        exit_code, payload = run("epic-get", "--slug", "storage")

        m1, m2, m3 = payload["entry"]["milestones"]
        assert exit_code == 0
        assert (m1["status"], m1["entry_key"], m1["branch"], m1["completed"], m1["pr"]) == ("shipped", f"{TODO}#^mealboard-loading-state", "m1", "2026-09-01", "https://example.test/pr/9")
        assert m1["plan_path"] == ".agents/plans/features/m1/m1-plan-20260901-120000.md"
        assert (m2["status"], m2["entry_key"], m2["branch"]) == ("implementing", "quickfix:m2-fix", "qf/m2")
        assert (m3["status"], m3["reason"]) == ("subsumed", "folded")
        progress = payload["progress"]  # _lib.epic_progress verbatim
        assert (progress["shipped"], progress["subsumed"], progress["in_progress"], progress["total"], progress["done"]) == (1, 1, 1, 3, False)
        assert progress["next"]["id"] == "M2" and progress["epic_file"] == EPIC_PLAN
        assert [m["key"] for m in progress["milestones"]] == [f"{TODO}#^mealboard-loading-state", "quickfix:m2-fix", None]
        assert progress["milestones"][0]["plan"] == ".agents/plans/features/m1/m1-plan-20260901-120000.md"
        assert payload["next_milestone"]["id"] == "M2"
        assert repo.entry("epic:storage")["milestones"][0]["status"] == "not-started"

    def test_get_with_nothing_linked_and_unknown_epic(self, repo):
        register_epic(repo)

        _, payload = run("epic-get", "--slug", "storage")
        missing_code, _ = run("epic-get", "--slug", "nope")

        assert [m["status"] for m in payload["entry"]["milestones"]] == ["not-started"] * 3
        assert (payload["progress"]["shipped"], payload["progress"]["subsumed"], payload["progress"]["total"], payload["progress"]["not_started"]) == (0, 0, 3, 3)
        assert payload["next_milestone"]["id"] == "M1"
        assert missing_code == 2

    def test_get_reports_no_next_milestone_when_all_done(self, repo):
        register_epic(repo)
        for milestone in ("M1", "M2", "M3"):
            run("milestone-set", "--slug", "storage", "--milestone", milestone, "--set", "status=subsumed")

        _, payload = run("epic-get", "--slug", "storage")

        assert payload["next_milestone"] is None
        assert payload["progress"]["subsumed"] == 3 and payload["progress"]["done"] is True

    def test_milestone_set_validates_size_id_and_existence(self, repo):
        register_epic(repo)

        size_code, _ = run("milestone-set", "--slug", "storage", "--milestone", "M1", "--set", "size=quickfix")
        bad_size_code, _ = run("milestone-set", "--slug", "storage", "--milestone", "M1", "--set", "size=huge")
        id_code, _ = run("milestone-set", "--slug", "storage", "--milestone", "M1", "--set", "id=M9")
        missing_code, _ = run("milestone-set", "--slug", "storage", "--milestone", "M9", "--set", "status=subsumed")

        assert (size_code, bad_size_code, id_code, missing_code) == (0, 1, 1, 2)
        assert repo.entry("epic:storage")["milestones"][0]["size"] == "quickfix"

    def test_link_parent_by_plan_path_updates_frontmatter_and_entry(self, repo):
        register_epic(repo)
        plan = repo.plan(".agents/plans/features/m1/m1-plan-20260901-120000.md")
        run("registry-upsert", "--branch", "m1", "--set", f"plan_path={plan}")

        exit_code, payload = run("link-parent", str(plan), "--parent-epic", "storage", "--milestone", "M1")
        bad_code, _ = run("link-parent", str(plan), "--parent-epic", "storage", "--milestone", "M9")

        metadata = _lib.read_frontmatter(plan)
        assert exit_code == 0 and bad_code == 2
        assert payload["key"] == "plan:m1"
        assert (metadata["parent_epic"], metadata["milestone"]) == ("storage", "M1")
        assert (repo.entry("plan:m1")["parent_epic"], repo.entry("plan:m1")["milestone"]) == ("storage", "M1")
        assert run("epic-get", "--slug", "storage")[1]["entry"]["milestones"][0]["entry_key"] == "plan:m1"

    def test_link_parent_creates_a_plan_entry_when_the_plan_has_none(self, repo):
        register_epic(repo)
        rel = ".agents/plans/features/feat-m1/feat-m1-plan-20260901-120000.md"
        plan = repo.plan(rel, _lib.render_frontmatter({"branch": "feat/m1"}) + "# Plan\n")

        exit_code, payload = run("link-parent", rel, "--parent-epic", "storage", "--milestone", "M1")

        entry = repo.entry("plan:feat-m1")
        assert exit_code == 0 and payload["key"] == "plan:feat-m1"
        assert (entry["kind"], entry["plan_mode"], entry["branch"], entry["parent_epic"], entry["milestone"]) == ("plan", "feature", "feat/m1", "storage", "M1")
        assert entry["plan_path"] == rel
        assert (_lib.read_frontmatter(plan)["parent_epic"], _lib.read_frontmatter(plan)["milestone"]) == ("storage", "M1")
        assert run("epic-get", "--slug", "storage")[1]["progress"]["milestones"][0]["key"] == "plan:feat-m1"


# ---------------------------------------------------------------------------
# Vault outside the repo
# ---------------------------------------------------------------------------


class TestVaultOutsideRepo:
    def test_scans_configured_absolute_vault(self, tmp_path, vault_name, monkeypatch):
        outside = tmp_path / "elsewhere" / vault_name
        (outside / "Mealboard").mkdir(parents=True)
        root = R.make_repo(tmp_path, vault_path=str(outside))
        (outside / TODO).write_text("- [ ] One.\n  ^dup\n- [ ] Two.\n  ^dup\n")
        other = outside / "Mealboard" / "Other.md"
        other.write_text("- [ ] Solo task here.\n")
        monkeypatch.chdir(root)

        ids_code, ids = run("list-task-ids")
        vault_code, vault = run("validate-vault")
        ensure_code, ensured = run("ensure-task-id", str(other))

        assert ids_code == 0 and ids["vault"] == str(outside)
        assert [r["note_ref"] for r in ids["task_ids"]] == [f"{TODO}#^dup", f"{TODO}#^dup"]
        assert vault_code == 1 and vault["note_path"] == TODO
        assert ensure_code == 0 and ensured["created"] is True
        assert ensured["note_ref"] == "Mealboard/Other.md#^mealboard-solo-task"
        assert "^mealboard-solo-task" in other.read_text()
        assert not (root / vault_name / TODO).exists()

    def test_missing_vault_is_exit_2(self, tmp_path, vault_name, monkeypatch):
        root = R.make_repo(tmp_path, vault_path=str(tmp_path / "does-not-exist"))
        monkeypatch.chdir(root)

        exit_code, payload = run("validate-vault")

        assert exit_code == 2
        assert "vault not found" in payload["error"]


# ---------------------------------------------------------------------------
# The executable, end to end
# ---------------------------------------------------------------------------


class TestCommandLine:
    def test_executable_prints_envelopes_with_exit_codes(self, repo):
        two_task_note(repo)

        ok = R.run(repo.root, "obsidian-workflow", "validate-vault")
        missing = R.run(repo.root, "obsidian-workflow", "registry-get", "quickfix:nope")
        invalid = R.run(repo.root, "obsidian-workflow", "note-update", f"{TODO}#^mealboard-loading-state", "--check", "--uncheck")

        assert MODULE_PATH.read_text().startswith("#!/usr/bin/env python3\n")
        assert os.access(MODULE_PATH, os.X_OK)
        assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "ok"
        assert missing.returncode == 2 and json.loads(missing.stdout)["error"] == "Registry entry not found"
        assert invalid.returncode == 1 and json.loads(invalid.stdout)["status"] == "error"
        assert ok.stderr == missing.stderr == invalid.stderr == ""
