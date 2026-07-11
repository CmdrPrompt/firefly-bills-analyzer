# TASK-005 Make init-project generate pyproject.toml with collected values

## Status

done

## Description

`make init-project` collects project name and description interactively and passes
them to `generate-governance-files`. However, it does not call `generate-pyproject`,
so `pyproject.toml` is generated later by `make install` using the Makefile defaults
(`my-project`, `Describe your project here.`) rather than the values the user entered.

## Acceptance criteria

- [x] `init-project` calls `generate-pyproject` with the same `PROJECT_NAME` and
  `PROJECT_DESCRIPTION` values collected interactively
- [x] `generate-pyproject` guards against overwriting an existing `pyproject.toml`
  unless `FORCE=1` is passed (consistent with the guard in `generate-governance-files`)
- [x] `make install` still auto-generates `pyproject.toml` with defaults when neither
  `init-project` nor `generate-pyproject` has been run (existing behaviour preserved)
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/005-init-project-generate-pyproject`
**Switch/create:** `git checkout -b task/005-init-project-generate-pyproject`
**Make target:** `make branch-task f=TASK-005`

## Completion

**Date:** 2026-04-30
**Summary:** Added `generate-pyproject` call to `init-project` with the collected
values. Added an overwrite guard to `generate-pyproject` for consistency.
**Files changed:**
- `Makefile` — `init-project` updated, `generate-pyproject` guard added
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/005-init-project-generate-pyproject`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-005-init-project-generate-pyproject.md`
**Commit:** `git commit -m "Fix init-project to generate pyproject.toml with collected project values"`
