"""UC2 pattern-recognition engine: group transactions by payee, classify their
frequency, and score how confidently each group represents a recurring payment.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.category_filter import resolve_category_name
from firefly_bills_analyzer.config import Config

_FREQUENCY_RANGES: dict[str, tuple[float, float]] = {
    "monthly": (25, 35),
    "quarterly": (80, 100),
    "half-yearly": (160, 200),
    "yearly": (340, 390),
}


@dataclass(frozen=True)
class RecurringPattern:
    """A candidate recurring payment identified for a single payee (UC2)."""

    destination_name: str
    category_name: str | None
    occurrences: int
    amount_min: float
    amount_max: float
    amount_mean: float
    median_interval_days: float
    frequency: str
    confidence: float
    source_account_name: str | None
    source_account_varies: bool
    amount_for_name: str | None = None


def _resolve_source_account(
    transactions_for_payee: list[TransactionRead],
) -> tuple[str | None, bool]:
    """Resolve the source account name and whether it varies (FR-30a).

    Returns the mode of non-``None`` ``source_name`` values and whether more
    than one distinct value occurs. There is no majority threshold: unlike
    category resolution, this is deterministic based on mode alone.
    """
    names = [t["source_name"] for t in transactions_for_payee if t["source_name"] is not None]
    if not names:
        return None, False

    counts = Counter(names)
    mode_name, _ = counts.most_common(1)[0]
    varies = len(counts) > 1
    return mode_name, varies


def _tolerance_gap_split(
    transactions: list[TransactionRead], tolerance: float
) -> list[list[TransactionRead]]:
    """Split transactions into contiguous groups via a tolerance-based amount-gap split.

    Transactions are sorted by amount ascending; a new group starts whenever
    the gap between two amount-adjacent transactions exceeds ``tolerance``
    times the smaller of the two amounts. Each group is contiguous in the
    sorted order.
    """
    sorted_transactions = sorted(transactions, key=lambda t: float(t["amount"]))

    groups: list[list[TransactionRead]] = []
    current: list[TransactionRead] = []
    previous_amount: float | None = None
    for transaction in sorted_transactions:
        amount = float(transaction["amount"])
        if previous_amount is not None and amount - previous_amount > tolerance * previous_amount:
            groups.append(current)
            current = []
        current.append(transaction)
        previous_amount = amount

    if current:
        groups.append(current)
    return groups


def _partition_by_source_account(
    transactions: list[TransactionRead],
) -> list[list[TransactionRead]]:
    """Partition a payee group by source account (FR-32d).

    Transactions sharing the same ``source_name`` value form one subgroup;
    transactions with no ``source_name`` form their own subgroup. Distinct
    financial roles that happen to share a payee name — e.g. a fixed
    transfer funding a spending account, versus that spending account's own
    purchases — are typically withdrawn through different source accounts,
    so partitioning here first keeps them from being amount-clustered
    together with the spending they fund.
    """
    groups: dict[str | None, list[TransactionRead]] = defaultdict(list)
    for transaction in transactions:
        groups[transaction["source_name"]].append(transaction)
    return list(groups.values())


def _split_into_amount_clusters(
    transactions: list[TransactionRead], tolerance: float
) -> list[list[TransactionRead]]:
    """Split a source-account subgroup's transactions into amount clusters (FR-32a).

    Clustering is based on corroborated same-date co-occurrence of differing
    amounts, not on amount variance alone: a subgroup whose transactions
    never show more than one distinct amount on the same date (e.g. a
    metered utility bill that fluctuates by season and consumption) is never
    split, however much its amount varies across different dates. A date
    where two or more differing amounts occur together is only trusted as
    evidence of genuinely parallel simultaneous charges (e.g. two
    subscriptions billed through the same merchant) once it is corroborated:
    the same combination of resulting candidate clusters ("signature") must
    recur across at least two distinct co-occurrence dates. A single day's
    coincidental co-occurrence (e.g. an incidental extra purchase from an
    otherwise continuously variable spending account) is not enough evidence
    on its own and does not split the group. Once corroborated, every
    transaction in the group — including ones not on a co-occurrence date —
    is assigned to whichever resulting cluster's mean amount is numerically
    closest to its own.
    """
    by_date: dict[str, list[TransactionRead]] = defaultdict(list)
    for transaction in transactions:
        by_date[transaction["date"]].append(transaction)

    co_occurrence_days = [
        same_day
        for same_day in by_date.values()
        if len({float(t["amount"]) for t in same_day}) >= 2
    ]
    co_occurring = [transaction for same_day in co_occurrence_days for transaction in same_day]

    if not co_occurring:
        return [transactions]

    seed_clusters = _tolerance_gap_split(co_occurring, tolerance)
    cluster_means = [
        statistics.mean(float(t["amount"]) for t in cluster) for cluster in seed_clusters
    ]

    def _nearest_cluster(amount: float) -> int:
        return min(range(len(cluster_means)), key=lambda i: abs(amount - cluster_means[i]))

    signature_counts: Counter[frozenset[int]] = Counter()
    for same_day in co_occurrence_days:
        signature = frozenset(_nearest_cluster(float(t["amount"])) for t in same_day)
        if len(signature) >= 2:
            signature_counts[signature] += 1

    if not any(count >= 2 for count in signature_counts.values()):
        return [transactions]

    assigned: list[list[TransactionRead]] = [[] for _ in seed_clusters]
    for transaction in transactions:
        assigned[_nearest_cluster(float(transaction["amount"]))].append(transaction)

    return assigned


def _collapse_into_billing_events(transactions: list[TransactionRead]) -> list[dict[str, Any]]:
    """Collapse same-date transactions within a cluster into billing events (FR-33a).

    Transactions sharing the exact same date are summed into a single event,
    since they represent one combined outflow rather than independent cycle
    points (e.g. the same monthly fee billed once per household member).
    Events are returned sorted by date ascending.
    """
    by_date: dict[str, list[TransactionRead]] = defaultdict(list)
    for transaction in transactions:
        by_date[transaction["date"]].append(transaction)

    events = [
        {
            "date": day,
            "amount": sum(float(t["amount"]) for t in same_day),
            "count": len(same_day),
        }
        for day, same_day in by_date.items()
    ]
    events.sort(key=lambda event: str(event["date"]))
    return events


def _classify_frequency(median_interval_days: float) -> str:
    for frequency, (low, high) in _FREQUENCY_RANGES.items():
        if low <= median_interval_days <= high:
            return frequency
    return "irregular"


def _confidence(
    *,
    occurrences: int,
    median_days: float,
    stddev_days: float,
    mean_amount: float,
    stddev_amount: float,
    category_name: str | None,
    config: Config,
) -> float:
    occurrence_score = min(occurrences / 4, 1.0)
    regularity_score = max(0.0, 1 - stddev_days / median_days) if median_days else 0.0
    amount_score = max(0.0, 1 - stddev_amount / mean_amount) if mean_amount else 0.0

    score = 0.4 * occurrence_score + 0.4 * regularity_score + 0.2 * amount_score

    if category_name is not None and category_name in config.include_categories:
        score += config.category_confidence_boost
    if category_name is None and config.uncategorized_behavior == "neutral":
        score -= config.uncategorized_confidence_penalty

    return max(0.0, min(1.0, score))


def _qualifying_clusters(
    group: list[TransactionRead], config: Config
) -> list[tuple[list[TransactionRead], list[dict[str, Any]]]]:
    """Partition a payee group by source account, split each subgroup into
    amount clusters, and keep only those whose billing events meet
    ``config.min_occurrences`` (FR-32d, FR-32a, FR-33a)."""
    qualifying = []
    for subgroup in _partition_by_source_account(group):
        clusters = _split_into_amount_clusters(subgroup, config.amount_cluster_tolerance)
        for cluster in clusters:
            events = _collapse_into_billing_events(cluster)
            if len(events) >= config.min_occurrences:
                qualifying.append((cluster, events))
    return qualifying


def _build_pattern(
    destination_name: str,
    cluster: list[TransactionRead],
    events: list[dict[str, Any]],
    *,
    multi_cluster: bool,
    config: Config,
) -> RecurringPattern:
    """Build a ``RecurringPattern`` for one amount cluster's billing events."""
    amounts = [float(event["amount"]) for event in events]
    dates = sorted(date.fromisoformat(str(event["date"])) for event in events)
    intervals = [(b - a).days for a, b in zip(dates, dates[1:])]

    median_days = float(statistics.median(intervals)) if intervals else 0.0
    stddev_days = statistics.pstdev(intervals) if intervals else 0.0
    mean_amount = statistics.mean(amounts)
    stddev_amount = statistics.pstdev(amounts)
    category_name = resolve_category_name(cluster, config)
    source_account_name, source_account_varies = _resolve_source_account(cluster)

    confidence = _confidence(
        occurrences=len(events),
        median_days=median_days,
        stddev_days=stddev_days,
        mean_amount=mean_amount,
        stddev_amount=stddev_amount,
        category_name=category_name,
        config=config,
    )

    return RecurringPattern(
        destination_name=destination_name,
        category_name=category_name,
        occurrences=len(events),
        amount_min=min(amounts),
        amount_max=max(amounts),
        amount_mean=mean_amount,
        median_interval_days=median_days,
        frequency=_classify_frequency(median_days),
        confidence=confidence,
        source_account_name=source_account_name,
        source_account_varies=source_account_varies,
        amount_for_name=f"{mean_amount:.2f}" if multi_cluster else None,
    )


