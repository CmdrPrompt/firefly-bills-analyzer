"""Integration tests — connect to a real Firefly III instance.

Run with:
    make test-integration

Skipped automatically when FIREFLY_URL or FIREFLY_TOKEN is absent.
No write operations are performed.
"""

from __future__ import annotations

import os

import pytest

from firefly_python_api import FireflyClient, load_config


def _credentials_present() -> bool:
    return bool(os.environ.get("FIREFLY_URL")) and bool(os.environ.get("FIREFLY_TOKEN"))


skip_if_no_credentials = pytest.mark.skipif(
    not _credentials_present(),
    reason="FIREFLY_URL and/or FIREFLY_TOKEN not set",
)


@pytest.fixture(scope="module")
def client() -> FireflyClient:
    try:
        url, token = load_config()
    except ValueError:
        pytest.skip("FIREFLY_URL and/or FIREFLY_TOKEN not set")
    return FireflyClient(url=url, token=token)


# ---------------------------------------------------------------------------
# UC-004-1: validate_connection
# ---------------------------------------------------------------------------


@skip_if_no_credentials
def test_validate_connection(client: FireflyClient) -> None:
    assert client.validate_connection() is True


# ---------------------------------------------------------------------------
# UC-004-2: get_asset_accounts
# ---------------------------------------------------------------------------


@skip_if_no_credentials
def test_get_asset_accounts_returns_list(client: FireflyClient) -> None:
    accounts = client.get_asset_accounts()
    assert isinstance(accounts, list)
    assert len(accounts) > 0, "Expected at least one asset account"


@skip_if_no_credentials
def test_get_asset_accounts_items_have_id_and_name(client: FireflyClient) -> None:
    accounts = client.get_asset_accounts()
    for account in accounts:
        assert "id" in account
        assert "name" in account
        assert isinstance(account["id"], str)
        assert isinstance(account["name"], str)


# ---------------------------------------------------------------------------
# UC-004-3: get_latest_transaction_date
# ---------------------------------------------------------------------------


@skip_if_no_credentials
def test_get_latest_transaction_date(client: FireflyClient) -> None:
    accounts = client.get_asset_accounts()
    account_id = accounts[0]["id"]
    result = client.get_latest_transaction_date(account_id)
    if result is not None:
        assert len(result) == 10, f"Expected YYYY-MM-DD, got: {result}"
        assert result[4] == "-" and result[7] == "-"


# ---------------------------------------------------------------------------
# UC-004-4: reporting methods
# ---------------------------------------------------------------------------


@skip_if_no_credentials
def test_get_bills_returns_list(client: FireflyClient) -> None:
    result = client.get_bills()
    assert isinstance(result, list)


@skip_if_no_credentials
def test_get_budgets_returns_list(client: FireflyClient) -> None:
    result = client.get_budgets()
    assert isinstance(result, list)


@skip_if_no_credentials
def test_get_categories_returns_list(client: FireflyClient) -> None:
    result = client.get_categories()
    assert isinstance(result, list)


@skip_if_no_credentials
def test_get_summary_returns_dict(client: FireflyClient) -> None:
    result = client.get_summary(start="2024-01-01", end="2024-12-31")
    assert isinstance(result, dict)
    assert len(result) > 0
