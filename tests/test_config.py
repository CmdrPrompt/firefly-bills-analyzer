import os
from unittest.mock import patch

import pytest

from firefly_bills_analyzer.config import Config, ConfigError

BASE_ENV = {"FIREFLY_URL": "https://firefly.example.com", "FIREFLY_TOKEN": "tok"}


def test_loads_required_vars() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.firefly_url == "https://firefly.example.com"
    assert cfg.firefly_token == "tok"


def test_missing_url_raises() -> None:
    with patch.dict(os.environ, {"FIREFLY_TOKEN": "tok"}, clear=True):
        with pytest.raises(ConfigError, match="FIREFLY_URL"):
            Config.from_env()


def test_missing_token_raises() -> None:
    with patch.dict(os.environ, {"FIREFLY_URL": "https://firefly.example.com"}, clear=True):
        with pytest.raises(ConfigError, match="FIREFLY_TOKEN"):
            Config.from_env()


def test_defaults() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.lookback_months == 24
    assert cfg.min_occurrences == 2
    assert cfg.amount_margin == 0.10
    assert cfg.dry_run is False
    assert cfg.export_format == "none"
    assert cfg.uncategorized_behavior == "neutral"
    assert cfg.web_port == 5000
    assert cfg.web_host == "127.0.0.1"


def test_lookback_months_override() -> None:
    env = {**BASE_ENV, "LOOKBACK_MONTHS": "12"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.lookback_months == 12


def test_dry_run_override() -> None:
    env = {**BASE_ENV, "DRY_RUN": "true"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.dry_run is True
