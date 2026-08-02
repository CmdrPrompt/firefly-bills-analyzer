# TASK-019 Normalized monthly equivalent per pattern (FR-37)

## Status

done

## Requirements

**Binding:** FR-37
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-012 (amount clustering and billing events, which
established `_build_pattern()` as the single construction site for
`RecurringPattern`)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user planning cash flow across the full year, I want each identified
pattern to carry a per-month figure alongside its frequency and mean amount,
so that I can sum a set of patterns billed at different cadences without
doing the division by hand in a spreadsheet after every export.

## Description

`RecurringPattern` currently carries `frequency` (a bucket label from
`_classify_frequency()`) and `amount_mean`, but nothing derives a per-month
figure from the two. Every consumer that wants to add a quarterly bill to a
yearly one has to know the divisor table and apply it itself. FR-37 moves
that derivation into the pattern, where the frequency bucket is already known.

The divisors come from the frequency bucket, not from the observed
`median_interval_days`. This is deliberate: the bucket is what FR-06 and
`bills_creator._REPEAT_FREQ_MAP` turn into the bill's `repeat_freq`, so a
bucket-derived monthly equivalent agrees with the bill that would actually be
created. A median-interval-derived figure would drift away from it (e.g. a
quarterly pattern with an observed 88-day median would report 1/2.89 rather
than 1/3 of the mean).

### FR-37: monthly equivalent

Add to `RecurringPattern` in `src/firefly_bills_analyzer/analyzer.py`:

```python
monthly_equivalent: float | None = None
```

Compute it in `_build_pattern()`, from the already-computed `mean_amount` and
the already-computed `_classify_frequency(median_days)` result, via a
module-level divisor table:

```python
_MONTHLY_DIVISORS: dict[str, int] = {
    "monthly": 1,
    "quarterly": 3,
    "half-yearly": 6,
    "yearly": 12,
}
```

`irregular` is absent from the table, and a pattern classified `irregular`
records `monthly_equivalent = None`. This matches the existing bill-creation
behavior, where `bills_creator.create_bills()` skips `irregular` patterns
because they have no valid `repeat_freq` mapping.

The divisor table's keys must stay in sync with `_FREQUENCY_RANGES`. Assert
that relationship in a test rather than duplicating the bucket names by hand
in a third place.

### Export

`exporter._FIELDNAMES` is derived from `dataclasses.fields(RecurringPattern)`,
so the new field reaches both the CSV and the JSON export with no change to
`exporter.py`. A `None` value serializes as an empty CSV cell and as JSON
`null`. Confirm this in the export tests rather than assuming it.

### CLI review output

`_format_suggestion()` in `__main__.py` is not changed by this task. The
suggestion line already carries frequency and an amount range, and adding a
third amount to it makes the line harder to scan. Displaying the monthly
equivalent is left to whichever task first needs it on screen.

## Branch

**Branch name:** `task/019-monthly-equivalent`
**Switch/create:** `git checkout -b task/019-monthly-equivalent`
**Make target:** `make branch-task f=TASK-019`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-019-monthly-equivalent.feature

- [x] 1. Scenario: Monthly pattern reports its mean amount unchanged
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: Monthly pattern reports its mean amount unchanged

- [x] 2. Scenario: Quarterly pattern is divided by 3
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: Quarterly pattern is divided by 3

- [x] 3. Scenario: Half-yearly pattern is divided by 6
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: Half-yearly pattern is divided by 6

- [x] 4. Scenario: Yearly pattern is divided by 12
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: Yearly pattern is divided by 12

- [x] 5. Scenario: Irregular pattern records no monthly equivalent
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: Irregular pattern records no monthly equivalent

- [x] 6. Scenario: A single billing event yields no monthly equivalent
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: A single billing event yields no monthly equivalent

- [x] 7. Scenario: The monthly equivalent reaches the CSV export
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: The monthly equivalent reaches the CSV export

- [x] 8. Scenario: The monthly equivalent reaches the JSON export
      See tests/bdd/features/TASK-019-monthly-equivalent.feature: Scenario: The monthly equivalent reaches the JSON export

- [x] 9. `_MONTHLY_DIVISORS` has exactly the same key set as `_FREQUENCY_RANGES`, asserted by a test rather than by inspection

- [x] 10. Hypothesis property test: for any mean amount and any median interval, `monthly_equivalent` is either `None` (exactly when `frequency == "irregular"`) or equals `amount_mean / _MONTHLY_DIVISORS[frequency]`

- [x] 11. Hypothesis property test: multiplying a pattern's `monthly_equivalent` by its bucket divisor recovers its `amount_mean` within floating-point tolerance

- [x] 12. `make lint && make test` pass with coverage >= the TASK-018 baseline (100% on `analyzer.py`)

