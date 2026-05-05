# TASK-007 Use current directory name as default PROJECT_NAME in init-project

## Status

done

## Description

`make init-project` currently shows `my-project` as the default for PROJECT_NAME.
The current directory name is almost always the intended project name and makes a
better dynamic default.

## Acceptance criteria

- [x] `init-project` uses `$(notdir $(CURDIR))` as the default for the PROJECT_NAME
  prompt instead of `$(PROJECT_NAME)` (which defaults to `my-project`)
- [x] The user can still override by typing a different name
- [x] Passing `PROJECT_NAME=foo` on the command line still works as expected
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/007-init-project-default-from-dirname`
**Switch/create:** `git checkout -b task/007-init-project-default-from-dirname`
**Make target:** `make branch-task f=TASK-007`

## Completion

**Date:** 2026-04-30
**Summary:** Changed the PROJECT_NAME prompt default in `init-project` to use
`$(notdir $(CURDIR))` so it reflects the current directory name.
**Files changed:**
- `Makefile` — PROJECT_NAME default in `init-project` updated
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/007-init-project-default-from-dirname`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-007-init-project-default-from-dirname.md`
**Commit:** `git commit -m "Default PROJECT_NAME in init-project to current directory name"`
