# TASK-018 Separate solo transactions into their own cluster when frequency buckets disagree (FR-32e)

## Status

done

## Requirements

**Binding:** FR-32e
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-012 (amount clustering, billing event collapse), TASK-014
(source-account partitioning, corroborated co-occurrence split)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As an analyst, I want solo transactions (transactions that never share a date
with a sibling transaction within a subgroup) to be folded into an existing
amount cluster only when their own recurrence interval agrees with that
cluster's, so that a merchant billing two independent recurring charges at
different cadences through the same payee name and source account (e.g.
"STOCKHOLM VATTEN AB" billing quarterly water+garbage as a same-day pair, and
yearly garden waste alone) doesn't get its solo charge silently merged into
the wrong cluster merely because its amount happens to sit closer to that
cluster's mean.

## Description

Owner review of a real analysis report found payee "STOCKHOLM VATTEN AB"
(source account `SEB Räkningskonto`) producing an incorrect "irregular"
7-occurrence pattern. Root cause, diagnosed against real transaction data:

- Water (~710-766 kr) and garbage collection (~1801-1940 kr) are billed
  together as a same-day co-occurring pair, quarterly. `_split_into_amount_clusters()`
  (FR-32a, TASK-012/TASK-014) correctly corroborates and separates these two
  into their own clusters via the existing co-occurrence-date signature logic.
- Garden waste (~1471-1560 kr) is billed once a year, always as a lone
  transaction with no same-day sibling — a "solo" transaction with no
  co-occurrence signature of its own.
- FR-32a step (d)/(e)'s existing nearest-mean assignment then folds the solo
  garden-waste transactions into whichever cluster's mean is numerically
  closest — here, the garbage-collection cluster (mean ~1904, vs. water's
  ~753) — merging a yearly charge into a quarterly one and producing one
  incorrectly-labeled "irregular" pattern instead of two correct patterns.

FR-32e (confirmed, `docs/REQUIREMENTS_new.md` v0.2.21) adds a secondary,
interval-based corroboration signal that solo transactions must pass before
nearest-mean assignment is allowed to apply.

### FR-32e: interval-bucket check for solo transactions

Modify `_split_into_amount_clusters()` in `src/firefly_bills_analyzer/analyzer.py`.
The function already computes `seed_clusters` (candidate clusters from
`_tolerance_gap_split`), confirms corroboration via `signature_counts`, and —
only if corroborated — assigns every transaction (co-occurring and solo
alike) to its nearest cluster by mean amount (existing lines ~163-167). This
task inserts a new step between corroboration succeeding and the final
per-transaction assignment loop:

1. Identify **solo transactions**: transactions in the subgroup that are not
   part of any `co_occurrence_days` entry (i.e. not in `co_occurring`).
2. If there are **fewer than 2 solo transactions**, apply the existing
   nearest-mean assignment unchanged — FR-32e does not apply.
3. Otherwise, for each solo transaction compute which seed cluster it would
   be nearest-mean-assigned to (`_nearest_cluster`), and group solo
   transactions by their target cluster index (only clusters that actually
   receive 2+ solo transactions are candidates for splitting off; clusters
   receiving 0 or 1 solo transaction assign those normally, per the existing
   rule above applied per-target-cluster).
4. For each target cluster index with 2+ solo transactions assigned to it:
   a. Compute the solo transactions' own median interval (sort by date,
      compute day gaps between consecutive dates, take the median — same
      method `_build_pattern()` already uses for `intervals`/`median_days`)
      and classify it into a frequency bucket via the **existing**
      `_classify_frequency()` helper (do not add a new/duplicate
      classification function — `_classify_frequency()` already implements
      the FR-03 threshold buckets this requirement needs).
   b. Compute the median interval of that candidate cluster's **own
      co-occurrence-date transactions only** (excluding any solo
      transactions), the same way, and classify it via `_classify_frequency()`.
   c. If the candidate cluster has fewer than 2 of its own co-occurrence-date
      occurrences, its bucket can't be determined — assign these solo
      transactions to that cluster unchanged (existing behavior).
   d. If both buckets are determined and **differ**, remove these solo
      transactions from that candidate cluster's assignment and instead
      collect them into a **new, separate cluster** of their own, appended to
      the returned list of clusters.
   e. If both buckets are determined and **agree**, assign them to the
      candidate cluster unchanged (existing behavior).
5. All non-solo (co-occurring) transactions continue to be assigned exactly
   as before (unaffected by this task).

