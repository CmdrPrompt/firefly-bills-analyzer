"""TASK-029 step definitions for exporting and displaying household spend
(UC13): FR-51a, FR-51b, FR-51c, FR-51d, FR-52.

Most scenarios drive the real `main()` pipeline with the withdrawal-side
fetch/filter/analyze stages mocked out (as `test_task_027_steps.py` does for
income), while `household_spend.aggregate_household_spend` is mocked to a
controlled `HouseholdSpendResult`. `exporter.export` and
`exporter.export_household_spend` are left unmocked so real files land in a
`tmp_path` the test chdirs into.
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
from firefly_bills_analyzer.household_spend import (
    HouseholdSpendRecord,
    HouseholdSpendResult,
    OneOffPurchase,
)

scenarios("../features/TASK-029-household-spend-export-and-display.feature")

BASE_ENV = {"FIREFLY_URL": "https://firefly.example.com", "FIREFLY_TOKEN": "tok"}

EMPTY_HOUSEHOLD_SPEND_RESULT = HouseholdSpendResult(
    records=[],
    one_off_purchases=[],
    unmatched_categories=[],
    include_tag_count=0,
    exclude_tag_count=0,
)


def _household_spend_record(
    source_account: str | None = "Checking",
    category: str | None = "Groceries",
    month_count: int = 6,
    monthly_totals: list[float] | None = None,
    median: float | None = 250.0,
    mean: float | None = 250.0,
    minimum: float | None = 200.0,
    maximum: float | None = 300.0,
) -> HouseholdSpendRecord:
    return HouseholdSpendRecord(
        source_account=source_account,
        category=category,
        month_count=month_count,
        monthly_totals=monthly_totals if monthly_totals is not None else [250.0] * month_count,
        median=median,
        mean=mean,
        minimum=minimum,
        maximum=maximum,
    )


def _one_off_purchase(
    date: str = "2026-01-15",
    amount: float = 1200.0,
    payee: str | None = "Furniture Shop",
    category: str | None = "Household",
    source_account: str | None = "Checking",
) -> OneOffPurchase:
    return OneOffPurchase(
        date=date,
        amount=amount,
        payee=payee,
        category=category,
        source_account=source_account,
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
    household_spend_result: HouseholdSpendResult | None = None,
) -> Iterator[dict[str, Any]]:
    """Patch every withdrawal-side pipeline stage `__main__` delegates to.

    `household_spend.aggregate_household_spend` is patched only when
    `household_spend_result` is given; otherwise the real function runs
    (over an empty transaction list by default, since
    `fetcher.fetch_transactions` is patched to `return_value=[]`), matching
    production behavior for an unconfigured feature (FR-47a).
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
        if household_spend_result is not None:
            # This patch target only exists once `__main__` wires in the
            # `household_spend` module (TASK-029's own change); until then
            # it fails with AttributeError, which is the expected red state.
            stack.enter_context(
                patch(
                    f"{mod}.household_spend.aggregate_household_spend",
                    return_value=household_spend_result,
                )
            )

        yield {"create": create_mock}


def _household_spend_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# AC-1: Household spend is exported to its own file
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a run with one household spend record and EXPORT_FORMAT={fmt}"),
    target_fixture="context",
)
def run_with_one_household_spend_record(
    fmt: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": fmt, "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record()],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@when("the run completes", target_fixture="run_result")
def the_run_completes(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    from firefly_bills_analyzer.__main__ import main

    with _pipeline(
        env=context.get("env"),
        patterns=context.get("patterns"),
        household_spend_result=context.get("household_spend_result"),
    ):
        code = main(["--auto-approve"])
    captured = capsys.readouterr()
    return {
        "code": code,
        "stdout": captured.out,
        "tmp_path": context["tmp_path"],
    }


@then("three export files exist")
def three_export_files_exist(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    bills_files = list(tmp_path.glob("firefly-bills-*.csv"))
    household_spend_files = list(tmp_path.glob("firefly-household-spend-*.csv"))
    assert len(bills_files) == 1
    assert len(household_spend_files) == 1


def _household_spend_files(run_result: dict[str, Any], ext: str = "csv") -> list[Path]:
    return list(run_result["tmp_path"].glob(f"firefly-household-spend-*.{ext}"))


@then(parsers.parse('the household spend file contains one row with record_type "{record_type}"'))
def household_spend_file_contains_one_row_with_record_type(
    run_result: dict[str, Any], record_type: str
) -> None:
    files = _household_spend_files(run_result)
    assert len(files) == 1
    rows = _household_spend_csv_rows(files[0])
    matching = [r for r in rows if r["record_type"] == record_type]
    assert len(matching) == 1


# ---------------------------------------------------------------------------
# AC-2: One-off purchases are distinguishable
# ---------------------------------------------------------------------------


@given(
    "a run with one household spend record and two one-off purchases",
    target_fixture="context",
)
def run_with_record_and_two_one_offs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record()],
            one_off_purchases=[
                _one_off_purchase(date="2026-01-15", payee="Furniture Shop"),
                _one_off_purchase(date="2026-02-20", payee="Appliance Store"),
            ],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@then(parsers.parse('the household spend file contains two rows with record_type "{record_type}"'))
def household_spend_file_contains_two_rows_with_record_type(
    run_result: dict[str, Any], record_type: str
) -> None:
    files = _household_spend_files(run_result)
    assert len(files) == 1
    rows = _household_spend_csv_rows(files[0])
    matching = [r for r in rows if r["record_type"] == record_type]
    assert len(matching) == 2


@then("each one-off row carries its date, amount, payee, category, and source account")
def each_one_off_row_carries_its_fields(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result)
    rows = _household_spend_csv_rows(files[0])
    one_off_rows = [r for r in rows if r["record_type"] == "one-off"]
    assert len(one_off_rows) == 2
    for row in one_off_rows:
        assert row["date"]
        assert row["amount"]
        assert row["destination_name"]
        assert row["category_name"]
        assert row["source_account_name"]


# ---------------------------------------------------------------------------
# AC-3: JSON format is honored
# ---------------------------------------------------------------------------


@given("the same run with EXPORT_FORMAT=json", target_fixture="context")
def same_run_with_json_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "json", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record()],
            one_off_purchases=[_one_off_purchase()],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@then("the household spend export is valid JSON with the same field names")
def household_spend_export_is_valid_json(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result, ext="json")
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert isinstance(data, list)
    record_types = {row["record_type"] for row in data}
    assert "household-spend" in record_types
    assert "one-off" in record_types
    household_row = next(row for row in data if row["record_type"] == "household-spend")
    assert "source_account_name" in household_row
    assert "category_name" in household_row
    assert "median_monthly" in household_row


# ---------------------------------------------------------------------------
# AC-4: No export when the format is none
# ---------------------------------------------------------------------------


@given("EXPORT_FORMAT=none and household spend measured", target_fixture="context")
def export_format_none_with_household_spend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "none", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record(category="Groceries")],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@then("no household spend file is written")
def no_household_spend_file_written(run_result: dict[str, Any]) -> None:
    files = list(run_result["tmp_path"].glob("firefly-household-spend-*"))
    assert files == []


@then("the CLI still displays the household spend figures")
def cli_still_displays_household_spend_figures(run_result: dict[str, Any]) -> None:
    assert "Groceries" in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-5: No export when the feature is disabled
# ---------------------------------------------------------------------------


@given("HOUSEHOLD_SPEND_CATEGORIES is empty", target_fixture="context")
def household_spend_categories_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": ""},
        "household_spend_result": EMPTY_HOUSEHOLD_SPEND_RESULT,
    }


# ---------------------------------------------------------------------------
# AC-6: A record with too few months exports without a median
# ---------------------------------------------------------------------------


@given("a household spend record produced under FR-49e", target_fixture="context")
def household_spend_record_under_fr_49e(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[
                _household_spend_record(
                    month_count=2,
                    monthly_totals=[100.0, 120.0],
                    median=None,
                    mean=110.0,
                    minimum=100.0,
                    maximum=120.0,
                )
            ],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@then("its row carries its complete month count and an empty median")
def row_carries_month_count_and_empty_median(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result)
    rows = _household_spend_csv_rows(files[0])
    household_rows = [r for r in rows if r["record_type"] == "household-spend"]
    assert len(household_rows) == 1
    assert household_rows[0]["complete_months"] == "2"
    assert household_rows[0]["median_monthly"] == ""


# ---------------------------------------------------------------------------
# AC-7: An unmatched category reaches the file
# ---------------------------------------------------------------------------


@given("a configured category matching no transaction", target_fixture="context")
def configured_category_matching_no_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": "Nonexistent Category"},
        "household_spend_result": HouseholdSpendResult(
            records=[],
            one_off_purchases=[],
            unmatched_categories=["Nonexistent Category"],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@then("it appears in the household spend export")
def it_appears_in_the_household_spend_export(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result)
    assert len(files) == 1
    rows = _household_spend_csv_rows(files[0])
    unmatched_rows = [r for r in rows if r["record_type"] == "unmatched-category"]
    assert any(r["category_name"] == "Nonexistent Category" for r in unmatched_rows)


# ---------------------------------------------------------------------------
# AC-8: Tag correction counts are exported
# ---------------------------------------------------------------------------


@given(
    "a run in which the include tag admitted two transactions and the exclude tag removed one",
    target_fixture="context",
)
def run_with_tag_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=2,
            exclude_tag_count=1,
        ),
    }


