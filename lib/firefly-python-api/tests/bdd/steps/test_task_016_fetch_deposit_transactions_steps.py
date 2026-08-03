"""BDD step definitions for TASK-016 deposit transaction fetching (REQ-011)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_python_api import FireflyClient, FireflyConnectionError

scenarios("../features/TASK-016-fetch-deposit-transactions.feature")


def _mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _page(total_pages: int, amount: str = "10.00", **split_fields: object) -> dict:
    split = {"date": "2024-01-05T10:00:00+00:00", "amount": amount, **split_fields}
    return {
        "data": [{"attributes": {"transactions": [split]}}],
        "meta": {"pagination": {"total_pages": total_pages}},
    }


@pytest.fixture
def client() -> FireflyClient:
    return FireflyClient(url="https://firefly.example.com", token="tok")


@pytest.fixture
def context(client: FireflyClient) -> dict:
    return {"client": client, "start": "2024-01-01", "end": "2024-12-31"}


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("a valid date range")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_get = MagicMock(return_value=_mock_response(_page(1)))
    monkeypatch.setattr(context["client"].session, "get", mock_get)
    context["mock_get"] = mock_get


@given(parsers.parse("an API response reporting total_pages of {n:d}"))
def _(context: dict, monkeypatch: pytest.MonkeyPatch, n: int) -> None:
    pages = [_mock_response(_page(n, amount=f"{i * 10}.00")) for i in range(1, n + 1)]
    mock_get = MagicMock(side_effect=pages)
    monkeypatch.setattr(context["client"].session, "get", mock_get)
    context["mock_get"] = mock_get


@given("a deposit transaction object with two splits under attributes.transactions")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "data": [
            {
                "attributes": {
                    "transactions": [
                        {
                            "date": "2024-03-15T00:00:00+00:00",
                            "amount": "10.00",
                            "source_name": "Employer A",
                            "destination_name": "Checking Account",
                        },
                        {
                            "date": "2024-03-15T00:00:00+00:00",
                            "amount": "20.00",
                            "source_name": "Employer B",
                            "destination_name": "Checking Account",
                        },
                    ]
                }
            }
        ],
        "meta": {"pagination": {"total_pages": 1}},
    }
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )


@given(
    "a deposit split whose source_name is a revenue account and whose "
    "destination_name is an asset account"
)
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page(
        1,
        amount="2500.00",
        source_name="Employer Inc",
        source_id="9",
        destination_name="Checking Account",
        category_name="Salary",
    )
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )


@given(
    "a deposit split with no category_name, no source_name, and no source_id in the API response"
)
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(_page(1)))
    )


@given("a callback that raises on the first page")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [_mock_response(_page(3)) for _ in range(3)]
    mock_get = MagicMock(side_effect=pages)
    monkeypatch.setattr(context["client"].session, "get", mock_get)
    context["mock_get"] = mock_get

    def raising_callback(page: int, total_pages: int) -> None:
        raise ValueError("boom")

    context["on_page"] = raising_callback


@given("an account with both deposits and transfers in the date range")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page(
        1,
        amount="2500.00",
        source_name="Employer Inc",
        destination_name="Checking Account",
    )
    mock_get = MagicMock(return_value=_mock_response(payload))
    monkeypatch.setattr(context["client"].session, "get", mock_get)
    context["mock_get"] = mock_get


@given("the API responds with a non-2xx status")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("500")
    monkeypatch.setattr(context["client"].session, "get", MagicMock(return_value=resp))


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("get_deposit_transactions is called")
def _(context: dict) -> None:
    try:
        context["result"] = context["client"].get_deposit_transactions(
            context["start"], context["end"]
        )
    except Exception as exc:  # noqa: BLE001 - captured for the Then step to assert on
        context["exception"] = exc


@when("get_deposit_transactions is called with an on_page callback")
def _(context: dict) -> None:
    on_page = context.setdefault("on_page", MagicMock())
    try:
        context["result"] = context["client"].get_deposit_transactions(
            context["start"], context["end"], on_page=on_page
        )
    except Exception as exc:  # noqa: BLE001 - captured for the Then step to assert on
        context["exception"] = exc


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(
    "the request is GET /api/v1/transactions with query parameters "
    "type=deposit, start, end, and page=1"
)
def _(context: dict) -> None:
    context["mock_get"].assert_called_once_with(
        "https://firefly.example.com/api/v1/transactions",
        params={
            "type": "deposit",
            "start": context["start"],
            "end": context["end"],
            "page": 1,
        },
    )


@then("pages 1, 2, and 3 are requested and the returned list contains the splits from all three")
def _(context: dict) -> None:
    assert context["mock_get"].call_count == 3
    pages_requested = [c.kwargs["params"]["page"] for c in context["mock_get"].call_args_list]
    assert pages_requested == [1, 2, 3]
    assert [t["amount"] for t in context["result"]] == ["10.00", "20.00", "30.00"]


@then("the returned list contains one TransactionRead per split")
def _(context: dict) -> None:
    assert len(context["result"]) == 2
    assert context["result"][0]["amount"] == "10.00"
    assert context["result"][1]["amount"] == "20.00"


@then(
    "the returned TransactionRead carries that revenue account in source_name "
    "and that asset account in destination_name"
)
def _(context: dict) -> None:
    txn = context["result"][0]
    assert txn["source_name"] == "Employer Inc"
    assert txn["destination_name"] == "Checking Account"


@then("those fields are None on the returned TransactionRead")
def _(context: dict) -> None:
    txn = context["result"][0]
    assert txn["category_name"] is None
    assert txn["source_name"] is None
    assert txn["source_id"] is None


@then("callback is invoked as (1, 2) and (2, 2), in that order")
def _(context: dict) -> None:
    assert context["on_page"].call_args_list == [((1, 2),), ((2, 2),)]


@then("the exception propagates to the caller and no further page is requested")
def _(context: dict) -> None:
    assert isinstance(context["exception"], ValueError)
    assert str(context["exception"]) == "boom"
    assert context["mock_get"].call_count == 1


@then("the request carries type=deposit and no transfer record appears in the result")
def _(context: dict) -> None:
    assert context["mock_get"].call_args.kwargs["params"]["type"] == "deposit"
    assert all(t["destination_name"] != "Savings (transfer)" for t in context["result"])


@then("FireflyConnectionError is raised")
def _(context: dict) -> None:
    assert isinstance(context["exception"], FireflyConnectionError)
