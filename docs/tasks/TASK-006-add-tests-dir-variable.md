# TASK-006 Add TESTS_DIR variable and use SRC_DIR/TESTS_DIR consistently in Makefile

## Status

done

## Description

The Makefile defines `SRC_DIR ?= src` but no corresponding `TESTS_DIR` variable.
The `lint` and `format` targets hardcode `src/ tests/` instead of using the
variables, so projects that keep source or tests in non-standard directories
cannot override them.

## Acceptance criteria

- [x] `TESTS_DIR ?= tests` is defined alongside `SRC_DIR` in the variable block
- [x] `lint` uses `$(SRC_DIR)/ $(TESTS_DIR)/` instead of hardcoded `src/ tests/`
- [x] `format` uses `$(SRC_DIR)/ $(TESTS_DIR)/` instead of hardcoded `src/ tests/`
- [x] `scaffold/pyproject.toml.tmpl` uses `{{TESTS_DIR}}` placeholder for `testpaths`
- [x] `generate-pyproject` substitutes `{{TESTS_DIR}}` and guards against overwriting with `FORCE=1`
- [x] CHANGELOG.md updated

## Branch

**Branch name:** `task/006-add-tests-dir-variable`
**Switch/create:** `git checkout -b task/006-add-tests-dir-variable`
**Make target:** `make branch-task f=TASK-006`

## Completion

**Date:** 2026-04-30
**Summary:** Added `TESTS_DIR ?= tests` to the variable block and replaced all
hardcoded `src/ tests/` references in `lint` and `format` with `$(SRC_DIR)/` and
`$(TESTS_DIR)/`.
**Files changed:**
- `Makefile` — `TESTS_DIR` added, `test` updated, `generate-pyproject` guard and substitution added
- `scaffold/pyproject.toml.tmpl` — `testpaths` uses `{{TESTS_DIR}}` placeholder
- `CHANGELOG.md` — entry added
**Branch:** `git checkout task/006-add-tests-dir-variable`
**Stage:** `git add Makefile scaffold/pyproject.toml.tmpl CHANGELOG.md docs/tasks/TASK-006-add-tests-dir-variable.md`
**Commit:** `git commit -m "Add TESTS_DIR variable and replace hardcoded paths in lint and format targets"`
