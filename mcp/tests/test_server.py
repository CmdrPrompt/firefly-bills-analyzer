"""Tests for the MCP server's thin wrappers over butler_core."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import server

from butler_core.tasks import TaskNotFoundError

EXPECTED_TOOL_NAMES = {
    "list_tasks",
    "get_task",
    "create_task",
    "check_acceptance_criterion",
    "set_task_status",
    "branch_task",
    "stage_task",
    "commit_task",
    "open_pr_for_task",
    "merge_task_pr",
}


def _write_task(tasks_dir: Path, task_id: str, status: str = "todo") -> Path:
    path = tasks_dir / f"{task_id}-sample.md"
    path.write_text(
        f"# {task_id} Sample task\n\n"
        f"## Status\n\n{status}\n\n"
        "## Description\n\nDo the thing.\n\n"
        "## Branch\n\n"
        f"**Branch name:** `task/{task_id.split('-')[1]}-sample`\n"
        f"**Switch/create:** `git checkout -b task/{task_id.split('-')[1]}-sample`\n"
        "**Make target:** `make branch-task f=" + task_id + "`\n\n"
        "## Acceptance criteria\n\n"
        "- [ ] First criterion\n"
        "- [x] Second criterion\n\n"
        "## Completion\n\n"
        "**Date:** \n"
        "**Summary:** \n"
        "**Files changed:**\n\n"
        f"**Branch:** `git checkout task/{task_id.split('-')[1]}-sample`\n"
        f"**Stage:** `git add {path} CHANGELOG.md`\n"
        '**Commit:** `git commit -m "Sample commit"`\n'
    )
    return path


@pytest.fixture
def tasks_dir(tmp_path, monkeypatch):
    directory = tmp_path / "docs" / "tasks"
    directory.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return directory


def test_registers_exactly_the_ten_required_tools():
    tool_names = {tool.name for tool in asyncio.run(server.app.list_tools())}

    assert tool_names == EXPECTED_TOOL_NAMES


def test_list_tasks_returns_only_tasks_matching_status_filter(tasks_dir):
    _write_task(tasks_dir, "TASK-001", status="todo")
    _write_task(tasks_dir, "TASK-002", status="done")

    result = server.list_tasks(status="done")

    assert [task["id"] for task in result] == ["TASK-002"]


def test_get_task_returns_structured_data_for_existing_task(tasks_dir):
    _write_task(tasks_dir, "TASK-001")

    result = server.get_task("TASK-001")

    assert result["id"] == "TASK-001", "expected get_task to return the requested task's id"
    assert result["title"] == "Sample task", "expected get_task to return the task's title"
    assert result["acceptance_criteria"] == [
        {"text": "First criterion", "checked": False},
        {"text": "Second criterion", "checked": True},
    ], "expected acceptance criteria to round-trip with correct text and checked state"


def test_get_task_propagates_task_not_found_error(tasks_dir):
    with pytest.raises(TaskNotFoundError):
        server.get_task("TASK-999")


def test_create_task_writes_a_new_task_file(tasks_dir):
    result = server.create_task(title="New feature", description="Add the feature.")

    assert result["id"] == "TASK-001"
    assert (tasks_dir / "TASK-001-new-feature.md").exists()


def test_check_acceptance_criterion_toggles_the_target_checkbox(tasks_dir):
    _write_task(tasks_dir, "TASK-001")

    server.check_acceptance_criterion("TASK-001", index=0)

    updated = server.get_task("TASK-001")
    assert updated["acceptance_criteria"][0]["checked"] is True
    assert updated["acceptance_criteria"][1]["checked"] is True


def test_set_task_status_updates_the_status_field(tasks_dir):
    _write_task(tasks_dir, "TASK-001", status="todo")

    server.set_task_status("TASK-001", "in-progress")

    assert server.get_task("TASK-001")["status"] == "in-progress"


_GIT_OPS_FUNCTION_NAMES = ("branch_for", "stage_for", "commit_for", "open_pr_for", "merge_pr_for")

_ACTION_TOOL_CASES = [
    (server.branch_task, "branch_for"),
    (server.stage_task, "stage_for"),
    (server.commit_task, "commit_for"),
    (server.open_pr_for_task, "open_pr_for"),
    (server.merge_task_pr, "merge_pr_for"),
]


@pytest.mark.parametrize("tool, target_function_name", _ACTION_TOOL_CASES)
def test_action_tool_invokes_only_its_own_git_ops_function_once(
    tasks_dir, monkeypatch, tool, target_function_name
):
    _write_task(tasks_dir, "TASK-001")
    calls: dict[str, list[str]] = {name: [] for name in _GIT_OPS_FUNCTION_NAMES}
    for name in _GIT_OPS_FUNCTION_NAMES:
        monkeypatch.setattr(
            server.git_ops,
            name,
            lambda task, _name=name, **_kwargs: calls[_name].append(task.id),
        )

    tool("TASK-001")

    assert calls[target_function_name] == ["TASK-001"], (
        f"expected {target_function_name} to be called exactly once with TASK-001"
    )
    other_calls = {
        name: invocations
        for name, invocations in calls.items()
        if name != target_function_name and invocations
    }
    assert not other_calls, (
        f"{tool.__name__} unexpectedly triggered other git_ops functions: {other_calls}"
    )
