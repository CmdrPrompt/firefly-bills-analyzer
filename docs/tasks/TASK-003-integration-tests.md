# TASK-003 Integration tests against a real Firefly III instance

## Status
done

## Description

Add a read-only integration test suite that connects to an actual Firefly III
instance using `load_config()` and exercises every public method defined in
REQ-001 through REQ-003.

Tests are skipped automatically when credentials are absent, so CI stays green
without a live instance. A `make test-integration` target runs them separately
from the unit tests.

## Branch
**Branch name:** `task/003-integration-tests`
**Switch/create:** `git checkout -b task/003-integration-tests`
**Make target:** `make branch-task f=TASK-003`

## Acceptance criteria

- [x] `tests/integration/test_integration.py` covers UC-004-1 through UC-004-4
- [x] Each test is skipped (via `pytest.skip`) when `FIREFLY_URL` or
  `FIREFLY_TOKEN` is absent rather than failing
- [x] `make test` does **not** run `tests/integration/`
- [x] `make test-integration` runs only `tests/integration/` and exits non-zero
  on failure
- [x] No write operations (`create_transaction`) are included
- [x] `make lint && make test` pass

## Completion
**Date:** 2026-04-30
**Summary:** Added read-only integration test suite (8 tests) verified against a real Firefly III instance. Discovered that get_summary() requires start/end parameters — fixed in REQ-003, _client.py, and unit tests.
**Files changed:**
- `tests/integration/__init__.py` — created
- `tests/integration/conftest.py` — created
- `tests/integration/test_integration.py` — created
- `Makefile` — modified (test, test-integration targets)
- `src/firefly_python_api/_client.py` — modified (get_summary signature)
- `tests/test_api_methods.py` — modified (get_summary calls)
- `docs/REQUIREMENTS.md` — modified (UC-003-5 updated)
- `.gitignore` — modified
- `CHANGELOG.md` — modified
**Branch:** `task/003-integration-tests`
**Stage:** `git add tests/integration/ Makefile src/firefly_python_api/_client.py tests/test_api_methods.py docs/ .gitignore CHANGELOG.md`
**Commit:** `git commit -m "Add integration tests and fix get_summary() to require start/end parameters (TASK-003)"`