def identify_recurring(
    transactions: list[TransactionRead], config: Config
) -> list[RecurringPattern]:
    """Group ``transactions`` by payee and return recurring patterns (UC2, FR-27).

    Each payee group is first partitioned by source account (FR-32d), so a
    fixed transfer funding a spending account and that spending account's own
    purchases are never analyzed together merely because they share a payee
    name. Each resulting subgroup is further split into amount clusters
    (FR-32a) based on corroborated same-date co-occurrence: distinct real
    charges that happen to share a payee and source account (e.g. several
    subscriptions billed through the same merchant) are analyzed
    independently rather than flattened into one noisy group. Within each
    cluster, transactions sharing the exact same date are collapsed into a
    single billing event (FR-33a) before occurrences, interval, and amount
    statistics are computed, so that e.g. the same fee billed twice on one
    day (once per household member) doesn't corrupt the interval
    calculation. Source account resolution (FR-30a) is unaffected and
    continues to operate on the pre-collapse transactions.

    Clusters with fewer than ``config.min_occurrences`` billing events, or
    payees with no ``destination_name``, are skipped. When a payee produces
    more than one qualifying cluster, each resulting pattern's ``amount_for_name``
    is set to its mean amount so bill names can be disambiguated (FR-32c);
    otherwise it is ``None``. Results are sorted by ``confidence`` descending.
    """
    groups: dict[str, list[TransactionRead]] = defaultdict(list)
    for transaction in transactions:
        destination_name = transaction["destination_name"]
        if destination_name is None:
            continue
        groups[destination_name].append(transaction)

    patterns = []
    for destination_name, group in groups.items():
        if len(group) < config.min_occurrences:
            continue

        qualifying_clusters = _qualifying_clusters(group, config)
        multi_cluster = len(qualifying_clusters) > 1

        for cluster, events in qualifying_clusters:
            patterns.append(
                _build_pattern(
                    destination_name, cluster, events, multi_cluster=multi_cluster, config=config
                )
            )

    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns
