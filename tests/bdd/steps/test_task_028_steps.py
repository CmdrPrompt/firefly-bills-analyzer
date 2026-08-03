"""TASK-028 step definitions for household spend aggregation (UC13)."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import patch

from firefly_python_api import TransactionRead
from pytest_bdd import given, scenarios, then, when

from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.household_spend import HouseholdSpendResult, aggregate_household_spend

scenarios("../features/TASK-028-household-spend-aggregation.feature")


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


def _run(withdrawals: list[TransactionRead], config: Config, today: date) -> HouseholdSpendResult:
    with patch("firefly_bills_analyzer.household_spend._today", return_value=today):
        return aggregate_household_spend(withdrawals, config)


@when("household spend is aggregated", target_fixture="result")
def household_spend_is_aggregated(context: dict[str, Any]) -> HouseholdSpendResult:
    return _run(context["withdrawals"], context["config"], context["today"])


# ---------------------------------------------------------------------------
# AC-1: Groceries bought several times a month are measured
# ---------------------------------------------------------------------------


@given(
    "twelve complete months of grocery withdrawals from one account, several per month",
    target_fixture="context",
)
def twelve_complete_months_several_per_month() -> dict[str, Any]:
    config = _make_config(lookback_months=12)
    withdrawals = []
    for i, month_date in enumerate(_monthly_dates(date(2026, 1, 1), 12)):
        withdrawals.append(
            _withdrawal(month_date, "300.00", "Groceries", destination_name=f"Store {i * 2}")
        )
        withdrawals.append(
            _withdrawal(
                date(month_date.year, month_date.month, 15),
                "50.00",
                "Groceries",
                destination_name=f"Store {i * 2 + 1}",
            )
        )
    return {"config": config, "withdrawals": withdrawals, "today": date(2027, 1, 1)}


@then(
    "one record is produced for that account and category, with a median of the twelve "
    "monthly totals"
)
def one_record_with_median_of_twelve(result: HouseholdSpendResult) -> None:
    assert len(result.records) == 1
    record = result.records[0]
    assert record.month_count == 12
    assert record.median == 350.0


# ---------------------------------------------------------------------------
# AC-2: The figure is the median, not the mean
# ---------------------------------------------------------------------------


@given("eleven monthly totals of 5000 and one of 20000", target_fixture="context")
def eleven_totals_of_5000_and_one_of_20000() -> dict[str, Any]:
    config = _make_config(lookback_months=12, household_spend_one_off_threshold=1_000_000)
    withdrawals = []
    months = _monthly_dates(date(2026, 1, 1), 12)
    for i, month_date in enumerate(months):
        amount = "20000.00" if i == 0 else "5000.00"
        withdrawals.append(
            _withdrawal(month_date, amount, "Groceries", destination_name=f"Store {i}")
        )
    return {"config": config, "withdrawals": withdrawals, "today": date(2027, 1, 1)}


@then("the reported median is 5000 and the reported mean is higher than it")
def median_5000_mean_higher(result: HouseholdSpendResult) -> None:
    record = result.records[0]
    assert record.median == 5000.0
    assert record.mean is not None
    assert record.mean > record.median


# ---------------------------------------------------------------------------
# AC-3: A month with no spending counts as zero
# ---------------------------------------------------------------------------


@given(
    "nine months with grocery spending and three complete months with none",
    target_fixture="context",
)
def nine_months_with_spending_three_without() -> dict[str, Any]:
    config = _make_config(lookback_months=12)
    months = _monthly_dates(date(2026, 1, 1), 12)
    withdrawals = [
        _withdrawal(m, "300.00", "Groceries", destination_name=f"Store {i}")
        for i, m in enumerate(months[:9])
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2027, 1, 1)}


@then("twelve monthly totals contribute to the median, three of them zero")
def twelve_totals_three_zero(result: HouseholdSpendResult) -> None:
    record = result.records[0]
    assert record.month_count == 12
    assert sum(1 for total in record.monthly_totals if total == 0.0) == 3


# ---------------------------------------------------------------------------
# AC-4: A subscription already counted as a pattern is not counted twice
# ---------------------------------------------------------------------------


@given(
    "a monthly subscription in a household spend category that UC2 identified as a pattern",
    target_fixture="context",
)
def monthly_subscription_identified_as_pattern() -> dict[str, Any]:
    config = _make_config(lookback_months=12, min_occurrences=2)
    months = _monthly_dates(date(2026, 1, 1), 12)
    subscription = [
        _withdrawal(m, "99.00", "Groceries", destination_name="Streaming Co") for m in months
    ]
    groceries = [
        _withdrawal(m, "300.00", "Groceries", destination_name=f"Store {i}")
        for i, m in enumerate(months)
    ]
    return {
        "config": config,
        "withdrawals": subscription + groceries,
        "today": date(2027, 1, 1),
        "subscription": subscription,
    }


@then("none of that subscription's transactions appear in any monthly total")
def subscription_excluded_from_totals(
    result: HouseholdSpendResult, context: dict[str, Any]
) -> None:
    assert len(result.records) == 1
    assert result.records[0].median == 300.0


# ---------------------------------------------------------------------------
# AC-5: A large purchase is set aside
# ---------------------------------------------------------------------------


@given(
    "a single withdrawal of 15000 in a household category and a threshold of 2000",
    target_fixture="context",
)
def single_withdrawal_above_threshold() -> dict[str, Any]:
    config = _make_config(household_spend_one_off_threshold=2000.0)
    withdrawals = [
        _withdrawal(date(2026, 6, 10), "15000.00", "Groceries", destination_name="Furniture Store"),
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then(
    "that withdrawal appears as a one-off purchase with its date, amount, payee, category, "
    "and source account"
)
def withdrawal_appears_as_one_off(result: HouseholdSpendResult) -> None:
    assert len(result.one_off_purchases) == 1
    one_off = result.one_off_purchases[0]
    assert one_off.amount == 15000.0
    assert one_off.date == "2026-06-10"
    assert one_off.payee == "Furniture Store"
    assert one_off.category == "Groceries"
    assert one_off.source_account == "Personal Checking"


@then("it contributes to no monthly total")
def one_off_contributes_to_no_monthly_total(result: HouseholdSpendResult) -> None:
    assert result.records == []


# ---------------------------------------------------------------------------
# AC-6: Partial months at the window edges are dropped
# ---------------------------------------------------------------------------


@given("an analysis window starting and ending mid-month", target_fixture="context")
def window_starting_and_ending_mid_month() -> dict[str, Any]:
    config = _make_config(lookback_months=1, household_spend_min_months=1)
    withdrawals = [
        _withdrawal(date(2026, 5, 20), "300.00", "Groceries"),
        _withdrawal(date(2026, 6, 5), "300.00", "Groceries"),
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 6, 15)}


@then("the first and last calendar months contribute no monthly total")
def first_and_last_months_contribute_nothing(result: HouseholdSpendResult) -> None:
    assert result.records == []


# ---------------------------------------------------------------------------
# AC-7: The exclude tag removes a transaction from a household category
# ---------------------------------------------------------------------------


@given(
    "a withdrawal in a household spend category carrying the exclude tag", target_fixture="context"
)
def withdrawal_with_exclude_tag() -> dict[str, Any]:
    config = _make_config(household_spend_exclude_tag="personal", household_spend_min_months=1)
    withdrawals = [_withdrawal(date(2026, 6, 5), "300.00", "Groceries", tags=["personal"])]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("it contributes to no monthly total and is counted in the exclude-tag count")
def contributes_nothing_and_counted_excluded(result: HouseholdSpendResult) -> None:
    assert result.records == []
    assert result.exclude_tag_count == 1


# ---------------------------------------------------------------------------
# AC-8: The include tag admits a transaction from a personal category
# ---------------------------------------------------------------------------


@given(
    "a withdrawal in a category that is not a household spend category, carrying the include tag",
    target_fixture="context",
)
def withdrawal_with_include_tag() -> dict[str, Any]:
    config = _make_config(
        household_spend_categories=["Groceries"],
        household_spend_include_tag="shared",
        household_spend_min_months=1,
        lookback_months=6,
    )
    withdrawals = [_withdrawal(date(2026, 7, 5), "300.00", "Personal Hobby", tags=["shared"])]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("it contributes to its account's monthly total and is counted in the include-tag count")
def contributes_and_counted_included(result: HouseholdSpendResult) -> None:
    assert len(result.records) == 1
    assert result.records[0].category == "Personal Hobby"
    assert result.include_tag_count == 1


# ---------------------------------------------------------------------------
# AC-9: The exclude tag beats the include tag
# ---------------------------------------------------------------------------


@given("a withdrawal carrying both override tags", target_fixture="context")
def withdrawal_with_both_tags() -> dict[str, Any]:
    config = _make_config(
        household_spend_include_tag="shared",
        household_spend_exclude_tag="personal",
        household_spend_min_months=1,
    )
    withdrawals = [
        _withdrawal(date(2026, 6, 5), "300.00", "Groceries", tags=["shared", "personal"]),
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


# ---------------------------------------------------------------------------
# AC-10: No tags configured leaves category behavior intact
# ---------------------------------------------------------------------------


@given(
    "neither override tag is configured, and records with no tags field", target_fixture="context"
)
def neither_tag_configured_no_tags_field() -> dict[str, Any]:
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
    return {"config": config, "withdrawals": [withdrawal], "today": date(2026, 12, 31)}


@then("qualification is by category alone and no error is raised")
def qualification_by_category_alone(result: HouseholdSpendResult) -> None:
    assert len(result.records) == 1


# ---------------------------------------------------------------------------
# AC-11: Too few complete months yields no median
# ---------------------------------------------------------------------------


@given(
    "two complete months of data and a minimum of three complete months required",
    target_fixture="context",
)
def two_complete_months_min_three_required() -> dict[str, Any]:
    config = _make_config(lookback_months=2, household_spend_min_months=3)
    withdrawals = [_withdrawal(date(2026, 2, 10), "300.00", "Groceries")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 3, 15)}


@then("the record carries a month count of 2 and no median figure")
def record_carries_month_count_no_median(result: HouseholdSpendResult) -> None:
    assert len(result.records) == 1
    record = result.records[0]
    assert record.month_count == 1
    assert record.median is None


# ---------------------------------------------------------------------------
# AC-12: An unmatched category is reported
# ---------------------------------------------------------------------------


@given("a configured category appearing on no transaction in the window", target_fixture="context")
def configured_category_with_no_transaction() -> dict[str, Any]:
    config = _make_config(household_spend_categories=["Groceries", "Clothing"])
    withdrawals = [_withdrawal(date(2026, 6, 5), "300.00", "Groceries")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("that category is reported as unmatched")
def category_reported_as_unmatched(result: HouseholdSpendResult) -> None:
    assert result.unmatched_categories == ["Clothing"]


# ---------------------------------------------------------------------------
# AC-13: Two accounts are measured independently
# ---------------------------------------------------------------------------


@given("household spending from two different source accounts", target_fixture="context")
def spending_from_two_accounts() -> dict[str, Any]:
    config = _make_config(lookback_months=12, household_spend_min_months=1)
    months = _monthly_dates(date(2026, 1, 1), 12)
    withdrawals = [
        _withdrawal(
            m, "300.00", "Groceries", source_name="Account A", destination_name=f"Store A{i}"
        )
        for i, m in enumerate(months)
    ]
    withdrawals += [
        _withdrawal(
            m, "150.00", "Groceries", source_name="Account B", destination_name=f"Store B{i}"
        )
        for i, m in enumerate(months)
    ]
    return {"config": config, "withdrawals": withdrawals, "today": date(2027, 1, 1)}


@then("each account and category pair has its own record")
def each_account_has_own_record(result: HouseholdSpendResult) -> None:
    assert len(result.records) == 2
    by_source = {r.source_account: r for r in result.records}
    assert by_source["Account A"].median == 300.0
    assert by_source["Account B"].median == 150.0


# ---------------------------------------------------------------------------
# AC-14: The feature is inert when unconfigured
# ---------------------------------------------------------------------------


@given("the household spend categories are empty", target_fixture="context")
def household_spend_categories_empty() -> dict[str, Any]:
    config = _make_config(household_spend_categories=[])
    withdrawals = [_withdrawal(date(2026, 1, 5), "100.00", "Groceries")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then(
    "no aggregation is performed and the result carries no records, one-offs, or unmatched "
    "categories"
)
def no_aggregation_performed(result: HouseholdSpendResult) -> None:
    assert result.records == []
    assert result.one_off_purchases == []
    assert result.unmatched_categories == []
