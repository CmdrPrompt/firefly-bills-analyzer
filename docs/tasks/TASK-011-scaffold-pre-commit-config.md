# TASK-011 Add .pre-commit-config.yaml to scaffold and wire into init-project

## Status

done

## Description

`make install` runs `uv run pre-commit install` unconditionally, which activates
pre-commit hooks. If no `.pre-commit-config.yaml` exists in the project, every
`git commit` produces a warning and exits non-zero until one is added.

Add a minimal `scaffold/.pre-commit-config.yaml.tmpl` with ruff and standard
hooks, and have `init-project` and `install` generate it alongside the other
scaffold files.

## Acceptance criteria

- [x] `scaffold/.pre-commit-config.yaml.tmpl` exists with ruff-based hooks
- [x] A `generate-pre-commit-config` target copies the template, with a `FORCE=1`
  overwrite guard
- [x] `init-project` calls `generate-pre-commit-config` and includes
  `.pre-commit-config.yaml` in the suggested `git add` command
- [x] `make install` auto-generates `.pre-commit-config.yaml` if missing
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/011-scaffold-pre-commit-config`
**Switch/create:** `git checkout -b task/011-scaffold-pre-commit-config`
**Make target:** `make branch-task f=TASK-011`

## Completion

**Date:** 2026-04-30
**Summary:** Added `scaffold/.pre-commit-config.yaml.tmpl` with ruff hooks,
`generate-pre-commit-config` target, wired into `init-project` and `install`.
**Files changed:**
- `scaffold/.pre-commit-config.yaml.tmpl` — created
- `Makefile` — `generate-pre-commit-config` added, `init-project` and `install` updated
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/011-scaffold-pre-commit-config`
**Stage:** `git add scaffold/.pre-commit-config.yaml.tmpl Makefile CHANGELOG.md docs/tasks/TASK-011-scaffold-pre-commit-config.md`
**Commit:** `git commit -m "Add .pre-commit-config.yaml scaffold and wire into init-project"`
