"""HTTP session wrapper for the Firefly III REST API."""

from __future__ import annotations

from typing import Any, Callable, cast

import requests

from firefly_python_api._exceptions import FireflyConnectionError
from firefly_python_api._types import (
    AssetAccount,
    BillData,
    BillPayload,
    BudgetData,
    BudgetLimitData,
    CategoryData,
    OpeningBalance,
    TransactionPayload,
    TransactionRead,
)


def _split_to_transaction_read(split: dict[str, Any]) -> TransactionRead:
    """Flatten a single Firefly III transaction split into a :class:`TransactionRead`.

    Parameters
    ----------
    split:
        One entry from a Firefly III transaction object's
        ``attributes.transactions`` list.

    Returns
    -------
    TransactionRead
        ``date`` truncated to ``YYYY-MM-DD``; ``destination_name``,
        ``category_name``, ``source_name`` and ``source_id`` default to
        ``None`` when absent from ``split``. ``tags`` defaults to ``[]``
        when absent or ``null``, and is never ``None``.
    """
    return TransactionRead(
        date=split["date"][:10],
        amount=split["amount"],
        destination_name=split.get("destination_name"),
        category_name=split.get("category_name"),
        source_name=split.get("source_name"),
        source_id=split.get("source_id"),
        tags=split.get("tags") or [],
    )


