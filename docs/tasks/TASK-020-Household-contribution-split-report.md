# TASK-020 Household contribution split report (UC11)

## Status

blocked

## Requirements

**Binding:** FR-38a, FR-38b, FR-38c, FR-38d, FR-38e, FR-38f, NFR-13
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-019 (FR-37 `monthly_equivalent`, the figure this report
sums), TASK-016 (`account_filter.py`, whose source-account matching approach
this task mirrors)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As one of two people funding a shared bills account, I want the application to
group its identified recurring costs by which account pays them and tell me
what each of us must transfer to the shared account each month, so that we
land on a deliberate split instead of a historical one that nobody has
recalculated since the last time our incomes changed.

## Description

The application already resolves a source account per pattern (FR-30a,
TASK-011) and, after TASK-019, a monthly equivalent per pattern (FR-37). Those
two fields are everything the split arithmetic needs. What is missing is the
declaration of who owns which account, the incomes, and the arithmetic itself.

New module `src/firefly_bills_analyzer/household.py`. It is a pure consumer of
`list[RecurringPattern]` plus `Config` and performs no I/O toward Firefly III,
which is what makes FR-38f hold by construction rather than by a guard.

### FR-38a: configuration

Add to `Config` (`config.py`):

- `household_members: list[str]`, from `HOUSEHOLD_MEMBERS` (pipe-separated)
- `household_incomes: dict[str, Decimal]`, from `HOUSEHOLD_INCOMES`
  (pipe-separated `name:amount`)
- `household_member_accounts: dict[str, list[str]]`, from
  `HOUSEHOLD_MEMBER_ACCOUNTS` (pipe-separated `name:acct,acct`)
- `household_shared_accounts: list[str]`, from `HOUSEHOLD_SHARED_ACCOUNTS`
  (comma-separated)
- `household_split_method: str`, from `HOUSEHOLD_SPLIT_METHOD`, one of
  `equal-remainder`, `proportional`, `both`, default `both`

The pipe separator is new to this codebase; the existing `_csv()` helper is
not sufficient, since member names and account names may both contain commas
in an account list. Add a `_pipe()` helper alongside it rather than
overloading `_csv()`.

Validation, raising `ConfigError` (which `main()` already reports as a
configuration error per the Common error definition):

1. A name in `HOUSEHOLD_MEMBERS` with no entry in `HOUSEHOLD_INCOMES`
2. A name in `HOUSEHOLD_MEMBERS` with no entry in `HOUSEHOLD_MEMBER_ACCOUNTS`
3. An account name claimed by two different members
4. An account name appearing in both a member list and `HOUSEHOLD_SHARED_ACCOUNTS`
5. A non-numeric or negative income
6. `HOUSEHOLD_SPLIT_METHOD` outside the three permitted values

An empty `HOUSEHOLD_MEMBERS` disables the feature, and the other four
parameters are then not validated.

### FR-38b: bucketing

```python
def bucket_patterns(patterns: list[RecurringPattern], config: Config) -> Buckets
```

Each pattern goes to exactly one bucket, decided by
`pattern.source_account_name`:

- a member's bucket, if that name is in that member's account list
- the shared bucket, if that name is in `household_shared_accounts`
- the unattributed bucket otherwise, including `source_account_name is None`

Patterns with `monthly_equivalent is None` are collected into a fourth,
separate list and excluded from every bucket total. They are reported
(FR-38e), not silently dropped.

`pattern.source_account_varies` is not consulted for bucketing. FR-30a's
resolved mode name is the bucketing key, matching how `account_filter`
already treats `source_name`. A varying pattern is still worth flagging in the
report output, since its attribution is less certain than the others.

### FR-38c / FR-38d: the arithmetic

With `I_i` = member income, `D_i` = member bucket total, `R` = shared bucket
total, `T = sum(D_i) + R`, `n` = member count:

```
equal-remainder:  remainder = (sum(I_i) - T) / n
                  C_i = (I_i - D_i) - remainder

proportional:     C_i = I_i / sum(I_i) * T - D_i
```

Both satisfy `sum(C_i) == R`. Assert that identity in the tests for both
methods; it is the single strongest check that the arithmetic is right.

