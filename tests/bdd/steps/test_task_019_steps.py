"""TASK-019 step definitions for normalized monthly equivalent per pattern."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from firefly_python_api import TransactionRead
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer.analyzer import RecurringPattern, identify_recurring
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.exporter import export

scenarios("../features/TASK-019-monthly-equivalent.feature")


def _make_config(**overrides: object) -> Config:
    base: dict[str, object] = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=1,
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
        household_spend_categories=[],
        household_spend_one_off_threshold=2000.0,
        household_spend_min_months=3,
        household_spend_include_tag=None,
        household_spend_exclude_tag=None,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _transaction(day: date, amount: str) -> TransactionRead:
    return TransactionRead(
        date=day.isoformat(),
        amount=amount,
        destination_name="Payee",
        category_name=None,
        source_name=None,
    )


def _transactions_at_interval(interval_days: int, count: int = 4) -> list[TransactionRead]:
    start = date(2026, 1, 1)
    return [_transaction(start + timedelta(days=interval_days * i), "9.99") for i in range(count)]


@given(
    parsers.parse(
        "a payee group whose billing events recur at a median interval inside "
        "the {label} range ({low:d}-{high:d} days)"
    ),
    target_fixture="transactions",
)
def payee_group_inside_range(label: str, low: int, high: int) -> list[TransactionRead]:
    return _transactions_at_interval((low + high) // 2)


@given(
    "a payee group whose billing events recur at a median interval outside "
    "every range in `_FREQUENCY_RANGES`",
    target_fixture="transactions",
)
def payee_group_outside_every_range() -> list[TransactionRead]:
    # 50 days falls between the monthly (25-35) and quarterly (80-100)
    # ranges, so `_classify_frequency()` yields "irregular".
    return _transactions_at_interval(50)


@given(
    "a payee group that produces exactly one billing event, so no interval "
    "can be computed and `median_interval_days` is 0.0",
    target_fixture="transactions",
)
def payee_group_single_event() -> list[TransactionRead]:
    return _transactions_at_interval(30, count=1)


@when("`identify_recurring()` builds the pattern", target_fixture="pattern")
def build_the_pattern(transactions: list[TransactionRead]) -> RecurringPattern:
    config = _make_config()
    patterns = identify_recurring(transactions, config)
    assert len(patterns) == 1
    return patterns[0]


@then(
    parsers.parse(
        "the pattern's `monthly_equivalent` equals its `amount_mean` divided by {divisor:d}"
    )
)
def monthly_equivalent_equals_mean_divided_by(pattern: RecurringPattern, divisor: int) -> None:
    assert pattern.monthly_equivalent == pattern.amount_mean / divisor


@then("the pattern's `frequency` is `irregular` and its `monthly_equivalent` is `None`")
def pattern_is_irregular_with_no_monthly_equivalent(pattern: RecurringPattern) -> None:
    assert pattern.frequency == "irregular"
    assert pattern.monthly_equivalent is None


def _quarterly_and_irregular_patterns() -> list[RecurringPattern]:
    quarterly = RecurringPattern(
        destination_name="Water Bill",
        category_name=None,
        occurrences=4,
        amount_min=90.0,
        amount_max=90.0,
        amount_mean=90.0,
        median_interval_days=90.0,
        frequency="quarterly",
        confidence=0.9,
        source_account_name=None,
        source_account_varies=False,
        monthly_equivalent=30.0,
    )
    irregular = RecurringPattern(
        destination_name="Corner Shop",
        category_name=None,
        occurrences=3,
        amount_min=5.0,
        amount_max=8.0,
        amount_mean=6.5,
        median_interval_days=50.0,
        frequency="irregular",
        confidence=0.4,
        source_account_name=None,
        source_account_varies=False,
        monthly_equivalent=None,
    )
    return [quarterly, irregular]


@given(
    "a list of patterns containing one quarterly pattern and one irregular pattern",
    target_fixture="patterns",
)
def list_of_quarterly_and_irregular_patterns() -> list[RecurringPattern]:
    return _quarterly_and_irregular_patterns()


@given("the same list of patterns", target_fixture="patterns")
def the_same_list_of_patterns() -> list[RecurringPattern]:
    return _quarterly_and_irregular_patterns()


@when(
    parsers.parse('`exporter.export(patterns, "{fmt}", path)` writes the file'),
    target_fixture="export_path",
)
def export_patterns(patterns: list[RecurringPattern], fmt: str, tmp_path: Path) -> Path:
    path = tmp_path / f"out.{fmt}"
    export(patterns, fmt, path)
    return path


@then(
    "the header row contains a `monthly_equivalent` column, the quarterly "
    "row carries its computed value, and the irregular row carries an empty cell"
)
def csv_carries_monthly_equivalent(export_path: Path) -> None:
    import csv

    with export_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        assert "monthly_equivalent" in reader.fieldnames
        rows = list(reader)

    by_name = {row["destination_name"]: row for row in rows}
    assert by_name["Water Bill"]["monthly_equivalent"] == "30.0"
    assert by_name["Corner Shop"]["monthly_equivalent"] == ""


@then("each object carries a `monthly_equivalent` key, `null` for the irregular pattern")
def json_carries_monthly_equivalent(export_path: Path) -> None:
    import json

    data = json.loads(export_path.read_text(encoding="utf-8"))

    by_name = {obj["destination_name"]: obj for obj in data}
    assert by_name["Water Bill"]["monthly_equivalent"] == 30.0
    assert by_name["Corner Shop"]["monthly_equivalent"] is None