class FireflyClient:
    """Wraps a :class:`requests.Session` with Firefly III authentication headers.

    Parameters
    ----------
    url:
        Base URL of the Firefly III instance (trailing slash is stripped).
    token:
        Personal access token used for ``Authorization: Bearer <token>``.
    """

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, **kwargs: Any) -> Any:
        """GET ``endpoint`` and return parsed JSON; raise on error."""
        try:
            response = self.session.get(endpoint, **kwargs)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FireflyConnectionError(f"GET {endpoint} failed: {exc}") from exc
        return response.json()

    def _post(self, endpoint: str, payload: dict[str, Any]) -> None:
        """POST ``payload`` to ``endpoint``; raise on non-2xx."""
        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FireflyConnectionError(f"POST {endpoint} failed: {exc}") from exc

    def _post_expect(
        self, endpoint: str, payload: dict[str, Any], expected_statuses: tuple[int, ...]
    ) -> None:
        """POST ``payload`` to ``endpoint``; raise unless the response status is in
        ``expected_statuses``.

        Unlike :meth:`_post`, this does not rely on ``raise_for_status()`` (which
        only raises on 4xx/5xx). Any status code outside ``expected_statuses`` —
        including unexpected 2xx/3xx codes — raises :class:`FireflyConnectionError`.
        """
        try:
            response = self.session.post(endpoint, json=payload)
        except requests.RequestException as exc:
            raise FireflyConnectionError(f"POST {endpoint} failed: {exc}") from exc
        if response.status_code not in expected_statuses:
            try:
                body = cast(dict[str, Any], response.json())
            except ValueError:
                body = None
            raise FireflyConnectionError(
                f"POST {endpoint} failed: unexpected status {response.status_code}",
                status_code=response.status_code,
                response_body=body,
            )

    def _put_expect(
        self, endpoint: str, payload: dict[str, Any], expected_statuses: tuple[int, ...]
    ) -> None:
        """PUT ``payload`` to ``endpoint``; raise unless the response status is in
        ``expected_statuses``.

        Mirrors :meth:`_post_expect`: any status code outside
        ``expected_statuses`` raises :class:`FireflyConnectionError`.
        """
        try:
            response = self.session.put(endpoint, json=payload)
        except requests.RequestException as exc:
            raise FireflyConnectionError(f"PUT {endpoint} failed: {exc}") from exc
        if response.status_code not in expected_statuses:
            try:
                body = cast(dict[str, Any], response.json())
            except ValueError:
                body = None
            raise FireflyConnectionError(
                f"PUT {endpoint} failed: unexpected status {response.status_code}",
                status_code=response.status_code,
                response_body=body,
            )

    def _delete_expect(self, endpoint: str, expected_statuses: tuple[int, ...]) -> None:
        """DELETE ``endpoint``; raise unless the response status is in
        ``expected_statuses``.

        Mirrors :meth:`_post_expect`: any status code outside
        ``expected_statuses`` raises :class:`FireflyConnectionError`.
        """
        try:
            response = self.session.delete(endpoint)
        except requests.RequestException as exc:
            raise FireflyConnectionError(f"DELETE {endpoint} failed: {exc}") from exc
        if response.status_code not in expected_statuses:
            try:
                body = cast(dict[str, Any], response.json())
            except ValueError:
                body = None
            raise FireflyConnectionError(
                f"DELETE {endpoint} failed: unexpected status {response.status_code}",
                status_code=response.status_code,
                response_body=body,
            )

    # ------------------------------------------------------------------
    # REQ-001 — connectivity
    # ------------------------------------------------------------------

    def validate_connection(self) -> bool:
        """Verify connectivity by calling ``GET /api/v1/about``.

        Returns
        -------
        bool
            ``True`` when the server responds with a 2xx status.

        Raises
        ------
        FireflyConnectionError
            On any network error or non-2xx HTTP response.
        """
        self._get(f"{self.url}/api/v1/about")
        return True

    # ------------------------------------------------------------------
    # REQ-002 — accounts and transactions
    # ------------------------------------------------------------------

    def get_asset_accounts(self) -> list[AssetAccount]:
        """Return all asset accounts, fetching every page automatically.

        Returns
        -------
        list[AssetAccount]
            Each item contains ``id`` and ``name``.
        """
        accounts: list[AssetAccount] = []
        page = 1
        while True:
            data = self._get(
                f"{self.url}/api/v1/accounts",
                params={"type": "asset", "page": page},
            )
            for item in data["data"]:
                accounts.append(AssetAccount(id=item["id"], name=item["attributes"]["name"]))
            if page >= data["meta"]["pagination"]["total_pages"]:
                break
            page += 1
        return accounts

    def get_latest_transaction_date(
        self, account_id: str, transaction_type: str | None = None
    ) -> str | None:
        """Return the most recent transaction date for an account.

        Parameters
        ----------
        account_id:
            Firefly III account ID.
        transaction_type:
            Optional Firefly III transaction type filter (e.g.
            ``"withdrawal,deposit"``), forwarded as the ``type`` query
            parameter. When omitted, no filter is applied.

        Returns
        -------
        str or None
            ISO date string ``YYYY-MM-DD``, or ``None`` if no transaction
            matches.
        """
        params: dict[str, str | int] = {"limit": 1, "page": 1}
        if transaction_type is not None:
            params["type"] = transaction_type
        data = self._get(
            f"{self.url}/api/v1/accounts/{account_id}/transactions",
            params=params,
        )
        if not data["data"]:
            return None
        raw_date: str = data["data"][0]["attributes"]["transactions"][0]["date"]
        return raw_date[:10]

    def create_transaction(self, payload: TransactionPayload) -> None:
        """Post a new transaction to Firefly III.

        Parameters
        ----------
        payload:
            Transaction data. Required fields: ``type``, ``date``, ``amount``,
            ``description``. Optional: ``source_id``, ``destination_id``,
            ``currency_code``.

        Raises
        ------
        FireflyConnectionError
            On any network error or non-2xx HTTP response.
        """
        self._post(f"{self.url}/api/v1/transactions", dict(payload))

    def get_transactions_for_account(self, account_id: str) -> list[str]:
        """Return all transaction IDs for an account, fetching every page automatically.

        Parameters
        ----------
        account_id:
            Firefly III account ID.

        Returns
        -------
        list[str]
            Transaction IDs in API response order. Empty when the account
            has no transactions.
        """
        transaction_ids: list[str] = []
        page = 1
        while True:
            data = self._get(
                f"{self.url}/api/v1/accounts/{account_id}/transactions",
                params={"page": page},
            )
            for item in data["data"]:
                transaction_ids.append(item["id"])
            if page >= data["meta"]["pagination"]["total_pages"]:
                break
            page += 1
        return transaction_ids

    def delete_transaction(self, transaction_id: str) -> None:
        """Delete a transaction from Firefly III.

        Parameters
        ----------
        transaction_id:
            Firefly III transaction ID.

        Raises
        ------
        FireflyConnectionError
            On any network error or a response status other than 204.
        """
        self._delete_expect(f"{self.url}/api/v1/transactions/{transaction_id}", (204,))

    # ------------------------------------------------------------------
    # REQ-003 — reporting and resource read methods
    # ------------------------------------------------------------------

    def get_bills(self) -> list[BillData]:
        """Return all bills from ``GET /api/v1/bills``.

        Returns
        -------
        list[BillData]
            Raw ``data`` list from the Firefly III response.
        """
        return cast(list[BillData], self._get(f"{self.url}/api/v1/bills")["data"])

    def get_budgets(self) -> list[BudgetData]:
        """Return all budgets from ``GET /api/v1/budgets``.

        Returns
        -------
        list[BudgetData]
            Raw ``data`` list from the Firefly III response.
        """
        return cast(list[BudgetData], self._get(f"{self.url}/api/v1/budgets")["data"])

    def get_budget_limits(self, budget_id: str) -> list[BudgetLimitData]:
        """Return spending limits for a budget.

        Parameters
        ----------
        budget_id:
            Firefly III budget ID.

        Returns
        -------
        list[BudgetLimitData]
            Raw ``data`` list from the Firefly III response.
        """
        return cast(
            list[BudgetLimitData],
            self._get(f"{self.url}/api/v1/budgets/{budget_id}/limits")["data"],
        )

    def get_categories(self) -> list[CategoryData]:
        """Return all categories from ``GET /api/v1/categories``.

        Returns
        -------
        list[CategoryData]
            Raw ``data`` list from the Firefly III response.
        """
        return cast(list[CategoryData], self._get(f"{self.url}/api/v1/categories")["data"])

    def get_summary(self, start: str, end: str) -> dict[str, Any]:
        """Return the summary dict from ``GET /api/v1/summary/basic``.

        Parameters
        ----------
        start:
            Start date in ``YYYY-MM-DD`` format.
        end:
            End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        dict[str, Any]
            Summary data keyed by category (structure varies by Firefly
            configuration).
        """
        return self._get(  # type: ignore[no-any-return]
            f"{self.url}/api/v1/summary/basic",
            params={"start": start, "end": end},
        )

    # ------------------------------------------------------------------
    # REQ-007 — create bill
    # ------------------------------------------------------------------

    def create_bill(self, payload: BillPayload) -> None:
        """Post a new bill to Firefly III.

        Parameters
        ----------
        payload:
            Bill data. Required fields: ``name``, ``amount_min``,
            ``amount_max``, ``date``, ``repeat_freq``, ``active``.
            ``repeat_freq`` is not validated client-side; invalid values are
            rejected by the Firefly III API.

        Raises
        ------
        FireflyConnectionError
            On any network error or a response status other than 200/201
            (including 422 for a duplicate bill name).
        """
        self._post_expect(f"{self.url}/api/v1/bills", dict(payload), (200, 201))

    # ------------------------------------------------------------------
    # REQ-010 — account opening balance read
    # ------------------------------------------------------------------

    def get_opening_balance(self, account_id: str) -> OpeningBalance:
        """Return an account's current opening balance and opening balance date.

        Parameters
        ----------
        account_id:
            Firefly III account ID.

        Returns
        -------
        OpeningBalance
            ``balance`` and ``date`` default to ``None`` when the account has
            no opening balance set.

        Raises
        ------
        FireflyConnectionError
            On any network error or non-2xx HTTP response (including 404 for
            an unknown ``account_id``).
        """
        attributes = self._get(f"{self.url}/api/v1/accounts/{account_id}")["data"]["attributes"]
        return OpeningBalance(
            balance=attributes.get("opening_balance"),
            date=attributes.get("opening_balance_date"),
        )

    # ------------------------------------------------------------------
    # REQ-009 — account opening balance
    # ------------------------------------------------------------------

    def set_opening_balance(self, account_id: str, balance: str, date: str) -> None:
        """Set an account's opening balance and opening balance date.

        Parameters
        ----------
        account_id:
            Firefly III account ID.
        balance:
            Opening balance amount as a decimal string.
        date:
            Opening balance date in ``YYYY-MM-DD`` format.

        Raises
        ------
        FireflyConnectionError
            On any network error or a response status other than 200.
        """
        self._put_expect(
            f"{self.url}/api/v1/accounts/{account_id}",
            {"opening_balance": balance, "opening_balance_date": date},
            (200,),
        )

    # ------------------------------------------------------------------
    # REQ-006 — withdrawal transactions / REQ-011 — deposit transactions
    # ------------------------------------------------------------------

    def _get_transactions_by_type(
        self,
        txn_type: str,
        start: str,
        end: str,
        on_page: Callable[[int, int], None] | None = None,
    ) -> list[TransactionRead]:
        """Return all transactions of `txn_type` in a date range, fetching every page.

        Each Firefly III transaction object may contain multiple splits under
        ``attributes.transactions``; each split is flattened into its own
        :class:`TransactionRead` entry.

        Parameters
        ----------
        txn_type:
            Firefly III transaction type filter, e.g. ``"withdrawal"`` or
            ``"deposit"``.
        start:
            Start date in ``YYYY-MM-DD`` format.
        end:
            End date in ``YYYY-MM-DD`` format.
        on_page:
            Optional callback invoked as ``on_page(page, total_pages)`` after
            each page has been fetched and parsed. `page` is the 1-indexed
            page just completed. Exceptions raised by `on_page` propagate to
            the caller and stop further page fetches.

        Returns
        -------
        list[TransactionRead]
            Flattened transaction splits.
        """
        transactions: list[TransactionRead] = []
        page = 1
        while True:
            data = self._get(
                f"{self.url}/api/v1/transactions",
                params={"type": txn_type, "start": start, "end": end, "page": page},
            )
            for item in data["data"]:
                for split in item["attributes"]["transactions"]:
                    transactions.append(_split_to_transaction_read(split))
            total_pages = data["meta"]["pagination"]["total_pages"]
            if on_page is not None:
                on_page(page, total_pages)
            if page >= total_pages:
                break
            page += 1
        return transactions

    def get_withdrawal_transactions(
        self,
        start: str,
        end: str,
        on_page: Callable[[int, int], None] | None = None,
    ) -> list[TransactionRead]:
        """Return all withdrawal transactions in a date range, fetching every page.

        Each Firefly III transaction object may contain multiple splits under
        ``attributes.transactions``; each split is flattened into its own
        :class:`TransactionRead` entry.

        Parameters
        ----------
        start:
            Start date in ``YYYY-MM-DD`` format.
        end:
            End date in ``YYYY-MM-DD`` format.
        on_page:
            Optional callback invoked as ``on_page(page, total_pages)`` after
            each page has been fetched and parsed. `page` is the 1-indexed
            page just completed. Exceptions raised by `on_page` propagate to
            the caller and stop further page fetches.

        Returns
        -------
        list[TransactionRead]
            Flattened withdrawal transaction splits.
        """
        return self._get_transactions_by_type("withdrawal", start, end, on_page)

    def get_deposit_transactions(
        self,
        start: str,
        end: str,
        on_page: Callable[[int, int], None] | None = None,
    ) -> list[TransactionRead]:
        """Return all deposit transactions in a date range, fetching every page.

        Each Firefly III transaction object may contain multiple splits under
        ``attributes.transactions``; each split is flattened into its own
        :class:`TransactionRead` entry.

        Account roles are reversed relative to the withdrawal case: this is
        Firefly III's own convention, not something this library normalizes.
        For a deposit, ``source_name`` is the revenue account the money came
        from (e.g. an employer) and ``destination_name`` is the asset account
        it landed in.

        The ``type=deposit`` filter excludes transfers between two of the
        user's own asset accounts (Firefly III types those as ``transfer``),
        so every returned record represents money entering from outside.

        Parameters
        ----------
        start:
            Start date in ``YYYY-MM-DD`` format.
        end:
            End date in ``YYYY-MM-DD`` format.
        on_page:
            Optional callback invoked as ``on_page(page, total_pages)`` after
            each page has been fetched and parsed. `page` is the 1-indexed
            page just completed. Exceptions raised by `on_page` propagate to
            the caller and stop further page fetches.

        Returns
        -------
        list[TransactionRead]
            Flattened deposit transaction splits.
        """
        return self._get_transactions_by_type("deposit", start, end, on_page)
