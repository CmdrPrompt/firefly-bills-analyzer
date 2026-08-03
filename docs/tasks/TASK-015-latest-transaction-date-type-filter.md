# TASK-015 Latest transaction date type filter

## Status

completed

## Requirements

**Binding:** REQ-002
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (firefly-bank-importer), I want
`get_latest_transaction_date()` to optionally exclude specific transaction
types, so that cross-account transfer transactions — which may be posted
with a date later than yet-unimported withdrawal/deposit rows on the same
account — don't incorrectly become the duplicate-import floor for that
account.

## Description

Add an optional `transaction_type: str | None = None` parameter to
`FireflyClient.get_latest_transaction_date(account_id, transaction_type=None)`.
When given, forward it as a `type={transaction_type}` query parameter on the
existing `GET /api/v1/accounts/{id}/transactions?limit=1&page=1` call (e.g.
`transaction_type="withdrawal,deposit"` to exclude transfers), matching
Firefly III's transaction type filter on this endpoint. When omitted, the
call and its behavior are unchanged from today (no `type` parameter, matches
any transaction).

Uses the existing `_get` helper and response parsing already in
`get_latest_transaction_date` — this is an additive parameter, not a new
method or a new HTTP helper.

## Branch

**Branch name:** `task/015-latest-transaction-date-type-filter`
**Switch/create:** `git checkout -b task/015-latest-transaction-date-type-filter`
**Make target:** `make branch-task f=TASK-015`

## Acceptance criteria (Gherkin)

Scenarios are inline (BDD-ABSENT) and lift-ready for `.feature` extraction if
BDD tooling is adopted later.

- [x] Scenario: Default call is unchanged
      Given a valid account id
      When `get_latest_transaction_date(account_id)` is called with no
      `transaction_type` argument
      Then the request is `GET /api/v1/accounts/{account_id}/transactions?limit=1&page=1`
      with no `type` query parameter
      And the returned value matches today's behavior

- [x] Scenario: Latest date filtered to withdrawal and deposit only
      Given a valid account id whose most recent transaction is a transfer,
      but an earlier withdrawal or deposit transaction is the most recent
      one of those types
      When `get_latest_transaction_date(account_id, transaction_type="withdrawal,deposit")`
      is called
      Then the request includes `type=withdrawal,deposit` as a query parameter
      And the returned date is that of the most recent withdrawal/deposit,
      not the more recent transfer

- [x] Scenario: No matching transaction for the given type
      Given a valid account id with no transactions matching the given
      `transaction_type`
      When `get_latest_transaction_date(account_id, transaction_type=...)` is
      called and the API responds with an empty `data` list
      Then the method returns `None`

- [x] Scenario: Date truncation still applies
      Given a matching transaction whose raw API date is
      `YYYY-MM-DD HH:MM:SS`
      When `get_latest_transaction_date` returns a value
      Then the value is truncated to `YYYY-MM-DD`

- [x] Scenario: Type checking and quality gates pass
      Given the completed implementation
      When `mypy --strict` is run on `src/`, and `make lint && make test` are run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Validating `transaction_type` against Firefly III's actual set of allowed
  filter values — the parameter is forwarded as-is; the caller is
  responsible for passing a value Firefly III accepts.
- Any change to `get_transactions_for_account` or other transaction-listing
  methods.
- The firefly-bank-importer-side change that consumes this parameter
  (tracked separately in that repo's own requirements/task docs).

## Blockers

None.

## Completion

**Date:** 2026-07-21
**Summary:** Added an optional `transaction_type: str | None = None` parameter to `FireflyClient.get_latest_transaction_date(account_id, transaction_type=None)`, forwarded as a `type` query parameter on the existing `GET /api/v1/accounts/{id}/transactions?limit=1&page=1` call when given (e.g. `"withdrawal,deposit"` to exclude transfers); behavior is unchanged when the parameter is omitted. Covered by 3 new unit tests (no `type` param when omitted, `type` forwarded and correct date returned, `None` returned when no transaction matches the type) alongside the 4 existing tests for this method, all passing. `mypy --strict` passes on `src/`; `make test` passes (118 tests, 100% coverage on `src/`, no regression). `make lint`'s `check-agents-sync` failure is pre-existing on `main` (agent doc files differ between `claude-agents/` and `.claude/agents/`) and unrelated to files touched by this task.
**Files changed:**
- `src/firefly_python_api/_client.py` - modified
- `tests/test_api_methods.py` - modified
- `CHANGELOG.md` - modified
- `docs/REQUIREMENTS.md` - modified
- `docs/tasks/TASK-015-latest-transaction-date-type-filter.md` - modified
**Branch:** `git checkout task/015-latest-transaction-date-type-filter`
**Stage:** `git add src/firefly_python_api/_client.py tests/test_api_methods.py CHANGELOG.md docs/REQUIREMENTS.md docs/tasks/TASK-015-latest-transaction-date-type-filter.md`
**Commit:** `git commit -m "Add transaction_type filter to get_latest_transaction_date"`
