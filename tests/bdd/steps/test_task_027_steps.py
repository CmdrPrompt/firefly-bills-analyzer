"""TASK-027 step definitions for exporting and displaying income sources
(UC12): FR-45a, FR-45b, FR-45c, FR-45d, FR-46, SE-04.

Most scenarios drive the real `main()` pipeline with the withdrawal-side
fetch/filter/analyze stages mocked out (as `test_main.py` does), while
`income.detect_income` is either mocked to a controlled `IncomeResult` or
left to run for real over deposits built in these steps. `exporter.export`
and `exporter.export_income` are left unmocked so real files land in a
`tmp_path` the test chdirs into, matching how `exporter_test.py` verifies
file content directly rather than asserting on mock call shape.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer import exporter as exporter_module
from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.bills_creator import BillOutcome
from firefly_bills_analyzer.income import (
    IncomeAccountIssue,
    IncomeCandidateSummary,
    IncomeResult,
    IncomeSource,
)

scenarios("../features/TASK-027-income-export-and-display.feature")

BASE_ENV = {"FIREFLY_URL": "https://firefly.example.com", "FIREFLY_TOKEN": "tok"}


def _source(
    income_account: str = "Salary Checking",
    payer: str = "Employer",
) -> IncomeSource:
    return IncomeSource(
        income_account=income_account,
        payer=payer,
        observed_net_income=2500.0,
        observed_date="2026-01-01",
        occurrences=6,
        median_interval_days=30.0,
        amount_min=2400.0,
        amount_max=2600.0,
        amount_mean=2500.0,
        outlier_count=0,
    )


def _ambiguous_issue(
    income_account: str = "Shared Checking",
    payer_a: str = "Employer A",
    payer_b: str = "Employer B",
) -> IncomeAccountIssue:
    return IncomeAccountIssue(
        income_account=income_account,
        reason="ambiguous",
        candidates=[
            IncomeCandidateSummary(payer=payer_a, occurrences=4, frequency="monthly"),
            IncomeCandidateSummary(payer=payer_b, occurrences=4, frequency="monthly"),
        ],
    )


def _no_qualifying_issue(
    income_account: str = "Quarterly Account",
    payer: str = "Pension Fund",
) -> IncomeAccountIssue:
    return IncomeAccountIssue(
        income_account=income_account,
        reason="no-qualifying-candidate",
        candidates=[IncomeCandidateSummary(payer=payer, occurrences=4, frequency="quarterly")],
    )


def _pattern(name: str = "Netflix", confidence: float = 0.9) -> RecurringPattern:
    return RecurringPattern(
        destination_name=name,
        category_name=None,
        occurrences=4,
        amount_min=9.0,
        amount_max=11.0,
        amount_mean=10.0,
        median_interval_days=30.0,
        frequency="monthly",
        confidence=confidence,
        source_account_name=None,
        source_account_varies=False,
    )


@contextmanager
def _pipeline(
    *,
    env: dict[str, str] | None = None,
    patterns: list[RecurringPattern] | None = None,
    income_result: IncomeResult | None = None,
) -> Iterator[dict[str, Any]]:
    """Patch every withdrawal-side pipeline stage `__main__` delegates to.

    `income.detect_income` is patched only when `income_result` is given;
    otherwise the real function runs (over an empty deposit list by
    default), matching production behavior for accounts with no income
    configured. `exporter.export` and `exporter.export_income` are left
    real so scenarios can assert on actual written files.
    """
    patterns = [] if patterns is None else patterns
    full_env = {**BASE_ENV, "EXPORT_FORMAT": "none", **(env or {})}
    mod = "firefly_bills_analyzer.__main__"

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, full_env, clear=True))
        stack.enter_context(patch(f"{mod}.fetcher.fetch_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.fetcher.fetch_deposits", return_value=[]))
        stack.enter_context(patch(f"{mod}.category_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.account_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.payee_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.analyzer.identify_recurring", return_value=patterns))
        create_mock = stack.enter_context(
            patch(
                f"{mod}.bills_creator.create_bills",
                return_value=[BillOutcome(name="Netflix", status="created", message="created")],
            )
        )
        stack.enter_context(patch(f"{mod}.FireflyClient"))
        if income_result is not None:
            # This patch target only exists once `__main__` wires in the
            # `income` module (TASK-027's own change); until then it fails
            # with AttributeError, which is the expected red state.
            stack.enter_context(patch(f"{mod}.income.detect_income", return_value=income_result))

        yield {"create": create_mock}


def _income_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# AC-1: Income is exported to its own file
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a run with one detected income source and EXPORT_FORMAT={fmt}"),
    target_fixture="context",
)
def run_with_one_income_source(
    fmt: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": fmt},
        "income_result": IncomeResult(sources=[_source()], issues=[]),
    }


@when("the run completes", target_fixture="run_result")
def the_run_completes(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    from firefly_bills_analyzer.__main__ import main

    with _pipeline(
        env=context.get("env"),
        patterns=context.get("patterns"),
        income_result=context.get("income_result"),
    ):
        code = main(["--auto-approve"])
    captured = capsys.readouterr()
    return {
        "code": code,
        "stdout": captured.out,
        "tmp_path": context["tmp_path"],
        "target_account": context.get("target_account"),
    }


@then("two files are written, the pattern export and an income export")
def two_files_written(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    bills_files = list(tmp_path.glob("firefly-bills-*.csv"))
    income_files = list(tmp_path.glob("firefly-income-*.csv"))
    assert len(bills_files) == 1
    assert len(income_files) == 1


@then(parsers.parse('the income file contains one row with status "{status}"'))
def income_file_contains_one_row_with_status(run_result: dict[str, Any], status: str) -> None:
    tmp_path = run_result["tmp_path"]
    income_files = list(tmp_path.glob("firefly-income-*.csv"))
    assert len(income_files) == 1
    rows = _income_csv_rows(income_files[0])
    assert len(rows) == 1
    assert rows[0]["status"] == status


# ---------------------------------------------------------------------------
# AC-2: JSON format is honored
# ---------------------------------------------------------------------------


@given("the same run with EXPORT_FORMAT=json", target_fixture="context")
def same_run_with_json_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "json"},
        "income_result": IncomeResult(sources=[_source()], issues=[]),
    }


@then("the income export is valid JSON with the same field names")
def income_export_is_valid_json(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    income_files = list(tmp_path.glob("firefly-income-*.json"))
    assert len(income_files) == 1
    data = json.loads(income_files[0].read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 1
    expected_fields = {
        "income_account",
        "payer",
        "observed_net_income",
        "observed_date",
        "occurrences",
        "median_interval_days",
        "amount_min",
        "amount_max",
        "amount_mean",
        "outlier_count",
        "status",
    }
    assert set(data[0].keys()) == expected_fields


# ---------------------------------------------------------------------------
# AC-3: No export when the format is none
# ---------------------------------------------------------------------------


@given(
    "EXPORT_FORMAT=none and a detected income source",
    target_fixture="context",
)
def export_format_none_with_income_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "none"},
        "income_result": IncomeResult(sources=[_source(payer="Employer Corp")], issues=[]),
    }


@then("no income file is written")
def no_income_file_written(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    income_files = list(tmp_path.glob("firefly-income-*"))
    assert income_files == []


@then("the CLI still displays the income source")
def cli_still_displays_income_source(run_result: dict[str, Any]) -> None:
    assert "Employer Corp" in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-4: No export when income detection is disabled
# ---------------------------------------------------------------------------


@given("INCOME_ACCOUNTS empty and EXPORT_FORMAT=csv", target_fixture="context")
def income_accounts_empty_export_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    # An empty `INCOME_ACCOUNTS` still resolves to a (trivially empty)
    # `IncomeResult` via `detect_income` (TASK-026's loop over configured
    # accounts yields nothing to iterate); force that call to be patched
    # here too so this scenario fails for missing *wiring* today, not
    # merely because the assertion happens to hold with no wiring at all.
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "INCOME_ACCOUNTS": ""},
        "income_result": IncomeResult(sources=[], issues=[]),
    }


@then("only the pattern export is written")
def only_pattern_export_written(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    bills_files = list(tmp_path.glob("firefly-bills-*.csv"))
    income_files = list(tmp_path.glob("firefly-income-*"))
    assert len(bills_files) == 1
    assert income_files == []


# ---------------------------------------------------------------------------
# AC-5: An ambiguous account appears as a row
# ---------------------------------------------------------------------------


@given("an income account with two qualifying payers", target_fixture="context")
def income_account_with_two_qualifying_payers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv"},
        "income_result": IncomeResult(
            sources=[], issues=[_ambiguous_issue("Shared Checking", "Employer A", "Employer B")]
        ),
        "target_account": "Shared Checking",
    }


def _income_row_for_account(run_result: dict[str, Any], income_account: str) -> dict[str, str]:
    tmp_path = run_result["tmp_path"]
    income_files = list(tmp_path.glob("firefly-income-*.csv"))
    assert len(income_files) == 1
    rows = _income_csv_rows(income_files[0])
    matching = [r for r in rows if r["income_account"] == income_account]
    assert len(matching) == 1
    return matching[0]


@then(parsers.parse('the income export contains a row for that account with status "{status}"'))
def income_export_contains_row_with_status(run_result: dict[str, Any], status: str) -> None:
    row = _income_row_for_account(run_result, run_result["target_account"])
    assert row["status"].startswith(status) or row["status"] == status


@then("the row has an empty observed net income")
def row_has_empty_observed_net_income(run_result: dict[str, Any]) -> None:
    row = _income_row_for_account(run_result, run_result["target_account"])
    assert row["observed_net_income"] == ""


@then("both payers are named in the row")
def both_payers_named_in_row(run_result: dict[str, Any]) -> None:
    row = _income_row_for_account(run_result, run_result["target_account"])
    row_text = " ".join(row.values())
    assert "Employer A" in row_text
    assert "Employer B" in row_text


# ---------------------------------------------------------------------------
# AC-6: An account with no qualifying candidate appears as a row
# ---------------------------------------------------------------------------


@given("an income account whose only candidate is quarterly", target_fixture="context")
def income_account_quarterly_only_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv"},
        "income_result": IncomeResult(
            sources=[], issues=[_no_qualifying_issue("Quarterly Account", "Pension Fund")]
        ),
        "target_account": "Quarterly Account",
    }


# AC-6 reuses `income_export_contains_row_with_status` above; the step text
# in the feature file is identical to AC-5's, and `run_result["target_account"]`
# (set by each scenario's Given step) disambiguates which account's row to check.


# ---------------------------------------------------------------------------
# AC-7: The written path is reported
# ---------------------------------------------------------------------------


@given("a completed income export", target_fixture="context")
def completed_income_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv"},
        "income_result": IncomeResult(sources=[_source()], issues=[]),
    }


@when("the run finishes", target_fixture="run_result")
def the_run_finishes(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    return the_run_completes(context, capsys)


@then("the income file path is printed, on the same terms as FR-31")
def income_file_path_printed(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    income_files = list(tmp_path.glob("firefly-income-*.csv"))
    assert len(income_files) == 1
    assert str(income_files[0].name) in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-8: Income is displayed before the review flow
# ---------------------------------------------------------------------------


@given(
    "a run with a detected income source and pending suggestions",
    target_fixture="context",
)
def run_with_income_source_and_pending_suggestions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "none"},
        "income_result": IncomeResult(sources=[_source(payer="Employer Corp")], issues=[]),
        "patterns": [_pattern("Netflix")],
    }


@when("the CLI runs", target_fixture="run_result")
def the_cli_runs(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    from firefly_bills_analyzer.__main__ import main

    with (
        _pipeline(
            env=context.get("env"),
            patterns=context.get("patterns"),
            income_result=context.get("income_result"),
        ),
        patch("builtins.input", return_value="n"),
    ):
        code = main([])
    captured = capsys.readouterr()
    return {"code": code, "stdout": captured.out, "tmp_path": context["tmp_path"]}


@then("the income block is printed before the first suggestion prompt")
def income_block_before_first_suggestion(run_result: dict[str, Any]) -> None:
    stdout = run_result["stdout"]
    income_index = stdout.find("Employer Corp")
    suggestion_index = stdout.find("Netflix")
    assert income_index != -1, "income source was not printed at all"
    assert suggestion_index != -1, "suggestion was not printed at all"
    assert income_index < suggestion_index


# ---------------------------------------------------------------------------
# AC-9: Nothing is created in Firefly III from the income path
# ---------------------------------------------------------------------------


@given(
    "a run with income accounts configured and DRY_RUN unset",
    target_fixture="context",
)
def run_with_income_accounts_dry_run_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "none", "INCOME_ACCOUNTS": "Salary Checking"},
        "income_result": IncomeResult(sources=[_source()], issues=[]),
        "patterns": [_pattern("Netflix")],
    }


@then("no bill-creation call is issued beyond those the approved withdrawal suggestions produce")
def no_extra_bill_creation_call(run_result: dict[str, Any], context: dict[str, Any]) -> None:
    # The `_pipeline` context manager only patches `bills_creator.create_bills`
    # for the duration of the `main()` call inside `the_run_completes`/
    # `the_cli_runs`; re-run here with the same setup, capturing the mock so
    # its call count can be asserted (SE-04: nothing beyond the withdrawal
    # suggestions' own single creation call).
    from firefly_bills_analyzer.__main__ import main

    with _pipeline(
        env=context.get("env"),
        patterns=context.get("patterns"),
        income_result=context.get("income_result"),
    ) as mocks:
        main(["--auto-approve"])

    assert mocks["create"].call_count == 1


# ---------------------------------------------------------------------------
# AC-10: A new field flows through without an exporter change
# ---------------------------------------------------------------------------


@given("a field added to IncomeSource", target_fixture="context")
def field_added_to_income_source() -> dict[str, Any]:
    return {}


@when("the income export runs", target_fixture="export_result")
def the_income_export_runs(tmp_path: Path) -> dict[str, Any]:
    """Simulate a future field addition to `IncomeSource` by monkeypatching
    the dataclass used by `income.py`, reloading `exporter` so its
    dataclass-derived field list picks up the change, then exporting.

    This exercises the same "derive from the dataclass" contract the
    pattern export already has via `_FIELDNAMES = [f.name for f in
    fields(RecurringPattern)]`; mirroring that structure for income is the
    behavior this scenario specifies.
    """
    import dataclasses

    from firefly_bills_analyzer import income as income_module

    ExtendedIncomeSource = dataclasses.make_dataclass(
        "ExtendedIncomeSource",
        [(f.name, f.type) for f in dataclasses.fields(income_module.IncomeSource)]
        + [("payer_iban", str, dataclasses.field(default=""))],
        frozen=True,
    )

    original_income_source = income_module.IncomeSource
    income_module.IncomeSource = ExtendedIncomeSource  # type: ignore[misc]
    try:
        exporter_reloaded = importlib.reload(exporter_module)
        source = ExtendedIncomeSource(
            income_account="Salary Checking",
            payer="Employer",
            observed_net_income=2500.0,
            observed_date="2026-01-01",
            occurrences=6,
            median_interval_days=30.0,
            amount_min=2400.0,
            amount_max=2600.0,
            amount_mean=2500.0,
            outlier_count=0,
            payer_iban="DE00 1234 5678",
        )
        path = tmp_path / "income.csv"
        exporter_reloaded.export_income([source], [], "csv", path)
        rows = _income_csv_rows(path)
    finally:
        income_module.IncomeSource = original_income_source
        importlib.reload(exporter_module)

    return {"rows": rows}


@then("the new field appears in the output without editing the field list")
def new_field_appears_in_output(export_result: dict[str, Any]) -> None:
    rows = export_result["rows"]
    assert len(rows) == 1
    assert "payer_iban" in rows[0]
    assert rows[0]["payer_iban"] == "DE00 1234 5678"
