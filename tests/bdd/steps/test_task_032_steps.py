"""TASK-032 step definitions for household spend confidence gating (FR-48b, UC13)."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import patch

from firefly_python_api import TransactionRead
from pytest_bdd import given, scenarios, then, when

from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.household_spend import HouseholdSpendResult, aggregate_household_spend

scenarios("../features/TASK-032-household-spend-confidence-threshold.feature")


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
        household_spend_min_months=1,
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
) -> TransactionRead:
    return TransactionRead(
        date=day.isoformat(),
        amount=amount,
        destination_name=destination_name,
        category_name=category_name,
        source_name=source_name,
    )


def _run(withdrawals: list[TransactionRead], config: Config, today: date) -> HouseholdSpendResult:
    with patch("firefly_bills_analyzer.household_spend._today", return_value=today):
        return aggregate_household_spend(withdrawals, config)


@when("household spend is aggregated", target_fixture="result")
def household_spend_is_aggregated(context: dict[str, Any]) -> HouseholdSpendResult:
    return _run(context["withdrawals"], context["config"], context["today"])


# ---------------------------------------------------------------------------
# AC-1: High-confidence recurring pattern excludes withdrawal from household
# spend
# ---------------------------------------------------------------------------


@given(
    "a monthly subscription in a household spend category with steady amounts and dates, "
    "forming a high-confidence pattern",
    target_fixture="context",
)
def monthly_subscription_high_confidence() -> dict[str, Any]:
    config = _make_config(lookback_months=4, min_occurrences=2)
    subscription_dates = [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]
    withdrawals = [
        _withdrawal(d, "99.00", "Groceries", destination_name="Netflix") for d in subscription_dates
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 5, 1)}


@then("none of the subscription's withdrawals appear in any monthly total")
def subscription_withdrawals_absent(result: HouseholdSpendResult) -> None:
    assert result.records == []


# ---------------------------------------------------------------------------
# AC-2: Low-confidence pattern allows withdrawal into household spend
# ---------------------------------------------------------------------------


@given(
    "two irregular withdrawals to the same payee in a household spend category, forming a "
    "low-confidence pattern",
    target_fixture="context",
)
def two_irregular_withdrawals_low_confidence() -> dict[str, Any]:
    config = _make_config(lookback_months=12, min_occurrences=2)
    withdrawals = [
        _withdrawal(date(2026, 1, 1), "50.00", "Groceries", destination_name="Corner Shop"),
        _withdrawal(date(2026, 3, 20), "480.00", "Groceries", destination_name="Corner Shop"),
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("the withdrawals are counted in the household spend monthly totals")
def withdrawals_counted_in_monthly_totals(result: HouseholdSpendResult) -> None:
    total = sum(month_total for record in result.records for month_total in record.monthly_totals)
    assert total == 530.0


# ---------------------------------------------------------------------------
# AC-3: Large single-cluster payee with varying amounts is measured as
# household spend (ICA-style regression)
# ---------------------------------------------------------------------------


@given(
    "many withdrawals to one payee and account in a household spend category, with varying "
    "amounts on distinct dates and no same-day co-occurrence",
    target_fixture="context",
)
def many_withdrawals_varying_amounts_distinct_dates() -> dict[str, Any]:
    config = _make_config(lookback_months=3, min_occurrences=2)
    days = [
        date(2026, 1, 3),
        date(2026, 1, 9),
        date(2026, 1, 14),
        date(2026, 1, 22),
        date(2026, 2, 2),
        date(2026, 2, 11),
        date(2026, 2, 19),
        date(2026, 2, 27),
    ]
    amounts = [
        "412.50",
        "88.90",
        "310.00",
        "1250.75",
        "45.30",
        "670.20",
        "199.99",
        "823.10",
    ]
    withdrawals = [
        _withdrawal(d, amount, "Groceries", destination_name="ICA")
        for d, amount in zip(days, amounts)
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 3, 15)}


@then("all of the withdrawals are counted in the household spend monthly totals")
def all_withdrawals_counted(result: HouseholdSpendResult, context: dict[str, Any]) -> None:
    expected_total = sum(float(w["amount"]) for w in context["withdrawals"])
    actual_total = sum(
        month_total for record in result.records for month_total in record.monthly_totals
    )
    assert actual_total == expected_total
