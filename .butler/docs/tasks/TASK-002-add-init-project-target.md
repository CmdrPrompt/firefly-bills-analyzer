# TASK-002 Add interactive `make init-project` target for new project scaffolding

## Status

done

## Description

`generate-governance-files` is a clean, non-interactive target that requires all
project-context variables to be passed explicitly on the command line. This is
correct for CI and scripted use, but creates a poor developer experience when
adopting butler in a new project for the first time.

Add a `make init-project` target that interactively prompts the user for the
required project-context values and then delegates to `generate-governance-files`
with the collected values. This keeps `generate-governance-files` CI-safe while
giving humans a guided entry point.

**Depends on:** TASK-001 (correct template and overwrite guard must exist first)

## Acceptance criteria

- [x] A `make init-project` target exists in `Makefile`
- [x] The target prompts for: `PROJECT_NAME`, `PROJECT_DESCRIPTION`,
  `REQUIREMENTS_PATH` (default: `docs/REQUIREMENTS.md`),
  and `PROJECT_MAKE_TARGET` (default: `make help`)
- [x] Each prompt shows its default value so the user can press Enter to accept
- [x] After collecting values the target calls `generate-governance-files` with
  the collected values
- [x] If `CLAUDE.md` already exists the target exits with a clear message
  (delegates to the guard in `generate-governance-files`) unless `FORCE=1` is set
- [x] `make help` lists `init-project` under a "First time on a new project" section
- [x] The target is documented in `README.md`
- [ ] End-to-end test: running `make init-project` in a fresh adopting project
  (e.g. firefly-bank-importer) produces a correct, project-specific `CLAUDE.md`

## Branch

**Branch name:** `task/002-add-init-project-target`
**Switch/create:** `git checkout -b task/002-add-init-project-target`
**Make target:** `make branch-task f=TASK-002`

## Completion

**Date:** 2026-04-30
**Summary:** Added `make init-project` target that interactively prompts for the four
project-context values and delegates to `generate-governance-files`. Updated `make help`
with a "First time on a new project" section and documented the target in README.md.
End-to-end verification in an adopting project is pending.
**Files changed:**
- `Makefile` — `init-project` target added, help text updated
- `README.md` — Governance files section updated
- `CHANGELOG.md` — behavior-first entry added
**Branch:** `git checkout task/002-add-init-project-target`
**Stage:** `git add Makefile README.md CHANGELOG.md docs/tasks/TASK-002-add-init-project-target.md`
**Commit:** `git commit -m "Add interactive make init-project target for new project scaffolding"`