Use `decimal.Decimal` throughout (NFR-13), converting `monthly_equivalent`
from `float` at the bucket boundary. Round only when formatting output.

A negative `C_i` is a valid result, not an error: it means that member already
pays more than their share directly and is owed a transfer. Do not clamp it.

### FR-38e: report output

```python
def format_report(result: HouseholdSplit, config: Config) -> str
```

Returns a printable block containing, per method:

- per member: income, own-bucket total, computed contribution, resulting
  remainder
- shared bucket total and household total
- an explicit note on any negative contribution, naming the member and the
  amount they are owed
- the unattributed patterns, each with its resolved source account name
- the patterns excluded for having no monthly equivalent, each with its
  resolved source account name and its occurrence count

When `household_split_method` is `both`, the two methods are reported one
after the other so the difference in remainders is directly comparable.

### FR-38f: activation and read-only guarantee

Add `--household-report` to `build_arg_parser()`. In `main()`, run the report
after `analyzer.identify_recurring()` and before the review flow, and return
`0` immediately after printing it without entering `_review()`,
`bills_creator.create_bills()`, or the export path. The report is a reporting
run, not a creation run with an extra section.

`household.py` imports nothing from `firefly_python_api` and holds no client.
Add an import-level test asserting that, so the read-only property is enforced
by a test rather than by convention.

## Branch

**Branch name:** `task/020-household-split-report`
**Switch/create:** `git checkout -b task/020-household-split-report`
**Make target:** `make branch-task f=TASK-020`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Contributions sum to the shared bucket total under equal-remainder
      Given two members with declared incomes, own-account patterns, and a shared account with its own patterns
      When the split is computed with `HOUSEHOLD_SPLIT_METHOD=equal-remainder`
      Then the members' contributions sum to the shared bucket total

- [ ] Scenario: Contributions sum to the shared bucket total under proportional
      Given the same household
      When the split is computed with `HOUSEHOLD_SPLIT_METHOD=proportional`
      Then the members' contributions sum to the shared bucket total

- [ ] Scenario: Equal-remainder leaves both members with the same remainder
      Given two members with different incomes
      When the split is computed with `HOUSEHOLD_SPLIT_METHOD=equal-remainder`
      Then each member's income minus own-bucket total minus contribution equals the same remainder value

- [ ] Scenario: Proportional leaves both members contributing the same share of income
      Given two members with different incomes
      When the split is computed with `HOUSEHOLD_SPLIT_METHOD=proportional`
      Then each member's own-bucket total plus contribution, divided by that member's income, equals the same share value

- [ ] Scenario: A member who already pays more than their share gets a negative contribution
      Given a member whose own-bucket total alone exceeds their share of the household total
      When the split is computed under either method
      Then that member's contribution is reported as a negative value with a note that they are owed a transfer, and is not clamped to zero

- [ ] Scenario: A pattern on an undeclared account is reported, not absorbed
      Given a pattern whose resolved source account matches no member account and no shared account
      When the split is computed
      Then that pattern appears in the unattributed list with its source account name, and its monthly equivalent is absent from every bucket total

- [ ] Scenario: An irregular pattern is reported, not absorbed
      Given a pattern whose `monthly_equivalent` is `None` and whose source account is the shared account
      When the split is computed
      Then that pattern appears in the excluded list with its source account name and occurrence count, and does not contribute to the shared bucket total

- [ ] Scenario: A pattern with no resolved source account is unattributed
      Given a pattern whose `source_account_name` is `None`
      When the split is computed
      Then that pattern appears in the unattributed list

- [ ] Scenario: An account claimed by two members is rejected at configuration time
      Given `HOUSEHOLD_MEMBER_ACCOUNTS` listing the same account name under two different members
      When `Config.from_env()` runs
      Then a `ConfigError` is raised naming the account and both members

- [ ] Scenario: An account that is both a member account and a shared account is rejected
      Given an account name present in both `HOUSEHOLD_MEMBER_ACCOUNTS` and `HOUSEHOLD_SHARED_ACCOUNTS`
      When `Config.from_env()` runs
      Then a `ConfigError` is raised naming the account

