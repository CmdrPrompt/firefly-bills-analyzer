# TASK-016 Fetch deposit transactions

## Status

done

## Requirements

**Binding:** REQ-011
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-005 (introduced `get_withdrawal_transactions()`, its
pagination loop and `_split_to_transaction_read()`), TASK-010 (added
`source_name`/`source_id` to `TransactionRead`), TASK-011 (introduced the
`on_page` callback this method mirrors)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (firefly-bills-analyzer), I want deposit transactions
in a date range with the same pagination and split flattening the withdrawal
side already gets, so that I can detect a recurring salary payment on an asset
account instead of asking the user to type their net income into a
configuration file and keep it up to date by hand.

## Description

Add `FireflyClient.get_deposit_transactions(start, end, on_page=None)`,
returning `list[TransactionRead]`.

The method is `get_withdrawal_transactions()` with `type=deposit` instead of
`type=withdrawal`. Everything else — the page loop, `total_pages` termination,
per-split flattening via `_split_to_transaction_read()`, the `on_page`
callback contract, and `FireflyConnectionError` propagation from `_get` — is
identical. Per REQ-011's constraints, extract the shared body into a private
helper (e.g. `_get_transactions_by_type(txn_type, start, end, on_page)`) and
implement both public methods on top of it, rather than copying the loop.

No new type is introduced. `TransactionRead` already carries both
`source_name` and `destination_name`, and Firefly III fills them per
transaction direction: on a deposit, `source_name` is the revenue account
(the payer) and `destination_name` is the asset account that received the
money. That is the reverse of the withdrawal case, and it is the API's own
convention, not something this library normalizes. Document it in the method
docstring so consumers do not have to rediscover it.

`source_id` is populated on the same terms as today. `destination_id` is not
part of `TransactionRead` and is not added here (see Out of scope).

Firefly III types a movement between two of the user's own asset accounts as
`transfer`. The `type=deposit` filter therefore excludes internal transfers at
the API level (UC-011-5), which is what lets a consumer treat every returned
record as money entering from outside. Assert this in a test against a mocked
response so the claim is enforced rather than assumed.

## Branch

**Branch name:** `task/016-fetch-deposit-transactions`
**Switch/create:** `git checkout -b task/016-fetch-deposit-transactions`
**Make target:** `make branch-task f=TASK-016`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-016-fetch-deposit-transactions.feature

- [x] 1. Scenario: Deposits are requested with the deposit type filter
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Deposits are requested with the deposit type filter"

- [x] 2. Scenario: All pages are followed
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "All pages are followed"

- [x] 3. Scenario: Multi-split deposits are flattened
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Multi-split deposits are flattened"

- [x] 4. Scenario: Account roles follow the API for a deposit
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Account roles follow the API for a deposit"

- [x] 5. Scenario: Absent fields default to None
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Absent fields default to None"

- [x] 6. Scenario: Progress callback is invoked per page
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Progress callback is invoked per page"

- [x] 7. Scenario: A callback exception stops fetching
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "A callback exception stops fetching"

- [x] 8. Scenario: Transfers are not returned
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Transfers are not returned"

- [x] 9. Scenario: Connection failure is reported
      See `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature`:
      Scenario "Connection failure is reported"

- [x] 10. Scenario: Withdrawal fetching is unchanged
      Given the refactor extracting the shared page loop
      When the existing `get_withdrawal_transactions()` tests are run
      Then they pass unmodified

- [x] 11. Scenario: Type checking and quality gates pass
      Given the completed implementation
      When `mypy --strict` is run on `src/`, and `make lint && make test` are run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Adding `destination_id` to `TransactionRead`. Consumers match asset accounts
  by name today (`source_name` on the withdrawal side), and nothing in the
  requesting use case needs the ID. Add it under its own requirement if a
  consumer ever does.
- Any classification of what a deposit *means* — salary, refund, reimbursement,
  gift. This library returns rows; recognizing a recurring income source is the
  consumer's concern (firefly-bills-analyzer's own requirements).
- Any filter on the deposit side equivalent to a consumer's account or payee
  filtering. The date range and the type filter are the only server-side
  narrowing here.
- Caching. The consumer owns its cache layer.

## Blockers

None.

## Completion

**Date:** 2026-08-02
**Summary:** Added `FireflyClient.get_deposit_transactions(start, end,
on_page=None)`, backed by a new private `_get_transactions_by_type()` helper
shared with the refactored `get_withdrawal_transactions()`. No new type was
introduced; the docstring documents that Firefly III reverses the
`source_name`/`destination_name` roles for deposits. Adopted the project's
now-current BDD tooling (`.butler` submodule updated to pick up
`pytest-bdd`/`tests/bdd/` support that landed after this repo's vendored copy
was pulled) and expressed all REQ-011 scenarios as a real `.feature` file
with bound step definitions, rather than inline pytest, per BDD-ACTIVE.

**Files changed:**

- `src/firefly_python_api/_client.py` - modified (new `get_deposit_transactions`
  and `_get_transactions_by_type` helper)
- `tests/bdd/features/TASK-016-fetch-deposit-transactions.feature` - created
- `tests/bdd/steps/test_task_016_fetch_deposit_transactions_steps.py` - created
- `.claude/skills/task-file-format/SKILL.md` - modified (synced from updated
  `.butler` submodule)
- `.butler` - modified (submodule pointer updated)
- `pyproject.toml`, `uv.lock` - modified (added `pytest-bdd` dev dependency)
- `CHANGELOG.md` - modified

**Branch:** `git checkout task/016-fetch-deposit-transactions`
**Stage:** `src/firefly_python_api/_client.py tests/bdd/features/TASK-016-fetch-deposit-transactions.feature tests/bdd/steps/test_task_016_fetch_deposit_transactions_steps.py .claude/skills/task-file-format/SKILL.md .butler pyproject.toml uv.lock CHANGELOG.md docs/tasks/TASK-016-fetch-deposit-transactions.md`
**Commit:** `git commit -m "Add get_deposit_transactions() and adopt BDD tooling for TASK-016"`
