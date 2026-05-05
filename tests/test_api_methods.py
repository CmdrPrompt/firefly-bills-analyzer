"""Tests for FireflyClient API methods — accounts, transactions, and reporting."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
import requests

from firefly_python_api import FireflyClient, FireflyConnectionError


def make_client() -> FireflyClient:
    return FireflyClient(url="https://firefly.example.com", token="tok")


def mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# get_asset_accounts
# ---------------------------------------------------------------------------


class TestGetAssetAccounts:
    def test_returns_accounts_from_single_page(self):
        client = make_client()
        payload = {
            "data": [
                {"id": "1", "attributes": {"name": "Checking"}},
                {"id": "2", "attributes": {"name": "Savings"}},
            ],
            "meta": {"pagination": {"total_pages": 1}},
        }
        with patch.object(client.session, "get", return_value=mock_response(payload)):
            result = client.get_asset_accounts()
        assert result == [{"id": "1", "name": "Checking"}, {"id": "2", "name": "Savings"}]

    def test_fetches_all_pages(self):
        client = make_client()
        page1 = {
            "data": [{"id": "1", "attributes": {"name": "Checking"}}],
            "meta": {"pagination": {"total_pages": 2}},
        }
        page2 = {
            "data": [{"id": "2", "attributes": {"name": "Savings"}}],
            "meta": {"pagination": {"total_pages": 2}},
        }
        with patch.object(
            client.session, "get", side_effect=[mock_response(page1), mock_response(page2)]
        ) as mock_get:
            result = client.get_asset_accounts()
        assert mock_get.call_count == 2
        assert mock_get.call_args_list == [
            call(
                "https://firefly.example.com/api/v1/accounts",
                params={"type": "asset", "page": 1},
            ),
            call(
                "https://firefly.example.com/api/v1/accounts",
                params={"type": "asset", "page": 2},
            ),
        ]
        assert result == [{"id": "1", "name": "Checking"}, {"id": "2", "name": "Savings"}]

    def test_returns_empty_list_when_no_accounts(self):
        client = make_client()
        payload = {"data": [], "meta": {"pagination": {"total_pages": 1}}}
        with patch.object(client.session, "get", return_value=mock_response(payload)):
            result = client.get_asset_accounts()
        assert result == []

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_asset_accounts()


# ---------------------------------------------------------------------------
# get_latest_transaction_date
# ---------------------------------------------------------------------------


class TestGetLatestTransactionDate:
    def test_returns_date_string(self):
        client = make_client()
        payload = {"data": [{"attributes": {"transactions": [{"date": "2024-03-15 00:00:00"}]}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_latest_transaction_date("42")
        mock_get.assert_called_once_with(
            "https://firefly.example.com/api/v1/accounts/42/transactions",
            params={"limit": 1, "page": 1},
        )
        assert result == "2024-03-15"

    def test_truncates_datetime_to_date(self):
        client = make_client()
        payload = {"data": [{"attributes": {"transactions": [{"date": "2024-03-15 14:32:07"}]}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)):
            result = client.get_latest_transaction_date("1")
        assert result == "2024-03-15"

    def test_returns_none_when_no_transactions(self):
        client = make_client()
        payload = {"data": []}
        with patch.object(client.session, "get", return_value=mock_response(payload)):
            result = client.get_latest_transaction_date("1")
        assert result is None

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("403")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_latest_transaction_date("1")


# ---------------------------------------------------------------------------
# create_transaction
# ---------------------------------------------------------------------------


class TestCreateTransaction:
    def _payload(self) -> dict:
        return {
            "transactions": [
                {
                    "type": "withdrawal",
                    "date": "2024-03-15",
                    "amount": "100.00",
                    "description": "Test",
                }
            ]
        }

    def test_posts_to_transactions_endpoint(self):
        client = make_client()
        with patch.object(
            client.session, "post", return_value=mock_response({}, status_code=201)
        ) as mock_post:
            client.create_transaction(self._payload())
        mock_post.assert_called_once_with(
            "https://firefly.example.com/api/v1/transactions",
            json=self._payload(),
        )

    def test_accepts_200_as_success(self):
        client = make_client()
        with patch.object(client.session, "post", return_value=mock_response({}, status_code=200)):
            client.create_transaction(self._payload())  # should not raise

    def test_accepts_201_as_success(self):
        client = make_client()
        with patch.object(client.session, "post", return_value=mock_response({}, status_code=201)):
            client.create_transaction(self._payload())  # should not raise

    def test_raises_on_non_2xx(self):
        client = make_client()
        resp = MagicMock()
        resp.status_code = 422
        resp.raise_for_status.side_effect = requests.HTTPError("422")
        with patch.object(client.session, "post", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.create_transaction(self._payload())

    def test_raises_on_connection_error(self):
        client = make_client()
        with patch.object(client.session, "post", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(FireflyConnectionError):
                client.create_transaction(self._payload())


# ---------------------------------------------------------------------------
# get_bills
# ---------------------------------------------------------------------------


class TestGetBills:
    def test_returns_data_list(self):
        client = make_client()
        payload = {"data": [{"id": "1", "attributes": {"name": "Rent"}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_bills()
        mock_get.assert_called_once_with("https://firefly.example.com/api/v1/bills")
        assert result == payload["data"]

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_bills()


# ---------------------------------------------------------------------------
# get_budgets
# ---------------------------------------------------------------------------


class TestGetBudgets:
    def test_returns_data_list(self):
        client = make_client()
        payload = {"data": [{"id": "1", "attributes": {"name": "Food"}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_budgets()
        mock_get.assert_called_once_with("https://firefly.example.com/api/v1/budgets")
        assert result == payload["data"]

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_budgets()


# ---------------------------------------------------------------------------
# get_budget_limits
# ---------------------------------------------------------------------------


class TestGetBudgetLimits:
    def test_returns_data_list(self):
        client = make_client()
        payload = {"data": [{"id": "1", "attributes": {"amount": "500"}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_budget_limits("7")
        mock_get.assert_called_once_with("https://firefly.example.com/api/v1/budgets/7/limits")
        assert result == payload["data"]

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_budget_limits("7")


# ---------------------------------------------------------------------------
# get_categories
# ---------------------------------------------------------------------------


class TestGetCategories:
    def test_returns_data_list(self):
        client = make_client()
        payload = {"data": [{"id": "1", "attributes": {"name": "Groceries"}}]}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_categories()
        mock_get.assert_called_once_with("https://firefly.example.com/api/v1/categories")
        assert result == payload["data"]

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_categories()


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_returns_response_dict(self):
        client = make_client()
        payload = {"earned": {"value": "1000.00"}, "spent": {"value": "500.00"}}
        with patch.object(client.session, "get", return_value=mock_response(payload)) as mock_get:
            result = client.get_summary("2024-01-01", "2024-12-31")
        mock_get.assert_called_once_with(
            "https://firefly.example.com/api/v1/summary/basic",
            params={"start": "2024-01-01", "end": "2024-12-31"},
        )
        assert result == payload

    def test_raises_on_http_error(self):
        client = make_client()
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(FireflyConnectionError):
                client.get_summary("2024-01-01", "2024-12-31")
