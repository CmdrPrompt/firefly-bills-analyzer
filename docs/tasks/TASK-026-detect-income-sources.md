# TASK-026 Detect income sources and resolve observed net income (UC12)

## Status

todo

## Requirements

**Binding:** FR-41a, FR-41b, FR-41c, FR-42a, FR-42b, FR-42c, FR-43, FR-44
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-025 (the deposit ingestion path and the `INCOME_*`
configuration), TASK-003 (`_classify_frequency()` and the median-interval
computation this reuses)
**Blocked on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user, I want the application to tell me what actually lands on my salary
account each month, and to tell me plainly when it cannot work that out, so
that I never build a cost split on a figure the application guessed.

## Description

New module `src/firefly_bills_analyzer/income.py`, a pure consumer of the
deposit list from TASK-025 plus `Config`. It performs no I/O.

```python
@dataclass(frozen=True)
class IncomeSource:
    income_account: str
    payer: str
    observed_net_income: float
    observed_date: str
    occurrences: int
    median_interval_days: float
    amount_min: float
    amount_max: float
    amount_mean: float
    outlier_count: int

@dataclass(frozen=True)
class IncomeAccountIssue:
    income_account: str
    reason: str            # "no-qualifying-candidate" | "ambiguous"
    candidates: list[IncomeCandidateSummary]

def detect_income(deposits: list[TransactionRead], config: Config) -> IncomeResult
```

Grouping (FR-41a): by `(destination_name, source_name)`, that is by income
account and payer. Note again the deposit-side inversion of the two fields.

Classification (FR-41b): compute the occurrence count and median interval and
call the existing `_classify_frequency()`. Reuse it; do not reimplement the
bucket boundaries. If it needs to be imported across module boundaries, promote
it from a private helper rather than copying it.

Qualification (FR-41c): frequency is `monthly` and occurrences >=
`income_min_occurrences`.

Resolution per account:

- exactly one qualifying candidate: emit an `IncomeSource` (FR-42a)
- none: emit an `IncomeAccountIssue` with `reason="no-qualifying-candidate"`
  and a summary of every rejected candidate, its payer, occurrence count, and
  frequency (FR-42b)
- more than one: emit an `IncomeAccountIssue` with `reason="ambiguous"` listing
  every qualifying payer (FR-42c). Do not sum, average, pick the largest, or
  pick the most recent. The whole point of the requirement is that this is the
  user's call

Observed net income (FR-43): the amount of the **most recent** occurrence, with
its date. Not the mean. The figure feeds a forward-looking split, and a mean
over a 24-month window hides a raise for up to 24 months. The mean is still
computed, as one of FR-44's variance figures, where it informs instead of
misleading.

Variance (FR-44): min, max, mean over the candidate's occurrences, plus
`outlier_count`, the number of occurrences deviating from the observed net
income by more than `income_variance_tolerance` as a fraction of it. This is
what surfaces a bonus, a holiday supplement, or a retroactive adjustment
instead of averaging it in silently.

Same-date deposits are collapsed into one occurrence by summing them, on the
same reasoning FR-33a applies to billing events: two splits of one salary
payment are one cycle point, not two.

## Branch

**Branch name:** `task/026-detect-income-sources`
**Switch/create:** `git checkout -b task/026-detect-income-sources`
**Make target:** `make branch-task f=TASK-026`

## Acceptance criteria (Gherkin)

- [ ] Scenario: A monthly salary is recognized
      Given twelve monthly deposits from one payer to a configured income account
      When `detect_income()` runs
      Then one income source is emitted for that account, with that payer and
      twelve occurrences

- [ ] Scenario: The observed figure is the latest, not the mean
      Given eleven monthly deposits of 30000 followed by one of 32000
      When `detect_income()` runs
      Then the observed net income is 32000, its date is the latest deposit's,
      and the reported mean is lower than the observed net income

- [ ] Scenario: A quarterly payer does not qualify
      Given four quarterly deposits from one payer to an income account
      When `detect_income()` runs
      Then no income source is emitted, and the account is reported with that
      candidate's payer, occurrence count, and frequency `quarterly`

- [ ] Scenario: Too few occurrences do not qualify
      Given two monthly deposits from one payer and `INCOME_MIN_OCCURRENCES` of 3
      When `detect_income()` runs
      Then no income source is emitted and the candidate is reported as rejected

- [ ] Scenario: Two qualifying payers are an ambiguity, not a sum
      Given twelve monthly deposits from one payer and twelve from another, both
      to the same income account
      When `detect_income()` runs
      Then no income source is emitted for that account, the account is reported
      with reason `ambiguous` naming both payers, and no summed or averaged
      amount appears anywhere in the result

