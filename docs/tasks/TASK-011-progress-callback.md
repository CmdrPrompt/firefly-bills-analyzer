# TASK-011 Add progress callback to get_withdrawal_transactions

## Status

done

## Requirements

**Binding:** REQ-008 (UC-008-1, UC-008-2, UC-008-3)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-005 (introduces `get_withdrawal_transactions` and its pagination loop)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bills-analyzer), I want to be notified
after each page of `get_withdrawal_transactions()` completes, so that I can
drive a CLI progress bar (or any other UI) during a long-running import,
without this library taking on a dependency on any particular progress-bar
package.

## Description

`get_withdrawal_transactions(start, end)` (TASK-005) already loops over pages
internally and only returns once every page has been fetched
(`src/firefly_python_api/_client.py`, the `while True` loop that checks
`page >= data["meta"]["pagination"]["total_pages"]`). Callers have no
visibility into progress until the whole call returns.

Add an optional `on_page` parameter:

```python
def get_withdrawal_transactions(
    self,
    start: str,
    end: str,
    on_page: Callable[[int, int], None] | None = None,
) -> list[TransactionRead]:
```

After each page's data is fetched and its splits flattened into the running
`transactions` list, if `on_page` is not `None`, call
`on_page(page, data["meta"]["pagination"]["total_pages"])` — `page` being the
1-indexed page number just completed. Do not catch exceptions raised by
`on_page`; let them propagate to the caller.

When `on_page` is omitted (default `None`), behavior is unchanged from today.

## Branch

**Branch name:** `task/011-progress-callback`
**Switch/create:** `git checkout -b task/011-progress-callback`
**Make target:** `make branch-task f=TASK-011`

## Acceptance criteria (Gherkin)

Scenarios are lift-ready for `.feature` extraction if BDD tooling is adopted later.

- [ ] Scenario: `on_page` is invoked once per page in order (UC-008-1)
      Given a Firefly III instance whose withdrawal transactions span 3 pages
      When `get_withdrawal_transactions(start, end, on_page=callback)` is called
      Then `callback` is invoked exactly 3 times
      And the calls occur in order with arguments `(1, 3)`, `(2, 3)`, `(3, 3)`
      And each call happens immediately after that page's data has been fetched and parsed, before the next page is requested

- [ ] Scenario: Default behavior is unchanged when `on_page` is omitted (UC-008-2)
      Given the same 3-page withdrawal transaction fixture
      When `get_withdrawal_transactions(start, end)` is called without `on_page`
      Then no callback is invoked
      And the returned `list[TransactionRead]` is identical to the pre-TASK-011 behavior

- [ ] Scenario: Single-page result invokes `on_page` once (UC-008-1)
      Given a Firefly III instance whose withdrawal transactions fit on 1 page
      When `get_withdrawal_transactions(start, end, on_page=callback)` is called
      Then `callback` is invoked exactly once with `(1, 1)`

- [ ] Scenario: Exception in `on_page` propagates (UC-008-3)
      Given an `on_page` callback that raises `ValueError` on its first call
      When `get_withdrawal_transactions(start, end, on_page=callback)` is called
      Then the `ValueError` propagates out of `get_withdrawal_transactions()`
      And no further pages are fetched after the exception

- [ ] Scenario: No new runtime dependency (constraint)
      Given the implementation of `on_page`
      When the package's dependencies are inspected (`pyproject.toml`)
      Then no new runtime dependency has been added (no `tqdm` or similar import in `_client.py`)

- [ ] Scenario: Type checking and test suite pass (constraints)
      Given the implementation of the `on_page` parameter
      When `mypy --strict` is run on `src/`
      Then it passes with no errors
      And when `make lint && make test` is run
      Then both succeed
      And unit test coverage does not drop below the baseline recorded at task start

## Out of scope

- Any progress-bar rendering, `tqdm`, or other UI dependency (belongs to
  consumer projects, e.g. firefly-bills-analyzer).
- Adding `on_page`-style callbacks to other paginated methods
  (`get_asset_accounts()`, etc.) — add only if a concrete consumer need
  arises.
- Reporting transaction counts (only page numbers) — `total_pages` combined
  with page number is sufficient for a page-based progress bar; per-page
  transaction counts are not exposed by this task.

## Blockers

None

## Completion

**Date:** 2026-07-11
**Summary:** Added an optional `on_page: Callable[[int, int], None] | None` parameter to `get_withdrawal_transactions()`, invoked once per page immediately after that page's data is fetched and parsed, with exceptions propagating and halting further page fetches. Default `None` leaves prior behavior unchanged.
**Files changed:**

- `src/firefly_python_api/_client.py` — modified (`on_page` parameter added to `get_withdrawal_transactions`)
- `tests/test_api_methods.py` — modified (on_page scenarios added)
- `CHANGELOG.md` — modified
- `README.md` — modified (documented `get_withdrawal_transactions`, `create_bill`, `on_page`, `FireflyConnectionError.status_code`/`.response_body`, exported `TypedDict` types, and `make test-integration`)
- `docs/tasks/TASK-011-progress-callback.md` — modified

**Branch:** `git checkout task/011-progress-callback`
**Stage:** `git add src/firefly_python_api/_client.py tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-011-progress-callback.md`
**Commit:** `git commit -m "Add progress callback to get_withdrawal_transactions (TASK-011)"`
