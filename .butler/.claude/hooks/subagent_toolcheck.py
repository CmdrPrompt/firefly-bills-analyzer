#!/usr/bin/env python3
"""SubagentStop hook: detect subagents that finished without a single
tool call (the "narrated tool calls" failure mode from TASK-025/TASK-034).

Behavior:
  - Reads the SubagentStop JSON from stdin (contains agent_id,
    agent_type, agent_transcript_path).
  - Counts real tool_use blocks in the subagent transcript.
  - If zero tool calls AND the agent produced at least one assistant
    turn AND the transcript carries corroborating evidence of the real
    "narrated tool calls" failure mode (TASK-038): writes a marker file
    under .claude/state/agent-failures/. The companion PostToolUse hook
    (agent_result_gate.py) picks the marker up and delivers a blocking
    error to the coordinator.
  - Agents whose `.agent.md` frontmatter declares `allow-tool-free: true`
    (e.g. Test Design Reviewer, deliberately briefed to work from pasted
    content with zero tool calls) are skipped entirely, regardless of
    evidence.
  - Always exits 0: retrying the subagent in-context is pointless when
    the cause is a broken tool configuration, so we do NOT block the
    stop here. Escalation happens in the parent instead.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Claude Code built-in tool names, used to detect "tool narration" text: a
# subagent with no real tools describing the tool call it would have made
# instead of executing it, e.g. `Read {"file_path": "foo.py"}`.
_TOOL_NAMES = (
    "Read",
    "Write",
    "Edit",
    "NotebookEdit",
    "Bash",
    "BashOutput",
    "KillShell",
    "Grep",
    "Glob",
    "Task",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "SlashCommand",
)
_NARRATION_RE = re.compile(r"\b(?:" + "|".join(_TOOL_NAMES) + r")\b\s*\(?\s*\{")

_ALLOW_TOOL_FREE_RE = re.compile(r"(?m)^allow-tool-free:\s*(\S+)\s*$")


def count_tool_uses(transcript_path: Path) -> tuple[int, int]:
    """Return (tool_use_blocks, assistant_turns) in a JSONL transcript."""
    tool_uses = 0
    assistant_turns = 0
    with transcript_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = event.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            assistant_turns += 1
            content = msg.get("content") or []
            if isinstance(content, list):
                tool_uses += sum(
                    1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use"
                )
    return tool_uses, assistant_turns


def _is_narration_text(text: str) -> bool:
    """True if `text` looks like a narrated tool call rather than free prose.

    Two signatures, either sufficient:
      - a bare tool-name token immediately followed by a JSON object, e.g.
        `Read {"file_path": "foo.py"}` or `Read({"file_path": "foo.py"})`.
      - the entire response is nothing but a JSON object (tool arguments,
        with no surrounding prose).
    A long free-text report (the TASK-038 false positive) matches neither.
    """
    if _NARRATION_RE.search(text):
        return True
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return False
        return isinstance(parsed, dict)
    return False


def _is_coordinator_followup(event: dict[str, object]) -> bool:
    """True if `event` is a coordinator follow-up message.

    Coordinator follow-ups are meta events (`isMeta: true`) carrying an
    `origin.kind == "coordinator"` marker (checked at both event level and
    inside `message`, matching the two shapes seen in real transcripts).
    Their presence indicates the coordinator already observed a stalled
    subagent turn and intervened.
    """
    if event.get("isMeta") is not True:
        return False
    origin = event.get("origin")
    if not isinstance(origin, dict):
        message = event.get("message")
        origin = message.get("origin") if isinstance(message, dict) else None
    return isinstance(origin, dict) and origin.get("kind") == "coordinator"


def has_corroborating_evidence(transcript_path: Path) -> bool:
    """Scan the transcript for a signature of the real zero-tool-call failure.

    Either signature is sufficient: a tool-narration text pattern in an
    assistant turn, or a coordinator follow-up event anywhere in the
    transcript.
    """
    with transcript_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if _is_coordinator_followup(event):
                return True

            msg = event.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "text"
                        and isinstance(block.get("text"), str)
                        and _is_narration_text(block["text"])
                    ):
                        return True
    return False


def _agent_slug(agent_type: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", agent_type.strip().lower()).strip("-")


def _agent_allows_tool_free(project_dir: Path, agent_type: str | None) -> bool:
    """True if the agent definition for `agent_type` declares allow-tool-free: true."""
    if not agent_type:
        return False
    slug = _agent_slug(agent_type)
    if not slug:
        return False
    agent_file = project_dir / ".claude" / "agents" / f"{slug}.agent.md"
    if not agent_file.is_file():
        return False
    try:
        text = agent_file.read_text(encoding="utf-8")
    except OSError:
        return False
    m = _ALLOW_TOOL_FREE_RE.search(text)
    if not m:
        return False
    return m.group(1).strip().strip("\"'").lower() == "true"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # never break the workflow on our own parse errors

    transcript = payload.get("agent_transcript_path")
    if not transcript:
        return 0
    transcript_path = Path(os.path.expanduser(transcript))
    if not transcript_path.is_file():
        return 0

    tool_uses, assistant_turns = count_tool_uses(transcript_path)
    if tool_uses > 0 or assistant_turns == 0:
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    agent_type = payload.get("agent_type")

    if _agent_allows_tool_free(project_dir, agent_type):
        return 0

    if not has_corroborating_evidence(transcript_path):
        return 0

    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    marker_dir.mkdir(parents=True, exist_ok=True)

    agent_id = payload.get("agent_id", "unknown")
    session_id = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID") or "unknown"
    marker = marker_dir / f"{agent_id}.json"
    marker.write_text(
        json.dumps(
            {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "assistant_turns": assistant_turns,
                "tool_uses": 0,
                "transcript": str(transcript_path),
                "session_id": session_id,
                "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "diagnosis": (
                    "Subagent finished with 0 tool calls and corroborating evidence "
                    "of a stalled turn (tool-narration text or a coordinator "
                    "follow-up). Most likely cause: invalid 'tools:' frontmatter in "
                    "the .agent.md definition (unknown tool names are dropped "
                    "silently). Run: make validate-agents"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
