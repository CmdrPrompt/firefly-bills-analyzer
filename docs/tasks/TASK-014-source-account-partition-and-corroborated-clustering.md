# TASK-014 Source-account partitioning and corroborated amount clustering (UC2)

## Status

done

## Requirements

**Binding:** FR-32a (revised), FR-32d (new)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-012 (amount clustering and billing event collapse)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As an analyst, I want a payee's transactions partitioned by source account before amount clustering, and I want a same-date co-occurrence split to only take effect once it is corroborated by a repeating pattern across more than one date, so that a payee whose transactions genuinely span two different financial roles (e.g. a fixed transfer funding a spending account, and that spending account's own variable purchases) isn't amount-clustered together, and so that a single day's coincidental double purchase from a continuously variable spending account doesn't fragment an otherwise coherent recurring pattern into many spurious low-confidence entries.

## Description

Owner review of a real analysis report generated after TASK-012 found payee
"ICA" fragmented into 15 rows. Root cause, diagnosed against the real report:

1. "ICA"'s transactions span two source accounts — a fixed 12 000 kr monthly
   transfer from `SEB Räkningskonto` (funding a dedicated spending account),
   and the actual day-to-day grocery purchases withdrawn from
   `ICA-banken Matkonto`. FR-32a's clustering ran across both source
   accounts together.
2. Even within the `ICA-banken Matkonto` subgroup alone, occasional same-day
   double purchases (differing amounts) were enough to trigger FR-32a's
   tolerance-based split. Because grocery amounts are continuously
   distributed and almost never repeat exactly, the tolerance-gap chained
   across the full amount range and fragmented the subgroup into a dozen-plus
   low-confidence sub-clusters — the same failure mode the 0.2.15 EON fix
   addressed, but reachable even when the *payee's overall* variance isn't
   the trigger; a single coincidental co-occurrence date was enough.

Two fixes, both confirmed with the owner (spec `docs/REQUIREMENTS_new.md`
v0.2.17):

### FR-32d: Partition by source account before amount clustering

Add a new helper function:

```python
def _partition_by_source_account(
    transactions: list[TransactionRead],
) -> list[list[TransactionRead]]:
    """Partition a payee group by source account (FR-32d).

    Transactions sharing the same `source_name` value form one subgroup;
    transactions with no `source_name` form their own subgroup. Distinct
    financial roles that happen to share a payee name -- e.g. a fixed
    transfer funding a spending account, versus that spending account's own
    purchases -- are typically withdrawn through different source accounts,
    so partitioning here first keeps them from being amount-clustered
    together.
    """
```

Call this in `_qualifying_clusters()`, before `_split_into_amount_clusters()`,
so each resulting subgroup is amount-clustered independently. A side effect:
since every transaction within a resulting cluster now shares the same
`source_name` (or all lack one), `_resolve_source_account()`'s
`source_account_varies` will be `False` for the large majority of patterns
going forward -- this is expected and correct, not a regression.

### FR-32a revision: corroborated co-occurrence

Revise `_split_into_amount_clusters()` so a split is only accepted when
corroborated:

```python
def _split_into_amount_clusters(
    transactions: list[TransactionRead],
    tolerance: float,
) -> list[list[TransactionRead]]:
    """
    Split a source-account subgroup's transactions into amount clusters
    (FR-32a), only when corroborated.

    1. Group transactions by date; identify co-occurrence dates (two or more
       differing amounts on the same date).
    2. If there is no co-occurrence date, return the whole group as a single
       cluster (unchanged from TASK-012).
    3. Otherwise, seed candidate clusters from the co-occurring amounts via
       `_tolerance_gap_split`, and for each co-occurrence date compute its
       "signature": the set of candidate-cluster indices its own amounts map
       to (nearest cluster mean).
    4. The split is corroborated only if some signature spanning two or more
       candidate clusters is shared by two or more distinct co-occurrence
       dates. If not corroborated, return the whole group as a single
       cluster -- a single day's coincidental co-occurrence is not enough
       evidence of a genuine second recurring charge.
    5. If corroborated, assign every transaction in the group (including
       those not on a co-occurrence date) to whichever candidate cluster's
       mean is numerically closest to its own amount, exactly as before.
    """
```

