# TASK-018 Fix butler-trim to remove all non-Makefile files dynamically

## Status

done

## Description

`butler-trim` removes a hardcoded list of known files and directories from
`.butler/`. Any file added to python-butler that is not on that list (e.g.
`LICENSE`) is silently left behind after a trim. This means `.butler/` can
contain unexpected files that were never intended to persist in adopting
projects.

The fix replaces the hardcoded list with a dynamic approach: remove everything
in `.butler/` except `Makefile`, both from the git index and the filesystem.

## Acceptance criteria

- [x] `butler-trim` removes all files and directories under `.butler/` except
  `Makefile`, regardless of what python-butler adds in the future
- [x] Running `butler-trim` on a project where `.butler/` only contains
  `Makefile` is a no-op (idempotent)
- [x] The hardcoded list of paths is gone from the target

## Branch

**Switch/create:** `git checkout -b task/018-fix-butler-trim-hardcoded-list`

## Completion

**Date:** 2026-05-12
**Summary:** Replaced the hardcoded path list in `butler-trim` with a dynamic
`git ls-files` + `find` approach that removes everything under `.butler/` except
`Makefile`.
**Files changed:**

- `Makefile` — modified (butler-trim target)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-018-fix-butler-trim-hardcoded-list.md` — created

**Branch:** `git checkout task/018-fix-butler-trim-hardcoded-list`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-018-fix-butler-trim-hardcoded-list.md`
**Commit:** `git commit -m "Fix butler-trim to remove all non-Makefile files dynamically"`
