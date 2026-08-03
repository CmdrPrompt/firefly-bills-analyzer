"""UC12: detect income sources and resolve observed net income.

A pure consumer of the deposit list `fetcher.py` (TASK-025) retrieves plus
`Config`. Performs no I/O.

Deposits are grouped into income candidates by income account and payer
(FR-41a), classified via the same frequency machinery UC2 uses (FR-41b), and
qualified as an income source when they recur monthly often enough
(FR-41c). Each configured income account resolves to exactly one of: an
`IncomeSource` (FR-42a), or an `IncomeAccountIssue` reporting why none could
be resolved (FR-42b, FR-42c).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.analyzer import (
    _collapse_into_billing_events,
    _median_interval_days,
    classify_frequency,
)
from firefly_bills_analyzer.config import Config


@dataclass(frozen=True)
class IncomeCandidateSummary:
    """A rejected or ambiguous income candidate's identifying figures.

    Deliberately carries no amount-bearing field (FR-42c): the whole point
    of an ambiguous account is that the application must not sum, average,
    or otherwise pick between the qualifying candidates' amounts.
    """

    payer: str
    occurrences: int
    frequency: str


@dataclass(frozen=True)
class IncomeSource:
    """The one income candidate on an account that qualifies (FR-42a)."""

    income_account: str
    payer: str
    observed_net_income: float
    observed_date: str
    occurrences: int
    median_interval_days: float
    amount_min: float
    amount_max: float
    amount_mean: float
    outlier_count: int


@dataclass(frozen=True)
class IncomeAccountIssue:
    """A configured income account with no single qualifying candidate."""

    income_account: str
    reason: str  # "no-qualifying-candidate" | "ambiguous"
    candidates: list[IncomeCandidateSummary]


@dataclass(frozen=True)
class IncomeResult:
    sources: list[IncomeSource]
    issues: list[IncomeAccountIssue]


def _select_observed_occurrence(
    sorted_events: list[dict[str, Any]], tolerance: float
) -> dict[str, Any]:
    """Select the occurrence whose amount becomes observed_net_income (FR-43,
    FR-43a).

    The most recent occurrence is used unless it deviates from the median of
    all occurrence amounts by more than `tolerance`, in which case the
    search walks backward from the most recent occurrence to find the first
    (i.e. most recent) one that does not so deviate. The median, not the
    observed figure itself, is the reference point, since comparing an
    occurrence to the very figure it would set is circular. If every
    occurrence deviates from the median, the oldest occurrence is used.
    """
    amounts = [float(event["amount"]) for event in sorted_events]
    median = statistics.median(amounts)

    for event in reversed(sorted_events):
        amount = float(event["amount"])
        if median == 0 or abs(amount - median) / median <= tolerance:
            return event

    return sorted_events[0]


def _build_income_source(
    income_account: str,
    payer: str,
    events: list[dict[str, Any]],
    config: Config,
) -> IncomeSource:
    """Build an `IncomeSource` from one payer's collapsed occurrences.

    Observed net income is the amount of the most recent occurrence, not
    the mean (FR-43), unless that occurrence deviates from the median
    occurrence amount by more than `INCOME_VARIANCE_TOLERANCE`, in which
    case the most recent non-deviating occurrence is used instead (FR-43a).
    Variance figures (FR-44) are computed over every occurrence, including
    any skipped when selecting the observed figure, with outlier_count
    measuring deviation from the selected observed_net_income.
    """
    sorted_events = sorted(events, key=lambda event: str(event["date"]))
    tolerance = config.income_variance_tolerance
    observed_event = _select_observed_occurrence(sorted_events, tolerance)
    observed_net_income = float(observed_event["amount"])
    observed_date = str(observed_event["date"])

    amounts = [float(event["amount"]) for event in events]
    outlier_count = sum(
        1
        for amount in amounts
        if observed_net_income != 0
        and abs(amount - observed_net_income) / observed_net_income > tolerance
    )

    return IncomeSource(
        income_account=income_account,
        payer=payer,
        observed_net_income=observed_net_income,
        observed_date=observed_date,
        occurrences=len(events),
        median_interval_days=_median_interval_days(events),
        amount_min=min(amounts),
        amount_max=max(amounts),
        amount_mean=statistics.mean(amounts),
        outlier_count=outlier_count,
    )


def detect_income(deposits: list[TransactionRead], config: Config) -> IncomeResult:
    """Resolve each configured income account to an income source or issue.

    Every account named in `config.income_accounts` appears exactly once in
    the result, whether or not any deposits were retained for it.
    """
    sources: list[IncomeSource] = []
    issues: list[IncomeAccountIssue] = []

    for income_account in config.income_accounts:
        account_deposits = [
            deposit for deposit in deposits if deposit["destination_name"] == income_account
        ]

        by_payer: dict[str, list[TransactionRead]] = defaultdict(list)
        for deposit in account_deposits:
            by_payer[deposit["source_name"]].append(deposit)

        candidates: list[tuple[str, list[dict[str, Any]], str]] = []
        for payer, payer_deposits in by_payer.items():
            events = _collapse_into_billing_events(payer_deposits)
            frequency = classify_frequency(_median_interval_days(events))
            candidates.append((payer, events, frequency))

        qualifying = [
            candidate
            for candidate in candidates
            if candidate[2] == "monthly" and len(candidate[1]) >= config.income_min_occurrences
        ]

        if len(qualifying) == 1:
            payer, events, _frequency = qualifying[0]
            sources.append(_build_income_source(income_account, payer, events, config))
        elif len(qualifying) == 0:
            issues.append(
                IncomeAccountIssue(
                    income_account=income_account,
                    reason="no-qualifying-candidate",
                    candidates=[
                        IncomeCandidateSummary(
                            payer=payer, occurrences=len(events), frequency=frequency
                        )
                        for payer, events, frequency in candidates
                    ],
                )
            )
        else:
            issues.append(
                IncomeAccountIssue(
                    income_account=income_account,
                    reason="ambiguous",
                    candidates=[
                        IncomeCandidateSummary(
                            payer=payer, occurrences=len(events), frequency=frequency
                        )
                        for payer, events, frequency in qualifying
                    ],
                )
            )

    return IncomeResult(sources=sources, issues=issues)
