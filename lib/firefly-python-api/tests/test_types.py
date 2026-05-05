"""Tests for TypedDict types — importability and structural correctness."""

from __future__ import annotations

from firefly_python_api import (
    AssetAccount,
    BillData,
    BudgetData,
    BudgetLimitData,
    CategoryData,
    TransactionPayload,
)


class TestTypesAreImportable:
    def test_asset_account_is_importable(self):
        assert AssetAccount is not None

    def test_transaction_payload_is_importable(self):
        assert TransactionPayload is not None

    def test_bill_data_is_importable(self):
        assert BillData is not None

    def test_budget_data_is_importable(self):
        assert BudgetData is not None

    def test_budget_limit_data_is_importable(self):
        assert BudgetLimitData is not None

    def test_category_data_is_importable(self):
        assert CategoryData is not None


class TestAssetAccount:
    def test_valid_instance(self):
        account: AssetAccount = {"id": "1", "name": "Checking"}
        assert account["id"] == "1"
        assert account["name"] == "Checking"


class TestTransactionPayload:
    def test_required_fields_only(self):
        payload: TransactionPayload = {
            "type": "withdrawal",
            "date": "2024-03-15",
            "amount": "100.00",
            "description": "Groceries",
        }
        assert payload["type"] == "withdrawal"

    def test_with_optional_fields(self):
        payload: TransactionPayload = {
            "type": "withdrawal",
            "date": "2024-03-15",
            "amount": "100.00",
            "description": "Groceries",
            "source_id": "42",
            "destination_id": None,
            "currency_code": "SEK",
        }
        assert payload["currency_code"] == "SEK"


class TestResourceDataTypes:
    def test_bill_data(self):
        item: BillData = {"id": "1", "attributes": {"name": "Rent"}}
        assert item["id"] == "1"

    def test_budget_data(self):
        item: BudgetData = {"id": "2", "attributes": {"name": "Food"}}
        assert item["id"] == "2"

    def test_budget_limit_data(self):
        item: BudgetLimitData = {"id": "3", "attributes": {"amount": "500"}}
        assert item["id"] == "3"

    def test_category_data(self):
        item: CategoryData = {"id": "4", "attributes": {"name": "Transport"}}
        assert item["id"] == "4"
