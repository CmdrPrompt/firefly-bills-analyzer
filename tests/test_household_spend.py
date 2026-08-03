"""UC13: measuring household spend per account and category (TASK-028)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from firefly_python_api import TransactionRead
from hypothesis import given, settings
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import pattern_member_transactions
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.household_spend import (
    _split_one_off_purchases,
    _today,
    _unmatched_threshold_overrides,
    aggregate_household_spend,
)


def _make_config(**overrides: object) -> Config:
    base: dict[str, object] = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=12,
        min_occurrences=2,
        amount_margin=0.10,
        amount_cluster_tolerance=0.15,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
        uncategorized_confidence_penalty=0.10,
        uncategorized_behavior="neutral",
        include_categories=[],
        exclude_categories=[],
        include_accounts=[],
        exclude_accounts=[],
        include_payees=[],
        exclude_payees=[],
        dry_run=False,
        export_format="none",
        web_port=5000,
        web_host="127.0.0.1",
        cache_dir="./cache",
        cache_ttl_categories=86400,
        cache_ttl_bills=3600,
        cache_ttl_transactions=3600,
        cache_ttl_payees=86400,
        income_accounts=[],
        income_min_occurrences=3,
        income_variance_tolerance=0.10,
        household_spend_categories=["Groceries"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={},
        household_spend_min_months=3,
        household_spend_include_tag=None,
        household_spend_exclude_tag=None,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _withdrawal(
    day: date,
    amount: str,
    category_name: str | None,
    source_name: str | None = "Personal Checking",
    destination_name: str | None = "Corner Shop",
    tags: list[str] | None = None,
) -> TransactionRead:
    txn = TransactionRead(
        date=day.isoformat(),
        amount=amount,
        destination_name=destination_name,
        category_name=category_name,
        source_name=source_name,
    )
    if tags is not None:
        txn["tags"] = tags
    return txn


def _monthly_dates(start: date, count: int) -> list[date]:
    dates = []
    year, month = start.year, start.month
    for _ in range(count):
        dates.append(date(year, month, 1))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates


def _groceries_month(
    month_date: date, amount: str, index: int, **overrides: object
) -> TransactionRead:
    """A single grocery withdrawal with a payee unique to its month.

    Day-to-day grocery shopping typically visits a different store each
    time; a distinct payee per transaction keeps this test data from
    accidentally exceeding ``min_occurrences`` for one payee and being
    swept up as a recurring pattern (FR-48b) itself.
    """
    return _withdrawal(
        month_date, amount, "Groceries", destination_name=f"Store {index}", **overrides
    )


def test_today_returns_the_current_date() -> None:
    assert _today() == date.today()


# ---------------------------------------------------------------------------
# AC-14: The feature is inert when unconfigured
# ---------------------------------------------------------------------------


def test_inert_when_no_categories_configured() -> None:
    config = _make_config(household_spend_categories=[])
    withdrawals = [_withdrawal(date(2026, 1, 5), "100.00", "Groceries")]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.records == []
    assert result.one_off_purchases == []
    assert result.unmatched_categories == []


# ---------------------------------------------------------------------------
# AC-1: Groceries bought several times a month are measured
# ---------------------------------------------------------------------------


def test_twelve_complete_months_produce_one_record_with_median() -> None:
    config = _make_config(lookback_months=12)
    withdrawals = []
    for i, month_date in enumerate(_monthly_dates(date(2026, 1, 1), 12)):
        withdrawals.append(_groceries_month(month_date, "300.00", i * 2))
        withdrawals.append(
            _groceries_month(date(month_date.year, month_date.month, 15), "50.00", i * 2 + 1)
        )

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2027, 1, 1)):
        result = aggregate_household_spend(withdrawals, config)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.month_count == 12
    assert record.median == pytest.approx(350.00)


# ---------------------------------------------------------------------------
# AC-2: The figure is the median, not the mean
# ---------------------------------------------------------------------------


def test_median_differs_from_mean_with_an_outlier_month() -> None:
    config = _make_config(lookback_months=12, household_spend_one_off_threshold=1_000_000)
    withdrawals = []
    months = _monthly_dates(date(2026, 1, 1), 12)
    for i, month_date in enumerate(months):
        amount = "20000.00" if i == 0 else "5000.00"
        withdrawals.append(_groceries_month(month_date, amount, i))

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2027, 1, 1)):
        result = aggregate_household_spend(withdrawals, config)

    record = result.records[0]
    assert record.median == pytest.approx(5000.0)
    assert record.mean is not None
    assert record.mean > record.median


# ---------------------------------------------------------------------------
# AC-3: A month with no spending counts as zero
# ---------------------------------------------------------------------------


def test_month_with_no_spending_counts_as_zero() -> None:
    config = _make_config(lookback_months=12)
    months = _monthly_dates(date(2026, 1, 1), 12)
    withdrawals = [_groceries_month(m, "300.00", i) for i, m in enumerate(months[:9])]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2027, 1, 1)):
        result = aggregate_household_spend(withdrawals, config)

    record = result.records[0]
    assert record.month_count == 12
    assert sum(1 for total in record.monthly_totals if total == 0.0) == 3


# ---------------------------------------------------------------------------
# AC-4: A subscription already counted as a pattern is not counted twice
# ---------------------------------------------------------------------------


def test_pattern_transactions_are_excluded_from_totals() -> None:
    config = _make_config(lookback_months=12, min_occurrences=2)
    months = _monthly_dates(date(2026, 1, 1), 12)
    subscription = [
        _withdrawal(m, "99.00", "Groceries", destination_name="Streaming Co") for m in months
    ]
    groceries = [_groceries_month(m, "300.00", i) for i, m in enumerate(months)]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2027, 1, 1)):
        result = aggregate_household_spend(subscription + groceries, config)

    assert len(result.records) == 1
    assert result.records[0].median == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# AC-5: A large purchase is set aside
# ---------------------------------------------------------------------------


def test_large_purchase_reported_as_one_off() -> None:
    config = _make_config(household_spend_one_off_threshold=2000.0)
    withdrawals = [
        _withdrawal(date(2026, 6, 10), "15000.00", "Groceries", destination_name="Furniture Store"),
    ]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.records == []
    assert len(result.one_off_purchases) == 1
    one_off = result.one_off_purchases[0]
    assert one_off.amount == pytest.approx(15000.0)
    assert one_off.date == "2026-06-10"
    assert one_off.payee == "Furniture Store"
    assert one_off.category == "Groceries"
    assert one_off.source_account == "Personal Checking"


# ---------------------------------------------------------------------------
# AC-6: Partial months at the window edges are dropped
# ---------------------------------------------------------------------------


def test_partial_edge_months_contribute_no_monthly_total() -> None:
    config = _make_config(lookback_months=1, household_spend_min_months=1)
    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 6, 15)):
        # window: 2026-05-15 .. 2026-06-15 -> May and June are both partial
        withdrawals = [
            _withdrawal(date(2026, 5, 20), "300.00", "Groceries"),
            _withdrawal(date(2026, 6, 5), "300.00", "Groceries"),
        ]
        result = aggregate_household_spend(withdrawals, config)

    assert result.records == []


# ---------------------------------------------------------------------------
# AC-7/8/9: Override tags
# ---------------------------------------------------------------------------


def test_exclude_tag_removes_transaction_from_household_category() -> None:
    config = _make_config(household_spend_exclude_tag="personal", household_spend_min_months=1)
    withdrawals = [
        _withdrawal(date(2026, 6, 5), "300.00", "Groceries", tags=["personal"]),
    ]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.records == []
    assert result.exclude_tag_count == 1


def test_include_tag_admits_transaction_from_personal_category() -> None:
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_include_tag="shared",
        household_spend_min_months=1,
        lookback_months=6,
    )
    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        withdrawals = [
            _withdrawal(date(2026, 7, 5), "300.00", "Personal Hobby", tags=["shared"]),
        ]
        result = aggregate_household_spend(withdrawals, config)

    assert len(result.records) == 1
    assert result.records[0].category == "Personal Hobby"
    assert result.include_tag_count == 1


def test_exclude_tag_beats_include_tag() -> None:
    config = _make_config(
        household_spend_include_tag="shared",
        household_spend_exclude_tag="personal",
        household_spend_min_months=1,
    )
    withdrawals = [
        _withdrawal(date(2026, 6, 5), "300.00", "Groceries", tags=["shared", "personal"]),
    ]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.records == []
    assert result.exclude_tag_count == 1


# ---------------------------------------------------------------------------
# AC-10: No tags configured leaves category behavior intact
# ---------------------------------------------------------------------------


def test_no_tags_configured_and_missing_tags_field_raises_no_error() -> None:
    config = _make_config(
        household_spend_include_tag=None,
        household_spend_exclude_tag=None,
        household_spend_min_months=1,
    )
    withdrawal = TransactionRead(
        date="2026-06-05",
        amount="300.00",
        destination_name="Corner Shop",
        category_name="Groceries",
        source_name="Personal Checking",
    )
    assert "tags" not in withdrawal

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend([withdrawal], config)

    assert len(result.records) == 1


# ---------------------------------------------------------------------------
# AC-11: Too few complete months yields no median
# ---------------------------------------------------------------------------


def test_too_few_complete_months_yields_no_median() -> None:
    config = _make_config(lookback_months=2, household_spend_min_months=3)
    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 3, 15)):
        # window 2026-01-15 .. 2026-03-15 -> only February is a complete month
        withdrawals = [_withdrawal(date(2026, 2, 10), "300.00", "Groceries")]
        result = aggregate_household_spend(withdrawals, config)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.month_count == 1
    assert record.median is None


# ---------------------------------------------------------------------------
# AC-12: An unmatched category is reported
# ---------------------------------------------------------------------------


def test_unmatched_category_is_reported() -> None:
    config = _make_config(household_spend_categories=["Groceries", "Clothing"])
    withdrawals = [_withdrawal(date(2026, 6, 5), "300.00", "Groceries")]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.unmatched_categories == ["Clothing"]


# ---------------------------------------------------------------------------
# TASK-033: per-category one-off purchase thresholds (FR-47e, FR-47f, FR-48c)
# ---------------------------------------------------------------------------


def test_split_one_off_purchases_uses_category_override_threshold() -> None:
    """A withdrawal above the default but at/under its category's override
    threshold is not set aside as a one-off purchase (FR-47e)."""
    config = _make_config(
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Groceries": 3000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "2500.00", "Groceries")]

    one_off_purchases, monthly_input = _split_one_off_purchases(withdrawals, config)

    assert one_off_purchases == []
    assert monthly_input == withdrawals


def test_split_one_off_purchases_still_excludes_above_the_category_override() -> None:
    config = _make_config(
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Groceries": 3000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "3500.00", "Groceries")]

    one_off_purchases, monthly_input = _split_one_off_purchases(withdrawals, config)

    assert monthly_input == []
    assert len(one_off_purchases) == 1
    assert one_off_purchases[0].amount == pytest.approx(3500.0)


def test_split_one_off_purchases_falls_back_to_default_for_unconfigured_category() -> None:
    """A category with no entry in `household_spend_one_off_thresholds`
    keeps using the plain default threshold, unchanged from prior behavior."""
    config = _make_config(
        household_spend_categories=["Groceries", "Transport"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Groceries": 3000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "2500.00", "Transport")]

    one_off_purchases, monthly_input = _split_one_off_purchases(withdrawals, config)

    assert monthly_input == []
    assert len(one_off_purchases) == 1
    assert one_off_purchases[0].amount == pytest.approx(2500.0)


def test_one_off_purchase_records_the_threshold_that_excluded_it() -> None:
    config = _make_config(
        household_spend_categories=["Groceries", "Transport"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Transport": 6000.0},
    )
    withdrawals = [
        _withdrawal(date(2026, 6, 10), "8000.00", "Transport", destination_name="Car Workshop")
    ]

    one_off_purchases, _ = _split_one_off_purchases(withdrawals, config)

    assert len(one_off_purchases) == 1
    assert one_off_purchases[0].threshold == pytest.approx(6000.0)


def test_one_off_purchase_records_the_default_threshold_when_no_override_applies() -> None:
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "15000.00", "Groceries")]

    one_off_purchases, _ = _split_one_off_purchases(withdrawals, config)

    assert len(one_off_purchases) == 1
    assert one_off_purchases[0].threshold == pytest.approx(2000.0)


def test_large_purchase_reported_as_one_off_via_aggregate_carries_its_threshold() -> None:
    """Integration-level: the threshold set by `_split_one_off_purchases`
    reaches `aggregate_household_spend`'s result unchanged."""
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Groceries": 3000.0},
    )
    withdrawals = [
        _withdrawal(date(2026, 6, 10), "15000.00", "Groceries", destination_name="Furniture Store")
    ]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert len(result.one_off_purchases) == 1
    assert result.one_off_purchases[0].threshold == pytest.approx(3000.0)


