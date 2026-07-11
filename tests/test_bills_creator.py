"""Tests for bills_creator (UC4): create bills in Firefly III with FR-05a-d
duplicate handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from firefly_python_api import FireflyConnectionError
from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.bills_creator import BillOutcome, create_bills
from firefly_bills_analyzer.config import Config


def _make_config(**overrides: object) -> Config:
    base: dict[str, object] = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=2,
        amount_margin=0.10,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
        uncategorized_confidence_penalty=0.10,
        uncategorized_behavior="neutral",
        include_categories=[],
        exclude_categories=[],
        dry_run=False,
        export_format="none",
        web_port=5000,
        web_host="127.0.0.1",
        cache_dir="./cache",
        cache_ttl_categories=86400,
        cache_ttl_bills=3600,
        cache_ttl_transactions=3600,
        cache_ttl_payees=86400,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _pattern(
    name: str = "Netflix",
    *,
    category_name: str | None = None,
    amount_mean: float = 12.00,
    frequency: str = "monthly",
    occurrences: int = 4,
) -> RecurringPattern:
    return RecurringPattern(
        destination_name=name,
        category_name=category_name,
        occurrences=occurrences,
        amount_min=amount_mean,
        amount_max=amount_mean,
        amount_mean=amount_mean,
        median_interval_days=30,
        frequency=frequency,
        confidence=0.9,
    )


def _bill(name: str, amount_min: str, amount_max: str, repeat_freq: str) -> dict:
    return {
        "id": "1",
        "attributes": {
            "name": name,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "repeat_freq": repeat_freq,
        },
    }


def _client(bills: list[dict] | None = None, create_bill_side_effect: object = None) -> MagicMock:
    client = MagicMock()
    client.get_bills.return_value = bills or []
    if create_bill_side_effect is not None:
        client.create_bill.side_effect = create_bill_side_effect
    return client


class TestHappyPath:
    def test_creates_bill_for_new_payee(self) -> None:
        client = _client()
        config = _make_config(amount_margin=0.10)
        outcomes = create_bills([_pattern(amount_mean=10.00)], client, config, dry_run=False)
        assert outcomes == [BillOutcome(name="Netflix", status="created", message="created")]
        client.create_bill.assert_called_once()
        payload = client.create_bill.call_args.args[0]
        assert payload["name"] == "Netflix"
        assert payload["amount_min"] == "9.00"
        assert payload["amount_max"] == "11.00"
        assert payload["repeat_freq"] == "monthly"
        assert payload["active"] is True

    def test_frequency_maps_to_firefly_repeat_freq(self) -> None:
        client = _client()
        config = _make_config()
        create_bills([_pattern(frequency="half-yearly")], client, config, dry_run=False)
        payload = client.create_bill.call_args.args[0]
        assert payload["repeat_freq"] == "half-year"


class TestExactDuplicate:
    def test_matching_name_amounts_and_frequency_reports_exists_no_post(self) -> None:
        existing = [_bill("Netflix", "9.00", "11.00", "monthly")]
        client = _client(bills=existing)
        config = _make_config(amount_margin=0.10)
        outcomes = create_bills([_pattern(amount_mean=10.00)], client, config, dry_run=False)
        assert outcomes == [BillOutcome(name="Netflix", status="exists", message="already exists")]
        client.create_bill.assert_not_called()


class TestNameOnlyDuplicate:
    def test_differing_amount_reports_exists_diff_with_values(self) -> None:
        existing = [_bill("Netflix", "5.00", "6.00", "monthly")]
        client = _client(bills=existing)
        config = _make_config(amount_margin=0.10)
        outcomes = create_bills([_pattern(amount_mean=10.00)], client, config, dry_run=False)
        assert len(outcomes) == 1
        assert outcomes[0].name == "Netflix"
        assert outcomes[0].status == "exists-diff"
        assert "9.00" in outcomes[0].message
        assert "11.00" in outcomes[0].message
        assert "5.00" in outcomes[0].message
        assert "6.00" in outcomes[0].message
        client.create_bill.assert_not_called()

    def test_differing_frequency_reports_exists_diff_with_values(self) -> None:
        existing = [_bill("Netflix", "9.00", "11.00", "yearly")]
        client = _client(bills=existing)
        config = _make_config(amount_margin=0.10)
        outcomes = create_bills([_pattern(amount_mean=10.00)], client, config, dry_run=False)
        assert outcomes[0].status == "exists-diff"
        assert "monthly" in outcomes[0].message
        assert "yearly" in outcomes[0].message
        client.create_bill.assert_not_called()


class TestNameMatchTrimmingAndCase:
    def test_surrounding_whitespace_is_trimmed_and_matches(self) -> None:
        existing = [_bill("  Netflix  ", "9.00", "11.00", "monthly")]
        client = _client(bills=existing)
        config = _make_config(amount_margin=0.10)
        outcomes = create_bills([_pattern(amount_mean=10.00)], client, config, dry_run=False)
        assert outcomes[0].status == "exists"
        client.create_bill.assert_not_called()

    def test_case_difference_does_not_match_locally_but_422_from_api_maps_to_exists(self) -> None:
        existing = [_bill("netflix", "9.00", "11.00", "monthly")]
        error = FireflyConnectionError("POST failed: unexpected status 422", status_code=422)
        client = _client(bills=existing, create_bill_side_effect=error)
        config = _make_config(amount_margin=0.10)
        pattern = _pattern(name="Netflix", amount_mean=10.00)
        outcomes = create_bills([pattern], client, config, dry_run=False)
        client.create_bill.assert_called_once()
        assert outcomes == [BillOutcome(name="Netflix", status="exists", message="already exists")]


class TestDryRun:
    def test_all_outcomes_skipped_no_post(self) -> None:
        client = _client()
        config = _make_config()
        patterns = [_pattern(), _pattern(name="Spotify")]
        outcomes = create_bills(patterns, client, config, dry_run=True)
        assert all(o.status == "skipped" for o in outcomes)
        client.create_bill.assert_not_called()


class TestIrregularSkip:
    def test_irregular_pattern_is_skipped_by_default(self) -> None:
        client = _client()
        config = _make_config()
        outcomes = create_bills([_pattern(frequency="irregular")], client, config, dry_run=False)
        assert outcomes[0].status == "skipped"
        client.create_bill.assert_not_called()

    def test_irregular_pattern_created_when_forced(self) -> None:
        client = _client()
        config = _make_config()
        outcomes = create_bills(
            [_pattern(frequency="irregular")], client, config, dry_run=False, force=True
        )
        assert outcomes[0].status == "error"
        assert "irregular" in outcomes[0].message.lower()
        client.create_bill.assert_not_called()


class TestApiError:
    def test_non_name_uniqueness_error_reports_error_status(self) -> None:
        error = FireflyConnectionError("POST failed: unexpected status 500", status_code=500)
        client = _client(create_bill_side_effect=error)
        config = _make_config()
        outcomes = create_bills([_pattern()], client, config, dry_run=False)
        assert outcomes[0].status == "error"
        assert "500" in outcomes[0].message or "POST failed" in outcomes[0].message

    def test_connection_error_with_no_status_code_reports_error(self) -> None:
        error = FireflyConnectionError("POST failed: refused")
        client = _client(create_bill_side_effect=error)
        config = _make_config()
        outcomes = create_bills([_pattern()], client, config, dry_run=False)
        assert outcomes[0].status == "error"


amount_mean_strategy = st.floats(
    min_value=0.01, max_value=100_000, allow_nan=False, allow_infinity=False
)
margin_strategy = st.floats(min_value=0.0, max_value=0.9, allow_nan=False, allow_infinity=False)


@given(amount_mean_strategy, margin_strategy)
def test_amount_range_is_ordered_and_close_to_mean(mean: float, margin: float) -> None:
    from firefly_bills_analyzer.bills_creator import _amount_range

    amount_min, amount_max = _amount_range(mean, margin)
    assert float(amount_min) <= float(amount_max)
    # Allow a small tolerance for the 2-decimal rounding applied to each bound.
    assert float(amount_min) <= mean + 0.01
    assert float(amount_max) >= mean - 0.01
