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


class BillPayload(TypedDict):
    """Payload for :meth:`FireflyClient.create_bill`.

    All fields are required: ``name``, ``amount_min``, ``amount_max``,
    ``date``, ``repeat_freq``, ``active``.
    """

    name: str
    amount_min: str
    """Minimum expected amount as a decimal string, e.g. ``"10.00"``."""
    amount_max: str
    """Maximum expected amount as a decimal string, e.g. ``"15.00"``."""
    date: str
    """First bill date in ``YYYY-MM-DD`` format."""
    repeat_freq: str
    """Repetition frequency, e.g. ``"weekly"``, ``"monthly"``, ``"quarterly"``,
    ``"half-year"``, ``"yearly"``. Not validated client-side."""
    active: bool


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


class TransactionRead(TypedDict):
    """A single flattened withdrawal split returned by
    :meth:`FireflyClient.get_withdrawal_transactions`.
    """

    date: str
    """Transaction date truncated to ``YYYY-MM-DD``."""
    amount: str
    """Absolute amount as a decimal string, e.g. ``"100.00"``."""
    destination_name: str | None
    """Destination account/payee name, or ``None`` when absent."""
    category_name: str | None
    """Category name, or ``None`` when absent or uncategorized."""
    source_name: str | None
    """Source account name (funds are withdrawn from), or ``None`` when absent."""
    source_id: str | None
    """Source account ID, or ``None`` when absent."""