def test_unmatched_threshold_overrides_reports_category_absent_from_categories() -> None:
    """FR-47f: a category named in `household_spend_one_off_thresholds` but
    not in `household_spend_categories` is reported, on the same terms
    FR-50 reports an unmatched household spend category."""
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_one_off_thresholds={"Groceries": 3000.0, "Nonexistent Category": 5000.0},
    )

    assert _unmatched_threshold_overrides(config) == ["Nonexistent Category"]


def test_unmatched_threshold_overrides_empty_when_every_override_matches() -> None:
    config = _make_config(
        household_spend_categories=["Groceries", "Transport"],
        household_spend_one_off_thresholds={"Groceries": 3000.0, "Transport": 6000.0},
    )

    assert _unmatched_threshold_overrides(config) == []


def test_aggregate_household_spend_reports_unmatched_threshold_override() -> None:
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_min_months=1,
        household_spend_one_off_thresholds={"Nonexistent Category": 5000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 5), "300.00", "Groceries")]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        result = aggregate_household_spend(withdrawals, config)

    assert result.unmatched_threshold_overrides == ["Nonexistent Category"]


# ---------------------------------------------------------------------------
# AC-13: Two accounts are measured independently
# ---------------------------------------------------------------------------


def test_two_accounts_produce_independent_records() -> None:
    config = _make_config(lookback_months=12, household_spend_min_months=1)
    months = _monthly_dates(date(2026, 1, 1), 12)
    withdrawals = [
        _groceries_month(m, "300.00", i, source_name="Account A") for i, m in enumerate(months)
    ]
    withdrawals += [
        _groceries_month(m, "150.00", i + 100, source_name="Account B")
        for i, m in enumerate(months)
    ]

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2027, 1, 1)):
        result = aggregate_household_spend(withdrawals, config)

    assert len(result.records) == 2
    by_source = {r.source_account: r for r in result.records}
    assert by_source["Account A"].median == pytest.approx(300.0)
    assert by_source["Account B"].median == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------

