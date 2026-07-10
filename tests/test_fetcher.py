import logging
from datetime import date
from unittest.mock import patch

import pytest
from firefly_python_api import FireflyConnectionError, TransactionRead

from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.fetcher import fetch_transactions


def _make_config(**overrides: object) -> Config:
    base = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=2,
        amount_margin=0.10,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
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


def test_happy_path_returns_transactions() -> None:
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
        result = fetch_transactions(_make_config())

    assert result == expected
    mock_client_cls.assert_called_once_with("https://firefly.example.com", "tok")


def test_start_and_end_dates_derived_from_lookback_months() -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
            fetch_transactions(_make_config(lookback_months=24))

    mock_client_cls.return_value.get_withdrawal_transactions.assert_called_once_with(
        "2024-07-10", "2026-07-10"
    )


def test_empty_result_returns_empty_list() -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        result = fetch_transactions(_make_config())

    assert result == []


def test_connection_error_exits_with_human_readable_message() -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.side_effect = (
            FireflyConnectionError("GET /api/v1/transactions failed: connection refused")
        )
        with pytest.raises(SystemExit) as exc_info:
            fetch_transactions(_make_config())

    assert exc_info.value.code != 0
    assert "connection refused" in str(exc_info.value)


def test_logs_api_call_outcome_at_debug_level(caplog: pytest.LogCaptureFixture) -> None:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
        with caplog.at_level(logging.DEBUG, logger="firefly_bills_analyzer.fetcher"):
            fetch_transactions(_make_config())

    assert any("get_withdrawal_transactions" in record.message for record in caplog.records)
