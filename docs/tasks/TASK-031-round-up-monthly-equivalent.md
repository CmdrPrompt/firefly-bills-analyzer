# TASK-031 Round monthly equivalent up to the nearest öre (FR-37)

## Status

done

## Requirements

**Binding:** FR-37
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-019 (introduced `monthly_equivalent` and `_MONTHLY_DIVISORS` in `_build_pattern()`)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user planning cash flow across the full year, I want each pattern's
monthly equivalent rounded to whole öre in the direction that never
understates the cost, so that the exported figures are readable currency
amounts and summing them never quietly undercounts my monthly spend.

## Description

`_build_pattern()` in `src/firefly_bills_analyzer/analyzer.py` currently
computes `monthly_equivalent` as the raw float division
`mean_amount / _MONTHLY_DIVISORS[frequency]`, with no rounding — e.g. a
quarterly pattern with `mean_amount = 100.0` records `33.333333333333336`
rather than `33.34`.

FR-37 now requires the result to be rounded up (ceiling, not
round-half-to-even) to two decimal places before being stored. Ceiling
rather than ordinary rounding is deliberate: an ordinary round would
sometimes round a fraction of an öre *down*, which would make a set of
summed monthly equivalents understate the actual yearly cost divided by 12.

Apply the rounding only to the non-`None` case; `irregular` patterns
continue to record `monthly_equivalent = None` (unchanged, out of scope).

Implementation note (not binding, may differ if a cleaner equivalent
exists): `math.ceil(value * 100) / 100` is the standard pattern for
ceiling-to-two-decimals in Python; a bare `round()` is insufficient because
it rounds half-to-even and can round down.

## Branch

**Branch name:** `task/031-round-up-monthly-equivalent`
**Switch/create:** `git checkout -b task/031-round-up-monthly-equivalent`
**Make target:** `make branch-task f=TASK-031`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-031-round-up-monthly-equivalent.feature

- [x] 1. Scenario: A monthly equivalent with a non-terminating fraction is rounded up to the nearest öre
      Given a quarterly pattern with a mean amount of 100.0
      When the pattern is built
      Then its monthly_equivalent is 33.34

- [x] 2. Scenario: A monthly equivalent already exact to two decimals is unchanged
      Given a monthly pattern with a mean amount of 42.50
      When the pattern is built
      Then its monthly_equivalent is 42.5

- [x] 3. Scenario: An irregular pattern still records no monthly equivalent
      See tests/bdd/features/TASK-031-round-up-monthly-equivalent.feature: Scenario "Irregular pattern records no monthly equivalent"

- [x] 4. Hypothesis property test: for any mean amount and any median interval where `frequency != "irregular"`, `monthly_equivalent * 100` is an integer (i.e. the stored value always has at most two decimal places)

- [x] 5. Hypothesis property test: for any mean amount and any median interval where `frequency != "irregular"`, `monthly_equivalent >= mean_amount / _MONTHLY_DIVISORS[frequency]` (rounding never understates the true value)

- [x] 6. `make lint && make test` pass with coverage >= the TASK-030 baseline

## Out of scope

- Changing `_MONTHLY_DIVISORS`, `_FREQUENCY_RANGES`, or `_classify_frequency()`
- Rounding any other exported field (`amount_mean`, `amount_for_name`, etc.)
- Changing behavior for `irregular` patterns (still `None`)

## Blockers

None

## Completion

**Date:** 2026-08-03
**Summary:** `_build_pattern()` in `analyzer.py` now rounds `monthly_equivalent`
up (ceiling) to two decimal places via a new `_round_up_to_ore()` helper,
which goes through `Decimal(str(value))` before quantizing with
`ROUND_CEILING` to avoid spurious round-ups from binary floating-point noise
on values already exact to two decimals. `irregular` patterns are unaffected
(still `None`). Updated the existing TASK-019 unit and BDD tests that
asserted exact `amount_mean / divisor` equality, since that is no longer
true in general after rounding; added new unit tests, Hypothesis property
tests, and a BDD feature file/step module for TASK-031's own acceptance
criteria.

**Files changed:**

- `docs/REQUIREMENTS_new.md` - modified (FR-37, UC2 step 9, "Monthly equivalent" definition)
- `docs/tasks/README.md` - modified (added TASK-031 row)
- `docs/tasks/TASK-031-round-up-monthly-equivalent.md` - created
- `src/firefly_bills_analyzer/analyzer.py` - modified
- `tests/test_analyzer.py` - modified
- `tests/bdd/features/TASK-031-round-up-monthly-equivalent.feature` - created
- `tests/bdd/steps/test_task_031_steps.py` - created
- `tests/bdd/steps/test_task_019_steps.py` - modified (rounding-aware assertion)
- `CHANGELOG.md` - modified

**Branch:** `git checkout task/031-round-up-monthly-equivalent`
**Stage:** `git add docs/REQUIREMENTS_new.md docs/tasks/README.md docs/tasks/TASK-031-round-up-monthly-equivalent.md src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py tests/bdd/features/TASK-031-round-up-monthly-equivalent.feature tests/bdd/steps/test_task_031_steps.py tests/bdd/steps/test_task_019_steps.py CHANGELOG.md`
**Commit:** `git commit -m "feat: round monthly equivalent up to the nearest öre (FR-37)"`
