# TASK-027 Packaging and optionality

## Status

todo

## Description

Finalize packaging so that `butler_core` and `butler_cli` are installable via
`uv tool install` / `pip install`, while remaining fully optional for projects
that only adopt butler's Makefile.

Covers Requirement 9 from REQUIREMENTS_MCP.md.

The MCP server has its own `mcp/pyproject.toml` (already created in TASK-025)
so its MCP SDK dependency does not leak. This task verifies the full adoption
matrix: Makefile-only, CLI-only, and CLI+MCP all work correctly.

Also update README to document CLI and MCP server installation and usage as
optional additions, separate from the base Makefile adoption flow.

**Depends on:** TASK-024 (CLI), TASK-025 (MCP), TASK-026 (Makefile refactor)

## Branch

**Branch name:** `task/027-packaging-and-optionality`
**Switch/create:** `git checkout -b task/027-packaging-and-optionality`
**Make target:** `make branch-task f=TASK-027`

## Acceptance criteria

- [x] `uv tool install .` (from repo root) installs the `butler` CLI entry point
- [x] A project that only includes `.butler/Makefile` (no Python package installed) still has fully working `make branch-task`, `stage-task`, `commit-task`, `pr-task`, `merge-pr` targets (falls back gracefully or the Makefile-only path is preserved)
- [x] `mcp/pyproject.toml` is independently installable and does not pull in `butler_core`'s dev dependencies
- [x] README has a section documenting CLI installation (`uv tool install`) and a section documenting MCP server setup, both clearly marked as optional
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-09
**Summary:** Verified via a new `tests/test_packaging.py` suite that the CLI entry point, MCP
server packaging isolation, and Makefile-only `check-butler` fallback already satisfied
Requirement 9 (added as characterization/regression tests). Added the two README sections that
were the only genuinely missing piece: CLI installation (`uv tool install`) and MCP server setup
(`cd mcp && uv sync`), both marked optional. Also added a namespace-collision constraint and a
"no PyPI release required" scope note to REQUIREMENTS_MCP.md Requirement 9 after discussion.
**Files changed:**

- `README.md` — modified (added "CLI (optional)" and "MCP server (optional)" sections)
- `tests/test_packaging.py` — added (packaging/optionality test suite)
- `REQUIREMENTS_MCP.md` — modified (Requirement 9: scope note + namespace collision constraint)
- `CHANGELOG.md` — modified (documented the README additions and test coverage)
- `docs/tasks/TASK-027-packaging-and-optionality.md` — modified (acceptance criteria + completion)

**Branch:** `git checkout task/027-packaging-and-optionality`
**Stage:** `git add README.md tests/test_packaging.py REQUIREMENTS_MCP.md CHANGELOG.md docs/tasks/TASK-027-packaging-and-optionality.md`
**Commit:** `git commit -m "Document CLI and MCP server installation as optional additions, verify packaging isolation"`
