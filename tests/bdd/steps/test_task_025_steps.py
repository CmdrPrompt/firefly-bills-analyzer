"""TASK-025 step definitions for fetching deposits for configured income
accounts (UC12)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from firefly_python_api import FireflyConnectionError, TransactionRead
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer import cache
from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.fetcher import fetch_deposits, fetch_transactions

scenarios("../features/TASK-025-fetch-deposits-for-income-accounts.feature")


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


def _deposit(destination_name: str, source_name: str = "Employer") -> TransactionRead:
    return TransactionRead(
        date="2026-01-01",
        amount="2500.00",
        destination_name=destination_name,
        source_name=source_name,
    )


# ---------------------------------------------------------------------------
# AC-1: No income account configured means no deposit fetch
# ---------------------------------------------------------------------------


@given("INCOME_ACCOUNTS is empty", target_fixture="config")
def income_accounts_empty(tmp_path: Path) -> Config:
    return _make_config(income_accounts=[], cache_dir=str(tmp_path))


@when("the analysis runs", target_fixture="run_result")
def the_analysis_runs(config: Config) -> dict[str, Any]:
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        deposits = fetch_deposits(config)
    return {"deposits": deposits, "client_cls": mock_client_cls}


@then("no deposit request is made to the API")
def no_deposit_request_made(run_result: dict[str, Any]) -> None:
    run_result["client_cls"].return_value.get_deposit_transactions.assert_not_called()


@then("no client is constructed for deposits")
def no_client_constructed(run_result: dict[str, Any]) -> None:
    run_result["client_cls"].assert_not_called()


@then("the run's behavior is identical to today's")
def behavior_identical_to_today(run_result: dict[str, Any]) -> None:
    assert run_result["deposits"] == []


# ---------------------------------------------------------------------------
# AC-2: Deposits are fetched for the configured window
# ---------------------------------------------------------------------------


@given(
    parsers.parse("INCOME_ACCOUNTS names one account"),
    target_fixture="config",
)
def income_accounts_names_one_account() -> dict[str, object]:
    return {"income_accounts": ["Salary Checking"]}


@given(parsers.parse("LOOKBACK_MONTHS is {months:d}"), target_fixture="config")
def lookback_months_is(config: dict[str, object], months: int, tmp_path: Path) -> Config:
    return _make_config(
        income_accounts=config["income_accounts"],
        lookback_months=months,
        cache_dir=str(tmp_path),
    )


@then(
    "get_deposit_transactions is called with the same start and end dates "
    "as fetch_transactions used in that run"
)
def deposit_and_transaction_windows_match(config: Config) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_withdrawal_transactions.return_value = []
            fetch_transactions(config)
        transactions_args = mock_client_cls.return_value.get_withdrawal_transactions.call_args

        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_deposit_client_cls:
            mock_deposit_client_cls.return_value.get_deposit_transactions.return_value = []
            fetch_deposits(config)
        deposits_args = mock_deposit_client_cls.return_value.get_deposit_transactions.call_args

    assert deposits_args.args[:2] == transactions_args.args[:2]


# ---------------------------------------------------------------------------
# AC-3: Deposits to other accounts are discarded
# ---------------------------------------------------------------------------


@given(
    "deposits landing on both a configured income account and an unconfigured account",
    target_fixture="config_and_deposits",
)
def deposits_on_configured_and_unconfigured_accounts(
    tmp_path: Path,
) -> dict[str, object]:
    config = _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
    deposits = [
        _deposit("Salary Checking"),
        _deposit("Some Other Account"),
    ]
    return {"config": config, "deposits": deposits}


@when("fetch_deposits returns", target_fixture="deposit_result")
def fetch_deposits_returns(config_and_deposits: dict[str, object]) -> list[TransactionRead]:
    config = config_and_deposits["config"]
    deposits = config_and_deposits["deposits"]
    with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
        mock_client_cls.return_value.get_deposit_transactions.return_value = deposits
        return fetch_deposits(config)  # type: ignore[arg-type]


@then("only records whose destination_name matches an income account are present in the result")
def only_income_account_deposits_present(deposit_result: list[TransactionRead]) -> None:
    assert len(deposit_result) == 1
    assert deposit_result[0]["destination_name"] == "Salary Checking"


# ---------------------------------------------------------------------------
# AC-4: Deposits never reach the withdrawal pipeline
# ---------------------------------------------------------------------------


@given("a run with income accounts configured", target_fixture="config")
def run_with_income_accounts_configured(tmp_path: Path) -> Config:
    return _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))


@when("the analysis completes", target_fixture="pipeline_mocks")
def the_analysis_completes(config: Config) -> dict[str, MagicMock]:
    import os

    env = {
        "FIREFLY_URL": config.firefly_url,
        "FIREFLY_TOKEN": config.firefly_token,
        "INCOME_ACCOUNTS": ",".join(config.income_accounts),
        "CACHE_DIR": config.cache_dir,
        "EXPORT_FORMAT": "none",
    }
    mod = "firefly_bills_analyzer.__main__"
    deposit = _deposit("Salary Checking")
    with (
        patch.dict(os.environ, env, clear=True),
        patch(f"{mod}.fetcher.fetch_transactions", return_value=[]),
        patch(f"{mod}.fetcher.fetch_deposits", return_value=[deposit]) as fetch_deposits_mock,
        patch(f"{mod}.category_filter.filter_transactions", return_value=[]) as category_filt,
        patch(f"{mod}.account_filter.filter_transactions", return_value=[]) as account_filt,
        patch(f"{mod}.payee_filter.filter_transactions", return_value=[]) as payee_filt,
        patch(f"{mod}.analyzer.identify_recurring", return_value=[]) as analyze,
        patch(f"{mod}.bills_creator.create_bills", return_value=[]) as create,
    ):
        from firefly_bills_analyzer.__main__ import main

        main(["--auto-approve"])

    return {
        "fetch_deposits": fetch_deposits_mock,
        "category_filter": category_filt,
        "account_filter": account_filt,
        "payee_filter": payee_filt,
        "analyze": analyze,
        "create": create,
        "deposit": deposit,
    }


@then(
    "no deposit record is passed to payee grouping, category filtering, "
    "account filtering, payee filtering, or bill creation"
)
def deposit_never_reaches_withdrawal_pipeline(pipeline_mocks: dict[str, MagicMock]) -> None:
    deposit = pipeline_mocks["deposit"]
    for name in ("category_filter", "account_filter", "payee_filter", "analyze", "create"):
        mock = pipeline_mocks[name]
        for call in mock.call_args_list:
            for call_arg in call.args:
                if isinstance(call_arg, list):
                    assert deposit not in call_arg


# ---------------------------------------------------------------------------
# AC-5: Deposits are cached under their own key
# ---------------------------------------------------------------------------


@given("a completed run with income accounts configured", target_fixture="cached_run")
def completed_run_with_income_accounts(tmp_path: Path) -> dict[str, object]:
    config = _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_deposit_transactions.return_value = []
            fetch_deposits(config)
    return {"config": config, "tmp_path": tmp_path}


@when("the cache directory is inspected", target_fixture="cache_inspection")
def the_cache_directory_is_inspected(cached_run: dict[str, object]) -> dict[str, object]:
    config = cached_run["config"]
    tmp_path = cached_run["tmp_path"]
    deposits_cached = cache.read("deposits", config.cache_ttl_transactions, tmp_path)  # type: ignore[arg-type]
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            fetch_deposits(config)  # type: ignore[arg-type]
    return {
        "deposits_cached": deposits_cached,
        "config": config,
        "tmp_path": tmp_path,
        "second_run_client_cls": mock_client_cls,
    }


@then("a deposits cache entry exists distinct from the transactions entry")
def deposits_cache_entry_distinct(cache_inspection: dict[str, object]) -> None:
    assert cache_inspection["deposits_cached"] is not None
    tmp_path = cache_inspection["tmp_path"]
    config = cache_inspection["config"]
    transactions_cached = cache.read(
        "transactions",
        config.cache_ttl_transactions,
        tmp_path,  # type: ignore[arg-type]
    )
    assert transactions_cached is None


@then("a second run within CACHE_TTL_TRANSACTIONS makes no deposit request")
def second_run_makes_no_deposit_request(cache_inspection: dict[str, object]) -> None:
    mock_client_cls = cache_inspection["second_run_client_cls"]
    mock_client_cls.return_value.get_deposit_transactions.assert_not_called()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# AC-6: A cached window mismatch forces a refetch
# ---------------------------------------------------------------------------


@given(
    "a cached deposit entry whose window differs from the current run's",
    target_fixture="config",
)
def cached_deposit_entry_wrong_window(tmp_path: Path) -> Config:
    config = _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))
    cache.write(
        "deposits",
        {"start": "2020-01-01", "end": "2020-12-31", "transactions": []},
        tmp_path,
    )
    return config


@then("the deposits are fetched again rather than read from cache")
def deposits_fetched_again(config: Config) -> None:
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2026, 7, 10)):
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_deposit_transactions.return_value = []
            fetch_deposits(config)

    mock_client_cls.return_value.get_deposit_transactions.assert_called_once()


# ---------------------------------------------------------------------------
# AC-7: An unreachable instance is reported, not crashed
# ---------------------------------------------------------------------------


@given("the deposit fetch raises FireflyConnectionError", target_fixture="config")
def deposit_fetch_raises_connection_error(tmp_path: Path) -> Config:
    return _make_config(income_accounts=["Salary Checking"], cache_dir=str(tmp_path))


@then("the error is reported per NFR-04 with no stack trace", target_fixture="error_report")
def error_reported_no_stack_trace(config: Config) -> None:
    # The shared "the analysis runs" When step already performed a live
    # (unmocked-_today) fetch_deposits() call for this scenario, writing a
    # cache entry keyed to whatever the real wall-clock date was at that
    # moment. Pin _today to a fixed, different date here so this call misses
    # that cache and reaches the client, instead of being served the earlier
    # cached (non-error) result.
    with patch("firefly_bills_analyzer.fetcher._today", return_value=date(2020, 1, 1)):
        with patch("firefly_bills_analyzer.fetcher.FireflyClient") as mock_client_cls:
            mock_client_cls.return_value.get_deposit_transactions.side_effect = (
                FireflyConnectionError("GET /api/v1/transactions failed: connection refused")
            )
            with pytest.raises(SystemExit) as exc_info:
                fetch_deposits(config)

    assert exc_info.value.code != 0
    assert "connection refused" in str(exc_info.value)
