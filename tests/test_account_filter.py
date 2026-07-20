from firefly_python_api import TransactionRead
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.account_filter import filter_transactions
from firefly_bills_analyzer.config import Config

ACCOUNTS = ["Checking", "Savings", "Groceries"]


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


def _transaction(source_name: str | None) -> TransactionRead:
    return TransactionRead(
        date="2026-01-01",
        amount="10.00",
        destination_name="Some Payee",
        source_name=source_name,
    )


account_or_none = st.one_of(st.none(), st.sampled_from(ACCOUNTS))
transactions_strategy = st.lists(
    account_or_none.map(_transaction),
    max_size=20,
)


@given(transactions_strategy)
def test_no_filters_configured_is_passthrough(transactions: list[TransactionRead]) -> None:
    config = _make_config(include_accounts=[], exclude_accounts=[])
    assert filter_transactions(transactions, config) == transactions


@given(transactions_strategy, st.sampled_from(ACCOUNTS))
def test_include_list_keeps_only_matching(
    transactions: list[TransactionRead], included: str
) -> None:
    config = _make_config(include_accounts=[included])
    result = filter_transactions(transactions, config)
    for t in result:
        assert t["source_name"] == included


@given(transactions_strategy, st.sampled_from(ACCOUNTS))
def test_exclude_list_drops_matching(transactions: list[TransactionRead], excluded: str) -> None:
    config = _make_config(exclude_accounts=[excluded])
    result = filter_transactions(transactions, config)
    assert all(t["source_name"] != excluded for t in result)


@given(transactions_strategy)
def test_exclude_applied_after_include(transactions: list[TransactionRead]) -> None:
    config = _make_config(
        include_accounts=["Checking"],
        exclude_accounts=["Checking"],
    )
    result = filter_transactions(transactions, config)
    assert all(t["source_name"] != "Checking" for t in result)


@given(transactions_strategy, st.sampled_from(ACCOUNTS))
def test_none_source_name_never_matches_include(
    transactions: list[TransactionRead], included: str
) -> None:
    config = _make_config(include_accounts=[included])
    result = filter_transactions(transactions, config)
    assert all(t["source_name"] is not None for t in result)


@given(transactions_strategy, st.sampled_from(ACCOUNTS))
def test_none_source_name_never_matches_exclude(
    transactions: list[TransactionRead], excluded: str
) -> None:
    config = _make_config(exclude_accounts=[excluded])
    result = filter_transactions(transactions, config)
    none_in = [t for t in transactions if t["source_name"] is None]
    none_out = [t for t in result if t["source_name"] is None]
    assert len(none_out) == len(none_in)