No new configuration: the "2 or more distinct dates" corroboration threshold
is fixed, not read from an environment variable (FR-32b's
`AMOUNT_CLUSTER_TOLERANCE` is unaffected and still applies to the gap-split
step).

### Test revisions required (TASK-012 regression)

Several TASK-012 tests encoded the pre-corroboration behavior (a single
co-occurrence date splitting a group) and must be updated to add a second,
matching-signature co-occurrence date, or to assert the new "absorbed, not
split" outcome where a single co-occurrence date has no repeat. This is the
same kind of revision TASK-012 itself made to pre-FR-32 tests when the EON
fix landed; see the completion notes below for the full list.

## Branch

**Branch name:** `task/014-source-account-partition-and-corroborated-clustering`
**Switch/create:** `git checkout -b task/014-source-account-partition-and-corroborated-clustering`
**Make target:** `make branch-task f=TASK-014`

## Acceptance criteria

- [x] Scenario: Payee partitioned by source account before amount clustering
      Given a payee "ICA" with a fixed 12000.00 kr transfer from "SEB Räkningskonto" (4 occurrences) and variable purchases from "ICA-banken Matkonto" (multiple occurrences, including one incidental same-day double purchase)
      When `identify_recurring()` processes the payee group
      Then two separate patterns are returned, one per source account
      And the `ICA-banken Matkonto` pattern is not further fragmented by the incidental same-day double purchase
      (`test_source_account_partition_keeps_transfer_and_spending_as_separate_patterns`)

- [x] Scenario: Transactions with no source name form their own subgroup
      Given a payee with some transactions carrying a `source_name` and others with `source_name = None`
      When `_partition_by_source_account()` processes the group
      Then transactions with a shared `source_name` are grouped together, and all `None`-source transactions form one additional subgroup
      (`test_partition_by_source_account_groups_by_source_name`, `test_partition_by_source_account_groups_missing_source_name_together`, `test_partition_by_source_account_preserves_all_transactions`)

- [x] Scenario: A single uncorroborated co-occurrence date does not split a cluster
      Given a payee with one co-occurrence date (two differing amounts) and no other date sharing that same cluster-pair signature
      When `_split_into_amount_clusters()` processes the group
      Then the whole group remains a single amount cluster
      (`test_split_into_amount_clusters_single_co_occurrence_date_is_not_corroborated`, `test_single_uncorroborated_co_occurrence_is_absorbed_not_split`)

- [x] Scenario: A repeating co-occurrence signature corroborates a split
      Given a payee with two distinct dates whose co-occurring amounts map to the same pair of candidate clusters
      When `_split_into_amount_clusters()` processes the group
      Then the group splits into the corroborated clusters, and every other transaction is assigned by nearest cluster mean, as in TASK-012
      (`test_split_into_amount_clusters_splits_on_co_occurring_amounts`, `test_split_into_amount_clusters_corroborated_split_keeps_small_cluster_distinct`)

- [x] Scenario: Non-matching co-occurrence signatures do not corroborate each other
      Given a payee with two co-occurrence dates whose amounts map to different, non-overlapping pairs of candidate clusters
      When `_split_into_amount_clusters()` processes the group
      Then the whole group remains a single amount cluster (no signature repeats)
      (`test_split_into_amount_clusters_non_matching_signatures_do_not_corroborate`)

- [x] Scenario: A corroborated cluster can still fail `min_occurrences`
      Given a payee whose corroborated split produces one well-populated cluster and one cluster below `MIN_OCCURRENCES`
      When `identify_recurring()` processes the payee
      Then only the well-populated cluster's pattern is returned, with `amount_for_name = None`
      (`test_corroborated_cluster_still_respects_min_occurrences`)

- [x] `make lint && make test` pass with coverage >= TASK-012 baseline (153 tests passed, 100% coverage on `analyzer.py`)

