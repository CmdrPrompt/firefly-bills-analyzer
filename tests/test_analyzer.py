import time
from collections import Counter
from datetime import date, timedelta

import pytest
from firefly_python_api import TransactionRead
from hypothesis import example, given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import (
    _classify_frequency,
    _collapse_into_billing_events,
    _confidence,
    _partition_by_source_account,
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


def test_source_account_split_produces_separate_patterns_per_account() -> None:
    """FR-32d: a payee whose transactions span two source accounts is
    partitioned by account before clustering, so each account gets its own
    pattern rather than one pattern with `source_account_varies = True`."""
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
        _transaction(
            start + timedelta(days=90), "9.99", "Netflix", "Streaming", source_name="Savings"
        ),
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 2
    by_source = {p.source_account_name: p for p in patterns}
    assert by_source["Checking"].occurrences == 2
    assert by_source["Checking"].source_account_varies is False
    assert by_source["Savings"].occurrences == 2
    assert by_source["Savings"].source_account_varies is False


def test_source_account_subgroup_below_min_occurrences_is_dropped() -> None:
    """FR-32d: a source-account subgroup with too few transactions to meet
    `MIN_OCCURRENCES` on its own does not produce a pattern, even though the
    payee as a whole has enough transactions across accounts combined."""
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
    assert patterns[0].source_account_varies is False


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
def test_source_account_partition_produces_one_pattern_per_qualifying_account(
    source_names: list[str | None],
) -> None:
    """FR-32d: each distinct source account (including "no source name") that
    meets `MIN_OCCURRENCES` on its own produces exactly one pattern, never a
    "varies" pattern, since accounts are partitioned before clustering."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(
            start + timedelta(days=i), "9.99", "Netflix", "Streaming", source_name=source_name
        )
        for i, source_name in enumerate(source_names)
    ]

    patterns = identify_recurring(transactions, config)

    counts = Counter(source_names)
    qualifying = {name for name, count in counts.items() if count >= 2}

    assert len(patterns) == len(qualifying)
    for pattern in patterns:
        assert pattern.source_account_name in qualifying
        assert pattern.source_account_varies is False
        assert pattern.occurrences == counts[pattern.source_account_name]


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
# Source-account partitioning (FR-32d)
# ---------------------------------------------------------------------------


def test_partition_by_source_account_groups_by_source_name() -> None:
    transactions = [
        _transaction(date(2026, 1, 1), "12000.00", "ICA", None, source_name="SEB Räkningskonto"),
        _transaction(date(2026, 2, 1), "12000.00", "ICA", None, source_name="SEB Räkningskonto"),
        _transaction(date(2026, 1, 5), "50.00", "ICA", None, source_name="ICA-banken Matkonto"),
        _transaction(date(2026, 2, 5), "60.00", "ICA", None, source_name="ICA-banken Matkonto"),
    ]

    subgroups = _partition_by_source_account(transactions)

    assert len(subgroups) == 2
    sizes = sorted(len(group) for group in subgroups)
    assert sizes == [2, 2]


def test_partition_by_source_account_groups_missing_source_name_together() -> None:
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None, source_name=None),
        _transaction(date(2026, 2, 1), "10.00", "Payee", None, source_name=None),
        _transaction(date(2026, 1, 1), "10.00", "Payee", None, source_name="Checking"),
    ]

    subgroups = _partition_by_source_account(transactions)

    assert len(subgroups) == 2
    sizes = sorted(len(group) for group in subgroups)
    assert sizes == [1, 2]


def test_partition_by_source_account_preserves_all_transactions() -> None:
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None, source_name="Checking"),
        _transaction(date(2026, 1, 1), "10.00", "Payee", None, source_name="Savings"),
        _transaction(date(2026, 1, 1), "10.00", "Payee", None, source_name=None),
    ]

    subgroups = _partition_by_source_account(transactions)

    assert sum(len(group) for group in subgroups) == len(transactions)


def test_source_account_partition_keeps_transfer_and_spending_as_separate_patterns() -> None:
    """Regression for "ICA": a fixed transfer from a household account into a
    dedicated spending account, and that spending account's own variable
    purchases, must not be amount-clustered together merely because they
    share a payee name; and an incidental same-day double purchase within
    the spending account must not fragment it further (FR-32a, revised)."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transfer = [
        _transaction(
            start + timedelta(days=31 * i),
            "12000.00",
            "ICA",
            "Mat och hushåll",
            source_name="SEB Räkningskonto",
        )
        for i in range(4)
    ]
    purchase_amounts = ["588.30", "664.39", "732.72", "76.53", "102.93"]
    purchases = [
        _transaction(
            start + timedelta(days=10 * i),
            amount,
            "ICA",
            "Mat och hushåll",
            source_name="ICA-banken Matkonto",
        )
        for i, amount in enumerate(purchase_amounts)
    ]
    # one incidental same-day double purchase that must not fragment the group
    purchases.append(
        _transaction(
            start + timedelta(days=10),
            "40.00",
            "ICA",
            "Mat och hushåll",
            source_name="ICA-banken Matkonto",
        )
    )

    patterns = identify_recurring(transfer + purchases, config)

    assert len(patterns) == 2
    by_source = {p.source_account_name: p for p in patterns}
    assert by_source["SEB Räkningskonto"].occurrences == 4
    assert by_source["SEB Räkningskonto"].amount_mean == 12000.00
    assert by_source["SEB Räkningskonto"].source_account_varies is False
    # 5 billing events: the day-10 incidental double purchase collapses (FR-33a)
    # into the same-date purchase rather than adding a 6th event
    assert by_source["ICA-banken Matkonto"].occurrences == 5
    assert by_source["ICA-banken Matkonto"].source_account_varies is False


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
    """Two differing amounts co-occurring on more than one date reveal
    genuinely parallel, recurring charges (e.g. two subscriptions billed
    through the same merchant); other transactions are assigned to whichever
    cluster's mean is closest (FR-32a, corroborated split)."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "11.00", "Payee", None),
        _transaction(date(2026, 2, 1), "26.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 2
    assert sorted(float(t["amount"]) for t in clusters[0]) == [10.00, 11.00]
    assert sorted(float(t["amount"]) for t in clusters[1]) == [25.00, 26.00]


def test_split_into_amount_clusters_single_co_occurrence_date_is_not_corroborated() -> None:
    """Regression for "ICA": a single day's coincidental extra charge must
    not fragment an otherwise coherent group merely because it happens to
    land on the same date as another transaction (FR-32a, revised)."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "40.00", "Payee", None),
        _transaction(date(2026, 3, 1), "60.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_split_into_amount_clusters_non_matching_signatures_do_not_corroborate() -> None:
    """Two co-occurrence dates whose amounts fall into different, unrelated
    cluster pairs do not corroborate each other."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "10.00", "Payee", None),
        _transaction(date(2026, 2, 1), "60.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 1


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


def test_split_into_amount_clusters_corroborated_split_keeps_small_cluster_distinct() -> None:
    """Once corroborated (the same cluster-pair signature recurs across two
    dates), a smaller resulting cluster stays distinct rather than being
    merged into the larger one."""
    transactions = [
        _transaction(date(2026, 1, 1), "10.00", "Payee", None),
        _transaction(date(2026, 1, 1), "25.00", "Payee", None),
        _transaction(date(2026, 2, 1), "10.00", "Payee", None),
        _transaction(date(2026, 2, 1), "25.00", "Payee", None),
        _transaction(date(2026, 3, 1), "10.00", "Payee", None),
        _transaction(date(2026, 4, 1), "10.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [2, 4]


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
# Solo transaction interval-bucket split (FR-32e)
# ---------------------------------------------------------------------------


def test_solo_transactions_matching_bucket_stay_in_nearest_cluster() -> None:
    """FR-32e: solo transactions whose own median interval bucket agrees with
    the nearest-mean cluster's own co-occurrence-date bucket are folded into
    that cluster unchanged, and no new cluster is created."""
    day0 = date(2026, 1, 1)
    co_occurring = [
        _transaction(day0, "10.00", "Payee", None),
        _transaction(day0, "25.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "25.00", "Payee", None),
    ]
    # Solo transactions nearest the ~25 cluster, 31 days apart -> monthly,
    # matching that cluster's own co-occurrence-date interval (also 31 days).
    solo = [
        _transaction(day0 + timedelta(days=62), "26.00", "Payee", None),
        _transaction(day0 + timedelta(days=93), "26.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(co_occurring + solo, tolerance=0.15)

    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [2, 4]
    large_cluster = max(clusters, key=len)
    assert sorted(float(t["amount"]) for t in large_cluster) == [25.00, 25.00, 26.00, 26.00]


def test_solo_transactions_differing_bucket_form_separate_cluster() -> None:
    """FR-32e: solo transactions whose own median interval bucket differs from
    the nearest-mean cluster's own co-occurrence-date bucket are split off
    into a new cluster of their own instead of being folded in (regression
    for "STOCKHOLM VATTEN AB": quarterly water/garbage pairs plus a yearly
    solo garden-waste charge)."""
    day0 = date(2026, 1, 1)
    water_and_garbage = []
    for i in range(4):
        d = day0 + timedelta(days=91 * i)
        water_and_garbage.append(_transaction(d, "730.00", "Stockholm Vatten", None))
        water_and_garbage.append(_transaction(d, "1900.00", "Stockholm Vatten", None))

    # Solo, yearly garden-waste transactions, nearest to the ~1900 (garbage)
    # cluster by amount, but on a different cadence (365 days apart).
    solo_start = day0 + timedelta(days=3650)
    solo = [
        _transaction(solo_start, "1471.00", "Stockholm Vatten", None),
        _transaction(solo_start + timedelta(days=365), "1560.00", "Stockholm Vatten", None),
    ]

    clusters = _split_into_amount_clusters(water_and_garbage + solo, tolerance=0.15)

    assert len(clusters) == 3
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [2, 4, 4]
    solo_cluster = next(c for c in clusters if len(c) == 2)
    assert sorted(float(t["amount"]) for t in solo_cluster) == [1471.00, 1560.00]


def test_solo_transactions_assigned_unchanged_when_candidate_bucket_undetermined() -> None:
    """FR-32e: when the nearest-mean candidate cluster has fewer than 2 of its
    own co-occurrence-date occurrences, its bucket can't be determined, so
    solo transactions are folded into it unchanged regardless of their own
    interval."""
    day0 = date(2026, 1, 1)
    co_occurring = [
        _transaction(day0, "10.00", "Payee", None),
        _transaction(day0, "25.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "25.00", "Payee", None),
        # A third, distinct cluster (~50) that co-occurs on only one date, so
        # it has just 1 co-occurrence-date occurrence of its own; overall
        # corroboration is still met via the {10, 25} signature above.
        _transaction(day0 + timedelta(days=62), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=62), "50.00", "Payee", None),
    ]
    # 2+ solo transactions, yearly-spaced, nearest to the ~50 cluster whose
    # bucket cannot be determined (only 1 co-occurrence occurrence).
    solo = [
        _transaction(day0 + timedelta(days=3650), "55.00", "Payee", None),
        _transaction(day0 + timedelta(days=3650 + 365), "55.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(co_occurring + solo, tolerance=0.15)

    assert len(clusters) == 3
    target_cluster = next(c for c in clusters if any(float(t["amount"]) == 50.00 for t in c))
    assert len(target_cluster) == 3
    assert sorted(float(t["amount"]) for t in target_cluster) == [50.00, 55.00, 55.00]


def test_single_solo_transaction_not_separated() -> None:
    """FR-32e requires 2+ solo transactions before the interval-bucket check
    applies; with only 1 solo transaction, existing nearest-mean assignment
    (TASK-014) is unchanged even if its interval would classify
    differently."""
    day0 = date(2026, 1, 1)
    co_occurring = [
        _transaction(day0, "10.00", "Payee", None),
        _transaction(day0, "25.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=31), "25.00", "Payee", None),
    ]
    # Single solo transaction, nearest the ~25 cluster; its own interval
    # bucket can't even be computed (needs a sibling solo transaction).
    solo = [_transaction(day0 + timedelta(days=3650), "26.00", "Payee", None)]

    clusters = _split_into_amount_clusters(co_occurring + solo, tolerance=0.15)

    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [2, 3]
    large_cluster = max(clusters, key=len)
    assert 26.00 in [float(t["amount"]) for t in large_cluster]


def test_uncorroborated_split_unaffected_by_solo_bucket_check() -> None:
    """FR-32e only engages once a split is corroborated; a single
    coincidental co-occurrence date, even with 2+ would-be solo transactions
    whose interval disagrees with the co-occurring amounts, leaves the whole
    subgroup as a single cluster (TASK-014 behavior, byte-for-byte
    unchanged)."""
    day0 = date(2026, 1, 1)
    transactions = [
        _transaction(day0, "10.00", "Payee", None),
        _transaction(day0, "25.00", "Payee", None),
        # 2+ "solo" transactions (never sharing a date with a sibling) whose
        # own interval (365 days) would disagree with a monthly bucket.
        _transaction(day0 + timedelta(days=100), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=465), "10.00", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(transactions, tolerance=0.15)

    assert len(clusters) == 1
    assert len(clusters[0]) == 4


@given(
    candidate_interval=st.integers(min_value=1, max_value=450),
    solo_interval=st.integers(min_value=1, max_value=450),
)
@example(candidate_interval=30, solo_interval=30)  # both monthly -> agree
@example(candidate_interval=30, solo_interval=90)  # monthly vs quarterly -> differ
@example(candidate_interval=24, solo_interval=36)  # both irregular either side of monthly -> agree
@example(candidate_interval=25, solo_interval=35)  # both at monthly boundary -> agree
@example(candidate_interval=79, solo_interval=101)  # both irregular, either side of quarterly
@example(candidate_interval=80, solo_interval=100)  # both at quarterly boundary -> agree
@example(candidate_interval=159, solo_interval=201)  # both irregular, either side of half-yearly
@example(candidate_interval=160, solo_interval=200)  # both at half-yearly boundary -> agree
@example(candidate_interval=339, solo_interval=391)  # both irregular either side of yearly -> agree
@example(candidate_interval=340, solo_interval=390)  # both at yearly boundary -> agree
def test_solo_bucket_classification_hypothesis(candidate_interval: int, solo_interval: int) -> None:
    """FR-32e: the split-vs-no-split decision for 2+ solo transactions must
    track exactly whether `_classify_frequency()` agrees or differs between
    the solo transactions' own median interval and the nearest candidate
    cluster's own co-occurrence-date median interval, across synthetic
    interval values straddling every FR-03 bucket boundary."""
    day0 = date(2026, 1, 1)
    co_occurring = [
        _transaction(day0, "10.00", "Payee", None),
        _transaction(day0, "25.00", "Payee", None),
        _transaction(day0 + timedelta(days=candidate_interval), "10.00", "Payee", None),
        _transaction(day0 + timedelta(days=candidate_interval), "25.00", "Payee", None),
    ]
    # Solo transactions far enough away to never collide with a
    # co-occurrence date, nearest the ~25 cluster by amount.
    solo_start = day0 + timedelta(days=10_000)
    solo = [
        _transaction(solo_start, "25.50", "Payee", None),
        _transaction(solo_start + timedelta(days=solo_interval), "25.50", "Payee", None),
    ]

    clusters = _split_into_amount_clusters(co_occurring + solo, tolerance=0.15)

    agree = _classify_frequency(solo_interval) == _classify_frequency(candidate_interval)
    if agree:
        assert len(clusters) == 2
    else:
        assert len(clusters) == 3


def test_stockholm_vatten_produces_three_separate_patterns() -> None:
    """FR-32e integration: a real-shaped payee billing quarterly water and
    garbage collection as a same-day co-occurring pair, plus solo yearly
    garden-waste transactions, must produce three independent patterns
    instead of garden waste being merged into the nearer-by-amount garbage
    collection cluster (regression for "STOCKHOLM VATTEN AB")."""
    config = _make_config(min_occurrences=2)
    day0 = date(2024, 1, 15)
    water_amounts = ["710.00", "735.00", "750.00", "766.00", "720.00"]
    garbage_amounts = ["1801.00", "1850.00", "1900.00", "1940.00", "1820.00"]

    transactions = []
    for i, (water_amount, garbage_amount) in enumerate(zip(water_amounts, garbage_amounts)):
        d = day0 + timedelta(days=91 * i)
        transactions.append(
            _transaction(
                d,
                water_amount,
                "STOCKHOLM VATTEN AB",
                None,
                source_name="SEB Räkningskonto",
            )
        )
        transactions.append(
            _transaction(
                d,
                garbage_amount,
                "STOCKHOLM VATTEN AB",
                None,
                source_name="SEB Räkningskonto",
            )
        )

    garden_waste_dates = [date(2024, 6, 1), date(2025, 6, 1)]
    garden_waste_amounts = ["1471.00", "1560.00"]
    for d, amount in zip(garden_waste_dates, garden_waste_amounts):
        transactions.append(
            _transaction(
                d,
                amount,
                "STOCKHOLM VATTEN AB",
                None,
                source_name="SEB Räkningskonto",
            )
        )

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 3

    garden_waste_pattern = next(p for p in patterns if p.occurrences == 2)
    assert garden_waste_pattern.frequency == "yearly"
    assert garden_waste_pattern.amount_mean == pytest.approx(1515.50, rel=0.01)

    quarterly_patterns = [p for p in patterns if p.occurrences == 5]
    assert len(quarterly_patterns) == 2
    assert all(p.frequency == "quarterly" for p in quarterly_patterns)
    water_pattern = min(quarterly_patterns, key=lambda p: p.amount_mean)
    garbage_pattern = max(quarterly_patterns, key=lambda p: p.amount_mean)
    assert water_pattern.amount_mean < 1000
    assert garbage_pattern.amount_mean > 1700


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


def test_single_uncorroborated_co_occurrence_is_absorbed_not_split() -> None:
    """Regression for "ICA": a single day's coincidental double purchase
    (only one co-occurrence date) is not corroborated (FR-32a, revised) and
    must not fragment an otherwise coherent group into a spurious
    low-confidence extra pattern; all transactions stay in one pattern."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 1)
    transactions = [
        _transaction(start, "10.00", "Apple", None),
        _transaction(start, "25.00", "Apple", None),
        _transaction(start + timedelta(days=30), "10.00", "Apple", None),
        _transaction(start + timedelta(days=60), "10.00", "Apple", None),
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].amount_for_name is None
    # 3 billing events: the day-0 co-occurring pair collapses (FR-33a) into
    # one combined-outflow event rather than seeding a second pattern
    assert patterns[0].occurrences == 3
    assert patterns[0].amount_mean == pytest.approx((35 + 10 + 10) / 3)


def test_corroborated_cluster_still_respects_min_occurrences() -> None:
    """A corroborated amount cluster (FR-32a) that nonetheless falls below
    `MIN_OCCURRENCES` is dropped, leaving only the well-populated cluster as
    a pattern with no amount disambiguation."""
    config = _make_config(min_occurrences=3)
    start = date(2026, 1, 1)
    co_occurrence = [
        _transaction(start, "10.00", "Apple", None),
        _transaction(start, "25.00", "Apple", None),
        _transaction(start + timedelta(days=30), "10.00", "Apple", None),
        _transaction(start + timedelta(days=30), "25.00", "Apple", None),
    ]
    more_of_the_common_amount = [
        _transaction(start + timedelta(days=30 * i), "10.00", "Apple", None) for i in range(2, 4)
    ]

    patterns = identify_recurring(co_occurrence + more_of_the_common_amount, config)

    assert len(patterns) == 1
    assert patterns[0].amount_for_name is None
    assert patterns[0].amount_mean == 10.00
    assert patterns[0].occurrences == 4


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


def test_source_account_resolved_after_billing_event_collapse() -> None:
    """FR-30a continues to resolve the source account correctly even when
    same-date transactions collapse into billing events (FR-33a). Since
    FR-32d already partitions by source account before clustering, the
    cluster's pre-collapse transactions are always a single, unambiguous
    account by construction."""
    config = _make_config(min_occurrences=2)
    start = date(2026, 1, 2)
    transactions = [
        _transaction(start, "276.00", "SEB", "Försäkring", source_name="Checking"),
        _transaction(start, "276.00", "SEB", "Försäkring", source_name="Checking"),
        _transaction(
            start + timedelta(days=31), "276.00", "SEB", "Försäkring", source_name="Checking"
        ),
    ]

    patterns = identify_recurring(transactions, config)

    assert len(patterns) == 1
    assert patterns[0].source_account_name == "Checking"
    assert patterns[0].source_account_varies is False
    assert patterns[0].occurrences == 2  # 2 billing events despite 3 raw transactions


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
