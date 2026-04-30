"""Conftest for integration tests.

Reads credentials from config.json and secrets.json in the project root
(same format as firefly-bank-importer) and injects them as environment
variables so load_config() can find them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent


def pytest_configure() -> None:
    """Populate FIREFLY_URL and FIREFLY_TOKEN from local JSON files if present."""
    config_file = _ROOT / "config.json"
    secrets_file = _ROOT / "secrets.json"

    if config_file.exists() and "FIREFLY_URL" not in os.environ:
        data = json.loads(config_file.read_text())
        os.environ["FIREFLY_URL"] = data["firefly_url"]

    if secrets_file.exists() and "FIREFLY_TOKEN" not in os.environ:
        data = json.loads(secrets_file.read_text())
        os.environ["FIREFLY_TOKEN"] = data["api_token"]