## Out of scope

- A configurable corroboration threshold (fixed at 2 distinct dates)
- Changes to FR-33a (billing event collapse) or FR-32b/c beyond what's needed for the above
- Re-tuning `AMOUNT_CLUSTER_TOLERANCE`'s default

## Blockers

None

## Completion

**Date:** 2026-07-11
**Summary:** Owner review of a real analysis report generated after TASK-012
found payee "ICA" fragmented into 15 rows. Root cause: FR-32a's clustering
ran across the payee's two source accounts together (a fixed 12000 kr
transfer from `SEB Räkningskonto` funding a dedicated spending account, and
the actual grocery purchases from `ICA-banken Matkonto`), and a single
day's incidental double purchase within `ICA-banken Matkonto` was enough to
trigger a tolerance-based amount split that then chained across the whole
continuously-distributed purchase-amount range.

Two fixes landed together: `_partition_by_source_account()` (FR-32d, new)
partitions each payee group by `source_name` before amount clustering runs,
so distinct financial roles sharing a payee name are never clustered
together; `_split_into_amount_clusters()` (FR-32a, revised) now only
accepts a co-occurrence-based split when it is *corroborated* — the same
cluster-pair signature (which candidate clusters a date's amounts map to)
must recur across at least two distinct co-occurrence dates. Both are wired
into `_qualifying_clusters()`, which now partitions by source account
first, then amount-clusters and collapses billing events within each
subgroup independently.

Verified against the owner's real Firefly III instance (dry-run export):
"ICA" dropped from 15 rows to 3 — the `SEB Räkningskonto` transfer
unchanged at 97% confidence, all `ICA-banken Matkonto` purchases now
collapsed into a single 80-occurrence pattern (41% confidence, correctly
low given the genuinely wide amount range of day-to-day grocery spend), and
a small residual pattern for a third source account. "STOCKHOLM VATTEN AB"
and "Media och Streaming" were confirmed by the owner as correctly split
(genuinely separate, independently recurring invoices) and are unaffected.
"Restauranger" and "Shopping Amazon" remain fragmented across several rows
because their co-occurrence signatures genuinely do recur across multiple
dates in the real data (corroborated per FR-32a) — this was explicitly
called out as out of scope for this task, which targeted the ICA-style
source-account/single-incident failure mode specifically; further
fragmentation reduction for those payees, if wanted, is a separate,
not-yet-scoped follow-up.

Owner-confirmed side effect: since a resulting pattern's transactions now
share one source account by construction, FR-30a's `source_account_varies`
flag no longer occurs in the normal case (there is nothing left to vary
within a partitioned pattern). Three existing TASK-011 tests exercising
`varies = True` via `identify_recurring()` were revised to assert the new
per-account pattern split instead; `_resolve_source_account()` itself is
unchanged and remains correct as specified.

**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified (new
  `_partition_by_source_account()` helper; `_split_into_amount_clusters()`
  now requires corroboration via a per-date cluster-pair signature count;
  `_qualifying_clusters()` partitions by source account before amount
  clustering; docstrings updated)
- `tests/test_analyzer.py` — modified (new
  `_partition_by_source_account()` unit tests and an ICA-style integration
  test; new/revised corroboration tests for `_split_into_amount_clusters()`
  and `identify_recurring()`; three source-account "varies" tests revised
  to assert per-account pattern splitting instead)
- `docs/REQUIREMENTS_new.md` — modified (spec 0.2.17: revised FR-32a, added
  FR-32d, updated Definitions/UC2/Alternative flow, changelog entry
  including the FR-30a `varies` side-effect note)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-014-source-account-partition-and-corroborated-clustering.md` — this file
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/014-source-account-partition-and-corroborated-clustering`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/TASK-014-source-account-partition-and-corroborated-clustering.md docs/tasks/README.md`
**Commit:** `git commit -m "Partition payees by source account and require corroborated co-occurrence for amount clustering (TASK-014)"`
