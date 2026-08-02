# TASK-019 Normalized monthly equivalent per pattern (FR-37)

## Status

todo

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

- [ ] Scenario: Monthly pattern reports its mean amount unchanged
      Given a payee group whose billing events recur at a median interval inside the monthly range (25-35 days)
      When `identify_recurring()` builds the pattern
      Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 1

- [ ] Scenario: Quarterly pattern is divided by 3
      Given a payee group whose billing events recur at a median interval inside the quarterly range (80-100 days)
      When `identify_recurring()` builds the pattern
      Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 3

- [ ] Scenario: Half-yearly pattern is divided by 6
      Given a payee group whose billing events recur at a median interval inside the half-yearly range (160-200 days)
      When `identify_recurring()` builds the pattern
      Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 6

- [ ] Scenario: Yearly pattern is divided by 12
      Given a payee group whose billing events recur at a median interval inside the yearly range (340-390 days)
      When `identify_recurring()` builds the pattern
      Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 12

- [ ] Scenario: Irregular pattern records no monthly equivalent
      Given a payee group whose billing events recur at a median interval outside every range in `_FREQUENCY_RANGES`
      When `identify_recurring()` builds the pattern
      Then the pattern's `frequency` is `irregular` and its `monthly_equivalent` is `None`

- [ ] Scenario: A single billing event yields no monthly equivalent
      Given a payee group that produces exactly one billing event, so no interval can be computed and `median_interval_days` is 0.0
      When `identify_recurring()` builds the pattern
      Then the pattern's `frequency` is `irregular` and its `monthly_equivalent` is `None`

- [ ] Scenario: The monthly equivalent reaches the CSV export
      Given a list of patterns containing one quarterly pattern and one irregular pattern
      When `exporter.export(patterns, "csv", path)` writes the file
      Then the header row contains a `monthly_equivalent` column, the quarterly row carries its computed value, and the irregular row carries an empty cell

- [ ] Scenario: The monthly equivalent reaches the JSON export
      Given the same list of patterns
      When `exporter.export(patterns, "json", path)` writes the file
      Then each object carries a `monthly_equivalent` key, `null` for the irregular pattern

- [ ] `_MONTHLY_DIVISORS` has exactly the same key set as `_FREQUENCY_RANGES`, asserted by a test rather than by inspection

- [ ] Hypothesis property test: for any mean amount and any median interval, `monthly_equivalent` is either `None` (exactly when `frequency == "irregular"`) or equals `amount_mean / _MONTHLY_DIVISORS[frequency]`

- [ ] Hypothesis property test: multiplying a pattern's `monthly_equivalent` by its bucket divisor recovers its `amount_mean` within floating-point tolerance

- [ ] `make lint && make test` pass with coverage >= the TASK-018 baseline (100% on `analyzer.py`)

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

**Date:** YYYY-MM-DD
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified
- `tests/test_analyzer.py` — modified
- `tests/test_exporter.py` — modified
- `docs/REQUIREMENTS_new.md` — modified prior to implementation (v0.2.21 → v0.2.22)
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-019-monthly-equivalent.md` — this file

**Branch:** `git checkout task/019-monthly-equivalent`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py tests/test_exporter.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-019-monthly-equivalent.md`
**Commit:** `git commit -m "feat: add a normalized monthly equivalent to each recurring pattern (FR-37)"`