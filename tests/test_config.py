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
    assert cfg.amount_cluster_tolerance == 0.15
    assert cfg.dry_run is False
    assert cfg.export_format == "none"
    assert cfg.uncategorized_behavior == "neutral"
    assert cfg.category_majority_threshold == 0.80
    assert cfg.uncategorized_confidence_penalty == 0.10
    assert cfg.web_port == 5000
    assert cfg.web_host == "127.0.0.1"


def test_category_majority_threshold_override() -> None:
    env = {**BASE_ENV, "CATEGORY_MAJORITY_THRESHOLD": "0.90"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.category_majority_threshold == 0.90


def test_amount_cluster_tolerance_override() -> None:
    env = {**BASE_ENV, "AMOUNT_CLUSTER_TOLERANCE": "0.20"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.amount_cluster_tolerance == 0.20


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


# ---------------------------------------------------------------------------
# Income accounts (TASK-025, FR-39a/FR-39b/FR-39c)
# ---------------------------------------------------------------------------


def test_income_accounts_defaults_to_empty_list() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.income_accounts == []


def test_income_accounts_unset_env_var_is_empty_list() -> None:
    env = {**BASE_ENV, "INCOME_ACCOUNTS": ""}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.income_accounts == []


def test_income_accounts_parses_single_value() -> None:
    env = {**BASE_ENV, "INCOME_ACCOUNTS": "Salary Checking"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.income_accounts == ["Salary Checking"]


def test_income_accounts_parses_comma_separated_values() -> None:
    env = {**BASE_ENV, "INCOME_ACCOUNTS": "Salary Checking, Freelance Account"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.income_accounts == ["Salary Checking", "Freelance Account"]


def test_income_min_occurrences_defaults_to_three() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.income_min_occurrences == 3


def test_income_min_occurrences_override() -> None:
    env = {**BASE_ENV, "INCOME_MIN_OCCURRENCES": "5"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.income_min_occurrences == 5


def test_income_variance_tolerance_defaults_to_point_one() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.income_variance_tolerance == 0.10


def test_income_variance_tolerance_override() -> None:
    env = {**BASE_ENV, "INCOME_VARIANCE_TOLERANCE": "0.25"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.income_variance_tolerance == 0.25
