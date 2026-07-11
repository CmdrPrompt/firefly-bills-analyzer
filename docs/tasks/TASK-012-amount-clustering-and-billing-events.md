# TASK-012 Amount clustering and billing event collapse (UC2)

## Status

todo

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

### FR-32a/b: Amount clustering

Add a new helper function to split a payee's transaction group into amount clusters:

```python
def _split_into_amount_clusters(
    transactions: list[TransactionRead], 
    tolerance: float
) -> list[list[TransactionRead]]:
    """
    Split transactions into amount clusters based on tolerance-based gap detection.
    
    Sort by amount ascending. Start a new cluster whenever the absolute difference
    between two consecutive amounts exceeds tolerance × min(amount_i, amount_j).
    Each cluster is a contiguous list of sorted transactions. Return the list of
    clusters, preserving the original transaction objects (not copies).
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

- [ ] Scenario: Single amount cluster (happy path, unchanged behavior)
      Given a payee with transactions whose amounts differ by less than the tolerance
      When `identify_recurring()` processes the payee group
      Then the group is classified as a single amount cluster
      And occurrence/interval/amount statistics are computed as before (unchanged from pre-FR-32 behavior)
      And `amount_for_name` is `None` (no disambiguation needed)

- [ ] Scenario: Split into multiple amount clusters
      Given a payee with two groups of amounts: [10.00, 11.00] and [25.00, 26.00]
      And `AMOUNT_CLUSTER_TOLERANCE = 0.15` (default)
      When `identify_recurring()` processes the payee group
      Then the group is split into two clusters (gap between 11.00 and 25.00 exceeds 15% of 11.00)
      And each cluster is analyzed independently for occurrence/frequency/confidence

- [ ] Scenario: Multiple clusters with independent occurrence thresholds
      Given a payee with two amount clusters, one with 3 occurrences and one with 2
      And `MIN_OCCURRENCES = 2` (default)
      When `identify_recurring()` processes the payee
      Then both clusters meet the occurrence threshold individually
      And two separate `RecurringPattern` entries are returned, one per cluster

- [ ] Scenario: Amount cluster disambiguates multi-cluster patterns
      Given the same payee producing two qualifying clusters with amounts ~10 and ~25
      When `identify_recurring()` processes the payee
      Then cluster 1's pattern has `amount_for_name = "10.00"`
      And cluster 2's pattern has `amount_for_name = "25.00"`
      And `_bill_name()` appends these to the bill names (e.g., "Payee 10.00" and "Payee 25.00")

- [ ] Scenario: Collapse same-date transactions into a single billing event
      Given a cluster with two transactions on 2026-07-11 (amounts 15.00 and 15.00)
      When `_collapse_into_billing_events()` processes the cluster
      Then a single billing event for 2026-07-11 is returned with amount = 30.00
      And the count field is 2 (informational)

- [ ] Scenario: Multiple same-date groups in a cluster
      Given a cluster with:
        - Two transactions on 2026-07-11 (15.00 each)
        - One transaction on 2026-07-18 (15.00)
        - Two transactions on 2026-07-25 (15.00 each)
      When `_collapse_into_billing_events()` processes the cluster
      Then three billing events are returned:
        - 2026-07-11 with amount 30.00
        - 2026-07-18 with amount 15.00
        - 2026-07-25 with amount 30.00

- [ ] Scenario: Interval calculation uses billing events, not transactions
      Given a cluster with transactions:
        - 2026-07-01 (10.00)
        - 2026-07-01 (10.00) [same day, will collapse to 20.00]
        - 2026-08-01 (10.00)
        - 2026-09-01 (10.00)
      When `identify_recurring()` processes the cluster
      Then the occurrence count is 3 (three billing events)
      And the interval calculation uses dates [2026-07-01, 2026-08-01, 2026-09-01]
      (not the pre-collapse date list [2026-07-01, 2026-07-01, 2026-08-01, 2026-09-01])
      And the median interval is correctly computed as 31 days (Aug→Sep, not collapsed to 0)

- [ ] Scenario: Source account resolution uses pre-collapse transactions (FR-30a unaffected)
      Given a cluster whose transactions collapse to 3 billing events
      When `identify_recurring()` resolves the source account for the pattern
      Then source account resolution examines all pre-collapse transactions, not the 3 billing events
      And `source_account_name` / `source_account_varies` reflect the actual transaction distribution

- [ ] Scenario: Amount clustering is tolerance-based and consistent
      Hypothesis property test: for any list of transaction amounts and a tolerance T,
      verify that `_split_into_amount_clusters()` produces clusters such that:
        - Every two amounts within the same cluster have a relative gap ≤ T
        - Every two amounts from different clusters have a relative gap > T
        - The sorted order is preserved (clusters are contiguous in the sorted list)
        - Clustering is deterministic (same input always yields the same clusters)

- [ ] Scenario: Billing event collapse is deterministic
      Hypothesis property test: for any transaction list with dates and amounts,
      verify that `_collapse_into_billing_events()` produces events such that:
        - All transactions with the same date are summed into one event
        - Events are sorted by date ascending
        - The sum of all event amounts equals the sum of all transaction amounts
        - Collapsing is deterministic

- [ ] Scenario: Multi-cluster pattern integration with category naming (FR-13b + FR-32c)
      Given a payee with two qualifying amount clusters, each with a different majority category
      When `_bill_name()` formats the bills for both clusters
      Then cluster 1's bill name is "{payee} ({category1}) {amount1}"
      And cluster 2's bill name is "{payee} ({category2}) {amount2}"
      And the two names do not collide

- [ ] Scenario: Single-cluster pattern has amount_for_name = None (no disambiguation)
      Given a payee with a single amount cluster
      When `identify_recurring()` processes the payee
      Then the pattern's `amount_for_name` is `None`
      And `_bill_name()` does not append any amount (category, if any, is still appended)

- [ ] Scenario: Below-threshold cluster does not produce a pattern
      Given a payee with two amount clusters, one with 3 occurrences and one with 1
      And `MIN_OCCURRENCES = 2` (default)
      When `identify_recurring()` processes the payee
      Then only one `RecurringPattern` is returned (the 3-occurrence cluster)
      And `amount_for_name` for that pattern is `None` (not multi-cluster)

- [ ] Scenario: Amount cluster tolerance configuration
      Given `AMOUNT_CLUSTER_TOLERANCE` set to 0.20 (20% instead of default 15%)
      When `identify_recurring()` processes a payee with amounts [10.00, 12.00, 15.00]
      Then the clustering behavior changes (e.g., 12.00 may move to a different cluster)
      And the gap calculation uses the configured tolerance value

- [ ] `make lint && make test` pass with coverage >= baseline

## Out of scope

- Configurable thresholds for billing event collapse: collapse is deterministic (all same-date transactions are summed)
- Visualization or reporting of amount clusters: clusters are an internal processing step
- Web UI columns for billing events or amount clusters: deferred with Open Item #5
- Changes to FR-30a (source account resolution): unaffected by this task, continues to operate on raw transactions

## Blockers

None

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
