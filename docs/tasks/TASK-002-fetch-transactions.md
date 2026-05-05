# TASK-002 Fetch withdrawal transactions (UC1)

## Status

todo

## Description

Implement `fetcher.py` — the UC1 data-ingestion layer. It calls
`FireflyClient.get_withdrawal_transactions(start, end)` from `firefly-python-api`
(added in TASK-005 of that repo) and returns a typed list of transactions ready
for the analyzer.

The lookback window is derived from `Config.lookback_months`: start date is today
minus that many months, end date is today.

Covers FR-01, FR-02, FR-09, NFR-03.

## Branch

**Branch name:** `task/002-fetch-transactions`
**Switch/create:** `git checkout -b task/002-fetch-transactions`
**Make target:** `make branch-task f=TASK-002`

## Acceptance criteria

- [ ] `firefly-python-api` is installed as a path dependency in `pyproject.toml`
      (e.g. `firefly-python-api @ file://${PROJECT_ROOT}/lib/firefly-python-api`)
      so that `from firefly_python_api import FireflyClient, TransactionRead` works
- [ ] `src/firefly_bills_analyzer/fetcher.py` exposes
      `fetch_transactions(config: Config) -> list[TransactionRead]`
- [ ] Start date is computed as today minus `config.lookback_months` calendar months;
      end date is today; both formatted as `YYYY-MM-DD`
- [ ] `FireflyConnectionError` is caught and re-raised as a plain `SystemExit` with
      a human-readable message (no stack trace — NFR-04)
- [ ] All API calls are logged at DEBUG level with endpoint and outcome (FR-09)
- [ ] `tests/test_fetcher.py` mocks `FireflyClient` and covers:
      the happy path (returns expected transactions), the empty result (returns `[]`),
      and the connection error (exits with a non-zero code)
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/fetcher.py` — created
- `tests/test_fetcher.py` — created
- `pyproject.toml` — modified (firefly-python-api path dependency)
- `uv.lock` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-002-fetch-transactions.md` — modified

**Branch:** `git checkout task/002-fetch-transactions`
**Stage:** `git add src/firefly_bills_analyzer/fetcher.py tests/test_fetcher.py pyproject.toml uv.lock CHANGELOG.md docs/tasks/TASK-002-fetch-transactions.md`
**Commit:** `git commit -m "Add fetcher.py for UC1 transaction ingestion (TASK-002)"`