- [ ] Scenario: A bonus is counted as an outlier, not absorbed
      Given eleven monthly deposits of 30000 and one of 45000, with
      `INCOME_VARIANCE_TOLERANCE` of 0.10
      When `detect_income()` runs
      Then the outlier count is 1 and the maximum is 45000

- [ ] Scenario: Same-day splits are one occurrence
      Given a salary paid as two deposits on the same date from the same payer
      When `detect_income()` runs
      Then those two rows count as one occurrence whose amount is their sum

- [ ] Scenario: Two income accounts are resolved independently
      Given monthly deposits to two configured income accounts from different payers
      When `detect_income()` runs
      Then one income source is emitted per account

- [ ] Scenario: No deposits means no result and no error
      Given an empty deposit list
      When `detect_income()` runs
      Then the result is empty and no exception is raised

- [ ] Hypothesis property test: for any set of deposits, every configured income
      account appears exactly once in the result, either as an income source or
      as an issue, and never as both

- [ ] Hypothesis property test: for any qualifying candidate, the observed net
      income equals the amount of the occurrence with the maximum date, and lies
      within `[amount_min, amount_max]`

- [ ] `make lint && make test` pass with coverage >= the task-start baseline

## Out of scope

- Exporting or displaying the result (TASK-027).
- Distinguishing salary from any other recurring deposit. Recurrence on a
  declared income account is the entire criterion, per SE-05.
- Gross income, tax, or deductions, which are not observable in a deposit
  (SE-06).
- Any split arithmetic over the resulting figures (SE-07).
- Deriving income for a person with no qualifying history. The consumer's
  configuration override covers that case, outside this repository.

## Blockers

None.

## Completion

**Date:** 2026-08-03
**Summary:** Implemented `detect_income()` in a new `src/firefly_bills_analyzer/income.py`
module. Deposits are grouped by `(destination_name, source_name)` per FR-41a
(the deposit-side field inversion, income account/payer), same-date deposits
from the same payer are collapsed into one summed occurrence, and each
group's occurrence count and median interval are classified via
`analyzer.classify_frequency()` (FR-41b). A group qualifies when its
frequency is `monthly` and its occurrence count meets `income_min_occurrences`
(FR-41c). Each configured income account resolves to exactly one
`IncomeSource` when exactly one candidate qualifies (FR-42a), an
`IncomeAccountIssue(reason="no-qualifying-candidate")` listing every rejected
candidate's payer/occurrence count/frequency when none qualify (FR-42b), or
`IncomeAccountIssue(reason="ambiguous")` listing every qualifying payer with
no summed/averaged/picked figure when more than one qualifies (FR-42c).
`observed_net_income`/`observed_date` are taken from the latest occurrence,
never the mean (FR-43); `amount_min`/`amount_max`/`amount_mean` and
`outlier_count` (occurrences deviating from the observed figure by more than
`income_variance_tolerance`) are computed over every occurrence (FR-44).
`_classify_frequency()` in `analyzer.py` was promoted to a public
`classify_frequency()` (with a `_classify_frequency` backward-compatible
alias so existing call sites/tests are unaffected) so `income.py` could
import and reuse it rather than reimplementing the frequency-bucket
boundaries, per the task's dependency on TASK-003. All 13 red tests in
`tests/test_income.py` (committed in a730fed) now pass.

One property-test assertion (`test_observed_net_income_matches_latest_occurrence_within_range`)
was corrected after implementation: it compared `observed_net_income` against
the unrounded Hypothesis-generated float instead of the rounded 2-decimal
amount actually carried by the deposit, causing an intermittent failure. The
assertion now compares against `float(f"{amounts[-1]:.2f}")`; this is a fix to
the test oracle, not a change in what the scenario verifies.

**Files changed:**

- `src/firefly_bills_analyzer/income.py` - created
- `src/firefly_bills_analyzer/analyzer.py` - modified (promoted `_classify_frequency` to public `classify_frequency`, kept a backward-compatible private alias)
- `tests/test_income.py` - modified (corrected rounding in one property-test assertion)
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-026-detect-income-sources.md` - modified (Completion section)

**Branch:** `git checkout task/026-detect-income-sources`
**Stage:** `git add src/firefly_bills_analyzer/income.py src/firefly_bills_analyzer/analyzer.py tests/test_income.py CHANGELOG.md docs/tasks/TASK-026-detect-income-sources.md`
**Commit:** `git commit -m "Detect income sources and resolve observed net income (UC12) (TASK-026)"`
