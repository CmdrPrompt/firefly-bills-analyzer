# TASK-019 Integration test for deposit transaction fetching

## Status

todo

## Requirements

**Binding:** REQ-011
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-016 (introduced `get_deposit_transactions()`)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a developer, I want an integration test that calls
`get_deposit_transactions()` against a real Firefly III instance, so that a
regression in pagination, split flattening, the reversed account-role
convention, or the deposit type filter is caught against actual API
responses, not only against mocks.

## Description

Add an integration test to `tests/integration/test_integration.py` covering
`get_deposit_transactions(start, end)` (REQ-011, UC-011-1). It follows the
file's existing pattern exactly: the module-scoped `client` fixture, the
`@skip_if_no_credentials` marker, and no write operations. No new fixtures,
teardown, or test infrastructure are introduced.

Call `get_deposit_transactions()` with a date range wide enough to likely
contain data (mirroring `test_get_summary_returns_dict`'s use of a full
calendar year), and assert the return type and shape: a `list`, and, for any
returned item, that it carries the `TransactionRead` fields (`date`,
`amount`, `destination_name`, `category_name`, `source_name`, `source_id`)
with `date` truncated to `YYYY-MM-DD`. Do not assert on specific transaction
content, since the real instance's data is outside this library's control.

## Branch

**Branch name:** `task/019-integration-test-deposit-transactions`
**Switch/create:** `git checkout -b task/019-integration-test-deposit-transactions`
**Make target:** `make branch-task f=TASK-019`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-019-integration-test-deposit-transactions.feature

- [ ] 1. Scenario: Deposit transactions are fetched from a real instance
      Given a configured Firefly III instance reachable via `FIREFLY_URL` and
      `FIREFLY_TOKEN`
      When `get_deposit_transactions(start, end)` is called with a
      calendar-year date range
      Then the call succeeds and returns a `list`

- [ ] 2. Scenario: Returned records carry the required fields
      Given the list returned by `get_deposit_transactions(start, end)`
      When any record is present in that list
      Then each record has `date` truncated to `YYYY-MM-DD`, and `amount`,
      `destination_name`, `category_name`, `source_name`, and `source_id`
      keys are present

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

- Any assertion on the specific content of returned transactions — the real
  instance's data is outside this library's control.
- Any assertion distinguishing deposits from transfers by content; UC-011-5
  is already covered by the mocked unit tests in TASK-016.
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
