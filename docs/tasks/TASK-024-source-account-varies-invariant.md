# TASK-024 Turn the source-account "varies" flag into an FR-32d invariant check (FR-30a, FR-30e)

## Status

todo

## Requirements

**Binding:** FR-30a, FR-30e
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-011 (introduced FR-30a's mode resolution and the varies
flag), TASK-014 (introduced FR-32d, which made the flag unreachable)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer, I want the "varies" indicator to mean something I can act on,
so that a column which is now structurally always false either disappears from
my mental model or tells me that partitioning has broken.

## Description

FR-30a specified the pattern's source account as the mode of `source_name`
across the pattern's transactions, and required recording whether more than one
distinct value occurs. `_resolve_source_account()` implements exactly that.

FR-32d, added later by TASK-014, partitions every payee group by `source_name`
before clustering. Every cluster therefore contains exactly one distinct
`source_name` value, or only `None`. Consequences:

- The mode computation is redundant: the mode of a single distinct value is
  that value.
- `source_account_varies` cannot be `True`.
- FR-30b's CLI "(varies)" branch in `_format_suggestion()` and FR-30d's exported
  varies field describe a state that cannot occur.

Verified: twelve monthly transactions to one payee from `Lonekonto` and twelve
from `Rakningskonto` produce two patterns, `varies=False` on both. Under the
pre-FR-32d behavior this was one pattern with `varies=True`.

Two options were considered. Deleting the flag, the column, and the CLI branch
is the smaller codebase. Keeping them as an invariant check is the safer one:
FR-32d's partitioning is the only thing making the flag unreachable, and a
future change to the partitioning order or key would silently reintroduce
mixed-source clusters with nothing to signal it. FR-30e (spec v0.2.23) takes
the second option, so the flag stays and gains a stated meaning.

### Change

`_resolve_source_account()` in `analyzer.py`: replace the mode computation with
a distinct-value computation. Return the single distinct non-`None` value and
`False`, or `None` and `False` when there are none. When more than one distinct
value is present, return that value set's first element and `True`, and log a
warning naming the payee and the distinct account names, since that state is an
FR-32d violation rather than data the user needs to reconcile.

`_format_suggestion()` in `__main__.py`: unchanged in behavior. Its "(varies)"
branch is now the anomaly path, and the comment above it should say so.

### Regression guard

The important test is the one that fails if partitioning regresses: given a
payee group spanning two source accounts, `identify_recurring()` produces one
pattern per source account and no pattern with `source_account_varies` set.
That is the assertion that makes FR-30e's invariant meaningful rather than
decorative.

Reaching the `True` branch requires calling `_resolve_source_account()` directly
with a mixed-source list, bypassing `identify_recurring()`. Test it at that
level; do not construct a fake pipeline to force it.

## Branch

**Branch name:** `task/024-source-account-varies-invariant`
**Switch/create:** `git checkout -b task/024-source-account-varies-invariant`
**Make target:** `make branch-task f=TASK-024`

## Acceptance criteria (Gherkin)

- [ ] Scenario: A payee paid from two accounts yields one pattern per account, none varying
      Given twelve monthly transactions to one payee from one source account and twelve from another
      When `identify_recurring()` runs
      Then two patterns are produced, each resolving its own source account name, and `source_account_varies` is `False` on both

- [ ] Scenario: A pattern with no source account resolves to none
      Given a cluster whose transactions all have `source_name` set to `None`
      When the source account is resolved
      Then the resolved name is `None` and `source_account_varies` is `False`

- [ ] Scenario: A mixed-source list is reported as an invariant violation
      Given `_resolve_source_account()` called directly with transactions spanning two distinct `source_name` values
      When it runs
      Then it returns `source_account_varies` as `True` and emits a warning naming both account names

- [ ] Scenario: The CLI still renders the anomaly path
      Given a pattern with `source_account_varies` set to `True`
      When `_format_suggestion()` formats it
      Then the output contains the "(varies)" indicator, unchanged from today (FR-30b)

- [ ] Scenario: The export still carries both fields
      Given any pattern
      When it is exported to CSV and to JSON
      Then the resolved source account name and the varies flag are both present (FR-30d)

- [ ] Hypothesis property test: for any transaction list sharing a single `source_name`, in any order, `_resolve_source_account()` returns that name and `False`

- [ ] `make lint && make test` pass with coverage >= the TASK-018 baseline

## Out of scope

- Removing `source_account_varies`, the FR-30d export field, or the FR-30b CLI
  indicator. FR-30e keeps them deliberately; removal would be a separate
  requirement change
- Changing FR-32d's partitioning key or the order of partitioning relative to
  FR-32a clustering
- Deciding what the application should do when the invariant is violated beyond
  logging and flagging. Failing the run on a violation would be a behavior
  change needing its own requirement
- The deferred web UI column (FR-30c), contingent on Open Item #5

## Blockers

None

## Completion

**Date:** YYYY-MM-DD
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified
- `src/firefly_bills_analyzer/__main__.py` — modified (comment only)
- `tests/test_analyzer.py` — modified
- `tests/test_main.py` — modified
- `docs/REQUIREMENTS_new.md` — modified prior to implementation (v0.2.22 → v0.2.23)
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-024-source-account-varies-invariant.md` — this file

**Branch:** `git checkout task/024-source-account-varies-invariant`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py src/firefly_bills_analyzer/__main__.py tests/test_analyzer.py tests/test_main.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-024-source-account-varies-invariant.md`
**Commit:** `git commit -m "fix: resolve a pattern's source account from FR-32d's single-account invariant and flag violations of it (FR-30e)"`