This only changes behavior when a split is already corroborated (the
existing `if not any(count >= 2 ...): return [transactions]` fallback above
it is untouched) and only for subgroups with 2+ solo transactions whose
interval disagrees with their nearest cluster's — every other case (no
co-occurrence at all, uncorroborated split, <2 solo transactions, or
agreeing buckets) is byte-for-byte unchanged from TASK-014's behavior.

### No new configuration

The FR-03 frequency-bucket thresholds are fixed and already implemented by
`_classify_frequency()`; no new environment variable or `Config` field.

## Branch

**Branch name:** `task/018-solo-transaction-interval-bucket-split`
**Switch/create:** `git checkout -b task/018-solo-transaction-interval-bucket-split`
**Make target:** `make branch-task f=TASK-018`

## Acceptance criteria

- [x] Scenario: Solo transactions whose interval bucket agrees with the nearest cluster are assigned unchanged
      Given a corroborated two-cluster split, and 2+ solo transactions whose own median interval classifies into the same frequency bucket (`_classify_frequency`) as the nearest-mean cluster's own co-occurrence-date occurrences
      When `_split_into_amount_clusters()` processes the subgroup
      Then the solo transactions are assigned to the nearest-mean cluster, and no new cluster is created
      (`test_solo_transactions_matching_bucket_stay_in_nearest_cluster`)

- [x] Scenario: Solo transactions whose interval bucket differs from the nearest cluster form a separate cluster
      Given a corroborated two-cluster split (e.g. quarterly co-occurring water/garbage-style pair), and 2+ solo transactions whose own median interval classifies into a different frequency bucket (e.g. yearly) than the nearest-mean cluster's own co-occurrence-date occurrences
      When `_split_into_amount_clusters()` processes the subgroup
      Then the solo transactions are returned as their own separate cluster, and the original clusters are otherwise unchanged
      (`test_solo_transactions_differing_bucket_form_separate_cluster`)

- [x] Scenario: Nearest-mean cluster has fewer than 2 of its own co-occurrence occurrences
      Given a corroborated split where the candidate cluster nearest to the solo transactions has only 1 co-occurrence-date occurrence
      When `_split_into_amount_clusters()` processes the subgroup
      Then the solo transactions are assigned to that cluster unchanged (bucket undetermined, existing behavior applies)
      (`test_solo_transactions_assigned_unchanged_when_candidate_bucket_undetermined`)

- [x] Scenario: Fewer than 2 solo transactions leaves behavior unchanged
      Given a corroborated split with exactly 1 (or 0) solo transactions, even if its interval would classify differently from the nearest cluster
      When `_split_into_amount_clusters()` processes the subgroup
      Then that transaction is assigned to the nearest-mean cluster per existing (TASK-014) behavior, and no new cluster is created
      (`test_single_solo_transaction_not_separated`)

- [x] Scenario: Uncorroborated split is unaffected by FR-32e
      Given a subgroup whose co-occurrence signature is not corroborated (per FR-32a step c / TASK-014)
      When `_split_into_amount_clusters()` processes the subgroup
      Then the whole subgroup remains a single cluster, exactly as before this task
      (`test_uncorroborated_split_unaffected_by_solo_bucket_check`)

- [x] Scenario: No co-occurrence date at all is unaffected by FR-32e
      Given a subgroup with no co-occurrence date
      When `_split_into_amount_clusters()` processes the subgroup
      Then the whole subgroup remains a single cluster, exactly as before this task
      (existing TASK-012 test continues to pass unmodified)

- [x] Scenario: Real-world case — STOCKHOLM VATTEN AB produces three separate patterns
      Given the payee's real-shaped transaction pattern: quarterly co-occurring water (~710-766 kr) + garbage collection (~1801-1940 kr) pairs, plus 2 solo yearly garden-waste transactions (~1471-1560 kr)
      When `identify_recurring()` processes the payee group
      Then three independent `RecurringPattern` results are produced — water (quarterly), garbage collection (quarterly), and garden waste (yearly, 2 occurrences) — instead of garden waste being merged into garbage collection
      (`test_stockholm_vatten_produces_three_separate_patterns`)

- [x] `_classify_frequency()` is reused for both the solo-transaction bucket and the candidate-cluster bucket — no duplicate/parallel classification helper is introduced

