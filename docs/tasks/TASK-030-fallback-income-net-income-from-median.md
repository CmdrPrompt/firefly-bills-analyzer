# TASK-030 Fallback income observed_net_income when latest occurrence deviates from median

## Status
todo

## Requirements
**Binding:** FR-43a, FR-44, UC12
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-025 (fetch deposits), TASK-026 (detect income sources)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a cash flow planner, I want the application to handle small income anomalies gracefully, so that a reimbursement or small allowance landing on an income account after the month's main salary does not override the observed net income figure with that anomaly's amount.

## Description
Today, `_build_income_source` in `src/firefly_bills_analyzer/income.py` (lines ~76–113) always sets `observed_net_income` to the amount of the most recent deposit occurrence, regardless of whether that occurrence is an outlier (e.g., a small reimbursement).

FR-43a requires that when the latest occurrence's amount deviates from the median amount by more than `INCOME_VARIANCE_TOLERANCE`, the function should instead select the most recent occurrence that does *not* deviate this way, and use its amount as `observed_net_income` and its date as `observed_date`.

At the same time, FR-44 requires that variance figures (outlier_count, min, max, mean) continue to include *all* occurrences, even those that are skipped when choosing the observed figure. This ensures that anomalies remain visible in the reported variance statistics.

The new algorithm:
1. Sort occurrences by date (ascending)
2. Calculate the median of all amounts
3. Starting from the most recent and moving backward, find the first occurrence whose amount does *not* deviate from the median by more than `INCOME_VARIANCE_TOLERANCE`
4. Use that occurrence's amount and date as `observed_net_income` and `observed_date`
5. Calculate variance figures (min, max, mean, outlier_count) over all occurrences, with outlier_count measuring deviation from the selected `observed_net_income`

## Branch
**Branch name:** `task/030-fallback-income-net-income-from-median`
**Switch/create:** `git checkout -b task/030-fallback-income-net-income-from-median`
**Make target:** `make branch-task f=TASK-030`

## Acceptance criteria (Gherkin)

- [ ] 1. Normal case: latest occurrence does not deviate from median
      Given an income account with occurrences `[1000, 1000, 1000, 1010]` and `INCOME_VARIANCE_TOLERANCE` of 0.10
      When the application detects the income source
      Then the observed_net_income is 1010 (the latest occurrence)
      And the observed_date is the date of the occurrence with amount 1010
      And outlier_count is 0 (no occurrence deviates from 1010 by more than 10%)

- [ ] 2. Latest occurrence deviates; fallback to previous non-deviating
      Given an income account with occurrences dated in sequence: 2026-07-01 (1000), 2026-08-01 (1000), 2026-09-01 (50), and `INCOME_VARIANCE_TOLERANCE` of 0.10
      When the application detects the income source
      Then the observed_net_income is 1000 (from 2026-08-01, the most recent non-deviating)
      And the observed_date is 2026-08-01
      And outlier_count is 1 (the 50 on 2026-09-01 deviates from 1000 by 95%, exceeding 10%)

- [ ] 3. All occurrences deviate from median except one
      Given an income account with occurrences `[1000, 100, 100, 100]` and `INCOME_VARIANCE_TOLERANCE` of 0.10
      When the application detects the income source
      Then the median amount is 100 (the median of [1000, 100, 100, 100])
      And the observed_net_income is 100 (the most recent non-deviating from median)
      And outlier_count is 1 (the 1000 deviates from 100 by 900%, exceeding 10%)
      And amount_min, amount_max, amount_mean include all four occurrences

- [ ] 4. Variance figures always span all occurrences
      Given an income account with occurrences `[1000, 1000, 1000, 50]` and `INCOME_VARIANCE_TOLERANCE` of 0.10
      When the application detects the income source
      Then amount_min is 50, amount_max is 1000, amount_mean is (1000+1000+1000+50)/4 = 762.5
      And occurrences count is 4 (all four are counted, not three)
      And outlier_count measures deviation from the selected observed_net_income only

## Out of scope
- Changing the frequency classification logic (UC2 applies unchanged)
- Modifying how income candidates are qualified (FR-41c remains unchanged)
- Changes to income export format or display (FR-45a, FR-45b, UC5 remain for later tasks)
- Changes to deposit fetching or grouping logic (UC12 steps 1–4 remain unchanged)

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `src/firefly_bills_analyzer/income.py` - modified `_build_income_source` function
- `tests/test_income.py` - added/updated test cases per TDD cycle
- `CHANGELOG.md` - added entry for FR-43a implementation
**Branch:** `git checkout task/030-fallback-income-net-income-from-median`
**Stage:** `git add docs/REQUIREMENTS_new.md docs/tasks/TASK-030-fallback-income-net-income-from-median.md`
**Commit:** `git commit -m "Add FR-43a and TASK-030 for income net income median fallback"`
