"""Credential loading from environment variables and .env files."""

from __future__ import annotations

import os

from dotenv import load_dotenv


def load_config(env_path: str | None = None) -> tuple[str, str]:
    """Load Firefly III connection credentials.

    Reads ``FIREFLY_URL`` and ``FIREFLY_TOKEN`` from the environment, optionally
    supplemented by a ``.env`` file. Existing environment variables take
    precedence over values in the file.

    Parameters
    ----------
    env_path:
        Path to a ``.env`` file. Defaults to ``.env`` in the current working
        directory when *None*.

    Returns
    -------
    tuple[str, str]
        ``(url, token)`` — the Firefly III base URL and personal access token.

    Raises
    ------
    ValueError
        When either ``FIREFLY_URL`` or ``FIREFLY_TOKEN`` is absent.
    """
    dotenv_path = env_path if env_path is not None else ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)

    url = os.environ.get("FIREFLY_URL")
    token = os.environ.get("FIREFLY_TOKEN")

    if not url:
        raise ValueError("FIREFLY_URL is not set in the environment or .env file.")
    if not token:
        raise ValueError("FIREFLY_TOKEN is not set in the environment or .env file.")

    return url, token
