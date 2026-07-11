import time
from collections import Counter
from datetime import date, timedelta

import pytest
from firefly_python_api import TransactionRead
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import (
    _classify_frequency,
    _collapse_into_billing_events,
    _confidence,
    _split_into_amount_clusters,
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
        amount_cluster_tolerance=0.15,
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
    day: date,
    amount: str,
    destination_name: str | None,
    category_name: str | None,
    source_name: str | None = None,
) -> TransactionRead:
    return TransactionRead(
        date=day.isoformat(),
        amount=amount,
        destination_name=destination_name,
        category_name=category_name,
        source_name=source_name,
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
        _transaction(start + timedelta(days=97), "5.50", "Corner Shop", None),
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


def test_source_account_resolved_when_all_transactions_share_source() -> None:
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(
            start + timedelta(days=30 * i), "9.99", "Netflix", "Streaming", source_name="Checking"
        )
        for i in range(4)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].source_account_name == "Checking"
    assert patterns[0].source_account_varies is False


def test_source_account_is_mode_when_transactions_span_two_sources() -> None:
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start, "9.99", "Netflix", "Streaming", source_name="Checking"),
        _transaction(
            start + timedelta(days=30), "9.99", "Netflix", "Streaming", source_name="Checking"
        ),
        _transaction(
            start + timedelta(days=60), "9.99", "Netflix", "Streaming", source_name="Savings"
        ),
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].source_account_name == "Checking"
    assert patterns[0].source_account_varies is True


def test_source_account_none_when_no_transactions_have_a_source_name() -> None:
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=30 * i), "9.99", "Netflix", "Streaming")
        for i in range(4)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].source_account_name is None
    assert patterns[0].source_account_varies is False


@given(
    st.lists(
        st.one_of(st.none(), st.sampled_from(["Checking", "Savings", "Cash"])),
        min_size=2,
        max_size=20,
    )
)
def test_source_account_resolution_is_statistical_mode_of_non_none_values(
    source_names: list[str | None],
) -> None:
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(
            start + timedelta(days=i), "9.99", "Netflix", "Streaming", source_name=source_name
        )
        for i, source_name in enumerate(source_names)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    pattern = patterns[0]

    non_none = [s for s in source_names if s is not None]
    distinct = set(non_none)

    if not non_none:
        assert pattern.source_account_name is None
        assert pattern.source_account_varies is False
    else:
        expected_mode = Counter(non_none).most_common(1)[0][0]
        assert pattern.source_account_name == expected_mode
        assert pattern.source_account_varies == (len(distinct) > 1)


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


# ---------------------------------------------------------------------------
# Amount clustering (FR-32a/b)
# ---------------------------------------------------------------------------


def test_split_into_amount_clusters_single_cluster_within_tolerance() -> None:
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 2, 1), "10.50", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_split_into_amount_clusters_no_split_without_co_occurrence() -> None:
    """A payee whose amount varies widely over time, but never shows more than
    one amount on the same date, must not be split (regression for "EON": a
    metered electricity bill priced by season and consumption, 661-4426 kr,
    never two transactions on the same date)."""
    transactions = [
        _transaction(date(2026, 1, 1), "661.00", "EON", None),
        _transaction(date(2026, 2, 1), "4426.00", "EON", None),
        _transaction(date(2026, 3, 1), "2029.00", "EON", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_split_into_amount_clusters_splits_on_co_occurring_amounts() -> None:
    """Two differing amounts on the same date reveal genuinely parallel
    charges (e.g. two subscriptions billed through the same merchant); other
    transactions are assigned to whichever cluster's mean is closest."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "11.00", "Payee", None),
        _transaction(date(2026, 3, 1), "26.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 2
    assert sorted(float(t["amount"]) for t in clusters[0]) == [10.00, 11.00]
    assert sorted(float(t["amount"]) for t in clusters[1]) == [25.00, 26.00]


def test_split_into_amount_clusters_tolerance_is_configurable() -> None:
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "12.00", "Payee", None),
        _transaction(date(2026, 2, 1), "10.00", "Payee", None),
        _transaction(date(2026, 2, 1), "12.00", "Payee", None),
    ]

    narrow = _split_into_amount_clusters(transactions, tolerance=0.10)
    wide = _split_into_amount_clusters(transactions, tolerance=0.30)

    assert len(narrow) == 2  # gap 2.0 > 10% of 10.00
    assert len(wide) == 1  # gap 2.0 <= 30% of 10.00


def test_split_into_amount_clusters_below_threshold_seed_absorbs_no_extra_members() -> None:
    """When a co-occurrence seed cluster only ever has one member (its own
    co-occurrence transaction), it stays a small, distinct cluster rather than
    being merged into the larger one."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "10.00", "Payee", None),
        _transaction(date(2026, 3, 1), "10.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 3]


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=5),
            st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=15,
    ),
    st.floats(min_value=0.01, max_value=1.0),
)
def test_split_into_amount_clusters_preserves_all_transactions_and_is_deterministic(
    day_amount_pairs: list[tuple[int, float]], tolerance: float
) -> None:
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=day_offset), f"{amount:.2f}", "Payee", None)
        for day_offset, amount in day_amount_pairs
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance)
    clusters_again = _split_into_amount_clusters(transactions, tolerance)

    def _amounts(cs: list[list[TransactionRead]]) -> list[list[float]]:
        return [[float(t["amount"]) for t in c] for c in cs]

    assert _amounts(clusters) == _amounts(clusters_again)  # deterministic
    assert sum(len(c) for c in clusters) == len(transactions)  # every transaction kept
    assert all(len(c) > 0 for c in clusters)  # no empty clusters


