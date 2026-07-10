# TASK-024 butler-cli

## Status

done

## Description

Implement `src/butler_cli/__main__.py` as a thin wrapper over `butler_core`,
exposing all task and git/gh operations as CLI subcommands under `butler task`.

Covers Requirement 6 from REQUIREMENTS_MCP.md.

The CLI entry point is registered in `pyproject.toml` as `butler-cli` (or
`butler`). It must be installable via `uv tool install` and work in terminals
including GitHub Codespaces.

**Depends on:** TASK-022 and TASK-023 (butler_core modules)

## Branch

**Branch name:** `task/024-butler-cli`
**Switch/create:** `git checkout -b task/024-butler-cli`
**Make target:** `make branch-task f=TASK-024`

## Acceptance criteria

- [x] `butler task list [--status todo|in-progress|done]` prints matching tasks
- [x] `butler task show TASK-015` prints structured task data
- [x] `butler task create --title "..." --description "..."` creates a new task file
- [x] `butler task check TASK-015 --criterion 2` checks the specified criterion
- [x] `butler task branch TASK-015` delegates to `git_ops.branch_for`
- [x] `butler task stage TASK-015` delegates to `git_ops.stage_for`
- [x] `butler task commit TASK-015` delegates to `git_ops.commit_for`
- [x] `butler task pr TASK-015` delegates to `git_ops.open_pr_for`
- [x] `butler task merge TASK-015` delegates to `git_ops.merge_pr_for`
- [x] CLI entry point declared in `pyproject.toml` and installable via `uv tool install`
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Implemented `src/butler_cli/__main__.py` as a thin `argparse`-based wrapper
(no new dependency) exposing `butler task list|show|create|check|branch|stage|commit|pr|merge`,
delegating all git/gh logic to the existing `butler_core.git_ops` functions and all task-file
logic to `butler_core.tasks`. Added a global `--tasks-dir` option (defaults to `docs/tasks`)
so tests and alternate adopting projects can point the CLI elsewhere without touching the real
repo. `--criterion` is 1-based on the CLI (matching how a human reads the numbered acceptance
criteria list) and converted to the 0-based index `check_criterion` expects. Errors
(`TaskNotFoundError`, `GitOpsError`, `ValueError`, `IndexError`) are caught in `main()`, printed
to stderr, and return exit code 1 instead of a traceback. An initial attempt to delegate this
work to the Implementation Worker sub-agent produced no worktree/commit (a no-op run), so the
work was done directly in the main conversation instead, per the Subagent verification gate.
Verified `uv run butler task list`/`--help` against the real `docs/tasks/` directory.
**Files changed:**

- `src/butler_cli/__main__.py` — implemented
- `tests/test_cli.py` — created

**Branch:** `git checkout task/024-butler-cli`
**Stage:** `git add src/butler_cli/__main__.py tests/test_cli.py pyproject.toml CHANGELOG.md docs/tasks/TASK-024-butler-cli.md`
**Commit:** `git commit -m "Implement butler-cli exposing all butler_core operations as subcommands"`
