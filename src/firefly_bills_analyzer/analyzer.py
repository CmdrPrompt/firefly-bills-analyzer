"""UC2 pattern-recognition engine: group transactions by payee, classify their
frequency, and score how confidently each group represents a recurring payment.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

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


def identify_recurring(
    transactions: list[TransactionRead], config: Config
) -> list[RecurringPattern]:
    """Group ``transactions`` by payee and return recurring patterns (UC2, FR-27).

    Payees with fewer than ``config.min_occurrences`` transactions, or with no
    ``destination_name``, are skipped. Results are sorted by ``confidence``
    descending.
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

        amounts = [float(t["amount"]) for t in group]
        dates = sorted(date.fromisoformat(t["date"]) for t in group)
        intervals = [(b - a).days for a, b in zip(dates, dates[1:])]

        median_days = float(statistics.median(intervals)) if intervals else 0.0
        stddev_days = statistics.pstdev(intervals) if intervals else 0.0
        mean_amount = statistics.mean(amounts)
        stddev_amount = statistics.pstdev(amounts)
        category_name = resolve_category_name(group, config)

        confidence = _confidence(
            occurrences=len(group),
            median_days=median_days,
            stddev_days=stddev_days,
            mean_amount=mean_amount,
            stddev_amount=stddev_amount,
            category_name=category_name,
            config=config,
        )

        patterns.append(
            RecurringPattern(
                destination_name=destination_name,
                category_name=category_name,
                occurrences=len(group),
                amount_min=min(amounts),
                amount_max=max(amounts),
                amount_mean=mean_amount,
                median_interval_days=median_days,
                frequency=_classify_frequency(median_days),
                confidence=confidence,
            )
        )

    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns
