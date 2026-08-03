"""TASK-031 step definitions for rounding the monthly equivalent up to the nearest öre."""

from __future__ import annotations

from datetime import date, timedelta

from firefly_python_api import TransactionRead
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer.analyzer import RecurringPattern, identify_recurring
from firefly_bills_analyzer.config import Config

scenarios("../features/TASK-031-round-up-monthly-equivalent.feature")


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


def _transactions_at_interval(
    interval_days: int, amount: str, count: int = 4
) -> list[TransactionRead]:
    start = date(2026, 1, 1)
    return [_transaction(start + timedelta(days=interval_days * i), amount) for i in range(count)]


@given(
    parsers.parse("a quarterly pattern with a mean amount of {amount:g}"),
    target_fixture="transactions",
)
def quarterly_pattern_with_mean_amount(amount: float) -> list[TransactionRead]:
    return _transactions_at_interval(90, f"{amount:.2f}")


@given(
    parsers.parse("a monthly pattern with a mean amount of {amount:g}"),
    target_fixture="transactions",
)
def monthly_pattern_with_mean_amount(amount: float) -> list[TransactionRead]:
    return _transactions_at_interval(30, f"{amount:.2f}")


@given(
    "a payee group whose billing events recur at a median interval outside "
    "every range in `_FREQUENCY_RANGES`",
    target_fixture="transactions",
)
def payee_group_outside_every_range() -> list[TransactionRead]:
    # 50 days falls between the monthly (25-35) and quarterly (80-100)
    # ranges, so `_classify_frequency()` yields "irregular".
    return _transactions_at_interval(50, "5.00")


@when("the pattern is built", target_fixture="pattern")
def build_the_pattern(transactions: list[TransactionRead]) -> RecurringPattern:
    config = _make_config()
    patterns = identify_recurring(transactions, config)
    assert len(patterns) == 1
    return patterns[0]


@then(parsers.parse("its monthly_equivalent is {expected:g}"))
def monthly_equivalent_is(pattern: RecurringPattern, expected: float) -> None:
    assert pattern.monthly_equivalent == expected


@then("its monthly_equivalent is None")
def monthly_equivalent_is_none(pattern: RecurringPattern) -> None:
    assert pattern.monthly_equivalent is None
