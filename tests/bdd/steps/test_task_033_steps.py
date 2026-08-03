"""TASK-033 step definitions for per-category one-off purchase thresholds
(FR-47e, FR-47f, FR-48c, FR-51c, UC13).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

from firefly_python_api import TransactionRead
from pytest_bdd import given, scenarios, then, when

from firefly_bills_analyzer import exporter as exporter_module
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.household_spend import HouseholdSpendResult, aggregate_household_spend

scenarios("../features/TASK-033-per-category-one-off-thresholds.feature")


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
        household_spend_categories=["Mat och hushåll", "Transport"],
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={},
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
# AC-1: Withdrawal under category override threshold is included in
# household spend
# ---------------------------------------------------------------------------


@given(
    "a withdrawal in a category with a configured threshold override, for an amount above "
    "the default threshold but below the override",
    target_fixture="context",
)
def withdrawal_above_default_below_override() -> dict[str, Any]:
    config = _make_config(
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Mat och hushåll": 3000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "2500.00", "Mat och hushåll")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("the withdrawal is counted in the household spend monthly totals")
def withdrawal_counted_in_monthly_totals(
    result: HouseholdSpendResult, context: dict[str, Any]
) -> None:
    assert result.one_off_purchases == []
    expected_total = sum(float(w["amount"]) for w in context["withdrawals"])
    total = sum(month_total for record in result.records for month_total in record.monthly_totals)
    assert total == expected_total


# ---------------------------------------------------------------------------
# AC-2: Withdrawal under default threshold in unconfigured category is
# included in household spend
# ---------------------------------------------------------------------------


@given(
    "a withdrawal in a category with no threshold override, for an amount under the default "
    "threshold, while other categories have overrides configured",
    target_fixture="context",
)
def withdrawal_under_default_no_override() -> dict[str, Any]:
    config = _make_config(
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Mat och hushåll": 3000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "1800.00", "Transport")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


# ---------------------------------------------------------------------------
# AC-3: Exported one-off purchase includes the threshold amount that
# excluded it
# ---------------------------------------------------------------------------


@given(
    "a one-off purchase excluded by its category's threshold override",
    target_fixture="context",
)
def one_off_purchase_excluded_by_override(tmp_path: Path) -> dict[str, Any]:
    config = _make_config(
        household_spend_one_off_threshold=2000.0,
        household_spend_one_off_thresholds={"Transport": 6000.0},
    )
    withdrawals = [
        _withdrawal(date(2026, 6, 10), "8000.00", "Transport", destination_name="Car Workshop")
    ]
    return {
        "config": config,
        "withdrawals": withdrawals,
        "today": date(2026, 12, 31),
        "tmp_path": tmp_path,
    }


@when("the household spend export runs", target_fixture="export_result")
def household_spend_export_runs(context: dict[str, Any]) -> dict[str, Any]:
    result = _run(context["withdrawals"], context["config"], context["today"])
    path = context["tmp_path"] / "household_spend.csv"
    exporter_module.export_household_spend(result, "csv", path)
    return {"result": result, "path": path}


@then("the exported one-off row carries the threshold amount that excluded it")
def exported_one_off_row_carries_threshold(export_result: dict[str, Any]) -> None:
    import csv

    with export_result["path"].open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    one_off_rows = [r for r in rows if r["record_type"] == "one-off"]
    assert len(one_off_rows) == 1
    assert one_off_rows[0]["threshold"] == "6000.0"


# ---------------------------------------------------------------------------
# AC-4: Unmatched threshold override category is reported
# ---------------------------------------------------------------------------


@given(
    "a threshold override configured for a category absent from the household spend categories",
    target_fixture="context",
)
def threshold_override_for_absent_category() -> dict[str, Any]:
    config = _make_config(
        household_spend_categories=["Mat och hushåll"],
        household_spend_one_off_thresholds={"Nonexistent Category": 5000.0},
    )
    withdrawals = [_withdrawal(date(2026, 6, 10), "300.00", "Mat och hushåll")]
    return {"config": config, "withdrawals": withdrawals, "today": date(2026, 12, 31)}


@then("the category is reported as an unmatched threshold override")
def category_reported_as_unmatched_threshold_override(result: HouseholdSpendResult) -> None:
    assert result.unmatched_threshold_overrides == ["Nonexistent Category"]
