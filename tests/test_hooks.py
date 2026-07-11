"""Characterization tests for the subagent hard-gate hooks.

Covers:
  - .claude/hooks/subagent_toolcheck.py (SubagentStop hook)
  - .claude/hooks/agent_result_gate.py (PostToolUse hook, matcher Agent|Task)

These hooks live under `.claude/hooks/`, which is not a Python package, and
they are designed to be invoked as standalone scripts reading JSON from
stdin. The hook modules are loaded by file path via importlib and their
`main()` is called directly with `sys.stdin` and `CLAUDE_PROJECT_DIR`
monkeypatched -- this mirrors how Claude Code actually invokes them
(subprocess with stdin/env) while keeping the tests fast and avoiding an
extra subprocess layer, matching the direct-import precedent used for the
CLI's `main()` in tests/test_cli.py.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLCHECK_PATH = REPO_ROOT / ".claude" / "hooks" / "subagent_toolcheck.py"
GATE_PATH = REPO_ROOT / ".claude" / "hooks" / "agent_result_gate.py"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def toolcheck() -> ModuleType:
    return _load_module(TOOLCHECK_PATH, "subagent_toolcheck")


@pytest.fixture()
def gate() -> ModuleType:
    return _load_module(GATE_PATH, "agent_result_gate")


def _assistant_event(content: list[dict[str, object]]) -> str:
    return json.dumps({"message": {"role": "assistant", "content": content}})


def _write_transcript(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_main(
    module: ModuleType,
    stdin_text: str,
    monkeypatch: pytest.MonkeyPatch,
    project_dir: Path,
) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    return module.main()


class TestCountToolUses:
    def test_counts_tool_use_blocks_and_assistant_turns(
        self, tmp_path: Path, toolcheck: ModuleType
    ) -> None:
        transcript = _write_transcript(
            tmp_path / "t.jsonl",
            [
                _assistant_event([{"type": "text", "text": "thinking"}]),
                _assistant_event([{"type": "tool_use", "name": "Read", "input": {}}]),
                json.dumps({"message": {"role": "user", "content": []}}),
            ],
        )

        tool_uses, assistant_turns = toolcheck.count_tool_uses(transcript)

        assert tool_uses == 1
        assert assistant_turns == 2

    def test_ignores_malformed_json_lines_and_blank_lines(
        self, tmp_path: Path, toolcheck: ModuleType
    ) -> None:
        transcript = _write_transcript(
            tmp_path / "t.jsonl",
            [
                "not json at all {{{",
                "",
                _assistant_event([{"type": "text", "text": "ok"}]),
            ],
        )

        tool_uses, assistant_turns = toolcheck.count_tool_uses(transcript)

        assert tool_uses == 0
        assert assistant_turns == 1


class TestSubagentToolcheckMain:
    def test_zero_tool_uses_with_assistant_turn_writes_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # TASK-038: bare narration text with no tool-narration signature no
        # longer triggers a marker (see TestCorroboratingEvidence below), so
        # this fixture uses a real tool-narration pattern -- a bare tool name
        # immediately followed by a JSON object of arguments -- matching the
        # TASK-025/TASK-034 "narrated tool calls" failure shape.
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [_assistant_event([{"type": "text", "text": 'Read {"file_path": "foo.py"}'}])],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-123",
                "agent_type": "test-writer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        marker = project_dir / ".claude" / "state" / "agent-failures" / "agent-123.json"
        assert exit_code == 0
        assert marker.is_file(), "expected a marker file to be written"
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert "validate-agents" in data.pop("diagnosis")
        data.pop("detected_at")
        data.pop("transcript")
        data.pop("session_id")
        assert data == {
            "agent_id": "agent-123",
            "agent_type": "test-writer",
            "tool_uses": 0,
            "assistant_turns": 1,
        }

    def test_transcript_with_a_tool_use_writes_no_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [_assistant_event([{"type": "tool_use", "name": "Read", "input": {}}])],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-456",
                "agent_type": "test-writer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        marker_dir = project_dir / ".claude" / "state" / "agent-failures"
        assert exit_code == 0
        assert not marker_dir.exists() or not any(marker_dir.iterdir())

    def test_transcript_with_zero_assistant_turns_writes_no_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [json.dumps({"message": {"role": "user", "content": []}})],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-789",
                "agent_type": "test-writer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        marker_dir = project_dir / ".claude" / "state" / "agent-failures"
        assert exit_code == 0
        assert not marker_dir.exists() or not any(marker_dir.iterdir())

    def test_malformed_stdin_json_does_not_crash(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exit_code = _run_main(toolcheck, "not { valid json", monkeypatch, tmp_path)

        assert exit_code == 0

    def test_missing_agent_transcript_path_key_does_not_crash(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = json.dumps({"agent_id": "agent-1", "agent_type": "foo"})

        exit_code = _run_main(toolcheck, payload, monkeypatch, tmp_path)

        assert exit_code == 0

    def test_nonexistent_transcript_path_does_not_crash(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = json.dumps(
            {
                "agent_transcript_path": str(tmp_path / "does_not_exist.jsonl"),
                "agent_id": "agent-1",
                "agent_type": "foo",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, tmp_path)

        assert exit_code == 0


def _write_marker(project_dir: Path, agent_id: str, agent_type: str) -> Path:
    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{agent_id}.json"
    marker.write_text(
        json.dumps({"agent_id": agent_id, "agent_type": agent_type}),
        encoding="utf-8",
    )
    return marker


def _stub_validator_subprocess(
    project_dir: Path, gate: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replace the real `validate_agents.py` subprocess spawn with a canned result.

    Keeps these tests fast and hermetic (no real process spawn) -- the gate's own
    subprocess call is an external-boundary concern already covered independently
    by manual verification and scripts/validate_agents.py's own test suite.
    """
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "validate_agents.py").touch()
    stub_output = "validate-agents: OK (1 agent definitions valid)\n"
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=a[0] if a else [], returncode=0, stdout=stub_output
        ),
    )