- [x] Hypothesis property test(s) covering the solo/candidate median-interval-to-bucket comparison across a range of synthetic interval values spanning the FR-03 boundaries (25/35, 80/100, 160/200, 340/390 days) and confirming the split/no-split decision matches whether the two buckets agree or differ
      (`test_solo_bucket_classification_hypothesis`)

- [x] All existing TASK-012/TASK-014 tests in `tests/test_analyzer.py` continue to pass unmodified (no regression to FR-32a/b/c/d behavior)

- [x] `make lint && make test` pass with coverage >= TASK-014 baseline (100% on `analyzer.py`)

## Out of scope

- A configurable frequency-bucket threshold or a configurable minimum
  solo-transaction count (fixed at 2, per FR-32e)
- Changes to FR-32a steps (a)-(c) (corroboration/signature logic), FR-32b
  (tolerance config), or FR-32d (source-account partitioning)
- Bill naming/disambiguation changes beyond what FR-32c already provides for
  any newly-created cluster (a solo-transaction cluster is just another
  amount cluster from FR-32c's point of view)
- Importing/validating against the additional year of real transaction
  history the owner is separately preparing for this payee — acceptance
  criteria are synthetic (Hypothesis + a real-shaped example scenario), not
  dependent on that data landing first

## Blockers

None

## Completion

**Date:** 2026-07-20
**Summary:** Extended `_split_into_amount_clusters()` in
`src/firefly_bills_analyzer/analyzer.py` per FR-32e. After a corroborated
split's existing nearest-mean assignment step, solo transactions (those not
part of any `co_occurrence_days` entry) are grouped by which seed cluster
they'd be nearest-mean-assigned to. For any target cluster receiving 2+ solo
transactions, the solo group's own median interval and the candidate
cluster's own co-occurrence-date-only median interval are each classified
via the existing `_classify_frequency()` helper (no new/duplicate
classification logic, per the acceptance criteria). If the candidate has
fewer than 2 of its own co-occurrence occurrences, its bucket is
undetermined and the solo group is assigned unchanged. If both buckets are
determined and disagree, the solo group is pulled out into a new, separate
cluster appended to the returned list; if they agree (or there are fewer
than 2 solo transactions targeting that cluster), the existing nearest-mean
assignment is unchanged. Added `_median_interval_days()` (sort dates,
compute consecutive day gaps, take the median — the same method
`_build_pattern()` already uses for `intervals`/`median_days`) so the new
logic doesn't diverge from that existing method. The new step was extracted
into `_split_off_disagreeing_solo_clusters()` to keep
`_split_into_amount_clusters()` under the project's complexipy complexity
limit (17 inline vs. 15 max; extracted, both functions pass at 9 and 8).
Also fixed 2 pre-existing `E501` line-too-long lint failures in the
Test-Writer-authored Hypothesis `@example` comments in
`tests/test_analyzer.py` (rewrapped comment text only, no behavior/logic
change — this blocked the mandatory `make lint` gate). `make lint && make
test` pass (172 tests, `analyzer.py` at 100% coverage, matching the
TASK-014 baseline; overall project coverage 99%).

**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified
  (`_split_into_amount_clusters()` extended per FR-32e; new
  `_split_off_disagreeing_solo_clusters()` and `_median_interval_days()`
  helpers; new `Callable` import from `collections.abc`)
- `tests/test_analyzer.py` — modified (Test Writer agent added the FR-32e
  "Solo transaction interval-bucket split" test section; this task fixed 2
  `E501` line-too-long lint failures in that section's `@example` comments,
  no logic change)
- `CHANGELOG.md` — modified (Unreleased/Added entry describing the
  behavior change)
- `docs/REQUIREMENTS_new.md` — modified prior to implementation (v0.2.20 →
  v0.2.21: FR-32a step (f) and the "Amount cluster" glossary entry updated
  to add FR-32e's solo-transaction interval-bucket check; confirmed with the
  user before this task's implementation began)
- `docs/tasks/README.md` — modified (TASK-018 status `not started` → `done`)
- `docs/tasks/TASK-018-solo-transaction-interval-bucket-split.md` —
  modified (status, acceptance-criteria checkboxes, this Completion section)

**Branch:** `task/018-solo-transaction-interval-bucket-split`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py
CHANGELOG.md docs/tasks/README.md docs/REQUIREMENTS_new.md
docs/tasks/TASK-018-solo-transaction-interval-bucket-split.md`
**Commit:** `git commit -m "feat: separate solo transactions into their own bill when their recurrence interval disagrees with the nearest amount cluster (FR-32e)"`
