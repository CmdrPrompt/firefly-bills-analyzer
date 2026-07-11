"""Tests for the TASK-038 fixes to the subagent zero-tool-call hard gate.

Covers the corroborating-evidence heuristic, the `allow-tool-free` opt-out,
and session-scoped marker handling across:
  - .claude/hooks/subagent_toolcheck.py (SubagentStop hook)
  - .claude/hooks/agent_result_gate.py (PostToolUse hook, matcher Agent|Task)

Follows the same load-by-path/`_run_main` harness conventions as
tests/test_hooks.py, since these hooks live under `.claude/hooks/`, which is
not a Python package.
"""

from __future__ import annotations

import importlib.util
import io
import json
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
    return _load_module(TOOLCHECK_PATH, "subagent_toolcheck_gate")


@pytest.fixture()
def gate() -> ModuleType:
    return _load_module(GATE_PATH, "agent_result_gate_gate")


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


def _marker_dir(project_dir: Path) -> Path:
    return project_dir / ".claude" / "state" / "agent-failures"


class TestCorroboratingEvidenceHeuristic:
    def test_tool_free_with_long_report_writes_no_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A long free-text final report with zero tool calls and no narration or
        coordinator-followup signature must NOT trigger a marker (TASK-038 bug)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        report_text = (
            "# Farley Index Report\n\n"
            "## Summary\nFarley Index: 8.6 / 10 (Good)\n"
            "Files analysed: 4\nTest methods analysed: 32\n\n"
            "## Per-Property Scores\nAll properties scored well, no significant "
            "issues found across the suite. The tests are understandable, "
            "maintainable, and fast.\n\n"
            "## Worst Offenders\nNone of significance.\n\n"
            "## Prioritised Recommendations\nNo changes recommended at this time."
        )
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [_assistant_event([{"type": "text", "text": report_text}])],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-report",
                "agent_type": "test-design-reviewer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        assert exit_code == 0
        marker_dir = _marker_dir(project_dir)
        assert not marker_dir.exists() or not any(marker_dir.iterdir()), (
            "a tool-free long free-text report must not write a marker"
        )

    def test_narration_pattern_writes_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bare tool-name token followed by a JSON object of arguments is the
        TASK-025/TASK-034 narrated-tool-call signature and must trigger a marker."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [
                _assistant_event(
                    [{"type": "text", "text": 'Grep {"pattern": "TODO", "path": "src/"}'}]
                )
            ],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-narrator",
                "agent_type": "test-writer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        assert exit_code == 0
        marker = _marker_dir(project_dir) / "agent-narrator.json"
        assert marker.is_file(), "narration-pattern text must write a marker"

    def test_coordinator_followup_writes_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A coordinator follow-up event (isMeta: true, origin.kind == "coordinator")
        indicates the coordinator already observed a stalled turn and must trigger
        a marker even without a narration-pattern text match."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [
                _assistant_event([{"type": "text", "text": "I have completed the review."}]),
                json.dumps(
                    {
                        "isMeta": True,
                        "origin": {"kind": "coordinator"},
                        "message": {"role": "user", "content": "please continue"},
                    }
                ),
            ],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-followup",
                "agent_type": "pr-reviewer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        assert exit_code == 0
        marker = _marker_dir(project_dir) / "agent-followup.json"
        assert marker.is_file(), "a coordinator follow-up event must write a marker"

    def test_opt_out_flag_writes_no_marker(
        self, tmp_path: Path, toolcheck: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An agent definition declaring allow-tool-free: true is skipped entirely,
        even when the transcript otherwise carries corroborating evidence."""
        project_dir = tmp_path / "project"
        agents_dir = project_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test-design-reviewer.agent.md").write_text(
            "---\n"
            "name: Test Design Reviewer\n"
            "description: desc\n"
            "tools: [Read]\n"
            "allow-tool-free: true\n"
            "---\nBody\n",
            encoding="utf-8",
        )
        transcript = _write_transcript(
            tmp_path / "transcript.jsonl",
            [_assistant_event([{"type": "text", "text": 'Read {"file_path": "foo.py"}'}])],
        )
        payload = json.dumps(
            {
                "agent_transcript_path": str(transcript),
                "agent_id": "agent-optout",
                "agent_type": "Test Design Reviewer",
            }
        )

        exit_code = _run_main(toolcheck, payload, monkeypatch, project_dir)

        assert exit_code == 0
        marker_dir = _marker_dir(project_dir)
        assert not marker_dir.exists() or not any(marker_dir.iterdir()), (
            "allow-tool-free agents must be skipped regardless of evidence"
        )


def _write_marker_with_session(
    project_dir: Path,
    agent_id: str,
    agent_type: str,
    session_id: str | None,
    detected_at: str,
) -> Path:
    marker_dir = _marker_dir(project_dir)
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{agent_id}.json"
    data: dict[str, object] = {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "detected_at": detected_at,
    }
    if session_id is not None:
        data["session_id"] = session_id
    marker.write_text(json.dumps(data), encoding="utf-8")
    return marker


class TestSessionScopedMarkers:
    def test_cross_session_marker_is_ignored_for_triggering(
        self, tmp_path: Path, gate: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A marker from a different session must not trigger this session's gate,
        and must be left in place (not consumed) for its own session to pick up."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Fresh marker (recent timestamp), but belongs to a different session.
        fresh_timestamp = "2100-12-31T23:59:59Z"
        marker = _write_marker_with_session(
            project_dir, "agent-other", "test-writer", "session-A", fresh_timestamp
        )
        monkeypatch.setenv("CLAUDE_SESSION_ID", "session-B")

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        assert exit_code == 0
        assert marker.exists(), (
            "a cross-session marker must be left in place, not consumed, by a "
            "gate run from a different session"
        )

    def test_stale_marker_older_than_24h_is_pruned(
        self, tmp_path: Path, gate: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Markers older than 24 hours are deleted on every run, regardless of
        which session they belong to."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        very_old_timestamp = "2000-01-01T00:00:00Z"
        marker = _write_marker_with_session(
            project_dir, "agent-ancient", "test-writer", "session-A", very_old_timestamp
        )
        monkeypatch.setenv("CLAUDE_SESSION_ID", "session-B")

        exit_code = _run_main(gate, "{}", monkeypatch, project_dir)

        assert exit_code == 0
        assert not marker.exists(), "a marker older than 24h must be pruned regardless of session"
