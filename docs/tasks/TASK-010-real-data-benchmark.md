# TASK-010 Calibrate performance benchmark against real transaction data (UC8)

## Status

done

## Description

TASK-009's benchmark measures `analyzer.identify_recurring` against
synthetic data only, so its 20,000-transaction reference volume (NFR-05,
spec v0.2.7) is disconnected from any real Firefly III instance. This task
adds a separate, opt-in, read-only developer script that runs the same
timing measurement against a developer's real transaction history, so the
synthetic reference volume can be confirmed or revised against real-world
data (Open Item #9).

This script is a manual calibration tool, not an automated regression
check: it requires a live Firefly III instance and real credentials
(`FIREFLY_URL`/`FIREFLY_TOKEN`), so it must stay out of `make test` and
`make benchmark`, both of which need to keep running without external
dependencies.

**Depends on:** TASK-002 (`fetcher.fetch_transactions`), TASK-009
(`tests/benchmark_analyzer.py`'s timing/reporting approach to reuse).
Independent of TASK-005/007 — can run any time after TASK-009.

Covers UC8, FR-28.

## Branch

**Branch name:** `task/010-real-data-benchmark`
**Switch/create:** `git checkout -b task/010-real-data-benchmark`
**Make target:** `make branch-task f=TASK-010`

## Acceptance criteria

- [x] A new opt-in script (e.g. `scripts/benchmark_real_data.py`) reuses
      `fetcher.fetch_transactions` to fetch the configured user's real
      withdrawal transactions for the configured lookback window, from the
      `FIREFLY_URL`/`FIREFLY_TOKEN` already configured via `.env` (FR-10) —
      no new configuration parameters
- [x] The script is read-only: it must not call `bills_creator.create_bills`
      or otherwise write any data to Firefly III
- [x] The script runs `identify_recurring()` against the real dataset,
      measures elapsed time with `time.perf_counter()` the same way
      TASK-009's benchmark does, and prints the real transaction count and
      elapsed time
- [x] The script is not part of `make test` or `make benchmark`; a new
      `make benchmark-real` target runs it explicitly
- [x] Running the script does not require network access beyond the
      configured Firefly III instance, and fails with a human-readable
      message (consistent with `fetcher.py`'s existing error handling) if
      the connection fails, rather than a stack trace
- [x] `docs/REQUIREMENTS_new.md` Open Item #9 is resolved based on the
      measured real-world result: either confirm NFR-05's 20,000-transaction
      reference volume or replace it with the measured real value, and add a
      changelog entry documenting the outcome
- [x] `make lint && make test` pass with coverage >= baseline (the script
      itself is excluded from coverage accounting, same as
      `tests/benchmark_analyzer.py`)

## Completion

**Date:** 2026-07-11
**Summary:** Added `scripts/benchmark_real_data.py`, an opt-in, read-only
developer script (not part of `make test` or `make benchmark`) that loads
`FIREFLY_URL`/`FIREFLY_TOKEN` via `Config.from_env()` (`.env`, already
git-ignored), fetches real withdrawal transactions with the existing
`fetcher.fetch_transactions` (never imports `bills_creator` — no writes to
Firefly III), runs `identify_recurring()`, times both steps with
`time.perf_counter()`, and prints a summary. Run via the new
`make benchmark-real` target. Measured against the requirement owner's own
Firefly III instance: 2,207 real withdrawal transactions, spanning ~16
months (2025-01-01 to 2026-05-05 — less than the full 24-month lookback
window); `identify_recurring()` completed in ~0.012s. Scaling the measured
rate (~4.5 transactions/day) to a 24-month window gives ~3,300 transactions.
This resolves Open Item #9 (spec v0.2.9): NFR-05's reference volume changed
from the provisional 20,000 (synthetic-only, TASK-009) to **5,000** — the
extrapolated 24-month volume (~3,300) plus a 50% safety margin for
slower/busier server conditions — and is no longer provisional.
**Files changed:**

- `scripts/benchmark_real_data.py` — created
- `Makefile` — modified (`benchmark-real` target)
- `docs/REQUIREMENTS_new.md` — modified (Open Item #9 resolved, changelog)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-010-real-data-benchmark.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/010-real-data-benchmark`
**Stage:** `git add scripts/benchmark_real_data.py Makefile docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/TASK-010-real-data-benchmark.md docs/tasks/README.md`
**Commit:** `git commit -m "Add opt-in real-data benchmark to calibrate NFR-05 reference volume (TASK-010)"`
