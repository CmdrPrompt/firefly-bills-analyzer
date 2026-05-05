# TASK-008 Update ruff line-length to 100 in pyproject.toml.tmpl

## Status

done

## Acceptance criteria

- [x] `scaffold/pyproject.toml.tmpl` has `line-length = 100`
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/008-ruff-line-length-100`
**Switch/create:** `git checkout -b task/008-ruff-line-length-100`
**Make target:** `make branch-task f=TASK-008`

## Completion

**Date:** 2026-04-30
**Summary:** Changed ruff line-length from 88 to 100 in the pyproject.toml scaffold template.
**Files changed:**
- `scaffold/pyproject.toml.tmpl` — line-length updated
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/008-ruff-line-length-100`
**Stage:** `git add scaffold/pyproject.toml.tmpl CHANGELOG.md docs/tasks/TASK-008-ruff-line-length-100.md`
**Commit:** `git commit -m "Set ruff line-length to 100 in scaffold template"`
