# TASK-012 Add push step to README adoption guide

## Status

done

## Description

After bootstrapping a new project the user needs to push to GitHub, but the
README doesn't mention this step. Add it to the "Adopting in a new project"
flow so it's easy to look up.

## Acceptance criteria

- [x] README "Adopting in a new project" includes the commit and push steps
  after `make install`
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/012-readme-push-note`
**Switch/create:** `git checkout -b task/012-readme-push-note`
**Make target:** `make branch-task f=TASK-012`

## Completion

**Date:** 2026-04-30
**Summary:** Added commit and push steps to the "Adopting in a new project"
section of the README.
**Files changed:**
- `README.md` — push step added
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/012-readme-push-note`
**Stage:** `git add README.md CHANGELOG.md docs/tasks/TASK-012-readme-push-note.md`
**Commit:** `git commit -m "Add commit and push steps to README adoption guide"`
