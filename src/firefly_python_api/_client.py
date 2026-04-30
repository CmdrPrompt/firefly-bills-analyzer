"""HTTP session wrapper for the Firefly III REST API."""

from __future__ import annotations

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
        endpoint = f"{self.url}/api/v1/about"
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FireflyConnectionError(
                f"Could not connect to Firefly III at {self.url}: {exc}"
            ) from exc
        return True
