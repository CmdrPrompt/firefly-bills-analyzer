# TASK-010 Add source account fields to TransactionRead

## Status

done

## Requirements

**Binding:** REQ-006 (UC-006-5)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-005 (introduces `TransactionRead` and `get_withdrawal_transactions`)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bills-analyzer), I want each
withdrawal transaction to carry its source account name, so that I can show
users which account a recurring payment is drawn from and help them plan
balance transfers ahead of bill payments.

## Description

`TransactionRead` currently carries `date`, `amount`, `destination_name`, and
`category_name` (TASK-005), but not the source account — the account funds
are withdrawn from. The raw Firefly III API response for each transaction
split already includes this data (confirmed via a live `GET
/api/v1/transactions` call): `source_id`, `source_name`, `source_iban`, and
`source_type` are present alongside the destination fields. Only the mapping
in `_split_to_transaction_read()` is missing it.

Add `source_name: str | None` and `source_id: str | None` to `TransactionRead`,
and populate them in `_split_to_transaction_read()` the same way
`destination_name`/`category_name` are handled today: read from the split,
default to `None` when absent.

## Branch

**Branch name:** `task/010-source-account-fields`
**Switch/create:** `git checkout -b task/010-source-account-fields`
**Make target:** `make branch-task f=TASK-010`

## Acceptance criteria (Gherkin)

Scenarios are lift-ready for `.feature` extraction if BDD tooling is adopted later.

- [x] Scenario: `TransactionRead` carries source account fields (UC-006-5)
      Given a Firefly III API response containing a withdrawal transaction split with
      `source_id` and `source_name` set
      When that split is converted into a `TransactionRead`
      Then the resulting `TransactionRead` has `source_name: str | None` equal to the
      split's `source_name`
      And `source_id: str | None` equal to the split's `source_id`

- [x] Scenario: Default missing source fields to None (UC-006-5)
      Given a Firefly III API response for a withdrawal transaction split where
      `source_name` and/or `source_id` are absent
      When that split is converted into a `TransactionRead`
      Then the resulting `TransactionRead` has `source_name` set to `None` for any
      absent `source_name`
      And `source_id` set to `None` for any absent `source_id`

- [x] Scenario: Existing fields and callers are unaffected
      Given the existing `get_withdrawal_transactions` pagination and multi-split
      flattening behavior (TASK-005)
      When `source_name`/`source_id` are added to `TransactionRead`
      Then `date`, `amount`, `destination_name`, and `category_name` behave exactly
      as before
      And no existing caller of `get_withdrawal_transactions` breaks

- [x] Scenario: Type checking and test suite pass (constraints)
      Given the implementation of the widened `TransactionRead`
      When `mypy --strict` is run on `src/`
      Then it passes with no errors
      And when `make lint && make test` is run
      Then both succeed
      And unit test coverage does not drop below the baseline recorded at task start

## Out of scope

- Exposing `source_iban` or `source_type` (not requested; add only if a
  concrete consumer need arises).
- Any change to `get_asset_accounts()` or other account-listing methods.
- Any write/create/update/delete operations.

## Blockers

None

## Completion

**Date:** 2026-07-11
**Summary:** Widened `TransactionRead` with `source_name: str | None` and `source_id: str | None`, populated in `_split_to_transaction_read()` the same way as `destination_name`/`category_name` (default `None` when absent). Coverage held at 100%, `mypy --strict` and `make lint` pass.
**Files changed:**

- `src/firefly_python_api/_types.py` — modified (`TransactionRead` widened)
- `src/firefly_python_api/_client.py` — modified (`_split_to_transaction_read` updated)
- `tests/test_transaction_flatten.py` — modified (source field coverage)
- `tests/test_api_methods.py` — modified (if source fields are asserted there too)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-010-source-account-fields.md` — modified

**Branch:** `git checkout task/010-source-account-fields`
**Stage:** `git add src/firefly_python_api/_types.py src/firefly_python_api/_client.py tests/test_transaction_flatten.py tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-010-source-account-fields.md`
**Commit:** `git commit -m "Add source_name/source_id to TransactionRead (TASK-010)"`
