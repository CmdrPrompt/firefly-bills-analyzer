# TASK-003 Improve README adoption guide with step-by-step flow

## Status

done

## Description

The current README covers the individual pieces of adoption (subtree commands,
`make init-project`, agents) but does not walk the reader through a complete
adoption flow. A developer adopting butler needs to know:

- Whether they have prerequisites (uv)
- What order to run commands in
- What to do differently for a new vs an existing project
- That `make init-project` requires `include .butler/Makefile` first

## Acceptance criteria

- [x] README has a clear step-by-step section for adopting in a **new project**
- [x] README has a clear step-by-step section for adopting in an **existing project**
  (including the caveat about Makefile include placement)
- [x] Prerequisites (uv) are mentioned before the adoption steps
- [x] The order: subtree → include → init-project is explicit
- [x] CHANGELOG.md updated with a behavior-first entry

## Branch

**Branch name:** `task/003-improve-readme-adoption-guide`
**Switch/create:** `git checkout -b task/003-improve-readme-adoption-guide`
**Make target:** `make branch-task f=TASK-003`

## Completion

**Date:** 2026-04-30
**Summary:** Rewrote the "Adopting in a project" section with separate numbered
flows for new and existing projects, added prerequisites note, and made the
subtree → include → init-project order explicit.
**Files changed:**
- `README.md` — Adopting section rewritten
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/003-improve-readme-adoption-guide`
**Stage:** `git add README.md CHANGELOG.md docs/tasks/TASK-003-improve-readme-adoption-guide.md`
**Commit:** `git commit -m "Improve README adoption guide with step-by-step flows for new and existing projects"`
