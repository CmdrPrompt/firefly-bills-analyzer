# TASK-001 Project scaffold and configuration layer

## Status

done

## Description

Establish the Python package structure and configuration foundation that all subsequent tasks
depend on. No application logic is included — only the skeleton and the config layer.

Covers FR-10 (configuration via .env / environment variables) and the project structure defined
in the Architecture section of the requirements spec.

## Branch

**Branch name:** `task/001-project-scaffold`
**Switch/create:** `git checkout -b task/001-project-scaffold`
**Make target:** `make branch-task f=TASK-001`

## Acceptance criteria

- [x] `src/firefly_bills_analyzer/__init__.py` exists and the package is importable
- [x] `src/firefly_bills_analyzer/config.py` loads all configuration parameters listed in the
      spec (FIREFLY_URL, FIREFLY_TOKEN, LOOKBACK_MONTHS, MIN_OCCURRENCES, AMOUNT_MARGIN,
      HIGH_CONFIDENCE_THRESHOLD, DRY_RUN, EXPORT_FORMAT, INCLUDE_CATEGORIES,
      EXCLUDE_CATEGORIES, CATEGORY_CONFIDENCE_BOOST, UNCATEGORIZED_BEHAVIOR,
      WEB_PORT, WEB_HOST, CACHE_DIR, CACHE_TTL_CATEGORIES, CACHE_TTL_BILLS,
      CACHE_TTL_TRANSACTIONS, CACHE_TTL_PAYEES) with correct types and defaults
- [x] `src/firefly_bills_analyzer/__main__.py` parses CLI flags: `--dry-run`, `--auto-approve`,
      `--clear-cache` and prints a "not yet implemented" stub
- [x] `.env.example` documents all parameters with their default values
- [x] `firefly-python-api` added as a git subtree under `lib/firefly-python-api/`
- [x] `python-dotenv` added to `[project.dependencies]` in `pyproject.toml`
- [x] Tests cover config defaults, type coercion, and that missing required values
      (FIREFLY_URL, FIREFLY_TOKEN) raise a clear error
- [x] `make lint && make test` pass with no errors

## Completion

**Date:** 2026-05-06
**Summary:** Scaffolded Python package with typed frozen `Config` dataclass (all spec
parameters, typed defaults, `ConfigError` for missing required vars), CLI entry-point with
`--dry-run`, `--auto-approve`, `--clear-cache`, and `.env.example`. Added `python-dotenv`
via `uv add`. Added `firefly-python-api` as a git subtree. 12 tests, 84 % coverage.
**Files changed:**

- `src/firefly_bills_analyzer/__init__.py` — created
- `src/firefly_bills_analyzer/config.py` — created
- `src/firefly_bills_analyzer/__main__.py` — created
- `tests/__init__.py` — created
- `tests/test_smoke.py` — created
- `tests/test_config.py` — created
- `tests/test_cli.py` — created
- `.env.example` — created
- `pyproject.toml` — modified (python-dotenv dependency)
- `uv.lock` — modified
- `lib/firefly-python-api/` — created (git subtree)
- `docs/REQUIREMENTS.md` — modified (spec updates from this session)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-001-project-scaffold.md` — modified

**Branch:** `git checkout task/001-project-scaffold`
**Stage:** `git add src/ tests/ .env.example pyproject.toml uv.lock CHANGELOG.md docs/REQUIREMENTS.md docs/tasks/TASK-001-project-scaffold.md`
**Commit:** `Add project scaffold and configuration layer`
