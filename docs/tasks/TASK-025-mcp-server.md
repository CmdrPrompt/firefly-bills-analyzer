# TASK-025 MCP server

## Status

done

## Description

Implement `mcp/server.py` as a thin wrapper over `butler_core`, exposing all
task and git/gh operations as MCP tools over stdio transport.

Covers Requirement 7 from REQUIREMENTS_MCP.md.

The MCP server lives in its own `mcp/pyproject.toml` so its dependency on the
MCP SDK does not leak into projects that don't use it. Each tool maps 1:1 to
a `butler_core` function — no implicit batching of multiple git operations.

**Depends on:** TASK-022 and TASK-023 (butler_core modules)

## Branch

**Branch name:** `task/025-mcp-server`
**Switch/create:** `git checkout -b task/025-mcp-server`
**Make target:** `make branch-task f=TASK-025`

## Acceptance criteria

- [x] `mcp/server.py` implements `list_tasks`, `get_task`, `create_task`, `check_acceptance_criterion`, `set_task_status` tools
- [x] `mcp/server.py` implements `branch_task`, `stage_task`, `commit_task`, `open_pr_for_task`, `merge_task_pr` tools
- [x] Each action tool (branch/stage/commit/pr/merge) performs exactly one git operation per call
- [x] `mcp/pyproject.toml` exists and declares the MCP SDK as a dependency, separate from main `pyproject.toml`
- [x] Server runs over stdio transport (invocable via `uv run --project mcp mcp/server.py`; see Summary for a naming-collision caveat on `python -m mcp.server`)
- [x] Manually verified: connected via the MCP Python SDK's stdio client and called `list_tasks` against this repo's `docs/tasks/`
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Implemented `mcp/server.py` using the official MCP Python SDK's `FastMCP`, registering
all 10 required tools as thin one-to-one wrappers over `butler_core.tasks`/`butler_core.git_ops`
(action tools read the `Task` via `read_task` then call exactly one `git_ops` function). Added
`mcp/pyproject.toml` as a fully separate uv project (own `mcp/uv.lock`) depending on the `mcp`
SDK and on `butler-core` via a local editable path dependency, so the SDK dependency never
touches the root `pyproject.toml`/`uv.lock` (verified unchanged). Removed the pre-existing empty
`mcp/__init__.py` placeholder: it made the `mcp/` directory a regular Python package, which
collided with the third-party `mcp` SDK package (also named `mcp` on PyPI) whenever the repo
root preceded site-packages on `sys.path` — this caused `from mcp.server.fastmcp import FastMCP`
inside our own `mcp/server.py` to shadow itself and crash both under pytest and under a plain
`python -m mcp.server` invocation from the repo root (reproduced and confirmed empirically).
Deleting `mcp/__init__.py` fixes this for script-style execution (`uv run server.py` from
inside `mcp/`, or `uv run --project mcp mcp/server.py` from the repo root — both verified
working), but **`python -m mcp.server` run from the repo root does not reliably invoke our
module** — it resolves to the SDK's own `mcp.server` subpackage instead, since the SDK's regular
package wins the namespace once installed in the same environment. This is a real, unavoidable
naming collision given the task's literal requirement to name our directory/module `mcp`/
`mcp.server`, and is not a code defect — flagged here rather than silently marked away. The
acceptance criterion is satisfied via the working `uv run` invocation form (the criterion offers
it as an alternative). Wrote 12 tests first (red), then implemented the server (green); a Test
Design Review flagged that the five action-tool "invokes ... exactly once" tests only checked
their own target function was called, not that the other four `git_ops` functions were *not*
called — the constraint under test ("no implicit batching") wasn't actually verified end to end.
Fixed by replacing the five near-duplicate tests with one `@pytest.mark.parametrize`-based test
that patches all five `git_ops` functions and asserts exclusivity. Manually verified end-to-end
with a throwaway MCP stdio client script (not literally through Claude Code's own MCP client
integration, which needs an interactive session this environment doesn't have): connected to the
server subprocess, listed all 10 tools, and called `list_tasks` against this repo's real
`docs/tasks/`, receiving actual task data back. The first Implementation Worker run (twice, via
`isolation: "worktree"`) produced zero tool calls and no worktree/branch on disk both times — a
tooling failure, not a difficult task — so per the Guardian's fallback rule the entire
implementation was done directly in the main conversation instead. Coverage: main project
unchanged at 99% (34 tests, same as the task-start baseline); the `mcp/` sub-project (not part of
the root coverage run, per its separate-project design) has its own 12 passing tests.
**Files changed:**

- `mcp/server.py` — created
- `mcp/pyproject.toml` — created
- `mcp/tests/__init__.py` — created
- `mcp/tests/test_server.py` — created
- `mcp/uv.lock` — created
- `mcp/__init__.py` — deleted (caused a package-name collision with the `mcp` SDK)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-025-mcp-server.md` — modified

**Branch:** `git checkout task/025-mcp-server`
**Stage:** `git add mcp/server.py mcp/pyproject.toml mcp/tests/__init__.py mcp/tests/test_server.py mcp/uv.lock mcp/__init__.py CHANGELOG.md docs/tasks/TASK-025-mcp-server.md`
**Commit:** `git commit -m "Implement MCP server exposing butler_core operations over stdio"`
