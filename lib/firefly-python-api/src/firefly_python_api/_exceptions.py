"""Custom exceptions for firefly-python-api."""

from __future__ import annotations

from typing import Any


class FireflyConnectionError(Exception):
    """Raised when a connection to the Firefly III instance cannot be established
    or the server returns an unexpected HTTP error during a connectivity check.

    ``status_code`` and ``response_body`` are populated by :meth:`FireflyClient._post_expect`
    when a response was received but its status was outside the expected set; both
    remain ``None`` for network-level failures or for call sites that don't use
    ``_post_expect`` (e.g. ``_get``, ``_post``).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
