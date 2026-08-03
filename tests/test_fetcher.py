import logging
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from firefly_python_api import FireflyClient, FireflyConnectionError, TransactionRead
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer import cache
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.fetcher import fetch_deposits, fetch_transactions


def _make_config(**overrides: object) -> Config:
    base = dict(
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
        income_accounts=[],
        income_min_occurrences=3,
        income_variance_tolerance=0.10,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def test_happy_path_returns_transactions(tmp_path: Path) -> None:
    expected: list[TransactionRead] = [
        TransactionRead(
            date="2026-01-01",
            amount="10.00",
            destination_name="Netflix",
            category_name="Entertainment",
        )
    ]
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = expected
        result = fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert result == expected
    mock_client_cls.assert_called_once_with("https://firefly.example.com", "tok")


def test_start_and_end_dates_derived_from_lookback_months(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
            fetch_transactions(_make_config(lookback_months=24, cache_dir=str(tmp_path)))

    args, kwargs = mock_client_cls.return_value.get_withdrawal_transactions.call_args
    assert args == ("2024-07-10", "2026-07-10")
    assert callable(kwargs["on_page"])


def test_on_page_callback_drives_progress_bar(tmp_path: Path) -> None:
    def fake_get_withdrawal_transactions(
        start: str, end: str, on_page: object = None
    ) -> list[object]:
        assert callable(on_page)
        on_page(1, 3)  # type: ignore[operator]
        on_page(2, 3)  # type: ignore[operator]
        on_page(3, 3)  # type: ignore[operator]
        return []

    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.side_effect = (
            fake_get_withdrawal_transactions
        )
        with patch("firefly_bills_analyzer.fetcher.tqdm") as mock_tqdm:
            bar = mock_tqdm.return_value.__enter__.return_value
            bar.total = None  # real tqdm starts with total=None when not passed at construction
            fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert bar.total == 3
    assert bar.update.call_count == 3


def test_progress_bar_total_set_only_once(tmp_path: Path) -> None:
    def fake_get_withdrawal_transactions(
        start: str, end: str, on_page: object = None
    ) -> list[object]:
        on_page(1, 2)  # type: ignore[operator]
        on_page(2, 999)  # type: ignore[operator]  # must not overwrite total set by the first call
        return []

    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.side_effect = (
            fake_get_withdrawal_transactions
        )
        with patch("firefly_bills_analyzer.fetcher.tqdm") as mock_tqdm:
            bar = mock_tqdm.return_value.__enter__.return_value
            bar.total = None
            fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert bar.total == 2


def test_empty_result_returns_empty_list(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        result = fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert result == []


def test_connection_error_exits_with_human_readable_message(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.side_effect = (
            FireflyConnectionError("GET /api/v1/transactions failed: connection refused")
        )
        with pytest.raises(SystemExit) as exc_info:
            fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert exc_info.value.code != 0
    assert "connection refused" in str(exc_info.value)


def test_logs_api_call_outcome_at_debug_level(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        with caplog.at_level(logging.DEBUG, logger="firefly_bills_analyzer.fetcher"):
            fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    assert any("get_withdrawal_transactions" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Cache-aware fetching (TASK-007, FR-21/22)
# ---------------------------------------------------------------------------


def test_cache_hit_skips_api_call(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(lookback_months=24, cache_dir=str(tmp_path))
        cache.write(
            "transactions",
            {
                "start": "2024-07-10",
                "end": "2026-07-10",
                "transactions": [
                    TransactionRead(
                        date="2026-01-01",
                        amount="9.99",
                        destination_name="Netflix",
                        category_name=None,
                    )
                ],
            },
            tmp_path,
        )

        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            result = fetch_transactions(config)

    mock_client_cls.assert_not_called()
    assert result == [
        TransactionRead(
            date="2026-01-01", amount="9.99", destination_name="Netflix", category_name=None
        )
    ]


def test_cache_miss_fetches_live_and_writes_cache(tmp_path: Path) -> None:
    expected: list[TransactionRead] = [
        TransactionRead(
            date="2026-01-01", amount="9.99", destination_name="Netflix", category_name=None
        )
    ]
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(lookback_months=24, cache_dir=str(tmp_path))
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_withdrawal_transactions.return_value = expected
            result = fetch_transactions(config)

    assert result == expected
    mock_client_cls.assert_called_once()
    cached = cache.read("transactions", config.cache_ttl_transactions, tmp_path)
    assert cached == {"start": "2024-07-10", "end": "2026-07-10", "transactions": expected}


def test_stale_cache_triggers_live_fetch(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(
            lookback_months=24, cache_dir=str(tmp_path), cache_ttl_transactions=3600
        )
        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0):
            cache.write(
                "transactions",
                {"start": "2024-07-10", "end": "2026-07-10", "transactions": []},
                tmp_path,
            )

        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0 + 3601):
            with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
                mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
                fetch_transactions(config)

    mock_client_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Withdrawal-only fetch layer (TASK-021, FR-32d rationale correction)
# ---------------------------------------------------------------------------


def test_fetch_transactions_calls_get_withdrawal_transactions_only(tmp_path: Path) -> None:
    """fetch_transactions() must obtain transactions from
    get_withdrawal_transactions() and no other client method, so that FR-32d's
    withdrawal-only rationale (a Firefly III transfer never reaches
    partitioning) stays true."""
    with patch("firefly_bills_analyzer.fetcher.FireflyClient", autospec=True) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_withdrawal_transactions.return_value = []
        fetch_transactions(_make_config(cache_dir=str(tmp_path)))

    mock_client.get_withdrawal_transactions.assert_called_once()
    other_transaction_methods = [
        name
        for name in dir(FireflyClient)
        if "transaction" in name.lower() and name != "get_withdrawal_transactions"
    ]
    assert other_transaction_methods, (
        "expected at least one sibling transaction-fetching method on FireflyClient "
        "to assert was not called; if none exist, this list needs revisiting"
    )
    for method_name in other_transaction_methods:
        getattr(mock_client, method_name).assert_not_called()


def test_cache_for_different_window_is_ignored(tmp_path: Path) -> None:
    """A cache entry for a different lookback window must not be served, since
    it does not answer the current query."""
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(lookback_months=24, cache_dir=str(tmp_path))
        cache.write(
            "transactions",
            {"start": "2025-01-01", "end": "2025-12-31", "transactions": []},
            tmp_path,
        )

        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
            fetch_transactions(config)

    mock_client_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Deposit fetch layer (TASK-025, FR-39/FR-40, UC12)
# ---------------------------------------------------------------------------


def _deposit(destination_name: str, source_name: str = "Employer") -> TransactionRead:
    return TransactionRead(
        date="2026-01-01",
        amount="2500.00",
        destination_name=destination_name,
        source_name=source_name,
    )


def test_no_income_accounts_returns_empty_without_constructing_client(tmp_path: Path) -> None:
    """FR-40b/NFR-14: an empty income_accounts list disables the feature
    entirely, without touching the network."""
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        result = fetch_deposits(_make_config(income_accounts=[], cache_dir=str(tmp_path)))

    assert result == []
    mock_client_cls.assert_not_called()


def test_fetches_deposits_for_configured_window(tmp_path: Path) -> None:
    """FR-40a: same window derivation as fetch_transactions()."""
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.return_value = []
        with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
            fetch_deposits(
                _make_config(
                    income_accounts=["Salary Checking"],
                    lookback_months=24,
                    cache_dir=str(tmp_path),
                )
            )

    args, kwargs = mock_client_cls.return_value.get_deposit_transactions.call_args
    assert args == ("2024-07-10", "2026-07-10")
    assert callable(kwargs["on_page"])


def test_on_page_callback_drives_progress_bar_for_deposits(tmp_path: Path) -> None:
    def fake_get_deposit_transactions(start: str, end: str, on_page: object = None) -> list[object]:
        assert callable(on_page)
        on_page(1, 2)  # type: ignore[operator]
        on_page(2, 2)  # type: ignore[operator]
        return []

    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.side_effect = (
            fake_get_deposit_transactions
        )
        with patch("firefly_bills_analyzer.fetcher.tqdm") as mock_tqdm:
            bar = mock_tqdm.return_value.__enter__.return_value
            bar.total = None
            fetch_deposits(
                _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
            )

    assert bar.total == 2
    assert bar.update.call_count == 2


def test_deposits_to_other_accounts_are_discarded(tmp_path: Path) -> None:
    """FR-40c: only records whose destination_name is a configured income
    account survive."""
    deposits = [_deposit("Salary Checking"), _deposit("Some Other Account")]
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.return_value = deposits
        result = fetch_deposits(
            _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
        )

    assert result == [_deposit("Salary Checking")]


def test_connection_error_exits_with_human_readable_message_for_deposits(
    tmp_path: Path,
) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.side_effect = FireflyConnectionError(
            "GET /api/v1/transactions failed: connection refused"
        )
        with pytest.raises(SystemExit) as exc_info:
            fetch_deposits(
                _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
            )

    assert exc_info.value.code != 0
    assert "connection refused" in str(exc_info.value)


def test_deposits_cache_hit_skips_api_call(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(
            income_accounts=["Salary Checking"], lookback_months=24, cache_dir=str(tmp_path)
        )
        cache.write(
            "deposits",
            {
                "start": "2024-07-10",
                "end": "2026-07-10",
                "transactions": [_deposit("Salary Checking")],
            },
            tmp_path,
        )

        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            result = fetch_deposits(config)

    mock_client_cls.assert_not_called()
    assert result == [_deposit("Salary Checking")]


def test_deposits_cache_miss_fetches_live_and_writes_own_cache_key(tmp_path: Path) -> None:
    expected = [_deposit("Salary Checking")]
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(
            income_accounts=["Salary Checking"], lookback_months=24, cache_dir=str(tmp_path)
        )
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_deposit_transactions.return_value = expected
            result = fetch_deposits(config)

    assert result == expected
    mock_client_cls.assert_called_once()
    cached_deposits = cache.read("deposits", config.cache_ttl_transactions, tmp_path)
    assert cached_deposits == {"start": "2024-07-10", "end": "2026-07-10", "transactions": expected}
    # Distinct cache key: the transactions entry must remain untouched.
    assert cache.read("transactions", config.cache_ttl_transactions, tmp_path) is None


def test_deposits_cache_for_different_window_is_ignored(tmp_path: Path) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        config = _make_config(
            income_accounts=["Salary Checking"], lookback_months=24, cache_dir=str(tmp_path)
        )
        cache.write(
            "deposits",
            {"start": "2025-01-01", "end": "2025-12-31", "transactions": []},
            tmp_path,
        )

        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_deposit_transactions.return_value = []
            fetch_deposits(config)

    mock_client_cls.assert_called_once()


def test_fetch_deposits_calls_get_deposit_transactions_only(tmp_path: Path) -> None:
    """Mirrors the withdrawal-only guarantee for fetch_transactions(): the
    deposit path must call get_deposit_transactions() and no other client
    method."""
    with patch("firefly_bills_analyzer.fetcher.FireflyClient", autospec=True) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_deposit_transactions.return_value = []
        fetch_deposits(_make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path)))

    mock_client.get_deposit_transactions.assert_called_once()
    other_transaction_methods = [
        name
        for name in dir(FireflyClient)
        if "transaction" in name.lower() and name != "get_deposit_transactions"
    ]
    assert other_transaction_methods, (
        "expected at least one sibling transaction-fetching method on FireflyClient "
        "to assert was not called; if none exist, this list needs revisiting"
    )
    for method_name in other_transaction_methods:
        getattr(mock_client, method_name).assert_not_called()


# ---------------------------------------------------------------------------
# AC-8: Hypothesis property test for income-account filtering
# ---------------------------------------------------------------------------

ACCOUNT_NAMES = ["Salary Checking", "Freelance Account", "Groceries", "Rent"]

destination_or_none = st.one_of(st.none(), st.sampled_from(ACCOUNT_NAMES))
deposits_strategy = st.lists(
    destination_or_none.map(
        lambda name: TransactionRead(
            date="2026-01-01",
            amount="1.00",
            destination_name=name,
            source_name="Employer",
        )
    ),
    max_size=20,
)
income_accounts_strategy = st.lists(st.sampled_from(ACCOUNT_NAMES), max_size=4, unique=True)


@given(deposits_strategy, income_accounts_strategy)
def test_every_result_record_matches_an_income_account(
    tmp_path_factory: pytest.TempPathFactory,
    deposits: list[TransactionRead],
    income_accounts: list[str],
) -> None:
    # A fresh cache directory per example: fetch_deposits() caches under a
    # window-keyed entry that is otherwise indistinguishable across examples
    # sharing the same (unmocked) "today", which would let one example's
    # cached result leak into the next.
    cache_dir = tmp_path_factory.mktemp("cache")
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.return_value = deposits
        result = fetch_deposits(
            _make_config(income_accounts=income_accounts, cache_dir=str(cache_dir))
        )

    for record in result:
        assert record["destination_name"] in income_accounts


@given(deposits_strategy, income_accounts_strategy)
def test_no_matching_record_is_dropped(
    tmp_path_factory: pytest.TempPathFactory,
    deposits: list[TransactionRead],
    income_accounts: list[str],
) -> None:
    cache_dir = tmp_path_factory.mktemp("cache")
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.return_value = deposits
        result = fetch_deposits(
            _make_config(income_accounts=income_accounts, cache_dir=str(cache_dir))
        )

    expected_matches = [d for d in deposits if d["destination_name"] in income_accounts]
    assert result == expected_matches
