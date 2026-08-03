"""BDD step definitions for TASK-017 transaction tags (REQ-012)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, scenarios, then, when

from firefly_python_api import FireflyClient

scenarios("../features/TASK-017-transaction-tags.feature")


def _mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _page(splits: list[dict]) -> dict:
    return {
        "data": [{"attributes": {"transactions": splits}}],
        "meta": {"pagination": {"total_pages": 1}},
    }


def _split(amount: str = "10.00", **split_fields: object) -> dict:
    return {"date": "2024-01-05T10:00:00+00:00", "amount": amount, **split_fields}


@pytest.fixture
def client() -> FireflyClient:
    return FireflyClient(url="https://firefly.example.com", token="tok")


@pytest.fixture
def context(client: FireflyClient) -> dict:
    return {"client": client, "start": "2024-01-01", "end": "2024-12-31"}


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("a withdrawal split carrying two tags in the API response")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page([_split(tags=["Personal", "Groceries"])])
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_withdrawal_transactions"


@given("a deposit split carrying one tag in the API response")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page([_split(tags=["Salary"])])
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_deposit_transactions"


@given("a split whose API response contains no tags key")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page([_split()])
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_withdrawal_transactions"


@given("a split whose API response contains a null tags value")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page([_split(tags=None)])
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_deposit_transactions"


@given("a split tagged with surrounding whitespace and mixed case")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    context["raw_tag"] = " Hushåll "
    payload = _page([_split(tags=[context["raw_tag"]])])
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_withdrawal_transactions"


@given("a multi-split transaction whose two splits carry different tags")
def _(context: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _page(
        [
            _split(amount="10.00", tags=["Personal"]),
            _split(amount="20.00", tags=["Shared", "Household"]),
        ]
    )
    monkeypatch.setattr(
        context["client"].session, "get", MagicMock(return_value=_mock_response(payload))
    )
    context["fetch_method"] = "get_deposit_transactions"


@given("the completed implementation")
def _(context: dict) -> None:
    pass


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("get_withdrawal_transactions is called")
def _(context: dict) -> None:
    context["result"] = context["client"].get_withdrawal_transactions(
        context["start"], context["end"]
    )


@when("get_deposit_transactions is called")
def _(context: dict) -> None:
    context["result"] = context["client"].get_deposit_transactions(context["start"], context["end"])


@when("either fetch method is called")
def _(context: dict) -> None:
    method = getattr(context["client"], context["fetch_method"])
    context["result"] = method(context["start"], context["end"])


@when("the existing get_withdrawal_transactions and get_deposit_transactions tests are run")
def _(context: dict) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_transaction_flatten.py",
            "tests/bdd/steps/test_task_016_fetch_deposit_transactions_steps.py",
            "tests/test_api_methods.py",
            "-q",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    context["subprocess_result"] = result


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the returned record's tags holds both tag strings, in the order the API returned them")
def _(context: dict) -> None:
    assert context["result"][0]["tags"] == ["Personal", "Groceries"]


@then("the returned record's tags holds that tag")
def _(context: dict) -> None:
    assert context["result"][0]["tags"] == ["Salary"]


@then("the returned record's tags is an empty list and not None")
def _(context: dict) -> None:
    tags = context["result"][0]["tags"]
    assert tags == []
    assert tags is not None


@then("the returned record's tags is an empty list")
def _(context: dict) -> None:
    assert context["result"][0]["tags"] == []


@then("the returned tag string is byte-identical to the API's value")
def _(context: dict) -> None:
    assert context["result"][0]["tags"] == [context["raw_tag"]]


@then("each returned record carries the tags of its own split")
def _(context: dict) -> None:
    assert context["result"][0]["tags"] == ["Personal"]
    assert context["result"][1]["tags"] == ["Shared", "Household"]


@then("they pass, and no field other than tags changed value")
def _(context: dict) -> None:
    # tests/test_api_methods.py asserts full-dict equality for withdrawal/deposit
    # records, so a green run here proves every field besides the newly added
    # tags key still holds its prior value.
    result = context["subprocess_result"]
    assert result.returncode == 0, result.stdout + result.stderr
