import time
from datetime import date, timedelta

from firefly_python_api import TransactionRead
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import (
    _classify_frequency,
    _confidence,
    identify_recurring,
)
from firefly_bills_analyzer.config import Config

CATEGORIES = ["Streaming", "Groceries", "Utilities"]


def _make_config(**overrides: object) -> Config:
    base: dict[str, object] = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=2,
        amount_margin=0.10,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
        uncategorized_confidence_penalty=0.10,
        uncategorized_behavior="neutral",
        include_categories=[],
        exclude_categories=[],
        dry_run=False,
        export_format="none",
        web_port=5000,
        web_host="127.0.0.1",
        cache_dir="./cache",
        cache_ttl_categories=86400,
        cache_ttl_bills=3600,
        cache_ttl_transactions=3600,
        cache_ttl_payees=86400,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _transaction(
    day: date, amount: str, destination_name: str | None, category_name: str | None
) -> TransactionRead:
    return TransactionRead(
        date=day.isoformat(),
        amount=amount,
        destination_name=destination_name,
        category_name=category_name,
    )


# ---------------------------------------------------------------------------
# Frequency classification
# ---------------------------------------------------------------------------


@given(st.floats(min_value=25, max_value=35))
def test_classify_frequency_monthly(days: float) -> None:
    assert _classify_frequency(days) == "monthly"


@given(st.floats(min_value=80, max_value=100))
def test_classify_frequency_quarterly(days: float) -> None:
    assert _classify_frequency(days) == "quarterly"


@given(st.floats(min_value=160, max_value=200))
def test_classify_frequency_half_yearly(days: float) -> None:
    assert _classify_frequency(days) == "half-yearly"


@given(st.floats(min_value=340, max_value=390))
def test_classify_frequency_yearly(days: float) -> None:
    assert _classify_frequency(days) == "yearly"


@given(
    st.one_of(
        st.floats(min_value=0, max_value=24.999),
        st.floats(min_value=35.001, max_value=79.999),
        st.floats(min_value=100.001, max_value=159.999),
        st.floats(min_value=200.001, max_value=339.999),
        st.floats(min_value=390.001, max_value=1000),
    )
)
def test_classify_frequency_irregular(days: float) -> None:
    assert _classify_frequency(days) == "irregular"


# ---------------------------------------------------------------------------
# Confidence formula
# ---------------------------------------------------------------------------


@given(
    occurrences=st.integers(min_value=1, max_value=50),
    median_days=st.floats(min_value=0, max_value=400),
    stddev_days=st.floats(min_value=0, max_value=400),
    mean_amount=st.floats(min_value=0, max_value=10000),
    stddev_amount=st.floats(min_value=0, max_value=10000),
)
def test_confidence_always_in_range(
    occurrences: int,
    median_days: float,
    stddev_days: float,
    mean_amount: float,
    stddev_amount: float,
) -> None:
    config = _make_config()
    confidence = _confidence(
        occurrences=occurrences,
        median_days=median_days,
        stddev_days=stddev_days,
        mean_amount=mean_amount,
        stddev_amount=stddev_amount,
        category_name=None,
        config=config,
    )
    assert 0.0 <= confidence <= 1.0


@given(
    occurrences=st.integers(min_value=1, max_value=50),
    median_days=st.floats(min_value=1, max_value=400),
    mean_amount=st.floats(min_value=1, max_value=10000),
)
def test_confidence_perfect_regularity_and_amount_has_no_deviation_penalty(
    occurrences: int, median_days: float, mean_amount: float
) -> None:
    config = _make_config()
    confidence = _confidence(
        occurrences=occurrences,
        median_days=median_days,
        stddev_days=0.0,
        mean_amount=mean_amount,
        stddev_amount=0.0,
        category_name=None,
        config=config,
    )
    expected = (
        min(0.4 * min(occurrences / 4, 1.0) + 0.4 + 0.2, 1.0)
        - config.uncategorized_confidence_penalty
    )
    assert confidence == max(0.0, expected)


def test_confidence_category_boost_applied_when_in_include_list() -> None:
    config = _make_config(include_categories=["Streaming"])
    with_category = _confidence(
        occurrences=2,
        median_days=30,
        stddev_days=5,
        mean_amount=10,
        stddev_amount=2,
        category_name="Streaming",
        config=config,
    )
    without_category = _confidence(
        occurrences=2,
        median_days=30,
        stddev_days=5,
        mean_amount=10,
        stddev_amount=2,
        category_name="Groceries",
        config=config,
    )
    assert with_category > without_category


