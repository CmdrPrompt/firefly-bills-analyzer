# TASK-019 Fix pr-task and branch-task spurious fatal error when branch already exists

## Status

done

## Description

`make pr-task` and `make branch-task` always attempt `git checkout -b <branch>`
from the task file's `**Switch/create:**` line. When the branch already exists
(the common case when running `pr-task` from the task branch), git prints
`fatal: a branch named '...' already exists` before the fallback to
`git checkout <branch>` succeeds. The operation completes correctly but the
`fatal:` output is confusing and looks like an error.

The fix checks whether the branch already exists before deciding which form of
`git checkout` to use, eliminating the spurious error output entirely.

## Acceptance criteria

- [x] Running `make pr-current-task` from the task branch produces no `fatal:`
  output
- [x] Running `make branch-task f=TASK-NNN` when the branch already exists
  switches to it silently, with no `fatal:` output
- [x] Running `make branch-task f=TASK-NNN` when the branch does not exist
  creates and switches to it as before

## Branch

**Switch/create:** `git checkout -b task/019-fix-pr-task-branch-already-exists-error`

## Completion

**Date:** 2026-05-12
**Summary:** Added `git show-ref --verify --quiet` check before `git checkout` in
`branch-task` and `pr-task` to pick the correct form silently when the branch exists.
**Files changed:**

- `Makefile` — modified (branch-task and pr-task targets)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-019-fix-pr-task-branch-already-exists-error.md` — created

**Branch:** `git checkout task/019-fix-pr-task-branch-already-exists-error`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-019-fix-pr-task-branch-already-exists-error.md`
**Commit:** `git commit -m "Fix spurious fatal error in pr-task and branch-task when branch already exists"`
