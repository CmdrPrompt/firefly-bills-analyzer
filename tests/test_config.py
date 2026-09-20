import os
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
    assert cfg.export_formats == ["none"]
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


# ---------------------------------------------------------------------------
# Household spend (TASK-028, FR-47a/FR-47b/FR-47c/FR-47d)
# ---------------------------------------------------------------------------


def test_household_spend_categories_defaults_to_empty_list() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_categories == []


def test_household_spend_categories_parses_comma_separated_values() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_CATEGORIES": "Groceries, Household"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_categories == ["Groceries", "Household"]


def test_household_spend_one_off_threshold_defaults_to_2000() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_threshold == 2000.0


def test_household_spend_one_off_threshold_override() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD": "5000"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_threshold == 5000.0


def test_household_spend_min_months_defaults_to_3() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_min_months == 3


def test_household_spend_min_months_override() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_MIN_MONTHS": "6"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_min_months == 6


def test_household_spend_include_tag_defaults_to_none() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_include_tag is None


def test_household_spend_include_tag_override() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_INCLUDE_TAG": "shared"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_include_tag == "shared"


def test_household_spend_exclude_tag_defaults_to_none() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_exclude_tag is None


def test_household_spend_exclude_tag_override() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_EXCLUDE_TAG": "personal"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_exclude_tag == "personal"


# ---------------------------------------------------------------------------
# Per-category one-off threshold overrides (TASK-033, FR-47e, FR-47f)
# ---------------------------------------------------------------------------


def test_household_spend_one_off_thresholds_defaults_to_empty_dict() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {}


def test_household_spend_one_off_thresholds_unset_env_var_is_empty_dict() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": ""}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {}


def test_household_spend_one_off_thresholds_parses_single_pair() -> None:
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": "Mat och hushåll:3000"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {"Mat och hushåll": 3000.0}


def test_household_spend_one_off_thresholds_parses_multiple_pairs() -> None:
    env = {
        **BASE_ENV,
        "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": "Mat och hushåll:3000,Transport:6000",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {
        "Mat och hushåll": 3000.0,
        "Transport": 6000.0,
    }


def test_household_spend_one_off_thresholds_strips_whitespace_around_pairs() -> None:
    env = {
        **BASE_ENV,
        "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": " Mat och hushåll : 3000 , Transport : 6000 ",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {
        "Mat och hushåll": 3000.0,
        "Transport": 6000.0,
    }


def test_household_spend_one_off_thresholds_skips_malformed_entry_without_colon() -> None:
    """No `:` separator: the entry carries no parseable amount, so it is
    silently skipped, mirroring `_csv()`'s treatment of blank entries rather
    than raising for a single bad pair among otherwise valid ones."""
    env = {
        **BASE_ENV,
        "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": "Mat och hushåll3000,Transport:6000",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {"Transport": 6000.0}


def test_household_spend_one_off_thresholds_skips_entry_with_empty_amount() -> None:
    """A `category:` pair with nothing after the colon has no parseable
    amount, so it is silently skipped like an entry with no colon at all."""
    env = {
        **BASE_ENV,
        "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": "Mat och hushåll:,Transport:6000",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {"Transport": 6000.0}


def test_household_spend_one_off_thresholds_skips_entry_with_unparseable_amount() -> None:
    """A `category:amount` pair whose amount isn't a valid float is silently
    skipped rather than raising, consistent with the other malformed-entry cases."""
    env = {
        **BASE_ENV,
        "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": "Mat och hushåll:not-a-number,Transport:6000",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == {"Transport": 6000.0}


# Category names avoid "," and ":" (the pair/field separators) and surrounding
# whitespace (stripped, so it would not round-trip through equality).
_category_name_strategy = (
    st.text(
        alphabet=st.characters(blacklist_characters=",:", blacklist_categories=("Cs", "Cc")),
        min_size=1,
        max_size=15,
    )
    .map(lambda s: s.strip())
    .filter(lambda s: s != "")
)

_amount_strategy = st.floats(
    min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False
).map(lambda amount: round(amount, 2))


@given(st.dictionaries(_category_name_strategy, _amount_strategy, min_size=0, max_size=8))
@settings(max_examples=50)
def test_household_spend_one_off_thresholds_round_trips_arbitrary_pairs(
    pairs: dict[str, float],
) -> None:
    """Any set of `category:amount` pairs joined with commas parses back to
    the same mapping, with amounts as floats (FR-47e's format)."""
    raw = ",".join(f"{category}:{amount}" for category, amount in pairs.items())
    env = {**BASE_ENV, "HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS": raw}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.household_spend_one_off_thresholds == pairs


# ---------------------------------------------------------------------------
# Multi-format export (TASK-037, FR-53a, FR-53b, FR-53c, FR-53d)
# ---------------------------------------------------------------------------


def test_export_formats_defaults_to_none() -> None:
    with patch.dict(os.environ, BASE_ENV, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["none"]


def test_export_formats_empty_env_var_defaults_to_none() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": ""}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["none"]


def test_export_formats_single_csv() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "csv"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["csv"]


def test_export_formats_single_json() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "json"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["json"]


def test_export_formats_comma_separated_list() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "csv,json"}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["csv", "json"]


def test_export_formats_strips_whitespace_around_entries() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": " csv , json "}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == ["csv", "json"]


def test_export_format_none_combined_with_other_format_raises() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "csv,none"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigError, match="none"):
            Config.from_env()


def test_export_format_unsupported_value_raises_and_names_it() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "yaml"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigError, match="yaml"):
            Config.from_env()


def test_export_format_duplicate_value_raises_and_names_it() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "csv,csv"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigError, match="csv"):
            Config.from_env()


def test_export_format_unsupported_value_in_list_is_named() -> None:
    env = {**BASE_ENV, "EXPORT_FORMAT": "csv,xml"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigError, match="xml"):
            Config.from_env()


_valid_format_strategy = st.sampled_from(["csv", "json"])


@given(
    st.lists(_valid_format_strategy, min_size=1, max_size=2, unique=True),
)
@settings(max_examples=25)
def test_export_formats_valid_permutations_parse_to_expected_list(formats: list[str]) -> None:
    """Any comma-separated permutation of distinct valid formats parses back
    to the same ordered list (FR-53a)."""
    raw = ",".join(formats)
    env = {**BASE_ENV, "EXPORT_FORMAT": raw}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == formats


@given(
    st.lists(_valid_format_strategy, min_size=1, max_size=2, unique=True),
    st.text(alphabet=" \t", min_size=0, max_size=3),
)
@settings(max_examples=25)
def test_export_formats_tolerates_surrounding_whitespace(formats: list[str], padding: str) -> None:
    """Whitespace around comma-separated entries is trimmed (FR-53a)."""
    raw = ",".join(f"{padding}{fmt}{padding}" for fmt in formats)
    env = {**BASE_ENV, "EXPORT_FORMAT": raw}
    with patch.dict(os.environ, env, clear=True):
        cfg = Config.from_env()
    assert cfg.export_formats == formats


@given(st.sampled_from(["none,csv", "csv,none", "none,json", "json,none"]))
@settings(max_examples=10)
def test_export_formats_none_combined_with_anything_raises(raw: str) -> None:
    """`none` combined with any other format is always rejected (FR-53c)."""
    env = {**BASE_ENV, "EXPORT_FORMAT": raw}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigError, match="none"):
            Config.from_env()
