"""Tests for butler_core.git_ops."""

from __future__ import annotations

import shlex
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from butler_core.git_ops import (
    GitOpsError,
    branch_for,
    commit_for,
    merge_pr_for,
    open_pr_for,
    stage_for,
)
from butler_core.tasks import TaskNotFoundError, create_task, read_task


def _completed(returncode: int = 0, stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    return result


class TestBranchFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_creates_new_branch_when_it_does_not_exist(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed(returncode=1)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        calls = mock_run.call_args_list
        assert calls[0].args[0] == [
            "git",
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{task.branch_name}",
        ]
        assert calls[1].args[0] == ["git", "checkout", "-b", task.branch_name]

    @patch("butler_core.git_ops.subprocess.run")
    def test_switches_to_branch_when_it_already_exists(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed(returncode=0)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        calls = mock_run.call_args_list
        assert calls[1].args[0] == ["git", "checkout", task.branch_name]


class TestStageFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_runs_fix_format_pymarkdown_add_and_refresh(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "README.md").write_text("# hi\n")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "excluded.md").write_text("nope\n")
        task = create_task("Some task", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed()

        stage_for(task, repo_root=tmp_path)

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[0] == ["uv", "run", "ruff", "check", "--fix", "."]
        assert commands[1] == ["uv", "run", "ruff", "format", "."]
        assert commands[2][:4] == ["uv", "run", "pymarkdown", "--config"]
        assert "./README.md" in commands[2]
        assert not any("venv" in f for f in commands[2])
        assert commands[3] == shlex.split(task.stage_cmd)
        assert commands[4] == ["git", "update-index", "-q", "--refresh"]


class TestCommitFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_commits_with_task_message(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed()
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        commit_for(task)

        mock_run.assert_called_once_with(["git", "commit", "-m", task.commit_message], check=True)


class TestOpenPrFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_pushes_creates_pr_and_returns_to_main(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "Some description body", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed()

        open_pr_for(task, tasks_dir=str(tasks_dir))

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[0] == ["git", "push", "-u", "origin", "HEAD"]
        assert commands[1][:2] == ["gh", "pr"]
        assert commands[1][2] == "create"
        title_index = commands[1].index("--title") + 1
        assert commands[1][title_index] == f"{task.id} {task.title}"
        body_index = commands[1].index("--body") + 1
        assert "Some description body" in commands[1][body_index]
        assert commands[2] == ["git", "checkout", "main"]

    def test_raises_task_not_found_error_for_missing_task_file(self, tmp_path: Path) -> None:
        task = create_task("Temp task", "desc", tasks_dir=str(tmp_path))
        (tmp_path / f"{task.id}-temp-task.md").unlink()

        with pytest.raises(TaskNotFoundError, match=f"No task file found matching '{task.id}'"):
            open_pr_for(task, tasks_dir=str(tmp_path))


class TestMergePrFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_squash_merges_mergeable_pr_and_pulls_main(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.side_effect = [
            _completed(stdout="42\n"),
            _completed(stdout="MERGEABLE\n"),
            _completed(),
            _completed(),
            _completed(),
        ]

        merge_pr_for(task)

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[2] == ["gh", "pr", "merge", "42", "--squash", "--delete-branch"]
        assert commands[3] == ["git", "checkout", "main"]
        assert commands[4] == ["git", "pull"]

    @patch("butler_core.git_ops.subprocess.run")
    def test_raises_when_no_open_pr_found(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.return_value = _completed(stdout="\n")

        with pytest.raises(GitOpsError, match=f"No open PR for branch {task.branch_name}"):
            merge_pr_for(task)

    @patch("butler_core.git_ops.subprocess.run")
    def test_raises_when_pr_not_mergeable(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.side_effect = [
            _completed(stdout="42\n"),
            _completed(stdout="CONFLICTING\n"),
        ]

        with pytest.raises(GitOpsError, match=r"PR #42 not mergeable \(CONFLICTING\)"):
            merge_pr_for(task)
