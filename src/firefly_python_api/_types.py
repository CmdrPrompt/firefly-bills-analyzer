"""TypedDict types for FireflyClient return values and parameters.

Import these alongside ``FireflyClient`` for full IDE code completion::

    from firefly_python_api import FireflyClient, AssetAccount, TransactionPayload
"""

from __future__ import annotations

from typing import Any, TypedDict


class AssetAccount(TypedDict):
    """An asset account returned by :meth:`FireflyClient.get_asset_accounts`."""

    id: str
    name: str


class _TransactionPayloadRequired(TypedDict):
    type: str
    """Transaction type: ``"withdrawal"``, ``"deposit"``, or ``"transfer"``."""
    date: str
    """Transaction date in ``YYYY-MM-DD`` format."""
    amount: str
    """Absolute amount as a decimal string, e.g. ``"100.00"``."""
    description: str


class TransactionPayload(_TransactionPayloadRequired, total=False):
    """Payload for :meth:`FireflyClient.create_transaction`.

    Required fields: ``type``, ``date``, ``amount``, ``description``.

    Optional fields: ``source_id``, ``destination_id``, ``currency_code``.
    """

    source_id: str | None
    """Source account ID (set for withdrawals)."""
    destination_id: str | None
    """Destination account ID (set for deposits)."""
    currency_code: str
    """ISO 4217 currency code, e.g. ``"SEK"``."""


class BillData(TypedDict):
    """A single item from :meth:`FireflyClient.get_bills`."""

    id: str
    attributes: dict[str, Any]


class BudgetData(TypedDict):
    """A single item from :meth:`FireflyClient.get_budgets`."""

    id: str
    attributes: dict[str, Any]


class BudgetLimitData(TypedDict):
    """A single item from :meth:`FireflyClient.get_budget_limits`."""

    id: str
    attributes: dict[str, Any]


class CategoryData(TypedDict):
    """A single item from :meth:`FireflyClient.get_categories`."""

    id: str
    attributes: dict[str, Any]
