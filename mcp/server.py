"""MCP server exposing butler_core task and git/gh operations over stdio.

Each tool is a thin wrapper over a single butler_core function: action tools
(branch/stage/commit/pr/merge) perform exactly one git operation per call,
with no implicit batching of multiple git operations behind one tool call.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from butler_core import git_ops
from butler_core import tasks as core_tasks

app = FastMCP("butler")


def _task_to_dict(task: core_tasks.Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "description": task.description,
        "branch_name": task.branch_name,
        "acceptance_criteria": [
            {"text": criterion.text, "checked": criterion.checked}
            for criterion in task.acceptance_criteria
        ],
    }


@app.tool()
def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    """List tasks in docs/tasks, optionally filtered by status."""
    return [_task_to_dict(task) for task in core_tasks.list_tasks(status=status)]


@app.tool()
def get_task(task_id: str) -> dict[str, Any]:
    """Read a single task as structured data."""
    return _task_to_dict(core_tasks.read_task(task_id))


@app.tool()
def create_task(title: str, description: str) -> dict[str, Any]:
    """Create a new task file, allocating the next TASK-NNN number."""
    return _task_to_dict(core_tasks.create_task(title, description))


@app.tool()
def check_acceptance_criterion(task_id: str, index: int) -> dict[str, Any]:
    """Toggle the acceptance criterion at the given 0-based index to checked."""
    core_tasks.check_criterion(task_id, index)
    return _task_to_dict(core_tasks.read_task(task_id))


@app.tool()
def set_task_status(task_id: str, status: str) -> dict[str, Any]:
    """Set a task's Status field (todo / in-progress / done)."""
    core_tasks.set_status(task_id, status)
    return _task_to_dict(core_tasks.read_task(task_id))


@app.tool()
def branch_task(task_id: str) -> dict[str, str]:
    """Create or switch to the task's branch."""
    git_ops.branch_for(core_tasks.read_task(task_id))
    return {"task_id": task_id, "result": "branched"}


@app.tool()
def stage_task(task_id: str) -> dict[str, str]:
    """Fix, format, and stage files for the task."""
    git_ops.stage_for(core_tasks.read_task(task_id))
    return {"task_id": task_id, "result": "staged"}


@app.tool()
def commit_task(task_id: str) -> dict[str, str]:
    """Commit using the task's commit message."""
    git_ops.commit_for(core_tasks.read_task(task_id))
    return {"task_id": task_id, "result": "committed"}


@app.tool()
def open_pr_for_task(task_id: str) -> dict[str, str]:
    """Push the branch and open a PR for the task."""
    git_ops.open_pr_for(core_tasks.read_task(task_id))
    return {"task_id": task_id, "result": "pr_opened"}


@app.tool()
def merge_task_pr(task_id: str) -> dict[str, str]:
    """Squash-merge the task's open PR and pull main."""
    git_ops.merge_pr_for(core_tasks.read_task(task_id))
    return {"task_id": task_id, "result": "merged"}


if __name__ == "__main__":
    app.run(transport="stdio")
