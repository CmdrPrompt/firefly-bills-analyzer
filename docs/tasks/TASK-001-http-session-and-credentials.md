# TASK-001 HTTP session, credential loading, and connection validation

## Status
done

## Description

Implement the core `firefly_python_api` package with the three public symbols
defined in REQ-001: `FireflyClient`, `load_config`, and `FireflyConnectionError`.

`FireflyClient` wraps `requests.Session` with the correct auth and content-type
headers. `load_config` reads credentials from environment or `.env` file.
`validate_connection` probes `/api/v1/about` and raises `FireflyConnectionError`
on failure.

## Branch
**Branch name:** `task/001-http-session-and-credentials`
**Switch/create:** `git checkout -b task/001-http-session-and-credentials`
**Make target:** `make branch-task f=TASK-001`

## Acceptance criteria

- [x] `src/firefly_python_api/__init__.py` exports `FireflyClient`, `load_config`,
  and `FireflyConnectionError`
- [x] `FireflyClient(url, token)` creates a `requests.Session` with headers
  `Authorization: Bearer <token>`, `Accept: application/json`, and
  `Content-Type: application/json`
- [x] `load_config(env_path)` reads `FIREFLY_URL` and `FIREFLY_TOKEN` from
  environment or the given `.env` file and returns `(url, token)`
- [x] `FireflyClient.validate_connection()` calls `GET /api/v1/about` and raises
  `FireflyConnectionError` on any non-2xx response or connection error
- [x] Runtime dependencies in `pyproject.toml` are limited to `requests` and
  `python-dotenv`
- [x] Unit test coverage for this package is ≥ 90 %
- [x] `make lint && make test` pass

## Completion
**Date:** 2026-04-30
**Summary:** Implemented FireflyClient, load_config, and FireflyConnectionError following TDD. 17 unit tests, 100% coverage. Also bootstrapped build-system config, pymarkdownlnt, and types-requests as dev dependency.
**Files changed:**
- `src/firefly_python_api/__init__.py` — created
- `src/firefly_python_api/_client.py` — created
- `src/firefly_python_api/_config.py` — created
- `src/firefly_python_api/_exceptions.py` — created
- `tests/__init__.py` — created
- `tests/test_client.py` — created
- `pyproject.toml` — modified (build-system, dependencies)
- `.pymarkdown` — created
- `CHANGELOG.md` — modified
**Branch:** `task/001-http-session-and-credentials`
**Stage:** `git add src/ tests/ pyproject.toml .pymarkdown CHANGELOG.md docs/tasks/TASK-001-http-session-and-credentials.md`
**Commit:** `git commit -m "Add FireflyClient, load_config, and FireflyConnectionError (TASK-001)"`
