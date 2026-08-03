"""UC13: aggregate household spend per source account and category.

A pure consumer of the withdrawal list `fetcher.py` (TASK-002) already
fetched and `Config`. Performs no I/O (NFR-15): the analysis window is
derived from `config.lookback_months` and today's date exactly as
`fetcher.fetch_transactions()` derives it, rather than being fetched again.

Qualification order (FR-48d, FR-48e, FR-48b, FR-48c):

1. Drop every withdrawal carrying the exclude tag — absolute, checked first.
2. Admit a withdrawal whose category is a household spend category, or
   which carries the include tag.
3. Drop every withdrawal belonging to a recurring pattern identified in UC2.
   Membership is by the transaction's own identity (`id()`), computed via
   `analyzer.pattern_member_transactions()` over this same withdrawal list,
   never by reconstructing a match from payee name or other fields (FR-48b).
4. Set aside every withdrawal above the one-off threshold.

The remainder is summed per (source account, category, calendar month);
months that don't fall entirely inside the analysis window are dropped
(FR-49b), and a month with no qualifying spending counts as zero, not as
missing (see module docstring rationale in the requirements document).
"""

from __future__ import annotations

import calendar
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.analyzer import pattern_member_transactions
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.fetcher import _subtract_months


def _today() -> date:
    return date.today()


@dataclass(frozen=True)
class OneOffPurchase:
    """A single withdrawal above `household_spend_one_off_threshold` (FR-48c)."""

    date: str
    amount: float
    payee: str | None
    category: str | None
    source_account: str | None


@dataclass(frozen=True)
class HouseholdSpendRecord:
    """The aggregate household spend figure for one (source account, category) pair."""

    source_account: str | None
    category: str | None
    month_count: int
    monthly_totals: list[float]
    median: float | None
    mean: float | None
    minimum: float | None
    maximum: float | None


@dataclass(frozen=True)
class HouseholdSpendResult:
    records: list[HouseholdSpendRecord]
    one_off_purchases: list[OneOffPurchase]
    unmatched_categories: list[str]
    include_tag_count: int
    exclude_tag_count: int


def _complete_months(window_start: date, window_end: date) -> list[str]:
    """Every "YYYY-MM" calendar month falling entirely inside the window (FR-49b)."""
    months: list[str] = []
    year, month = window_start.year, window_start.month
    while date(year, month, 1) <= window_end:
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
        if month_start >= window_start and month_end <= window_end:
            months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _qualifies(
    transaction: TransactionRead,
    categories: set[str],
    include_tag: str | None,
) -> tuple[bool, bool]:
    """Return (qualifies, admitted_by_include_tag_only) for one transaction (FR-48d)."""
    category_match = transaction.get("category_name") in categories
    tags = transaction.get("tags", [])
    include_match = bool(include_tag) and include_tag in tags
    return category_match or include_match, include_match and not category_match


def _select_qualifying(
    withdrawals: list[TransactionRead], config: Config, pattern_ids: set[int]
) -> tuple[list[TransactionRead], int, int]:
    """Apply the FR-48d/e/b qualification order, returning the survivors and
    the include/exclude tag counts (FR-48f)."""
    categories = set(config.household_spend_categories)
    include_tag = config.household_spend_include_tag
    exclude_tag = config.household_spend_exclude_tag

    qualifying: list[TransactionRead] = []
    include_tag_count = 0
    exclude_tag_count = 0

    for transaction in withdrawals:
        tags = transaction.get("tags", [])
        if exclude_tag and exclude_tag in tags:
            exclude_tag_count += 1
            continue

        qualifies, include_tag_only = _qualifies(transaction, categories, include_tag)
        if not qualifies:
            continue
        if include_tag_only:
            include_tag_count += 1

        if id(transaction) in pattern_ids:
            continue

        qualifying.append(transaction)

    return qualifying, include_tag_count, exclude_tag_count


