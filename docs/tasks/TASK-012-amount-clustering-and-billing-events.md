# TASK-012 Amount clustering and billing event collapse (UC2)

## Status

done

## Requirements

**Binding:** FR-32a, FR-32b, FR-32c, FR-33a
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-003 (RecurringPattern exists), TASK-004 (bills_creator exists), TASK-008 (category naming), TASK-011 (source account resolution)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As an analyst, I want transactions grouped by amount clusters within each payee (so that multiple distinct subscriptions billed through the same merchant can be identified separately) and same-day charges within a cluster collapsed into a single billing event (so that household-member charges or multiple invoices on the same day are treated as one combined outflow), so that frequency classification and confidence scoring operate on meaningful units, not on inflated variance or flattened intervals.

## Description

Extend the UC2 analyzer to identify distinct amount clusters within each payee group (FR-32a/b), collapse same-date transactions within each cluster into billing events (FR-33a), compute occurrence/frequency/confidence statistics over billing events rather than raw transactions (while source account resolution continues on raw transactions per FR-30a), and disambiguate multi-cluster bill names by appending each cluster's representative amount (FR-32c).

### FR-32a/b: Amount clustering (revised mid-task — see below)

**Revision note:** the original design below (pure amount-gap clustering across
all of a payee's transactions) was implemented first, then revised after
owner review against real transaction data surfaced a regression: "EON" (a
monthly electricity bill whose amount legitimately fluctuates 661–4426 kr by
season and consumption, but never has two transactions on the same date) was
being fragmented into several weak sub-clusters, because a pure amount-gap
tolerance cannot distinguish a genuinely variable single bill from a payee
that bundles multiple simultaneous charges (e.g. "Apple"'s two co-occurring
subscriptions). The requirements document (`docs/REQUIREMENTS_new.md`
v0.2.15) was updated accordingly and is binding; the implementation below
reflects the revised, shipped behavior.

Add a new helper function to split a payee's transaction group into amount
clusters, based on same-date co-occurrence of differing amounts rather than
amount variance alone:

```python
def _split_into_amount_clusters(
    transactions: list[TransactionRead],
    tolerance: float,
) -> list[list[TransactionRead]]:
    """
    Split a payee's transactions into amount clusters (FR-32a).

    1. Group transactions by date. A date with two or more transactions of
       differing amounts is a co-occurrence date, revealing genuinely
       parallel simultaneous charges (e.g. two subscriptions billed through
       the same merchant).
    2. If the group has no co-occurrence date at all, return the whole group
       as a single cluster, regardless of how much its amount varies across
       different dates (this is what keeps a single variable bill, e.g. a
       metered utility, from being fragmented).
    3. Otherwise, cluster the amounts observed at co-occurrence dates via a
       tolerance-based gap split (`_tolerance_gap_split`: sort ascending,
       start a new group whenever the gap to the previous amount exceeds
       `tolerance` times the smaller of the two), then assign every
       transaction in the group -- including ones not on a co-occurrence
       date -- to whichever resulting cluster's mean amount is numerically
       closest to its own.
    """
```

In `config.py`, add a new field:

- `amount_cluster_tolerance: float` (read from `AMOUNT_CLUSTER_TOLERANCE` env var, default `0.15`)

### FR-33a: Billing event collapse

Add a new helper function to collapse same-date transactions within a cluster:

```python
def _collapse_into_billing_events(
    transactions: list[TransactionRead]
) -> list[dict[str, Any]]:
    """
    Collapse transactions that share the exact same date into single billing events.
    
    For each unique date in the cluster (sorted ascending), if multiple transactions
    share that date, sum their amounts. Return a list of "billing event" dicts:
    - "date": the date (str, YYYY-MM-DD)
    - "amount": the sum of all transaction amounts on that date (float)
    - "count": the number of transactions summed (int, informational)
    
    Billing events are sorted by date ascending and represent the collapsed timeline
    for subsequent interval/frequency calculations. Source account resolution is NOT
    affected; it continues to operate on the pre-collapse transaction list.
    """
```

### Integration into identify_recurring()

In `analyzer.identify_recurring()`, after grouping by payee (UC2 step 1) and before computing statistics (UC2 steps 4–7):

1. Split the payee group into amount clusters (UC2 step 2, FR-32a)
2. For each amount cluster:
   a. Collapse same-date transactions into billing events (UC2 step 3, FR-33a)
   b. Compute occurrence count, median interval, and amount statistics over the
      billing events (not the pre-collapse transactions)
   c. Resolve source account over the pre-collapse transactions (FR-30a, unaffected)
3. Store a flag on `RecurringPattern` indicating whether this cluster is one of
   multiple for the same payee (used by FR-32c; see below)

### FR-32c: Bill name disambiguation via amount

When a payee produces multiple amount clusters that each independently qualify as
recurring patterns (i.e., both meet the `min_occurrences` threshold after
clustering/collapsing), add a new field to `RecurringPattern`:

- `amount_for_name: str | None` — the formatted mean amount (as a string with 2
  decimals, e.g., "29.99") if this pattern is one of 2+ clusters for the same
  payee and qualifies as recurring on its own; otherwise `None`

In `bills_creator._bill_name()`, after constructing the name with category (if any,
per TASK-008), append the `amount_for_name` if it is not `None`:

```python
def _bill_name(pattern: RecurringPattern) -> str:
    """Build bill name per FR-13b (category) and FR-32c (amount for disambiguation)."""
    name = pattern.destination_name
    if pattern.category_name is not None:
        name = f"{name} ({pattern.category_name})"
    if pattern.amount_for_name is not None:
        name = f"{name} {pattern.amount_for_name}"
    return name
```

This ensures that distinct amount clusters under the same payee do not collide
under FR-05a's name-only duplicate check.

## Branch

**Branch name:** `task/012-amount-clustering-and-billing-events`
**Switch/create:** `git checkout -b task/012-amount-clustering-and-billing-events`
**Make target:** `make branch-task f=TASK-012`

## Acceptance criteria

Revised to match the shipped, co-occurrence-based FR-32a (see revision note
above). All scenarios below are implemented in `tests/test_analyzer.py`
and/or `tests/test_bills_creator.py`.

- [x] Scenario: No co-occurrence date — payee is never split, however much its amount varies
      Given a payee whose transactions never show two differing amounts on the same date (e.g. "EON", a metered electricity bill, 661.00-4426.00 kr across 16 monthly dates)
      When `identify_recurring()` processes the payee group
      Then the group is classified as a single amount cluster
      And all 16 transactions are counted as one pattern with `frequency = "monthly"`
      And `amount_for_name` is `None` (no disambiguation needed)
      (`test_split_into_amount_clusters_no_split_without_co_occurrence`, `test_widely_varying_single_amount_payee_is_not_fragmented`)

- [x] Scenario: Co-occurring differing amounts split into multiple clusters
      Given a payee with a date where two differing amounts occur together (e.g. 10.00 and 25.00 on the same day), plus further solo-date occurrences near each amount
      And `AMOUNT_CLUSTER_TOLERANCE = 0.15` (default)
      When `identify_recurring()` processes the payee group
      Then the co-occurring amounts seed two clusters, and every other transaction is assigned to whichever cluster's mean is closest
      And each cluster is analyzed independently for occurrence/frequency/confidence
      (`test_split_into_amount_clusters_splits_on_co_occurring_amounts`, `test_payee_splits_into_two_independent_patterns_by_amount`)

- [x] Scenario: Multiple clusters with independent occurrence thresholds
      Given a payee with two amount clusters, one with 3 occurrences and one with 2
      And `MIN_OCCURRENCES = 2` (default)
      When `identify_recurring()` processes the payee
      Then both clusters meet the occurrence threshold individually
      And two separate `RecurringPattern` entries are returned, one per cluster
      (`test_amount_cluster_tolerance_affects_clustering`)

- [x] Scenario: Amount cluster disambiguates multi-cluster patterns
      Given the same payee producing two qualifying clusters with amounts ~10 and ~25
      When `identify_recurring()` processes the payee
      Then cluster 1's pattern has `amount_for_name = "10.00"`
      And cluster 2's pattern has `amount_for_name = "25.00"`
      And `_bill_name()` appends these to the bill names (e.g., "Netflix 10.00" and "Netflix 25.00")
      (`test_amount_for_name_set_when_multiple_clusters_qualify`, `TestAmountClusterDisambiguation` in `test_bills_creator.py`)

- [x] Scenario: Collapse same-date transactions into a single billing event
      Given a cluster with two transactions on 2026-07-11 (amounts 15.00 and 15.00)
      When `_collapse_into_billing_events()` processes the cluster
      Then a single billing event for 2026-07-11 is returned with amount = 30.00
      And the count field is 2 (informational)
      (`test_collapse_into_billing_events_sums_same_date_transactions`)

- [x] Scenario: Multiple same-date groups in a cluster
      Given a cluster with two transactions on 2026-07-11 (15.00 each), one on 2026-07-18 (15.00), and two on 2026-07-25 (15.00 each)
      When `_collapse_into_billing_events()` processes the cluster
      Then three billing events are returned: 2026-07-11 (30.00), 2026-07-18 (15.00), 2026-07-25 (30.00)
      (`test_collapse_into_billing_events_multiple_dates`)

- [x] Scenario: Interval calculation uses billing events, not transactions
      Given the same monthly fee billed twice on the same day every month (e.g. "SEB", 276.00 kr x2 per month for 6 months)
      When `identify_recurring()` processes the cluster
      Then the occurrence count is 6 (billing events, not 12 raw transactions)
      And the median interval is correctly computed as ~31 days and classified `monthly` (not collapsed to 0 / `irregular`)
      (`test_same_day_transactions_collapse_for_interval_calculation`)

- [x] Scenario: Source account resolution uses pre-collapse transactions (FR-30a unaffected)
      Given a cluster whose transactions collapse to 2 billing events, drawn from 2 distinct source accounts across the 4 pre-collapse transactions
      When `identify_recurring()` resolves the source account for the pattern
      Then source account resolution examines all 4 pre-collapse transactions, not the 2 billing events
      And `source_account_name` / `source_account_varies` reflect the actual transaction distribution
      (`test_source_account_resolution_uses_pre_collapse_transactions`)

- [x] Scenario: Amount clustering is deterministic and preserves all transactions
      Hypothesis property test: for any list of (date offset, amount) pairs and a tolerance T,
      verify that `_split_into_amount_clusters()` is deterministic, keeps every transaction exactly once, and produces no empty clusters
      (`test_split_into_amount_clusters_preserves_all_transactions_and_is_deterministic`)

- [x] Scenario: Billing event collapse is deterministic
      Hypothesis property test: for any transaction list with dates and amounts,
      verify that `_collapse_into_billing_events()` sums same-date transactions, sorts events by date, preserves the total amount, and is deterministic
      (`test_collapse_into_billing_events_preserves_total_and_is_deterministic`)

- [x] Scenario: Multi-cluster pattern integration with category naming (FR-13b + FR-32c)
      Given a payee with two qualifying amount clusters, each with a category and an `amount_for_name`
      When `_bill_name()` formats the bills for both clusters
      Then each bill name is `"{payee} ({category}) {amount}"`, and the two names do not collide
      (`TestAmountClusterDisambiguation.test_amount_for_name_appended_after_category`, `test_two_clusters_for_same_payee_do_not_collide`)

- [x] Scenario: Single-cluster pattern has amount_for_name = None (no disambiguation)
      Given a payee with a single amount cluster
      When `identify_recurring()` processes the payee
      Then the pattern's `amount_for_name` is `None`
      And `_bill_name()` does not append any amount (category, if any, is still appended)
      (`test_single_amount_cluster_has_no_disambiguation`, `TestAmountClusterDisambiguation.test_no_amount_for_name_leaves_name_unchanged`)

- [x] Scenario: Below-threshold cluster does not produce a pattern
      Given a payee where a co-occurrence seed cluster ends up with only 1 member after nearest-mean assignment, while the other cluster has 3
      And `MIN_OCCURRENCES = 2` (default)
      When `identify_recurring()` processes the payee
      Then only one `RecurringPattern` is returned (the 3-occurrence cluster)
      And `amount_for_name` for that pattern is `None` (not multi-cluster)
      (`test_below_threshold_cluster_does_not_produce_pattern_or_disambiguation`)

- [x] Scenario: Amount cluster tolerance configuration
      Given `AMOUNT_CLUSTER_TOLERANCE` set to 0.10 vs. 0.30 for the same co-occurring amounts (10.00 and 12.00)
      When `identify_recurring()` processes the payee
      Then the narrower tolerance splits into 2 patterns and the wider tolerance merges into 1
      (`test_amount_cluster_tolerance_affects_clustering`, `test_split_into_amount_clusters_tolerance_is_configurable`)

- [x] `make lint && make test` pass with coverage >= baseline (123 tests passed, 100% coverage on `analyzer.py` and `bills_creator.py`)

## Out of scope

- Configurable thresholds for billing event collapse: collapse is deterministic (all same-date transactions are summed)
- Visualization or reporting of amount clusters: clusters are an internal processing step
- Web UI columns for billing events or amount clusters: deferred with Open Item #5
- Changes to FR-30a (source account resolution): unaffected by this task, continues to operate on raw transactions

## Blockers

None

## Completion

**Date:** 2026-07-11
**Summary:** `analyzer.identify_recurring()` now splits each payee group into
amount clusters (FR-32a/b) before computing statistics, and collapses
same-date transactions within each cluster into billing events (FR-33a).
Amount clustering was implemented in two passes: an initial pure amount-gap
tolerance split (matching the original task description), then revised
after owner review against real transaction data showed it fragmenting
"EON" (a monthly electricity bill whose amount legitimately varies
661-4426 kr by season/consumption, never two transactions on the same
date) into several weak sub-clusters. The shipped design instead clusters
only on same-date co-occurrence of differing amounts — a genuine signal of
parallel simultaneous charges (e.g. "Apple"'s two subscriptions, or
"Stockholm Vatten"'s water/sewage + waste-collection sub-invoices) — and
assigns every other transaction to the nearest resulting cluster by mean
amount; a payee with no co-occurrence date is never split. This also fixed
an incidental bug in the original design: two "Stockholm Vatten" outlier
dates that matched neither established cluster tightly enough were forming
a spurious third `yearly` pattern; under nearest-mean assignment they now
correctly join the closer real cluster.
`RecurringPattern` gained `amount_for_name: str | None` (FR-32c), set to
the cluster's mean amount when a payee produces more than one qualifying
cluster; `bills_creator._bill_name()` appends it after the category suffix
so distinct clusters never collide under FR-05a's name-only duplicate
check. `config.py` gained `amount_cluster_tolerance` (`AMOUNT_CLUSTER_TOLERANCE`,
default `0.15`). Verified against the owner's real Firefly III instance:
EON returned to one 16-occurrence `monthly` pattern (87.7% confidence,
matching pre-task behavior); Stockholm Vatten now produces two clean
clusters instead of the original naive design's three (one spurious);
Apple and Media och Streaming correctly split into their constituent
subscriptions; Skandinaviska Enskilda Banken (FR-33a) reclassified from
`irregular`/60% to `monthly`/97.5% via billing-event collapse.
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified (`_tolerance_gap_split`,
  `_split_into_amount_clusters`, `_collapse_into_billing_events`,
  `_qualifying_clusters`, `_build_pattern` helpers; `amount_for_name` field
  on `RecurringPattern`; `identify_recurring()` rewired through clustering
  and billing-event collapse)
- `src/firefly_bills_analyzer/bills_creator.py` — modified (`_bill_name()`
  appends `amount_for_name`)
- `src/firefly_bills_analyzer/config.py` — modified (`amount_cluster_tolerance`
  field and `AMOUNT_CLUSTER_TOLERANCE` env var)
- `tests/test_analyzer.py` — modified (amount-clustering and billing-event
  unit/property tests, `identify_recurring()` integration tests, updated
  `_make_config` helper and one pre-existing test's fixture amounts)
- `tests/test_bills_creator.py` — modified (`_pattern()` helper gains
  `amount_for_name`; `TestAmountClusterDisambiguation` test class)
- `tests/test_category_filter.py`, `tests/test_config.py`,
  `tests/test_fetcher.py`, `tests/benchmark_analyzer.py` — modified
  (`_make_config`/`Config(...)` helpers updated for the new required field)
- `docs/REQUIREMENTS_new.md` — modified (spec 0.2.14 added FR-32a/b/c and
  FR-33a; spec 0.2.15 revised FR-32a to the co-occurrence-based design)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-012-amount-clustering-and-billing-events.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/012-amount-clustering-and-billing-events`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py src/firefly_bills_analyzer/bills_creator.py src/firefly_bills_analyzer/config.py tests/test_analyzer.py tests/test_bills_creator.py tests/test_category_filter.py tests/test_config.py tests/test_fetcher.py tests/benchmark_analyzer.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/TASK-012-amount-clustering-and-billing-events.md docs/tasks/README.md`
**Commit:** `git commit -m "Split payees into amount clusters and collapse same-date billing events (TASK-012)"`