_amount_strategy = st.floats(
    min_value=1, max_value=50_000, allow_nan=False, allow_infinity=False
).map(lambda amount: f"{amount:.2f}")

_withdrawal_strategy = st.builds(
    _withdrawal,
    day=st.dates(min_value=date(2026, 1, 1), max_value=date(2026, 12, 31)),
    amount=_amount_strategy,
    category_name=st.sampled_from(["Groceries", "Other"]),
    source_name=st.sampled_from(["Account A", "Account B"]),
    destination_name=st.sampled_from(["Corner Shop", "Streaming Co", "Furniture Store"]),
)


@given(st.lists(_withdrawal_strategy, max_size=25))
@settings(max_examples=50)
def test_no_amount_created_or_lost_by_partitioning(withdrawals: list[TransactionRead]) -> None:
    """AC-15: the sum of every monthly total, the one-off purchases, and the
    pattern-excluded amount equals the sum of every category-qualifying
    withdrawal — no amount is created or lost by the partitioning."""
    config = _make_config(lookback_months=12, household_spend_min_months=1)

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        pattern_ids = {id(t) for t in pattern_member_transactions(withdrawals, config)}
        result = aggregate_household_spend(withdrawals, config)

    categories = set(config.household_spend_categories)
    qualifying = [w for w in withdrawals if w.get("category_name") in categories]
    qualifying_total = sum(float(w["amount"]) for w in qualifying)
    pattern_excluded_total = sum(float(w["amount"]) for w in qualifying if id(w) in pattern_ids)

    monthly_total = sum(
        month_total for record in result.records for month_total in record.monthly_totals
    )
    one_off_total = sum(o.amount for o in result.one_off_purchases)

    assert monthly_total + one_off_total + pattern_excluded_total == pytest.approx(qualifying_total)


@given(st.lists(_withdrawal_strategy, max_size=25))
@settings(max_examples=50)
def test_pattern_transactions_never_appear_in_monthly_totals(
    withdrawals: list[TransactionRead],
) -> None:
    """AC-16: no transaction belonging to an identified pattern contributes
    to any monthly total, for any combination of categories and tags."""
    config = _make_config(lookback_months=12, household_spend_min_months=1, min_occurrences=2)

    with patch("firefly_bills_analyzer.household_spend._today", return_value=date(2026, 12, 31)):
        pattern_ids = {id(t) for t in pattern_member_transactions(withdrawals, config)}
        result = aggregate_household_spend(withdrawals, config)

    categories = set(config.household_spend_categories)
    threshold = config.household_spend_one_off_threshold
    expected_monthly_total = sum(
        float(w["amount"])
        for w in withdrawals
        if w.get("category_name") in categories
        and id(w) not in pattern_ids
        and float(w["amount"]) <= threshold
    )
    actual_monthly_total = sum(
        month_total for record in result.records for month_total in record.monthly_totals
    )

    assert actual_monthly_total == pytest.approx(expected_monthly_total)
