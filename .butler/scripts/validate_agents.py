#!/usr/bin/env python3
"""Validate .claude/agents/*.agent.md frontmatter.

Fails (exit 1) if any agent definition:
  - lacks YAML frontmatter or required keys (name, description, tools)
  - declares a tool name not in VALID_TOOLS (unknown names are silently
    dropped by Claude Code, leaving the subagent with no tools at all --
    the root cause of the TASK-025/TASK-034 "narrated tool calls" failures)
  - declares an empty tools list
  - declares an `allow-tool-free` key with a non-boolean value (optional key;
    when `true`, opts the agent out of the runtime zero-tool-call hard gate
    for agents whose task is legitimately text-in/text-out, see TASK-038)

Usage:
  python3 scripts/validate_agents.py [agents_dir]   (default .claude/agents)

Stdlib only. No PyYAML dependency: frontmatter is parsed with a minimal
line parser that covers the key: value and key: [a, b] forms used here.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Built-in Claude Code tool names (case-sensitive). Extend if new tools
# are adopted. MCP tools (mcp__server__tool) are allowed via pattern.
VALID_TOOLS = {
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
}
MCP_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_-]+__[A-Za-z0-9_-]+$")

REQUIRED_KEYS = {"name", "description", "tools"}
OPTIONAL_BOOLEAN_KEYS = {"allow-tool-free"}
VALID_BOOLEAN_LITERALS = {"true", "false"}

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict[str, object] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            items = [i.strip().strip("\"'") for i in raw[1:-1].split(",")]
            fm[key] = [i for i in items if i]
        else:
            fm[key] = raw.strip("\"'")
    return fm


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{path.name}: missing or malformed YAML frontmatter"]

    for key in sorted(REQUIRED_KEYS - fm.keys()):
        errors.append(f"{path.name}: missing required key '{key}'")

    if "tools" in fm:
        tools = fm["tools"]
        if not isinstance(tools, list):
            errors.append(f"{path.name}: 'tools' must be a list, got: {tools!r}")
        elif not tools:
            errors.append(f"{path.name}: 'tools' is empty (agent will have no tools)")
        else:
            for tool in tools:
                if tool in VALID_TOOLS or MCP_TOOL_RE.match(tool):
                    continue
                hint = ""
                for valid in VALID_TOOLS:
                    if valid.lower() == tool.lower():
                        hint = f" (did you mean '{valid}'?)"
                        break
                errors.append(
                    f"{path.name}: unknown tool '{tool}'{hint} -- "
                    "unknown names are dropped silently and the agent "
                    "may end up with NO tools"
                )

    for key in OPTIONAL_BOOLEAN_KEYS:
        if key not in fm:
            continue
        value = fm[key]
        if not isinstance(value, str) or value.lower() not in VALID_BOOLEAN_LITERALS:
            errors.append(
                f"{path.name}: '{key}' must be a boolean ('true' or 'false'), got: {value!r}"
            )
    return errors


def main() -> int:
    agents_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".claude/agents")
    if not agents_dir.is_dir():
        print(f"validate-agents: directory not found: {agents_dir}")
        return 1

    files = sorted(agents_dir.glob("*.agent.md"))
    if not files:
        print(f"validate-agents: no *.agent.md files in {agents_dir}")
        return 1

    all_errors: list[str] = []
    for f in files:
        all_errors.extend(validate_file(f))

    if all_errors:
        print(f"validate-agents: FAIL ({len(all_errors)} error(s))")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print(f"validate-agents: OK ({len(files)} agent definitions valid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
