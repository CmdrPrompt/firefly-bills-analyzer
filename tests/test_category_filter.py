from firefly_python_api import TransactionRead
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.category_filter import filter_transactions, resolve_category_name
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


def _transaction(category_name: str | None) -> TransactionRead:
    return TransactionRead(
        date="2026-01-01",
        amount="10.00",
        destination_name="Some Payee",
        category_name=category_name,
    )


category_or_none = st.one_of(st.none(), st.sampled_from(CATEGORIES))
transactions_strategy = st.lists(
    category_or_none.map(_transaction),
    max_size=20,
)


@given(transactions_strategy)
def test_no_filters_configured_is_passthrough(transactions: list[TransactionRead]) -> None:
    config = _make_config(
        include_categories=[], exclude_categories=[], uncategorized_behavior="neutral"
    )
    assert filter_transactions(transactions, config) == transactions


@given(transactions_strategy, st.sampled_from(CATEGORIES))
def test_include_list_keeps_only_matching_and_uncategorized(
    transactions: list[TransactionRead], included: str
) -> None:
    config = _make_config(include_categories=[included], uncategorized_behavior="neutral")
    result = filter_transactions(transactions, config)
    for t in result:
        assert t["category_name"] in (included, None)
    kept_categorized = {t["category_name"] for t in result if t["category_name"] is not None}
    assert kept_categorized <= {included}


@given(transactions_strategy, st.sampled_from(CATEGORIES))
def test_exclude_list_drops_matching(transactions: list[TransactionRead], excluded: str) -> None:
    config = _make_config(exclude_categories=[excluded], uncategorized_behavior="neutral")
    result = filter_transactions(transactions, config)
    assert all(t["category_name"] != excluded for t in result)


@given(transactions_strategy)
def test_exclude_applied_after_include(transactions: list[TransactionRead]) -> None:
    config = _make_config(
        include_categories=["Streaming"],
        exclude_categories=["Streaming"],
        uncategorized_behavior="neutral",
    )
    result = filter_transactions(transactions, config)
    assert all(t["category_name"] != "Streaming" for t in result)


@given(transactions_strategy)
def test_uncategorized_behavior_include_keeps_uncategorized(
    transactions: list[TransactionRead],
) -> None:
    config = _make_config(uncategorized_behavior="include")
    result = filter_transactions(transactions, config)
    uncategorized_in = [t for t in transactions if t["category_name"] is None]
    uncategorized_out = [t for t in result if t["category_name"] is None]
    assert len(uncategorized_out) == len(uncategorized_in)


@given(transactions_strategy)
def test_uncategorized_behavior_neutral_keeps_uncategorized(
    transactions: list[TransactionRead],
) -> None:
    config = _make_config(uncategorized_behavior="neutral")
    result = filter_transactions(transactions, config)
    uncategorized_in = [t for t in transactions if t["category_name"] is None]
    uncategorized_out = [t for t in result if t["category_name"] is None]
    assert len(uncategorized_out) == len(uncategorized_in)


@given(transactions_strategy)
def test_uncategorized_behavior_exclude_drops_uncategorized(
    transactions: list[TransactionRead],
) -> None:
    config = _make_config(uncategorized_behavior="exclude")
    result = filter_transactions(transactions, config)
    assert all(t["category_name"] is not None for t in result)


def test_resolve_category_name_empty_returns_none() -> None:
    config = _make_config()
    assert resolve_category_name([], config) is None


def test_resolve_category_name_all_same_category() -> None:
    config = _make_config(category_majority_threshold=0.80)
    transactions = [_transaction("Streaming") for _ in range(5)]
    assert resolve_category_name(transactions, config) == "Streaming"


def test_resolve_category_name_below_threshold_returns_none() -> None:
    config = _make_config(category_majority_threshold=0.80)
    transactions = [_transaction("Streaming")] * 3 + [_transaction("Groceries")] * 2
    assert resolve_category_name(transactions, config) is None


def test_resolve_category_name_meets_threshold_with_outlier() -> None:
    config = _make_config(category_majority_threshold=0.80)
    transactions = [_transaction("Streaming")] * 9 + [_transaction("Groceries")] * 1
    assert resolve_category_name(transactions, config) == "Streaming"


def test_resolve_category_name_all_uncategorized_returns_none() -> None:
    config = _make_config()
    transactions = [_transaction(None) for _ in range(5)]
    assert resolve_category_name(transactions, config) is None


@given(st.integers(min_value=1, max_value=20), st.floats(min_value=0.5, max_value=1.0))
def test_resolve_category_name_threshold_property(count: int, threshold: float) -> None:
    config = _make_config(category_majority_threshold=threshold)
    transactions = [_transaction("Streaming") for _ in range(count)]
    assert resolve_category_name(transactions, config) == "Streaming"