# ---------------------------------------------------------------------------
# Billing event collapse (FR-33a)
# ---------------------------------------------------------------------------


def test_collapse_into_billing_events_sums_same_date_transactions() -> None:
    transactions = [
        _transaction(date(2026, 7, 11), "15.00", "Payee", None),
        _transaction(date(2026, 7, 11), "15.00", "Payee", None),
    ]

    events = _collapse_into_billing_events(transactions)

    assert events == [{"date": "2026-07-11", "amount": 30.00, "count": 2}]


def test_collapse_into_billing_events_multiple_dates() -> None:
    transactions = [
        _transaction(date(2026, 7, 11), "15.00", "Payee", None),
        _transaction(date(2026, 7, 11), "15.00", "Payee", None),
        _transaction(date(2026, 7, 18), "15.00", "Payee", None),
        _transaction(date(2026, 7, 25), "15.00", "Payee", None),
        _transaction(date(2026, 7, 25), "15.00", "Payee", None),
    ]

    events = _collapse_into_billing_events(transactions)

    assert events == [
        {"date": "2026-07-11", "amount": 30.00, "count": 2},
        {"date": "2026-07-18", "amount": 15.00, "count": 1},
        {"date": "2026-07-25", "amount": 30.00, "count": 2},
    ]


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=10),
            st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=15,
    )
)
def test_collapse_into_billing_events_preserves_total_and_is_deterministic(
    day_amount_pairs: list[tuple[int, float]],
) -> None:
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=day_offset), f"{amount:.2f}", "Payee", None)
        for day_offset, amount in day_amount_pairs
    ]

    events = _collapse_into_billing_events(transactions)
    events_again = _collapse_into_billing_events(transactions)

    assert events == events_again  # deterministic

    total_before = sum(float(t["amount"]) for t in transactions)
    total_after = sum(float(e["amount"]) for e in events)
    assert total_after == pytest.approx(total_before)

    dates_seen = [e["date"] for e in events]
    assert dates_seen == sorted(dates_seen)
    assert len(dates_seen) == len(set(dates_seen))


# ---------------------------------------------------------------------------
# identify_recurring integration: clustering + billing events (TASK-012)
# ---------------------------------------------------------------------------


def test_single_amount_cluster_has_no_disambiguation() -> None:
    config = _make_config()
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start + timedelta(days=30 * i), "9.99", "Netflix", "Streaming")
        for i in range(4)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].amount_for_name is None


def test_payee_splits_into_two_independent_patterns_by_amount() -> None:
    config = _make_config()
    start = date(2026, 1, 1)
    cheap = [_transaction(start + timedelta(days=30 * i), "10.00", "Apple", None) for i in range(4)]
    expensive = [
        _transaction(start + timedelta(days=30 * i), "25.00", "Apple", None) for i in range(4)
    ]

    patterns = identify_recurring(cheap + expensive, config)

    assert len(patterns) == 2
    assert sorted(p.amount_mean for p in patterns) == [10.00, 25.00]


