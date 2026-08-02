# TASK-021 Correct FR-32d's transfer-based rationale (documentation only)

## Status

todo

## Requirements

**Binding:** FR-32d (rationale only, normative content unchanged)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-014 (introduced FR-32d and the incorrect rationale)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer reading FR-32d to decide whether a change is safe, I want its
justifying example to describe a case that can actually occur, so that I do
not reason about the partitioning logic from a scenario the fetch layer makes
impossible.

## Description

FR-32d, UC2 step 2.a, and UC2's alternative-flow bullet all motivated
source-account partitioning with the example of "a fixed transfer funding a
spending account, versus that spending account's own purchases". The
`_partition_by_source_account()` docstring in `analyzer.py` repeats it.

The example cannot occur. A Firefly III transfer between two of the user's own
asset accounts has transaction type `transfer`; `fetcher.fetch_transactions()`
calls `client.get_withdrawal_transactions()` and therefore only ever supplies
withdrawals to the analyzer. The real case behind TASK-014 was withdrawals to a
single payee from two different source accounts.

This is a documentation defect with no behavioral component. FR-32d's normative
sentence is correct and unchanged; the partitioning it requires is correct and
unchanged. Only the justifying example is wrong, and it is wrong in a way that
invites a future reader to conclude that transfer handling is a concern of this
module.

Spec side is already done in `docs/REQUIREMENTS_new.md` v0.2.23. This task
brings the code comment into line and adds the one assertion that keeps the
claim true.

### Change

`src/firefly_bills_analyzer/analyzer.py`, `_partition_by_source_account()`
docstring: replace the transfer example with the same-payee/two-accounts
example used in the revised FR-32d, and state the withdrawal-only constraint.

`src/firefly_bills_analyzer/fetcher.py`: no change. Its module docstring
already says "fetch withdrawal transactions from Firefly III", which is the
constraint the revised requirement now leans on.

### Regression guard

Add one test asserting that `fetcher.fetch_transactions()` obtains its
transactions from `get_withdrawal_transactions()` and from no other client
method. The revised FR-32d rationale is only true while that holds, so the
assertion is what stops the corrected wording from silently going stale if the
fetch layer is ever widened to other transaction types.

## Branch

**Branch name:** `task/021-fr32d-rationale-correction`
**Switch/create:** `git checkout -b task/021-fr32d-rationale-correction`
**Make target:** `make branch-task f=TASK-021`

## Acceptance criteria (Gherkin)

- [ ] Scenario: The fetch layer supplies withdrawals only
      Given a mocked `FireflyClient`
      When `fetcher.fetch_transactions()` runs
      Then `get_withdrawal_transactions()` is the only client method called to obtain transactions

- [ ] `_partition_by_source_account()`'s docstring no longer describes a transfer funding a spending account, and states that only withdrawals reach the function

- [ ] No behavioral change: every existing test in `tests/` passes unmodified, and no test assertion is edited

- [ ] `make lint && make test` pass with coverage >= the TASK-018 baseline

## Out of scope

- Any change to FR-32d's normative sentence, to `_partition_by_source_account()`'s
  behavior, or to the partitioning order relative to FR-32a
- Widening `fetcher.py` to fetch deposits or transfers. If internal transfers
  are ever wanted as analysis input, that is a new use case with its own
  requirement, not an adjustment to this one
- The `lib/firefly-python-api` vendored copy, which is out of bounds per the
  Cross-Workspace Boundary section of `CLAUDE.md`

## Blockers

None

## Completion

**Date:** YYYY-MM-DD
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified (docstring only)
- `tests/test_fetcher.py` — modified (withdrawal-only assertion)
- `docs/REQUIREMENTS_new.md` — modified prior to implementation (v0.2.22 → v0.2.23)
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-021-fr32d-rationale-correction.md` — this file

**Branch:** `git checkout task/021-fr32d-rationale-correction`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_fetcher.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-021-fr32d-rationale-correction.md`
**Commit:** `git commit -m "docs: correct FR-32d's source-account partitioning rationale, which described a transfer the fetch layer never supplies"`
