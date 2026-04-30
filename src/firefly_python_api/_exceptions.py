"""Custom exceptions for firefly-python-api."""

from __future__ import annotations


class FireflyConnectionError(Exception):
    """Raised when a connection to the Firefly III instance cannot be established
    or the server returns an unexpected HTTP error during a connectivity check."""