def test_confidence_uncategorized_neutral_reduces_confidence() -> None:
    config = _make_config(uncategorized_behavior="neutral")
    categorized = _confidence(
        occurrences=4,
        median_days=30,
        stddev_days=0,
        mean_amount=10,
        stddev_amount=0,
        category_name="Groceries",
        config=config,
    )
    uncategorized = _confidence(
        occurrences=4,
        median_days=30,
        stddev_days=0,
        mean_amount=10,
        stddev_amount=0,
        category_name=None,
        config=config,
    )
    assert uncategorized < categorized


@given(st.sampled_from(["include", "exclude"]))
def test_confidence_uncategorized_non_neutral_does_not_reduce_confidence(
    behavior: str,
) -> None:
    config = _make_config(uncategorized_behavior=behavior)
    categorized = _confidence(
        occurrences=4,
        median_days=30,
        stddev_days=0,
        mean_amount=10,
        stddev_amount=0,
        category_name="Groceries",
        config=config,
    )
    uncategorized = _confidence(
        occurrences=4,
        median_days=30,
        stddev_days=0,
        mean_amount=10,
        stddev_amount=0,
        category_name=None,
        config=config,
    )
    assert uncategorized == categorized


# ---------------------------------------------------------------------------
# identify_recurring: happy path, filtering, sorting
# ---------------------------------------------------------------------------


def test_happy_path_identifies_monthly_pattern() -> None:
    config = _make_config()
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=30 * i), "9.99", "Netflix", "Streaming")
        for i in range(6)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.destination_name == "Netflix"
    assert pattern.category_name == "Streaming"
    assert pattern.occurrences == 6
    assert pattern.frequency == "monthly"
    assert pattern.amount_min == 9.99
    assert pattern.amount_max == 9.99
    assert pattern.amount_mean == 9.99


def test_single_occurrence_is_filtered_out() -> None:
    config = _make_config(min_occurrences=2)
    transactions = [_transaction(date(2026, 1, 1), "9.99", "Netflix", "Streaming")]

    assert identify_recurring(transactions, config) == []


def test_destination_name_none_is_ignored() -> None:
    config = _make_config(min_occurrences=1)
    transactions = [_transaction(date(2026, 1, 1), "9.99", None, "Streaming")]

    assert identify_recurring(transactions, config) == []


def test_results_sorted_by_confidence_descending() -> None:
    config = _make_config()
    start = date(2026, 1, 1)
    regular = [
        _transaction(start + timedelta(days=30 * i), "9.99", "Netflix", "Streaming")
        for i in range(6)
    ]
    irregular = [
        _transaction(start + timedelta(days=1), "5.00", "Corner Shop", None),
        _transaction(start + timedelta(days=97), "40.00", "Corner Shop", None),
    ]

    patterns = identify_recurring(regular + irregular, config)

    assert [p.destination_name for p in patterns] == ["Netflix", "Corner Shop"]
    assert patterns[0].confidence >= patterns[1].confidence


def test_uncategorized_neutral_penalty_lowers_pattern_confidence() -> None:
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=30 * i), "9.99", "Netflix", None) for i in range(6)
    ]

    neutral_config = _make_config(uncategorized_behavior="neutral")
    include_config = _make_config(uncategorized_behavior="include")
    neutral_patterns = identify_recurring(transactions, neutral_config)
    include_patterns = identify_recurring(transactions, include_config)

    assert neutral_patterns[0].confidence < include_patterns[0].confidence


# ---------------------------------------------------------------------------
# Performance sanity check (NFR-05, full benchmark owned by TASK-009)
# ---------------------------------------------------------------------------


def test_analysis_of_24_months_completes_quickly() -> None:
    config = _make_config()
    start = date(2024, 7, 1)
    transactions = []
    for payee_index in range(200):
        for occurrence in range(24):
            transactions.append(
                _transaction(
                    start + timedelta(days=30 * occurrence),
                    "9.99",
                    f"Payee {payee_index}",
                    "Streaming",
                )
            )

    started = time.monotonic()
    identify_recurring(transactions, config)
    elapsed = time.monotonic() - started

    assert elapsed < 60
