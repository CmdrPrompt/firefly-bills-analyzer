# TASK-021 Package scaffolding

## Status

done

## Description

Set up `python-butler` as a proper Python project: create `pyproject.toml`,
`src/butler_core/`, `src/butler_cli/` package skeletons, `mcp/` directory
skeleton, and `tests/` directory. This is the prerequisite for all subsequent
butler_core implementation tasks.

Includes installing dev dependencies so `make lint && make test` pass on the
empty package.

## Branch

**Branch name:** `task/021-package-scaffolding`
**Switch/create:** `git checkout -b task/021-package-scaffolding`
**Make target:** `make branch-task f=TASK-021`

## Acceptance criteria

- [x] `pyproject.toml` exists and declares `butler_core` and `butler_cli` as packages under `src/`
- [x] `src/butler_core/__init__.py` and `src/butler_cli/__init__.py` exist
- [x] `mcp/` directory exists with a placeholder `server.py`
- [x] `tests/` directory exists with a placeholder test
- [x] `make install` succeeds (uv sync + pre-commit install)
- [x] `make lint && make test` pass on the empty skeleton

## Completion

**Date:** 2026-07-07
**Summary:** Created `pyproject.toml`, package init files under `src/`, `mcp/` placeholder,
`tests/` placeholder, and `.pymarkdown` config. Installed dev dependencies via `uv sync`.
`make lint` and `make test` both pass.
**Files changed:**

- `pyproject.toml` — created
- `.pymarkdown` — created (copied from scaffold)
- `.pre-commit-config.yaml` — created (copied from scaffold)
- `uv.lock` — created
- `src/butler_core/__init__.py` — created
- `src/butler_cli/__init__.py` — created
- `src/butler_cli/__main__.py` — created
- `mcp/__init__.py` — created
- `mcp/server.py` — created
- `tests/__init__.py` — created
- `tests/test_placeholder.py` — created
- `Makefile` — modified (sync-main, merge-worktree, commit-output targets added)
- `REQUIREMENTS_MCP.md` — modified (pymarkdown auto-fix)
- `.claude/agents/bug-triage.agent.md` — modified (write tool, execution context, no direct git)
- `.claude/agents/characterization-test-writer.agent.md` — modified (write tool, execution context)
- `.claude/agents/dependency-auditor.agent.md` — modified (write tool, execution context, no direct git)
- `.claude/agents/implementation-worker.agent.md` — modified (write tool, execution context)
- `.claude/agents/requirements-drafter.agent.md` — modified (execution context, no direct git)
- `.claude/agents/workflow-guardian.agent.md` — modified (worktree isolation, no direct git)
- `.claude/agents/test-design-reviewer.agent.md` — created (new agent)
- `.claude/agents/test-writer.agent.md` — created (new agent)
- `claude-agents/bug-triage.agent.md` — modified (mirrors .claude/agents/)
- `claude-agents/characterization-test-writer.agent.md` — modified
- `claude-agents/dependency-auditor.agent.md` — modified
- `claude-agents/implementation-worker.agent.md` — modified
- `claude-agents/requirements-drafter.agent.md` — modified
- `claude-agents/workflow-guardian.agent.md` — modified
- `docs/tasks/TASK-014-fix-pyproject-scaffold.md` — modified (pymarkdown auto-fix)
- `docs/tasks/TASK-015-butler-trim-target.md` — modified (pymarkdown auto-fix)
- `docs/tasks/TASK-017-add-mit-license.md` — modified (status → done, completion filled)
- `docs/tasks/TASK-018-fix-butler-trim-hardcoded-list.md` — modified (status → done, completion filled)
- `docs/tasks/TASK-019-fix-pr-task-branch-already-exists-error.md` — modified (status → done, completion filled)
- `docs/tasks/TASK-020-clarify-agent-invocation.md` — modified (status → done)

**Branch:** `git checkout task/021-package-scaffolding`
**Stage:** `git add pyproject.toml .pymarkdown .pre-commit-config.yaml uv.lock src/ mcp/ tests/ Makefile REQUIREMENTS_MCP.md .claude/agents/ claude-agents/ docs/tasks/ CHANGELOG.md docs/tasks/TASK-021-package-scaffolding.md`
**Commit:** `git commit -m "Add agent governance improvements and Makefile worktree helpers"`
