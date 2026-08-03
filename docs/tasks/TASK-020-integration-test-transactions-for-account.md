# TASK-020 Integration test for get_transactions_for_account

## Status

todo

## Requirements

**Binding:** REQ-002
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-012 (introduced `get_transactions_for_account()`)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a developer, I want an integration test that calls
`get_transactions_for_account()` against a real Firefly III instance, so
that a regression in pagination or the transaction-ID return shape is caught
against actual API responses, not only against mocks.

## Description

Add an integration test to `tests/integration/test_integration.py` covering
`get_transactions_for_account(account_id)` (REQ-002, UC-002-4). It follows
the file's existing pattern exactly: the module-scoped `client` fixture, the
`@skip_if_no_credentials` marker, and no write operations. No new fixtures,
teardown, or test infrastructure are introduced.

Use the first account from `get_asset_accounts()` (mirroring
`test_get_latest_transaction_date`'s existing use of that fixture pattern)
and call `get_transactions_for_account()` with its `id`. Assert the return
type and shape: a `list`, and, for any item in that list, that it is a
`str` (a transaction ID, per UC-002-4). Do not assert on how many
transactions exist or their specific IDs, since the real instance's data is
outside this library's control.

## Branch

**Branch name:** `task/020-integration-test-transactions-for-account`
**Switch/create:** `git checkout -b task/020-integration-test-transactions-for-account`
**Make target:** `make branch-task f=TASK-020`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-020-integration-test-transactions-for-account.feature

- [ ] 1. Scenario: Transaction IDs are fetched from a real instance
      Given a configured Firefly III instance reachable via `FIREFLY_URL` and
      `FIREFLY_TOKEN`, and the first account returned by `get_asset_accounts()`
      When `get_transactions_for_account(account_id)` is called with that
      account's `id`
      Then the call succeeds and returns a `list`

- [ ] 2. Scenario: Returned items are transaction ID strings
      Given the list returned by `get_transactions_for_account(account_id)`
      When any item is present in that list
      Then the item is a `str`

- [ ] 3. Scenario: The test is skipped without credentials
      Given `FIREFLY_URL` or `FIREFLY_TOKEN` is absent from the environment
      When the integration test suite runs
      Then this test is skipped automatically

- [ ] 4. Scenario: Quality gates pass
      Given the completed test
      When `make lint` is run
      Then it passes; the test is excluded from `make test` and only runs
      under `make test-integration`

## Out of scope

- Any assertion on the number of transactions or their specific IDs — the
  real instance's data is outside this library's control.
- Any new fixture, teardown, or seeding of test data on the real instance.
- Mutating methods (`create_transaction`, `delete_transaction`,
  `create_bill`, `set_opening_balance`) — REQ-004's read-only constraint is
  unchanged; those methods stay untested by the integration suite for now.
- Changing `docs/REQUIREMENTS.md`.

## Blockers

None.

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
