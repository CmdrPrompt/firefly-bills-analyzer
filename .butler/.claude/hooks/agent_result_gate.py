#!/usr/bin/env python3
"""PostToolUse hook (matcher: Agent|Task): hard gate for zero-tool-call
subagents.

Runs in the parent session right after a subagent returns. If the
SubagentStop hook (subagent_toolcheck.py) left a failure marker for this
session, this hook:

  1. Runs scripts/validate_agents.py to confirm/deny the config-error
     hypothesis.
  2. Exits 2 with a directive on stderr. Exit 2 on PostToolUse feeds
     stderr straight back to the coordinator model as a deterministic
     instruction: what to do next depends on whether validate-agents
     passed (see below).

Session scoping (TASK-038): `.claude/state/agent-failures/` is project-global
state, shared across all concurrent sessions. Markers carry a `session_id`
(written by subagent_toolcheck.py); this hook only treats markers matching
its own session id as candidates to trigger the gate. Markers from other
sessions are left in place -- untouched -- so that session can consume them
itself. Markers with no `session_id` (legacy / characterization-test shape)
are treated as belonging to the current session, for backward compatibility.

Regardless of session, any marker older than 24 hours is pruned (deleted) on
every run to prevent unbounded accumulation of orphaned markers.

Same-session markers are consumed (deleted) once read, exactly as before.
Same-session markers older than the staleness threshold (60 minutes) are
informational only and do not contribute to exit code or error message.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Staleness threshold in seconds (60 minutes): same-session markers older
# than this are excluded from the gate message/exit code, but still consumed.
STALENESS_THRESHOLD_SECONDS = 60 * 60

# Prune threshold in seconds (24 hours): markers older than this are deleted
# regardless of session, to prevent unbounded accumulation.
PRUNE_THRESHOLD_SECONDS = 24 * 60 * 60


def _marker_age_seconds(marker_data: dict[str, object]) -> float | None:
    """Return the marker's age in seconds, or None if unknown/unparseable."""
    detected_at_str = marker_data.get("detected_at")
    if not isinstance(detected_at_str, str):
        return None
    try:
        # detected_at is ISO-8601 UTC: "2026-07-09T12:34:56Z"
        detected_at = datetime.fromisoformat(detected_at_str.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        return (datetime.now(tz=timezone.utc) - detected_at).total_seconds()
    except (ValueError, TypeError):
        return None


def is_marker_stale(marker_data: dict[str, object]) -> bool:
    """Check if a marker is older than the staleness threshold.

    A marker with missing or unparseable detected_at is treated as fresh
    (fail toward reporting, not toward silent dropping).
    """
    age_seconds = _marker_age_seconds(marker_data)
    if age_seconds is None:
        return False  # treat as fresh if missing or unparseable
    return age_seconds >= STALENESS_THRESHOLD_SECONDS


def _is_marker_prunable(marker_data: dict[str, object]) -> bool:
    """Check if a marker is older than the prune threshold (24 hours).

    Unlike staleness, a marker with missing/unparseable detected_at is NOT
    prunable (we cannot know its age, so we do not delete it purely on that
    basis -- same fail-toward-caution stance as staleness).
    """
    age_seconds = _marker_age_seconds(marker_data)
    if age_seconds is None:
        return False
    return age_seconds >= PRUNE_THRESHOLD_SECONDS


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    own_session_id = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID") or "unknown"

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    if not marker_dir.is_dir():
        return 0
    markers = sorted(marker_dir.glob("*.json"))
    if not markers:
        return 0

    same_session_failures = []
    for m in markers:
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            m.unlink(missing_ok=True)
            continue

        if _is_marker_prunable(data):
            m.unlink(missing_ok=True)  # prune: too old regardless of session
            continue

        marker_session_id = data.get("session_id")
        if marker_session_id is not None and marker_session_id != own_session_id:
            # Cross-session marker: not a candidate for this run. Leave it in
            # place for its own session's gate invocation to consume.
            continue

        same_session_failures.append(data)
        m.unlink(missing_ok=True)  # consume: same-session marker read

    # Separate fresh from stale failures (same-session only)
    fresh_failures = [f for f in same_session_failures if not is_marker_stale(f)]

    # If all same-session markers are stale (or there were none), exit
    # silently with 0
    if not fresh_failures:
        return 0

    # Fresh markers trigger the gate
    validator = project_dir / "scripts" / "validate_agents.py"
    validator_passed: bool | None
    if validator.is_file():
        result = subprocess.run(
            [sys.executable, str(validator), str(project_dir / ".claude" / "agents")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        validation = result.stdout.strip() or result.stderr.strip()
        validator_passed = result.returncode == 0
    else:
        validation = "validator not found (scripts/validate_agents.py missing)"
        validator_passed = None

    agents = ", ".join(
        f"{f.get('agent_type', '?')} ({f.get('agent_id', '?')})" for f in fresh_failures
    )

    header = (
        "SUBAGENT HARD GATE TRIPPED: the following subagent(s) finished "
        f"with ZERO tool calls: {agents}.\n\n"
    )

    if validator_passed:
        directive = (
            "Automatic validation confirms all agent definitions are valid, "
            "so this is NOT a frontmatter configuration error. Investigate "
            "the subagent transcript and the marker diagnosis above for the "
            "actual cause instead (e.g. the model narrated tool calls as "
            "text without a real tool config problem, or the subagent's "
            "task is legitimately tool-free and should declare "
            "'allow-tool-free: true' in its .agent.md frontmatter).\n\n"
            f"Automatic validation result:\n{validation}\n\n"
            "Required action: report this to the user with the transcript "
            "path and marker diagnosis; do not blindly retry or respawn the "
            "subagent without understanding the actual cause.\n"
        )
    else:
        directive = (
            "This is a known failure mode caused by invalid 'tools:' "
            "frontmatter in .claude/agents/*.agent.md (unknown tool names "
            "are silently dropped, leaving the agent with no tools -- it "
            "then narrates tool calls as plain text).\n\n"
            "DO NOT retry, respawn, or send follow-up messages to the "
            "subagent: a model without tools cannot comply. Treat this as "
            "a configuration error.\n\n"
            f"Automatic validation result:\n{validation}\n\n"
            "Required action: report this to the user, and do not continue "
            "the task until 'make validate-agents' passes.\n"
        )

    sys.stderr.write(header + directive)
    return 2


if __name__ == "__main__":
    sys.exit(main())
