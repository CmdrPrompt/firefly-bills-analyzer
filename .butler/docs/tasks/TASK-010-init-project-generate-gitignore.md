# TASK-010 Generate .gitignore from scaffold template in init-project

## Status

done

## Description

`make init-project` generates `CLAUDE.md`, `pyproject.toml`, and governance files
but does not produce a `.gitignore`. A new Python project needs a `.gitignore`
immediately to avoid accidentally committing `.venv/`, `__pycache__/`, etc.

Add a `scaffold/.gitignore.tmpl` with standard Python ignores and have
`init-project` copy it (via `generate-gitignore`) alongside the other files.

## Acceptance criteria

- [x] `scaffold/.gitignore.tmpl` exists with sensible Python defaults
- [x] A `generate-gitignore` target copies the template to `.gitignore`,
  with a `FORCE=1` overwrite guard
- [x] `init-project` calls `generate-gitignore` and includes `.gitignore` in
  the suggested `git add` command
- [x] `make install` auto-generates `.gitignore` if missing (same pattern as
  `pyproject.toml`)
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/010-init-project-generate-gitignore`
**Switch/create:** `git checkout -b task/010-init-project-generate-gitignore`
**Make target:** `make branch-task f=TASK-010`

## Completion

**Date:** 2026-04-30
**Summary:** Added `scaffold/.gitignore.tmpl`, `generate-gitignore` target, wired
it into `init-project` and `install`, and updated the suggested commit command.
**Files changed:**
- `scaffold/.gitignore.tmpl` — created
- `Makefile` — `generate-gitignore` target added, `init-project` and `install` updated
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/010-init-project-generate-gitignore`
**Stage:** `git add scaffold/.gitignore.tmpl Makefile CHANGELOG.md docs/tasks/TASK-010-init-project-generate-gitignore.md`
**Commit:** `git commit -m "Generate .gitignore from scaffold template in init-project"`