@then("both counts appear in the export")
def both_counts_appear_in_the_export(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result)
    assert len(files) == 1
    rows = _household_spend_csv_rows(files[0])
    tag_rows = [r for r in rows if r["record_type"] == "tag-counts"]
    assert len(tag_rows) == 1
    assert tag_rows[0]["include_tag_count"] == "2"
    assert tag_rows[0]["exclude_tag_count"] == "1"


# ---------------------------------------------------------------------------
# AC-9: The written path is reported
# ---------------------------------------------------------------------------


@given("a completed household spend export", target_fixture="context")
def completed_household_spend_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "csv", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record()],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@when("the run finishes", target_fixture="run_result")
def the_run_finishes(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    return the_run_completes(context, capsys)


@then("the household spend file path is printed, on the same terms as FR-31")
def household_spend_file_path_printed(run_result: dict[str, Any]) -> None:
    files = _household_spend_files(run_result)
    assert len(files) == 1
    assert str(files[0].name) in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-10: Household spend is displayed before the review flow
# ---------------------------------------------------------------------------


@given(
    "a run with household spend measured and pending suggestions",
    target_fixture="context",
)
def run_with_household_spend_and_pending_suggestions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": "none", "HOUSEHOLD_SPEND_CATEGORIES": "Groceries"},
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record(source_account="Checking Account")],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
        "patterns": [_pattern("Netflix")],
    }


@when("the CLI runs", target_fixture="run_result")
def the_cli_runs(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    from firefly_bills_analyzer.__main__ import main

    with (
        _pipeline(
            env=context.get("env"),
            patterns=context.get("patterns"),
            household_spend_result=context.get("household_spend_result"),
        ),
        patch("builtins.input", return_value="n"),
    ):
        code = main([])
    captured = capsys.readouterr()
    return {"code": code, "stdout": captured.out, "tmp_path": context["tmp_path"]}


@then("the household spend block is printed before the first suggestion prompt")
def household_spend_block_before_first_suggestion(run_result: dict[str, Any]) -> None:
    stdout = run_result["stdout"]
    household_spend_index = stdout.find("Checking Account")
    suggestion_index = stdout.find("Netflix")
    assert household_spend_index != -1, "household spend was not printed at all"
    assert suggestion_index != -1, "suggestion was not printed at all"
    assert household_spend_index < suggestion_index


# ---------------------------------------------------------------------------
# AC-11: A new field flows through without an exporter change
# ---------------------------------------------------------------------------


@given("a field added to the household spend record", target_fixture="context")
def field_added_to_household_spend_record() -> dict[str, Any]:
    return {}


@when("the export runs", target_fixture="export_result")
def the_export_runs(tmp_path: Path) -> dict[str, Any]:
    """Simulate a future field addition to `HouseholdSpendRecord` by
    monkeypatching the dataclass used by `household_spend.py`, reloading
    `exporter` so its dataclass-derived field list picks up the change,
    then exporting.
    """
    import dataclasses

    from firefly_bills_analyzer import household_spend as household_spend_module

    ExtendedRecord = dataclasses.make_dataclass(
        "ExtendedHouseholdSpendRecord",
        [(f.name, f.type) for f in dataclasses.fields(household_spend_module.HouseholdSpendRecord)]
        + [("notes", str, dataclasses.field(default=""))],
        frozen=True,
    )

    original_record = household_spend_module.HouseholdSpendRecord
    household_spend_module.HouseholdSpendRecord = ExtendedRecord  # type: ignore[misc]
    try:
        exporter_reloaded = importlib.reload(exporter_module)
        record = ExtendedRecord(
            source_account="Checking",
            category="Groceries",
            month_count=6,
            monthly_totals=[250.0] * 6,
            median=250.0,
            mean=250.0,
            minimum=200.0,
            maximum=300.0,
            notes="extra field",
        )
        path = tmp_path / "household_spend.csv"
        result = HouseholdSpendResult(
            records=[record],
            one_off_purchases=[],
            unmatched_categories=[],
            include_tag_count=0,
            exclude_tag_count=0,
        )
        exporter_reloaded.export_household_spend(result, "csv", path)
        rows = _household_spend_csv_rows(path)
    finally:
        household_spend_module.HouseholdSpendRecord = original_record
        importlib.reload(exporter_module)

    return {"rows": rows}


@then("the new field appears in the output without editing the field list")
def new_field_appears_in_output(export_result: dict[str, Any]) -> None:
    rows = export_result["rows"]
    household_rows = [r for r in rows if r["record_type"] == "household-spend"]
    assert len(household_rows) == 1
    assert "notes" in household_rows[0]
    assert household_rows[0]["notes"] == "extra field"
