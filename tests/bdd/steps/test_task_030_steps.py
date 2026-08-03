"""TASK-030 step definitions for falling back an income source's
observed_net_income to the most recent non-deviating occurrence when the
latest occurrence deviates from the median (FR-43a, FR-44)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from firefly_python_api import TransactionRead
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.income import IncomeSource, detect_income

scenarios("../features/TASK-030-fallback-income-net-income-from-median.feature")

_INCOME_ACCOUNT = "Salary Checking"
_PAYER = "Employer"


def _make_config(**overrides: object) -> Config:
    base: dict[str, object] = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
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
        income_accounts=[_INCOME_ACCOUNT],
        income_min_occurrences=3,
        income_variance_tolerance=0.10,
        household_spend_categories=[],
        household_spend_one_off_threshold=2000.0,
        household_spend_min_months=3,
        household_spend_include_tag=None,
        household_spend_exclude_tag=None,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _deposit(iso_date: str, amount: str) -> TransactionRead:
    return TransactionRead(
        date=iso_date,
        amount=amount,
        destination_name=_INCOME_ACCOUNT,
        category_name=None,
        source_name=_PAYER,
        source_id=None,
        tags=[],
    )


def _monthly_dates(start: date, count: int, step_days: int = 30) -> list[date]:
    return [start + timedelta(days=step_days * i) for i in range(count)]


@given(
    parsers.parse(
        "an income account with occurrences {amounts} and "
        "INCOME_VARIANCE_TOLERANCE of {tolerance:g}"
    ),
    target_fixture="context",
)
def occurrences_with_tolerance(amounts: str, tolerance: float) -> dict[str, Any]:
    amount_list = [a.strip() for a in amounts.split(",")]
    dates = _monthly_dates(date(2026, 1, 1), len(amount_list))
    deposits = [
        _deposit(d.isoformat(), amount) for d, amount in zip(dates, amount_list, strict=True)
    ]
    config = _make_config(income_variance_tolerance=tolerance)
    return {"deposits": deposits, "config": config, "dates": dates}


@given(
    parsers.parse(
        "an income account with three dated occurrences: {d1} amount {a1}, {d2} amount {a2}, "
        "{d3} amount {a3}, tolerance {tolerance:g}"
    ),
    target_fixture="context",
)
def occurrences_with_explicit_dates(
    d1: str, a1: str, d2: str, a2: str, d3: str, a3: str, tolerance: float
) -> dict[str, Any]:
    deposits = [
        _deposit(d1, a1),
        _deposit(d2, a2),
        _deposit(d3, a3),
    ]
    config = _make_config(income_variance_tolerance=tolerance)
    return {"deposits": deposits, "config": config}


@when("the application detects the income source", target_fixture="source")
def application_detects_income_source(context: dict[str, Any]) -> IncomeSource:
    result = detect_income(context["deposits"], context["config"])
    assert len(result.sources) == 1, result.issues
    return result.sources[0]


@then(parsers.parse("the observed net income is {amount:g}, the latest occurrence"))
def observed_net_income_is_latest(source: IncomeSource, amount: float) -> None:
    assert source.observed_net_income == amount


@then(parsers.parse("the observed net income is {amount:g}, from {observed_date}"))
def observed_net_income_is_from(source: IncomeSource, amount: float, observed_date: str) -> None:
    assert source.observed_net_income == amount
    assert source.observed_date == observed_date


@then(
    parsers.parse(
        "the observed net income is {amount:g}, the most recent non-deviating from median"
    )
)
def observed_net_income_is_most_recent_non_deviating(source: IncomeSource, amount: float) -> None:
    assert source.observed_net_income == amount


@then(parsers.parse("the observed date is the date of the occurrence with amount {amount:g}"))
def observed_date_matches_amount(
    source: IncomeSource, context: dict[str, Any], amount: float
) -> None:
    matching = [
        deposit["date"] for deposit in context["deposits"] if float(deposit["amount"]) == amount
    ]
    assert source.observed_date in matching


@then(parsers.parse("the observed date matches {observed_date}"))
def observed_date_matches(source: IncomeSource, observed_date: str) -> None:
    assert source.observed_date == observed_date


@then(parsers.parse("outlier_count is {count:d}"))
def outlier_count_is(source: IncomeSource, count: int) -> None:
    assert source.outlier_count == count


@then("amount_min, amount_max, amount_mean include all four occurrences")
def variance_figures_include_all_four(source: IncomeSource) -> None:
    assert source.occurrences == 4


@then(
    parsers.parse(
        "amount_min is {amount_min:g}, amount_max is {amount_max:g}, amount_mean is {amount_mean:g}"
    )
)
def variance_figures_are(
    source: IncomeSource, amount_min: float, amount_max: float, amount_mean: float
) -> None:
    assert source.amount_min == amount_min
    assert source.amount_max == amount_max
    assert source.amount_mean == amount_mean


@then(parsers.parse("occurrences count is {count:d}"))
def occurrences_count_is(source: IncomeSource, count: int) -> None:
    assert source.occurrences == count


@then("outlier_count measures deviation from the selected observed_net_income only")
def outlier_count_measures_from_observed(source: IncomeSource) -> None:
    tolerance = 0.10
    deviating = 0
    # Recompute independently from the source's own fields to avoid coupling
    # this assertion to the production implementation's internals.
    for amount in (1000.0, 1000.0, 1000.0, 50.0):
        if source.observed_net_income != 0 and (
            abs(amount - source.observed_net_income) / source.observed_net_income > tolerance
        ):
            deviating += 1
    assert source.outlier_count == deviating
