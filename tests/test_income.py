"""TASK-026: detect income sources and resolve observed net income (UC12).

Covers FR-41a through FR-44: grouping deposits into income candidates by
income account and payer, classifying them via the frequency machinery UC2
already implements, qualifying (or rejecting/flagging) candidates per
account, and computing the observed net income and variance figures for
each resulting income source.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import date, timedelta

import pytest
from firefly_python_api import TransactionRead
from hypothesis import given, settings
from hypothesis import strategies as st

from firefly_bills_analyzer.config import Config
from firefly_bills_analyzer.income import (
    IncomeAccountIssue,
    IncomeSource,
    detect_income,
)


def _make_config(**overrides: object) -> Config:
    base = dict(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=2,
        amount_margin=0.10,
        amount_cluster_tolerance=0.15,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
        uncategorized_confidence_penalty=0.10,
        uncategorized_behavior="neutral",
        include_categories=[],
        exclude_categories=[],
        include_accounts=[],
        exclude_accounts=[],
        include_payees=[],
        exclude_payees=[],
        dry_run=False,
        export_format="none",
        web_port=5000,
        web_host="127.0.0.1",
        cache_dir="./cache",
        cache_ttl_categories=86400,
        cache_ttl_bills=3600,
        cache_ttl_transactions=3600,
        cache_ttl_payees=86400,
        income_accounts=[],
        income_min_occurrences=3,
        income_variance_tolerance=0.10,
    )
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def _deposit(
    iso_date: str, amount: str, destination_name: str, source_name: str
) -> TransactionRead:
    """Build a deposit-shaped ``TransactionRead``: note the deposit-side
    inversion where ``destination_name`` is the income account and
    ``source_name`` is the payer."""
    return TransactionRead(
        date=iso_date,
        amount=amount,
        destination_name=destination_name,
        category_name=None,
        source_name=source_name,
        source_id=None,
        tags=[],
    )


def _monthly_dates(start: date, count: int, step_days: int = 30) -> list[date]:
    return [start + timedelta(days=step_days * i) for i in range(count)]


# ---------------------------------------------------------------------------
# AC-1: A monthly salary is recognized (FR-42a, FR-43, FR-44)
# ---------------------------------------------------------------------------


def test_monthly_salary_is_recognized_as_income_source() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 12)
    deposits = [_deposit(d.isoformat(), "30000.00", "Salary Checking", "Employer") for d in dates]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    assert result.issues == []
    assert len(result.sources) == 1
    source = result.sources[0]
    assert isinstance(source, IncomeSource)
    assert source.income_account == "Salary Checking"
    assert source.payer == "Employer"
    assert source.occurrences == 12


# ---------------------------------------------------------------------------
# AC-2: The observed figure is the latest, not the mean (FR-43)
# ---------------------------------------------------------------------------


def test_observed_net_income_is_latest_occurrence_not_mean() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 12)
    amounts = ["30000.00"] * 11 + ["32000.00"]
    deposits = [
        _deposit(d.isoformat(), amount, "Salary Checking", "Employer")
        for d, amount in zip(dates, amounts)
    ]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    source = result.sources[0]
    assert source.observed_net_income == 32000.0
    assert source.observed_date == dates[-1].isoformat()
    assert source.amount_mean < source.observed_net_income


# ---------------------------------------------------------------------------
# AC-3: A quarterly payer does not qualify (FR-41c, FR-42b)
# ---------------------------------------------------------------------------


def test_quarterly_payer_does_not_qualify() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 4, step_days=90)
    deposits = [_deposit(d.isoformat(), "5000.00", "Salary Checking", "Contractor") for d in dates]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    assert result.sources == []
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert isinstance(issue, IncomeAccountIssue)
    assert issue.income_account == "Salary Checking"
    assert issue.reason == "no-qualifying-candidate"
    assert len(issue.candidates) == 1
    candidate = issue.candidates[0]
    assert candidate.payer == "Contractor"
    assert candidate.occurrences == 4
    assert candidate.frequency == "quarterly"


# ---------------------------------------------------------------------------
# AC-4: Too few occurrences do not qualify (FR-41c, FR-42b)
# ---------------------------------------------------------------------------


def test_too_few_occurrences_do_not_qualify() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 2)
    deposits = [_deposit(d.isoformat(), "30000.00", "Salary Checking", "Employer") for d in dates]
    config = _make_config(income_accounts=["Salary Checking"], income_min_occurrences=3)

    result = detect_income(deposits, config)

    assert result.sources == []
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.reason == "no-qualifying-candidate"
    assert len(issue.candidates) == 1
    assert issue.candidates[0].payer == "Employer"
    assert issue.candidates[0].occurrences == 2


# ---------------------------------------------------------------------------
# AC-5: Two qualifying payers are an ambiguity, not a sum (FR-42c)
# ---------------------------------------------------------------------------


def test_two_qualifying_payers_are_reported_as_ambiguous_not_summed() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 12)
    deposits = [
        _deposit(d.isoformat(), "30000.00", "Salary Checking", "Employer A") for d in dates
    ] + [_deposit(d.isoformat(), "20000.00", "Salary Checking", "Employer B") for d in dates]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    assert result.sources == []
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.income_account == "Salary Checking"
    assert issue.reason == "ambiguous"
    payers = {candidate.payer for candidate in issue.candidates}
    assert payers == {"Employer A", "Employer B"}


def test_ambiguous_candidate_summary_carries_no_amount_figure() -> None:
    """FR-42c: the application shall not sum, average, or otherwise combine
    the qualifying candidates. Assert this at the level of the public
    contract: an ``IncomeCandidateSummary`` has no amount-bearing field at
    all, so there is nowhere for a summed or averaged figure to hide."""
    dates = _monthly_dates(date(2024, 1, 1), 12)
    deposits = [
        _deposit(d.isoformat(), "30000.00", "Salary Checking", "Employer A") for d in dates
    ] + [_deposit(d.isoformat(), "20000.00", "Salary Checking", "Employer B") for d in dates]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    issue = result.issues[0]
    for candidate in issue.candidates:
        field_names = {f.name for f in fields(candidate)}
        assert not any("amount" in name for name in field_names)


# ---------------------------------------------------------------------------
# AC-6: A bonus is counted as an outlier, not absorbed (FR-44)
# ---------------------------------------------------------------------------


def test_bonus_is_counted_as_outlier_not_absorbed() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 12)
    amounts = ["30000.00"] * 12
    amounts[5] = "45000.00"
    deposits = [
        _deposit(d.isoformat(), amount, "Salary Checking", "Employer")
        for d, amount in zip(dates, amounts)
    ]
    config = _make_config(income_accounts=["Salary Checking"], income_variance_tolerance=0.10)

    result = detect_income(deposits, config)

    source = result.sources[0]
    # The bonus is not the latest occurrence, so the observed figure stays
    # the regular salary amount, and the bonus alone is flagged.
    assert source.observed_net_income == 30000.0
    assert source.outlier_count == 1
    assert source.amount_max == 45000.0


# ---------------------------------------------------------------------------
# AC-7: Same-day splits are one occurrence (FR-33a's reasoning, applied here)
# ---------------------------------------------------------------------------


def test_same_day_deposits_collapse_into_one_summed_occurrence() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 3)
    deposits = [
        _deposit(dates[0].isoformat(), "15000.00", "Salary Checking", "Employer"),
        _deposit(dates[0].isoformat(), "15000.00", "Salary Checking", "Employer"),
        _deposit(dates[1].isoformat(), "30000.00", "Salary Checking", "Employer"),
        _deposit(dates[2].isoformat(), "30000.00", "Salary Checking", "Employer"),
    ]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.occurrences == 3
    assert source.amount_min == 30000.0
    assert source.amount_max == 30000.0
    assert source.amount_mean == 30000.0


# ---------------------------------------------------------------------------
# AC-8: Two income accounts are resolved independently
# ---------------------------------------------------------------------------


def test_two_income_accounts_are_resolved_independently() -> None:
    dates = _monthly_dates(date(2024, 1, 1), 12)
    deposits = [
        _deposit(d.isoformat(), "30000.00", "Salary Checking", "Employer A") for d in dates
    ] + [_deposit(d.isoformat(), "8000.00", "Freelance Account", "Employer B") for d in dates]
    config = _make_config(income_accounts=["Salary Checking", "Freelance Account"])

    result = detect_income(deposits, config)

    assert result.issues == []
    assert len(result.sources) == 2
    accounts = {source.income_account for source in result.sources}
    assert accounts == {"Salary Checking", "Freelance Account"}


# ---------------------------------------------------------------------------
# AC-9: No deposits means no result and no error
# ---------------------------------------------------------------------------


def test_empty_deposit_list_yields_no_source_and_raises_nothing() -> None:
    """No occurrences at all is the degenerate case of "no qualifying
    candidate": every configured income account still appears exactly once
    in the result (per the property test below), just with an empty
    candidate list, and no exception is raised."""
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income([], config)

    assert result.sources == []
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.income_account == "Salary Checking"
    assert issue.reason == "no-qualifying-candidate"
    assert issue.candidates == []


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------

_INCOME_ACCOUNTS_UNIVERSE = ["Salary Checking", "Freelance Account"]
_PAYER_UNIVERSE = ["Employer A", "Employer B", "Employer C"]

_deposit_strategy = st.builds(
    _deposit,
    iso_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 1, 1)).map(
        lambda d: d.isoformat()
    ),
    amount=st.floats(min_value=1, max_value=100_000, allow_nan=False, allow_infinity=False).map(
        lambda amount: f"{amount:.2f}"
    ),
    destination_name=st.sampled_from(_INCOME_ACCOUNTS_UNIVERSE),
    source_name=st.sampled_from(_PAYER_UNIVERSE),
)


@given(st.lists(_deposit_strategy, max_size=30))
@settings(max_examples=50)
def test_every_configured_income_account_appears_exactly_once(
    deposits: list[TransactionRead],
) -> None:
    config = _make_config(income_accounts=_INCOME_ACCOUNTS_UNIVERSE)

    result = detect_income(deposits, config)

    source_accounts = [source.income_account for source in result.sources]
    issue_accounts = [issue.income_account for issue in result.issues]

    assert sorted(source_accounts + issue_accounts) == sorted(_INCOME_ACCOUNTS_UNIVERSE)
    assert set(source_accounts).isdisjoint(issue_accounts)


@given(
    st.lists(
        st.floats(min_value=1, max_value=1_000_000, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=15,
    )
)
@settings(max_examples=50)
def test_observed_net_income_matches_latest_occurrence_within_range(
    amounts: list[float],
) -> None:
    dates = _monthly_dates(date(2024, 1, 1), len(amounts))
    deposits = [
        _deposit(d.isoformat(), f"{amount:.2f}", "Salary Checking", "Employer")
        for d, amount in zip(dates, amounts)
    ]
    config = _make_config(income_accounts=["Salary Checking"])

    result = detect_income(deposits, config)

    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.observed_net_income == pytest.approx(amounts[-1])
    assert source.amount_min <= source.observed_net_income <= source.amount_max
