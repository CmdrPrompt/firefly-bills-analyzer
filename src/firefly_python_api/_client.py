"""HTTP session wrapper for the Firefly III REST API."""

from __future__ import annotations

from typing import Any

import requests

from firefly_python_api._exceptions import FireflyConnectionError


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

    def get_asset_accounts(self) -> list[dict[str, str]]:
        """Return all asset accounts, fetching every page automatically.

        Returns
        -------
        list[dict[str, str]]
            Each item contains ``{"id": str, "name": str}``.
        """
        accounts: list[dict[str, str]] = []
        page = 1
        while True:
            data = self._get(
                f"{self.url}/api/v1/accounts",
                params={"type": "asset", "page": page},
            )
            for item in data["data"]:
                accounts.append({"id": item["id"], "name": item["attributes"]["name"]})
            if page >= data["meta"]["pagination"]["total_pages"]:
                break
            page += 1
        return accounts

    def get_latest_transaction_date(self, account_id: str) -> str | None:
        """Return the most recent transaction date for an account.

        Parameters
        ----------
        account_id:
            Firefly III account ID.

        Returns
        -------
        str or None
            ISO date string ``YYYY-MM-DD``, or ``None`` if the account has
            no transactions.
        """
        data = self._get(
            f"{self.url}/api/v1/accounts/{account_id}/transactions",
            params={"limit": 1, "page": 1},
        )
        if not data["data"]:
            return None
        raw_date: str = data["data"][0]["attributes"]["transactions"][0]["date"]
        return raw_date[:10]

    def create_transaction(self, payload: dict[str, Any]) -> None:
        """Post a new transaction to Firefly III.

        Parameters
        ----------
        payload:
            Transaction payload as expected by ``POST /api/v1/transactions``.

        Raises
        ------
        FireflyConnectionError
            On any network error or non-2xx HTTP response.
        """
        self._post(f"{self.url}/api/v1/transactions", payload)

    # ------------------------------------------------------------------
    # REQ-003 — reporting and resource read methods
    # ------------------------------------------------------------------

    def get_bills(self) -> list[Any]:
        """Return all bills (``data`` list from ``GET /api/v1/bills``)."""
        return self._get(f"{self.url}/api/v1/bills")["data"]  # type: ignore[no-any-return]

    def get_budgets(self) -> list[Any]:
        """Return all budgets (``data`` list from ``GET /api/v1/budgets``)."""
        return self._get(f"{self.url}/api/v1/budgets")["data"]  # type: ignore[no-any-return]

    def get_budget_limits(self, budget_id: str) -> list[Any]:
        """Return limits for a budget.

        Parameters
        ----------
        budget_id:
            Firefly III budget ID.
        """
        return self._get(f"{self.url}/api/v1/budgets/{budget_id}/limits")["data"]  # type: ignore[no-any-return]

    def get_categories(self) -> list[Any]:
        """Return all categories (``data`` list from ``GET /api/v1/categories``)."""
        return self._get(f"{self.url}/api/v1/categories")["data"]  # type: ignore[no-any-return]

    def get_summary(self) -> dict[str, Any]:
        """Return the summary dict from ``GET /api/v1/summary/basic``."""
        return self._get(f"{self.url}/api/v1/summary/basic")  # type: ignore[no-any-return]
