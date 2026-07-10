# TASK-004 Clarify initial commit requirement for locally created repos in README

## Status

done

## Description

`git subtree add` requires at least one commit to exist in the repo. If the repo
was created on GitHub and cloned, this is already satisfied. If the repo was
created locally with `git init`, an initial commit must be made first.

The README currently jumps straight to `git subtree add` without mentioning this,
which will cause the command to fail for locally initialised repos.

## Acceptance criteria

- [x] README "Adopting in a new project" section makes clear that an initial commit
  is required if the repo was created locally (not when cloned from GitHub)
- [x] The wording does not clutter the flow for the GitHub-clone case
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/004-readme-initial-commit-note`
**Switch/create:** `git checkout -b task/004-readme-initial-commit-note`
**Make target:** `make branch-task f=TASK-004`

## Completion

**Date:** 2026-04-30
**Summary:** Added a note in the "Adopting in a new project" section explaining
that an initial empty commit is needed when the repo was created locally with
`git init`, and that this step can be skipped when cloning from GitHub.
**Files changed:**
- `README.md` — initial commit note added
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/004-readme-initial-commit-note`
**Stage:** `git add README.md CHANGELOG.md docs/tasks/TASK-004-readme-initial-commit-note.md`
**Commit:** `git commit -m "Clarify initial commit requirement for locally created repos in README"`