def _split_one_off_purchases(
    qualifying: list[TransactionRead], threshold: float
) -> tuple[list[OneOffPurchase], list[TransactionRead]]:
    """Set aside every withdrawal above the one-off threshold (FR-48c)."""
    one_off_purchases: list[OneOffPurchase] = []
    monthly_input: list[TransactionRead] = []
    for transaction in qualifying:
        amount = float(transaction["amount"])
        if amount > threshold:
            one_off_purchases.append(
                OneOffPurchase(
                    date=str(transaction["date"]),
                    amount=amount,
                    payee=transaction.get("destination_name"),
                    category=transaction.get("category_name"),
                    source_account=transaction.get("source_name"),
                )
            )
        else:
            monthly_input.append(transaction)
    return one_off_purchases, monthly_input


def _group_monthly_totals(
    monthly_input: list[TransactionRead], complete_months: list[str]
) -> dict[tuple[str | None, str | None], dict[str, float]]:
    """Sum ``monthly_input`` per (source, category, month) (FR-49a), keeping
    only months that fall entirely inside the analysis window (FR-49b)."""
    totals: dict[tuple[str | None, str | None, str], float] = defaultdict(float)
    for transaction in monthly_input:
        key = (
            transaction.get("source_name"),
            transaction.get("category_name"),
            str(transaction["date"])[:7],
        )
        totals[key] += float(transaction["amount"])

    grouped: dict[tuple[str | None, str | None], dict[str, float]] = defaultdict(dict)
    for (source, category, month), total in totals.items():
        if month in complete_months:
            grouped[(source, category)][month] = total
    return grouped


def _unmatched_categories(withdrawals: list[TransactionRead], config: Config) -> list[str]:
    """Configured categories matching no transaction in the window (FR-50)."""
    present_categories = {transaction.get("category_name") for transaction in withdrawals}
    return [
        category
        for category in config.household_spend_categories
        if category not in present_categories
    ]


def aggregate_household_spend(
    withdrawals: list[TransactionRead], config: Config
) -> HouseholdSpendResult:
    """Aggregate household spend per source account and category (UC13).

    Returns an inert, empty result with no processing when
    `config.household_spend_categories` is empty (FR-47a), so the feature
    costs nothing when unconfigured (NFR-15).
    """
    if not config.household_spend_categories:
        return HouseholdSpendResult(
            records=[],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        )

    pattern_ids = {id(t) for t in pattern_member_transactions(withdrawals, config)}
    qualifying, include_tag_count, exclude_tag_count = _select_qualifying(
        withdrawals, config, pattern_ids
    )
    one_off_purchases, monthly_input = _split_one_off_purchases(
        qualifying, config.household_spend_one_off_threshold
    )

    window_end = _today()
    window_start = _subtract_months(window_end, config.lookback_months)
    complete_months = _complete_months(window_start, window_end)
    grouped = _group_monthly_totals(monthly_input, complete_months)

    records = [
        _build_record(source, category, month_totals, complete_months, config)
        for (source, category), month_totals in grouped.items()
    ]

    return HouseholdSpendResult(
        records=records,
        one_off_purchases=one_off_purchases,
        unmatched_categories=_unmatched_categories(withdrawals, config),
        include_tag_count=include_tag_count,
        exclude_tag_count=exclude_tag_count,
    )


def _build_record(
    source: str | None,
    category: str | None,
    month_totals: dict[str, float],
    complete_months: list[str],
    config: Config,
) -> HouseholdSpendRecord:
    monthly_totals = [month_totals.get(month, 0.0) for month in complete_months]
    month_count = len(monthly_totals)
    has_median = month_count >= config.household_spend_min_months

    return HouseholdSpendRecord(
        source_account=source,
        category=category,
        month_count=month_count,
        monthly_totals=monthly_totals,
        median=statistics.median(monthly_totals) if has_median else None,
        mean=statistics.mean(monthly_totals) if monthly_totals else None,
        minimum=min(monthly_totals) if monthly_totals else None,
        maximum=max(monthly_totals) if monthly_totals else None,
    )