def test_amount_for_name_set_when_multiple_clusters_qualify() -> None:
    config = _make_config()
    start = date(2026, 1, 1)
    cheap = [_transaction(start + timedelta(days=30 * i), "10.00", "Apple", None) for i in range(4)]
    expensive = [
        _transaction(start + timedelta(days=30 * i), "25.00", "Apple", None) for i in range(4)
    ]

    patterns = identify_recurring(cheap + expensive, config)

    by_amount = {p.amount_mean: p for p in patterns}
    assert by_amount[10.00].amount_for_name == "10.00"
    assert by_amount[25.00].amount_for_name == "25.00"


def test_below_threshold_cluster_does_not_produce_pattern_or_disambiguation() -> None:
    """A co-occurrence seed with only one member ends up in its own cluster
    (per FR-32a's nearest-mean assignment) but fails min_occurrences on its
    own and is dropped, leaving the well-populated cluster as the sole
    pattern with no amount disambiguation."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    co_occurrence = [
        _transaction(start, "10.00", "Apple", None),
        _transaction(start, "25.00", "Apple", None),
    ]
    more_of_the_common_amount = [
        _transaction(start + timedelta(days=30 * i), "10.00", "Apple", None) for i in range(1, 3)
    ]

    patterns = identify_recurring(co_occurrence + more_of_the_common_amount, config)

    assert len(patterns) == 1
    assert patterns[0].amount_for_name is None
    assert patterns[0].amount_mean == 10.00
    assert patterns[0].occurrences == 3


def test_same_day_transactions_collapse_for_interval_calculation() -> None:
    """Regression for the SEB case: two same-day, same-amount transactions per
    month (e.g. billed once per household member) must not corrupt the median
    interval to 0 and misclassify a clean monthly pattern as irregular."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 2)
    transactions = []
    for month in range(6):
        day = start + timedelta(days=31 * month)
        transactions.append(_transaction(day, "276.00", "SEB", "Försäkring"))
        transactions.append(_transaction(day, "276.00", "SEB", "Försäkring"))

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.occurrences == 6  # billing events, not 12 raw transactions
    assert pattern.frequency == "monthly"
    assert pattern.amount_mean == 552.00  # summed per billing event


def test_source_account_resolution_uses_pre_collapse_transactions() -> None:
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 2)
    transactions = [
        _transaction(start, "276.00", "SEB", "Försäkring", source_name="Checking"),
        _transaction(start, "276.00", "SEB", "Försäkring", source_name="Savings"),
        _transaction(
            start + timedelta(days=31), "276.00", "SEB", "Försäkring", source_name="Checking"
        ),
        _transaction(
            start + timedelta(days=31), "276.00", "SEB", "Försäkring", source_name="Checking"
        ),
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].source_account_name == "Checking"
    assert patterns[0].source_account_varies is True
    assert patterns[0].occurrences == 2  # 2 billing events despite 4 raw transactions


def test_amount_cluster_tolerance_affects_clustering() -> None:
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start, "10.00", "Payee", None),
        _transaction(start, "12.00", "Payee", None),
        _transaction(start + timedelta(days=30), "10.00", "Payee", None),
        _transaction(start + timedelta(days=30), "12.00", "Payee", None),
    ]

    narrow_config = _make_config(amount_cluster_tolerance=0.10, min_occurrences=2)
    wide_config = _make_config(amount_cluster_tolerance=0.30, min_occurrences=2)

    narrow_patterns = identify_recurring(transactions, narrow_config)
    wide_patterns = identify_recurring(transactions, wide_config)

    assert len(narrow_patterns) == 2  # 10.00 and 12.00 split (gap 2.0 > 10% of 10.00)
    assert len(wide_patterns) == 1  # merged (gap 2.0 <= 30% of 10.00)


def test_widely_varying_single_amount_payee_is_not_fragmented() -> None:
    """Regression for "EON": a metered electricity bill with no two
    transactions ever on the same date must remain one pattern, however much
    its amount fluctuates by season and consumption, rather than being
    fragmented into several low-confidence sub-clusters."""
    config = _make_config(min_occurrences=2)
    start = date(2025, 1, 28)
    amounts = [
        "2542.00",
        "2876.00",
        "3223.00",
        "2029.00",
        "1036.00",
        "1164.00",
        "661.00",
        "1035.00",
        "1465.00",
        "1530.00",
        "1938.00",
        "2681.00",
        "1915.00",
        "4426.00",
        "1854.00",
    ]
    transactions = [
        _transaction(start + timedelta(days=31 * i), amount, "EON", "El och nätavgift")
        for i, amount in enumerate(amounts)
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].occurrences == len(amounts)
    assert patterns[0].amount_for_name is None
    assert patterns[0].frequency == "monthly"
