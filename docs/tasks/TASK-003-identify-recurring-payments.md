# TASK-003 Identify recurring payments (UC2)

## Status

todo

## Description

Implement `analyzer.py` — the UC2 pattern-recognition engine. It takes the
transaction list from TASK-002, groups by payee (`destination_name`), and returns
a list of `RecurringPattern` objects sorted by confidence score descending.

The confidence score formula and frequency thresholds are specified in the
requirements spec (UC2, FR-27). The formula includes both the category boost
(FR-12) and an uncategorized-behavior penalty (FR-14/FR-27): patterns with no
category have `config.uncategorized_confidence_penalty` subtracted when
`config.uncategorized_behavior` is `"neutral"`.

Covers UC2, FR-03, FR-04b, FR-12, FR-14 (scoring part), FR-27, NFR-05.

## Branch

**Branch name:** `task/003-identify-recurring-payments`
**Switch/create:** `git checkout -b task/003-identify-recurring-payments`
**Make target:** `make branch-task f=TASK-003`

## Acceptance criteria

- [ ] `src/firefly_bills_analyzer/analyzer.py` defines a `RecurringPattern`
      dataclass with fields: `destination_name: str`, `category_name: str | None`,
      `occurrences: int`, `amount_min: float`, `amount_max: float`,
      `amount_mean: float`, `median_interval_days: float`,
      `frequency: str`, `confidence: float`
- [ ] `identify_recurring(transactions, config) -> list[RecurringPattern]`
      groups by `destination_name`, skips payees with fewer than
      `config.min_occurrences` transactions, and returns results sorted by
      `confidence` descending
- [ ] Frequency classification uses the thresholds from the spec:
      monthly 25–35 d, quarterly 80–100 d, half-yearly 160–200 d,
      yearly 340–390 d, irregular otherwise
- [ ] Confidence is computed as:
      `0.4 × min(n/4, 1.0) + 0.4 × max(0, 1 − stddev_days/median_days) + 0.2 × max(0, 1 − stddev_amount/mean_amount)`
      plus `config.category_confidence_boost` when `category_name` is in
      `config.include_categories`, minus `config.uncategorized_confidence_penalty`
      when `category_name` is `None` and `config.uncategorized_behavior` is
      `"neutral"`, all clamped to [0.0, 1.0] (FR-27)
- [ ] `tests/test_analyzer.py` uses **Hypothesis** (`@given`) for the confidence
      formula and interval classification; additionally covers the happy path,
      the single-occurrence filter, the sorting order, and the
      uncategorized-penalty cases (`"neutral"` reduces confidence for
      no-category patterns; `"include"`/`"exclude"` do not)
- [ ] Analysis of 24 months of data completes in under 60 seconds against a
      moderate synthetic dataset (a quick sanity check within `test_analyzer.py`
      is enough here — the systematic benchmark across dataset sizes is
      TASK-009, which owns closing Open Item #6)
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — created
- `tests/test_analyzer.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-003-identify-recurring-payments.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/003-identify-recurring-payments`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py CHANGELOG.md docs/tasks/TASK-003-identify-recurring-payments.md`
**Commit:** `git commit -m "Add analyzer.py for UC2 pattern recognition and confidence scoring (TASK-003)"`