## Out of scope

- Any use of `monthly_equivalent` by a consumer. This task only produces the
  field; TASK-020 is the first consumer
- Displaying the monthly equivalent in `_format_suggestion()`'s CLI review
  line, or in the deferred web UI table (FR-17a/FR-30c)
- Deriving the monthly equivalent from `median_interval_days` instead of the
  frequency bucket, for `irregular` patterns or any other
- Changing `_FREQUENCY_RANGES`, `_classify_frequency()`, or the FR-03 bucket
  boundaries
- Changing how `bills_creator` handles `irregular` patterns

## Blockers

None

## Completion

**Date:** 2026-08-02
**Summary:** Added a `monthly_equivalent: float | None` field to
`RecurringPattern`, computed in `_build_pattern()` from the already-computed
`mean_amount` and `_classify_frequency(median_days)` result via a new
module-level `_MONTHLY_DIVISORS` table (monthly=1, quarterly=3,
half-yearly=6, yearly=12; `irregular` absent, so those patterns record
`monthly_equivalent = None`). `exporter.py` required no code change since
`_FIELDNAMES` is derived from `dataclasses.fields(RecurringPattern)`; added
tests confirming the field serializes as an empty CSV cell / JSON `null` for
`None`. Also migrated the task file to `BDD-ACTIVE` format ahead of
implementation: created `tests/bdd/features/TASK-019-monthly-equivalent.feature`
(8 scenarios, copied verbatim from the acceptance criteria) and
`tests/bdd/steps/test_task_019_steps.py` with real `@given`/`@when`/`@then`
bindings calling `identify_recurring()`/`exporter.export()`; all 8 scenarios
pass (`make bdd`: 9 passed, including the pre-existing example scenario).
Added `pytest-bdd` as a dev dependency (`pyproject.toml`/`uv.lock`), required
for `tests/bdd/steps/*.py` to import and for `make test`/`make bdd` to
collect them at all — without it `make test` failed outright at collection,
blocking the coverage baseline this task's own gate depends on. Also fixed a
one-byte pre-existing lint failure (missing trailing newline) in
`docs/tasks/TASK-020-Household-contribution-split-report.md`, unrelated to
FR-37 but blocking `make lint` for this task.

Two implementation subagents ran in isolated worktrees and could not commit
via `make commit-current-task` (branch name mismatch); their file changes
were verified, committed via `make commit-output`, and squash-merged into
`task/019-monthly-equivalent` by the coordinator
(`make merge-worktree`/`make commit-current-task`), per this repo's
worktree commit-workflow. One squash-merge produced an add/add conflict in
`tests/bdd/steps/test_task_019_steps.py` (BDD-scaffold placeholder vs. real
step bindings); resolved by taking the fully-bound implementation version.

Verified independently (not solely trusting subagent reports): `make lint`
clean; `make test` → 192 passed, 0 failed, 99% total coverage (552 stmts, 1
pre-existing miss in `__main__.py`, unrelated to this task),
`analyzer.py` 100% — meets the recorded task-start baseline (173 passed, 8
xfailed, 99% total / 548 stmts / 1 miss, `analyzer.py` 100%) with no
regression. `make bdd` → 9 passed (all 8 TASK-019 scenarios green, no
longer `xfail`). Test Design Reviewer scored the new/changed tests 8.2/10 on
Farley's 8 properties; flagged two real-but-optional gaps out of this task's
scope (no test for the `multi_cluster=True` interaction with
`monthly_equivalent`, no test at the exact monthly/irregular day-count
boundary) — not required by any of the 12 acceptance criteria, left as
possible future follow-up rather than blocking this task.

**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified
- `tests/test_analyzer.py` — modified
- `tests/test_exporter.py` — modified
- `tests/bdd/features/TASK-019-monthly-equivalent.feature` — created
- `tests/bdd/steps/test_task_019_steps.py` — created (scaffold), then modified (real step bindings)
- `pyproject.toml` — modified (`pytest-bdd` dev dependency)
- `uv.lock` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status: todo → done)
- `docs/tasks/TASK-020-Household-contribution-split-report.md` — modified (trailing newline, unrelated lint fix)
- `docs/tasks/TASK-019-normalized-monthly-equivalent-per-pattern.md` — this file

**Branch:** `git checkout task/019-monthly-equivalent`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py tests/test_exporter.py tests/bdd/features/TASK-019-monthly-equivalent.feature tests/bdd/steps/test_task_019_steps.py pyproject.toml uv.lock CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-020-Household-contribution-split-report.md docs/tasks/TASK-019-normalized-monthly-equivalent-per-pattern.md`
**Commit:** `git commit -m "feat: add a normalized monthly equivalent to each recurring pattern (FR-37)"`
