"""Tests for TypedDict types — importability and structural correctness."""

from __future__ import annotations

from firefly_python_api import (
    AssetAccount,
    BillData,
    BillPayload,
    BudgetData,
    BudgetLimitData,
    CategoryData,
    TransactionPayload,
    TransactionRead,
)


class TestTypesAreImportable:
    def test_asset_account_is_importable(self):
        assert AssetAccount is not None

    def test_transaction_payload_is_importable(self):
        assert TransactionPayload is not None

    def test_bill_data_is_importable(self):
        assert BillData is not None

    def test_bill_payload_is_importable(self):
        assert BillPayload is not None

    def test_budget_data_is_importable(self):
        assert BudgetData is not None

    def test_budget_limit_data_is_importable(self):
        assert BudgetLimitData is not None

    def test_category_data_is_importable(self):
        assert CategoryData is not None

    def test_transaction_read_is_importable(self):
        assert TransactionRead is not None


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


class TestBillPayload:
    def test_required_fields(self):
        payload: BillPayload = {
            "name": "Netflix",
            "amount_min": "10.00",
            "amount_max": "15.00",
            "date": "2024-03-15",
            "repeat_freq": "monthly",
            "active": True,
        }
        assert payload["name"] == "Netflix"
        assert payload["amount_min"] == "10.00"
        assert payload["amount_max"] == "15.00"
        assert payload["date"] == "2024-03-15"
        assert payload["repeat_freq"] == "monthly"
        assert payload["active"] is True


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


class TestTransactionRead:
    def test_valid_instance_with_values(self):
        item: TransactionRead = {
            "date": "2024-03-15",
            "amount": "100.00",
            "destination_name": "Grocery Store",
            "category_name": "Groceries",
        }
        assert item["date"] == "2024-03-15"
        assert item["amount"] == "100.00"
        assert item["destination_name"] == "Grocery Store"
        assert item["category_name"] == "Groceries"

    def test_valid_instance_with_none_optional_fields(self):
        item: TransactionRead = {
            "date": "2024-03-15",
            "amount": "100.00",
            "destination_name": None,
            "category_name": None,
        }
        assert item["destination_name"] is None
        assert item["category_name"] is None
