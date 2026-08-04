# TASK-035 Investigate and fix flaky Hypothesis CSV/JSON round-trip tests

## Status

todo

## Requirements

**Binding:** FR-08, FR-45b, FR-45c, FR-51b, FR-51c
**BDD mode:** BDD-EXEMPT (test-infrastructure reliability, no new observable
application behavior)
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer running `make test`, I want the exporter's Hypothesis-based
CSV/JSON round-trip tests to pass deterministically, so that a red `make
test` run always means a real regression and never a false alarm I have to
re-run to distinguish from a genuine failure.

## Description

`tests/test_exporter.py` (and at least one test in `tests/test_fetcher.py`)
contains several Hypothesis property tests asserting that a
`RecurringPattern` / income source / household spend record / one-off
purchase round-trips through CSV or JSON export unchanged (these tests exist
to protect FR-08's pattern export, FR-45b/FR-45c's income export, and
FR-51b/FR-51c's household spend export — the requirements that specify what
an exported record must carry). Across repeated `make test` runs on an
otherwise unchanged tree, a different subset of these round-trip tests fails
each time, e.g. observed in one session:

- `test_json_round_trip_preserves_all_fields`
- `test_income_csv_round_trip_preserves_income_accounts`
- `test_every_result_record_matches_an_income_account` (`tests/test_fetcher.py`)
- `test_csv_round_trip_preserves_destination_names`
- `test_household_spend_one_off_csv_round_trip_preserves_purchases`

No production code changed between these runs, and each failing test passed
when re-run individually or on a subsequent full run — consistent with
Hypothesis generating a different failing example (or exhausting a different
per-test example budget) from one run to the next, rather than a real defect
in the exported data. Several of these tests use `st.floats(...)` strategies
with no explicit `derandomize`/fixed seed and no `@settings(deadline=...)` or
example-count tuning visible on a quick read; the amount fields these
strategies generate span a wide range (`0.01` to `10_000`–`100_000`) with no
rounding, which is a plausible source of edge-case values that interact
badly with whatever tolerance or formatting the round-trip assertion uses.

This task is investigative as well as corrective: the root cause has not
been confirmed (float formatting precision, an `@settings` profile issue, a
shared random seed, or something else), and the fix should follow from
whatever the investigation finds — the specific offending strategies,
comparison assertions, or Hypothesis settings should be diagnosed first,
not guessed at.

## Branch

**Branch name:** `task/035-flaky-csv-json-round-trip-tests`
**Switch/create:** `git checkout -b task/035-flaky-csv-json-round-trip-tests`
**Make target:** `make branch-task f=TASK-035`

## Acceptance criteria

- [ ] 1. The root cause of the non-deterministic failures is identified and
      documented (in this task file's Completion section), naming the
      specific strategy/assertion/settings responsible
- [ ] 2. `uv run pytest tests/test_exporter.py tests/test_fetcher.py -p
      no:randomly --hypothesis-seed=random` (or an equivalent repeated-run
      check) passes consistently across at least 10 consecutive runs with no
      change to production code
- [ ] 3. No existing round-trip test's coverage of FR-08/FR-45b/FR-45c/
      FR-51b/FR-51c is weakened (e.g. by narrowing a Hypothesis strategy's
      range to avoid the failure without understanding why it failed, or by
      loosening an assertion's tolerance past what the requirement's data
      actually needs) — the fix addresses the flakiness's cause, not its
      symptom
- [ ] 4. `make lint && make test` pass

## Out of scope

- Any change to `Config`, `household_spend.py`, `exporter.py`'s row-building
  logic, or other application behavior, unless the investigation shows the
  flakiness is caused by a genuine data-correctness bug in one of them
  rather than a test-only issue
- Fixing unrelated pre-existing flaky or slow tests outside the CSV/JSON
  round-trip tests named above

## Blockers

None

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/035-flaky-csv-json-round-trip-tests`
**Stage:**
**Commit:**
