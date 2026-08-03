# TASK-017 Transaction tags

## Status

done

## Requirements

**Binding:** REQ-012
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-005 (introduced `TransactionRead` and
`_split_to_transaction_read()`), TASK-016 (introduced
`_get_transactions_by_type()`, through which both fetch methods now build
their records)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (firefly-bills-analyzer), I want each transaction to
carry its tags, so that a user can mark one grocery purchase as personal, or
one purchase in a personal category as shared, without having to reorganize
their categories to express the exception.

## Description

Add `tags: list[str]` to `TransactionRead`, read from the split's
`attributes.transactions[].tags` in the Firefly III response.

The change is confined to `_split_to_transaction_read()` and the `TypedDict`
definition. Both `get_withdrawal_transactions()` and
`get_deposit_transactions()` build their records through
`_get_transactions_by_type()`, which calls that helper, so both gain the field
without either method changing (UC-012-3).

Absent or `null` tags become `[]`, never `None` (UC-012-2). This deviates from
the `None`-defaulting convention the other optional fields follow, and does so
deliberately: a consumer asking "does this transaction carry tag X" wants a
container to test, and the distinction between "no tags" and "tags not
reported" carries no meaning here.

Tag strings are stored exactly as returned (UC-012-4). Do not case-fold, trim,
or sort them. A consumer matching tags decides its own comparison rules, and a
library that normalizes silently makes the consumer's rules unpredictable.

The field is additive; no existing field or signature changes.

## Branch

**Branch name:** `task/017-transaction-tags`
**Switch/create:** `git checkout -b task/017-transaction-tags`
**Make target:** `make branch-task f=TASK-017`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-017-transaction-tags.feature

- [x] 1. Scenario: Tags are returned on a withdrawal
      Given a withdrawal split carrying two tags in the API response
      When `get_withdrawal_transactions(start, end)` is called
      Then the returned record's `tags` holds both tag strings, in the order
      the API returned them

- [x] 2. Scenario: Tags are returned on a deposit
      Given a deposit split carrying one tag in the API response
      When `get_deposit_transactions(start, end)` is called
      Then the returned record's `tags` holds that tag

- [x] 3. Scenario: An absent tags field becomes an empty list
      Given a split whose API response contains no `tags` key
      When either fetch method is called
      Then the returned record's `tags` is `[]` and not `None`

- [x] 4. Scenario: A null tags field becomes an empty list
      Given a split whose API response contains `"tags": null`
      When either fetch method is called
      Then the returned record's `tags` is `[]`

- [x] 5. Scenario: Tag strings are preserved verbatim
      Given a split tagged `" Hushåll "` with surrounding whitespace and mixed case
      When either fetch method is called
      Then the returned tag string is byte-identical to the API's value

- [x] 6. Scenario: Each split carries its own tags
      Given a multi-split transaction whose two splits carry different tags
      When either fetch method is called
      Then each returned record carries the tags of its own split

- [x] 7. Scenario: Existing fields are unchanged
      Given the completed implementation
      When the existing `get_withdrawal_transactions()` and
      `get_deposit_transactions()` tests are run
      Then they pass, and no field other than `tags` changed value

- [x] 8. Scenario: Type checking and quality gates pass
      Given the completed implementation
      When `mypy --strict` is run on `src/`, and `make lint && make test` are run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Any tag-based server-side filter. Firefly III can filter by tag at the API,
  but the requesting consumer reads a full window and filters in memory; adding
  a query parameter nothing calls would be speculative.
- Writing, creating, or modifying tags. This library's tag support is read-only
  here.
- Normalizing, deduplicating, or sorting tag values.
- Any tag field on the resources other than transactions (bills, accounts,
  budgets).

## Blockers

None.

## Completion

**Date:** 2026-08-02
**Summary:** Added `tags: list[str]` to `TransactionRead` and populated it in
`_split_to_transaction_read()` from `split.get("tags") or []`, so an absent
or `null` tags value becomes `[]` and never `None`; tag strings are passed
through verbatim. Both `get_withdrawal_transactions()` and
`get_deposit_transactions()` gain the field automatically through
`_get_transactions_by_type()`, with no signature change. The pre-existing
`TestGetWithdrawalTransactions` tests in `tests/test_api_methods.py` assert
full-dict equality, so adding a new required `TypedDict` key required
updating 4 of their expected dicts to include `"tags": []` (same pattern as
TASK-010's `source_name`/`source_id` addition). Scenario 7 was reworded from
"pass unmodified" to "pass, and no field other than tags changed value" to
state the actual invariant, and its step was widened to run
`tests/test_api_methods.py` as well — a green run of those full-dict
comparisons is what proves no other field's value changed. One unrelated,
pre-existing failure was left untouched:
`tests/integration/test_integration.py::test_get_opening_balance_returns_balance_and_date`
fails identically on `main` (requires live credentials; unrelated date-format
bug), and `make lint`'s `check-agents-sync` target fails identically on
`main` (unsynced `.claude/agents/` vs `claude-agents/`, unrelated to this
task's scope); `ruff check`, `ruff format --check`, `mypy --strict`, `bandit`,
and `complexipy` all pass directly.
**Files changed:**

- `src/firefly_python_api/_types.py` - modified (added `tags: list[str]` to `TransactionRead`)
- `src/firefly_python_api/_client.py` - modified (`_split_to_transaction_read()` populates `tags`)
- `tests/test_api_methods.py` - modified (added `"tags": []` to 4 pre-existing expected dicts broken by the additive field)
- `tests/bdd/features/TASK-017-transaction-tags.feature` - created (by Test Writer)
- `tests/bdd/steps/test_task_017_transaction_tags_steps.py` - created (by Test Writer)
- `tests/test_transaction_tags.py` - created (by Test Writer)
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-017-transaction-tags.md` - modified

**Branch:** `git checkout task/017-transaction-tags`
**Stage:** `src/firefly_python_api/_types.py src/firefly_python_api/_client.py tests/test_api_methods.py tests/bdd/features/TASK-017-transaction-tags.feature tests/bdd/steps/test_task_017_transaction_tags_steps.py tests/test_transaction_tags.py CHANGELOG.md docs/tasks/TASK-017-transaction-tags.md`
**Commit:** `git commit -m "Add tags field to TransactionRead (TASK-017)"`