- [ ] Scenario: A member without a declared income is rejected
      Given a name in `HOUSEHOLD_MEMBERS` with no matching entry in `HOUSEHOLD_INCOMES`
      When `Config.from_env()` runs
      Then a `ConfigError` is raised naming the member

- [ ] Scenario: The report writes nothing to Firefly III
      Given a run with `--household-report` and a mocked `FireflyClient`
      When `main()` completes
      Then no bill-creation call is made, `_review()` is not entered, no export file is written, and `main()` returns 0
      (holds independently of `DRY_RUN`, asserted with `DRY_RUN` both set and unset)

- [ ] `HOUSEHOLD_MEMBERS` empty disables the feature: `--household-report` reports that no household is configured and returns a non-zero exit code, and a run without the flag is unaffected

- [ ] `household.py` imports nothing from `firefly_python_api`, asserted by a test over the module's imports

- [ ] Every monetary figure is computed as `Decimal`, with rounding applied only in `format_report()` (NFR-13)

- [ ] Hypothesis property test: for any set of 2 or more members with positive incomes and non-negative bucket totals, `sum(C_i) == R` holds exactly under both methods

- [ ] Hypothesis property test: under `equal-remainder`, all members' remainders are equal within `Decimal` exactness

- [ ] `Config(...)` call sites across the existing test suite are updated for the new required fields, mirroring what TASK-016 and TASK-017 did

- [ ] `make lint && make test` pass with coverage >= the TASK-019 baseline

## Out of scope

- Creating the computed transfers, or any recurring transaction, in Firefly III
  (Scope Exclusions)
- Reading income from Firefly III deposit transactions. `fetcher.py` fetches
  withdrawals only (UC1), and widening that is a separate use case
- More than one shared account tier (e.g. a shared account funded by another
  shared account). `HOUSEHOLD_SHARED_ACCOUNTS` accepts several names but they
  all sum into one bucket
- Any web UI surface for UC11, contingent on Open Item #5
- Recommending a split method. FR-38e reports both under the default
  `HOUSEHOLD_SPLIT_METHOD=both` and the choice stays with the user
- Historical or per-month reporting. The report describes the current
  configured steady state, not a time series

## Blockers

- [ ] Open Item #10 (scope: does UC11 belong in this repository, or in a
      separate consumer of the FR-08 export?) is unresolved. FR-38a through
      FR-38f each carry `[SCOPE TBD]` pending it. This task must not be
      implemented until the owner resolves or waives the item. TASK-019 is
      not blocked by this and can proceed independently.

## Completion

**Date:** YYYY-MM-DD
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/household.py` — new
- `tests/test_household.py` — new
- `src/firefly_bills_analyzer/config.py` — modified
- `src/firefly_bills_analyzer/__main__.py` — modified
- `tests/test_config.py` — modified
- `tests/test_main.py` — modified
- `tests/test_analyzer.py` — modified (`_make_config()` fields)
- `tests/test_bills_creator.py` — modified (`_make_config()` fields)
- `tests/test_fetcher.py` — modified (`_make_config()` fields)
- `tests/test_category_filter.py` — modified (`_make_config()` fields)
- `tests/test_account_filter.py` — modified (`_make_config()` fields)
- `tests/test_payee_filter.py` — modified (`_make_config()` fields)
- `tests/benchmark_analyzer.py` — modified (`_make_config()` fields)
- `.env.example` — modified
- `docs/REQUIREMENTS_new.md` — modified prior to implementation
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-020-household-split-report.md` — this file

**Branch:** `git checkout task/020-household-split-report`
**Stage:** `git add src/firefly_bills_analyzer/household.py tests/test_household.py src/firefly_bills_analyzer/config.py src/firefly_bills_analyzer/__main__.py tests/test_config.py tests/test_main.py tests/test_analyzer.py tests/test_bills_creator.py tests/test_fetcher.py tests/test_category_filter.py tests/test_account_filter.py tests/test_payee_filter.py tests/benchmark_analyzer.py .env.example docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-020-household-split-report.md`
**Commit:** `git commit -m "feat: report household contribution split per member from recurring pattern monthly equivalents (UC11)"`