class TestAgentResultGateMain:
    def test_no_markers_exits_zero_silently(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.err == ""

    def test_markers_present_exits_two_with_gate_message(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)
        _write_marker(project_dir, "agent-999", "test-writer")

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "SUBAGENT HARD GATE TRIPPED" in captured.err
        assert "test-writer (agent-999)" in captured.err
        assert "validate-agents: OK" in captured.err
        # TASK-038: when validate-agents passes, the message must not claim
        # a frontmatter configuration error -- that framing belongs only to
        # the validator-failed path.
        assert "invalid 'tools:' frontmatter" not in captured.err
        assert "NOT a frontmatter configuration error" in captured.err

    def test_validator_missing_uses_fallback_message(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _write_marker(project_dir, "agent-999", "test-writer")

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "validator not found (scripts/validate_agents.py missing)" in captured.err
        # When the validator can't confirm agent config is valid, the
        # frontmatter configuration-error framing still applies.
        assert "invalid 'tools:' frontmatter" in captured.err

    def test_markers_present_are_consumed(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)
        marker = _write_marker(project_dir, "agent-999", "test-writer")

        _run_main(gate, "{}", monkeypatch, project_dir)

        assert not marker.exists(), "marker should be consumed (deleted) after reporting"

    def test_second_run_after_consumption_exits_zero(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)
        _write_marker(project_dir, "agent-999", "test-writer")

        first_exit = _run_main(gate, "{}", monkeypatch, project_dir)
        capsys.readouterr()  # discard first run's stderr
        second_exit = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert first_exit == 2
        assert second_exit == 0
        assert captured.err == ""

    def test_malformed_stdin_json_does_not_crash(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        exit_code = _run_main(gate, "not { valid json", monkeypatch, project_dir)

        assert exit_code == 0


def _write_marker_with_timestamp(
    project_dir: Path, agent_id: str, agent_type: str, detected_at: str
) -> Path:
    """Write a marker with an explicit detected_at timestamp."""
    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{agent_id}.json"
    marker.write_text(
        json.dumps(
            {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "detected_at": detected_at,
            }
        ),
        encoding="utf-8",
    )
    return marker


class TestAgentResultGateStaleness:
    def test_all_stale_markers_exits_zero_silently(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """All markers older than 60 minutes should not trigger the gate."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)

        # Write markers that are > 60 minutes old
        # Current time is used by gate's is_marker_stale(), so we use a very old timestamp
        old_timestamp = "2000-01-01T00:00:00Z"
        _write_marker_with_timestamp(project_dir, "agent-old-1", "test-writer", old_timestamp)
        _write_marker_with_timestamp(project_dir, "agent-old-2", "test-reviewer", old_timestamp)

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.err == ""

    def test_stale_markers_are_still_consumed(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Stale markers should be deleted even though they don't trigger the gate."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)

        old_timestamp = "2000-01-01T00:00:00Z"
        marker = _write_marker_with_timestamp(
            project_dir, "agent-old", "test-writer", old_timestamp
        )

        _run_main(gate, "{}", monkeypatch, project_dir)

        assert not marker.exists(), "stale marker should be consumed (deleted)"

    def test_mixed_stale_and_fresh_reports_only_fresh(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Mixed stale+fresh markers should report only fresh, exit 2, but delete all."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)

        # Very old marker (stale)
        old_timestamp = "2000-01-01T00:00:00Z"
        old_marker = _write_marker_with_timestamp(
            project_dir, "agent-old", "old-writer", old_timestamp
        )

        # Recent marker (fresh, < 60 minutes old)
        fresh_timestamp = "2100-12-31T23:59:59Z"  # Far in future to ensure freshness
        fresh_marker = _write_marker_with_timestamp(
            project_dir, "agent-fresh", "fresh-writer", fresh_timestamp
        )

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "SUBAGENT HARD GATE TRIPPED" in captured.err
        # Fresh agent should be in message
        assert "fresh-writer (agent-fresh)" in captured.err
        # Stale agent should NOT be in message
        assert "old-writer" not in captured.err
        # Both should be deleted
        assert not old_marker.exists(), "stale marker should be deleted"
        assert not fresh_marker.exists(), "fresh marker should be deleted"

    def test_missing_detected_at_treated_as_fresh(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Marker without detected_at should be treated as fresh and trigger gate."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)

        _write_marker(project_dir, "agent-no-timestamp", "test-writer")

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "SUBAGENT HARD GATE TRIPPED" in captured.err
        assert "test-writer (agent-no-timestamp)" in captured.err

    def test_invalid_detected_at_format_treated_as_fresh(
        self,
        tmp_path: Path,
        gate: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Marker with unparseable detected_at should be treated as fresh."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _stub_validator_subprocess(project_dir, gate, monkeypatch)

        _write_marker_with_timestamp(
            project_dir, "agent-bad-timestamp", "test-writer", "not-a-valid-timestamp"
        )

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "SUBAGENT HARD GATE TRIPPED" in captured.err
        assert "test-writer (agent-bad-timestamp)" in captured.err
