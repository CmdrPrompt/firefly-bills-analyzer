# TASK-013 CLI progress bar for transaction fetch (UC1)

## Status

todo

## Requirements

**Binding:** FR-34, NFR-02 (tqdm dependency)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-002 (fetcher.py exists), TASK-005 (CLI entry point exists)
**Cross-repo dependency (resolved 2026-07-11):** `firefly-python-api`'s REQ-008 /
TASK-011 added an optional `on_page: Callable[[int, int], None] | None`
callback to `get_withdrawal_transactions()` (upstream commit `e6dcc2b`,
merged PR #11). `lib/firefly-python-api` has been re-synced in this repo via
`git subtree pull` to pick it up, and `.venv` has been rebuilt against the
updated vendored copy — confirmed via
`inspect.signature(FireflyClient.get_withdrawal_transactions)` showing the
new `on_page` parameter. The dependency is a local path dependency
(`{ path = "lib/firefly-python-api" }` in `pyproject.toml`), always the exact
vendored copy, not a version range — so no graceful-fallback/version-detection
logic is needed in this task; `on_page` can be relied on unconditionally.
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user running the CLI against a real Firefly III instance, I want to see
a progress bar while transactions are being fetched, so that a long-running
fetch (24 months of history from a remote server) doesn't look like the
application has hung.

## Description

`fetcher.fetch_transactions()` currently calls
`client.get_withdrawal_transactions(start_str, end_str)` as a single blocking
call with no visibility into how many of the total pages have been fetched
(`src/firefly_bills_analyzer/fetcher.py`). Once `firefly-python-api` exposes
an `on_page(page, total_pages)` callback (that package's REQ-008), wire a
`tqdm` progress bar through it:

```python
from tqdm import tqdm

def fetch_transactions(config: Config) -> list[TransactionRead]:
    ...
    with tqdm(desc="Fetching transactions", unit="page") as bar:
        def on_page(page: int, total_pages: int) -> None:
            if bar.total is None:
                bar.total = total_pages
            bar.update(1)

        transactions = client.get_withdrawal_transactions(
            start_str, end_str, on_page=on_page
        )
    ...
```

### Dependency addition

Add `tqdm` to `dependencies` in `pyproject.toml` (currently
`python-dotenv>=1.2.2`, `firefly-python-api`).

## Branch

**Branch name:** `task/013-cli-fetch-progress-bar`
**Switch/create:** `git checkout -b task/013-cli-fetch-progress-bar`
**Make target:** `make branch-task f=TASK-013`

## Acceptance criteria

- [x] Scenario: Progress bar advances one step per fetched page
      Given a Firefly III response spanning 3 pages
      When `fetcher.fetch_transactions()` runs
      Then `get_withdrawal_transactions()` is called with an `on_page` callback
      And invoking that callback as `on_page(1, 3)`, `on_page(2, 3)`, `on_page(3, 3)` drives a `tqdm` progress bar from 0 to 3 steps, setting its total to 3 on the first call

- [x] Scenario: Returned transactions are unaffected
      Given a fake `get_withdrawal_transactions()` returning a fixed transaction list and invoking `on_page` for each simulated page
      When `fetcher.fetch_transactions()` completes
      Then the returned `list[TransactionRead]` equals exactly what the fake returned, unchanged by the progress bar wiring

- [x] Scenario: `tqdm` is a declared runtime dependency
      Given `pyproject.toml`
      When dependencies are inspected
      Then `tqdm` is listed alongside `python-dotenv` and `firefly-python-api`

- [x] `make lint && make test` pass with coverage >= baseline

## Out of scope

- Any progress indication in the web UI (deferred with Open Item #5, no web UI exists yet).
- Progress reporting for the analysis step (UC2) — considered separately if the owner requests it; `identify_recurring()` has no natural per-item checkpoints to report today and already completes within NFR-05's 60-second budget for the reference volume.
- Any change to `firefly-python-api` itself — that package's REQ-008/TASK-011 must be implemented and synced into `lib/firefly-python-api` in a separate, explicitly-approved step, per the Cross-Workspace Boundary rule in this repo's `CLAUDE.md`.

## Blockers

None. Was blocked on `firefly-python-api`'s REQ-008/TASK-011; resolved
2026-07-11 (upstream PR #11 merged, `lib/firefly-python-api` re-synced via
`git subtree pull`, `.venv` rebuilt).

## Completion

**Date:** 2026-07-11
**Summary:** `fetcher.fetch_transactions()` now wraps
`client.get_withdrawal_transactions()` in a `tqdm` progress bar, passing an
`on_page(page, total_pages)` callback that sets the bar's `total` on the
first call and advances it by one step per page. Verified against the real
Firefly III instance (`.env` credentials) with a 1-month lookback: the bar
rendered and completed correctly. `tqdm` added as a runtime dependency,
`types-tqdm` as a dev dependency for `mypy --strict`. Existing
`test_start_and_end_dates_derived_from_lookback_months` updated to assert
`on_page` is passed as a callable kwarg alongside the unchanged positional
start/end arguments; two new tests cover the callback driving the bar and
`total` being set only once.
**Files changed:**

- `src/firefly_bills_analyzer/fetcher.py` — modified (`tqdm` progress bar
  wired through `on_page`)
- `pyproject.toml` — modified (`tqdm` runtime dependency, `types-tqdm` dev
  dependency)
- `tests/test_fetcher.py` — modified (updated existing assertion, two new
  tests)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-013-cli-fetch-progress-bar.md` — modified
- `docs/tasks/README.md` — modified (status, resolved blocker note)

**Branch:** `git checkout task/013-cli-fetch-progress-bar`
**Stage:** `git add src/firefly_bills_analyzer/fetcher.py pyproject.toml uv.lock tests/test_fetcher.py CHANGELOG.md docs/tasks/TASK-013-cli-fetch-progress-bar.md docs/tasks/README.md`
**Commit:** `git commit -m "Add CLI progress bar for transaction fetch (TASK-013)"`

