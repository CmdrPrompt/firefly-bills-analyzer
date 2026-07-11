"""Regression tests for TASK-047 / check-agents-sync.

`check-agents-sync` diffs `claude-agents/*.agent.md` against
`.claude/agents/*.agent.md` and is wired into `make lint`. Adopting projects
that vendor python-butler's Makefile have no `claude-agents/` directory at
all, so the target must treat its absence as "nothing to check" rather than
emitting false-positive literal-glob errors and failing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MAKEFILE = _REPO_ROOT / "Makefile"


def _run_check_agents_sync(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-f", str(_MAKEFILE), "check-agents-sync"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class TestCheckAgentsSyncWithoutClaudeAgentsDir:
    """Scenario: adopting project has no claude-agents/ directory at all."""

    def test_exits_zero_with_no_output_when_claude_agents_dir_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / ".claude" / "agents" / "bug-triage.agent.md").write_text("content\n")

        result = _run_check_agents_sync(tmp_path)

        assert result.returncode == 0
        assert "check-agents-sync" not in result.stdout
        assert "check-agents-sync" not in result.stderr


class TestCheckAgentsSyncWithClaudeAgentsDir:
    """Scenario: python-butler's own repo still keeps claude-agents/ and
    .claude/agents/ in sync — existing drift-detection behavior must be
    unchanged."""

    def test_reports_file_missing_from_claude_agents_dir(self, tmp_path: Path) -> None:
        (tmp_path / "claude-agents").mkdir()
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / ".claude" / "agents" / "orphan.agent.md").write_text("content\n")

        result = _run_check_agents_sync(tmp_path)

        assert result.returncode != 0
        assert "'orphan.agent.md' exists in .claude/agents/ but not in claude-agents/" in (
            result.stdout + result.stderr
        )

    def test_reports_differing_content(self, tmp_path: Path) -> None:
        (tmp_path / "claude-agents").mkdir()
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / "claude-agents" / "same-name.agent.md").write_text("a\n")
        (tmp_path / ".claude" / "agents" / "same-name.agent.md").write_text("b\n")

        result = _run_check_agents_sync(tmp_path)

        assert result.returncode != 0
        assert "'same-name.agent.md' differs between claude-agents/ and .claude/agents/" in (
            result.stdout + result.stderr
        )

    def test_exits_zero_when_directories_are_identical(self, tmp_path: Path) -> None:
        (tmp_path / "claude-agents").mkdir()
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / "claude-agents" / "same.agent.md").write_text("same\n")
        (tmp_path / ".claude" / "agents" / "same.agent.md").write_text("same\n")

        result = _run_check_agents_sync(tmp_path)

        assert result.returncode == 0


class TestRealRepoStillPasses:
    """python-butler's own claude-agents/ and .claude/agents/ must actually
    stay in sync — this is the real check the target guards in this repo."""

    def test_check_agents_sync_passes_against_the_real_repo(self) -> None:
        result = _run_check_agents_sync(_REPO_ROOT)
        assert result.returncode == 0, result.stdout + result.stderr
