"""TASK-037 step definitions for multi-format export support (FR-53a,
FR-53b, FR-53c, FR-53d, FR-08, FR-45a, FR-51a, FR-29, FR-31).

Scenarios that run a real analysis (AC-1, AC-2, AC-3, AC-7) drive the real
`main()` pipeline with fetch/filter/analyze stages mocked out, income and
household spend results controlled directly, and `exporter` left unmocked
so real files land in a `tmp_path` the test chdirs into. Scenarios that
validate configuration (AC-4, AC-5, AC-6) call `Config.from_env()` directly.
AC-8 checks the static `--help` text.
"""

from __future__ import annotations

import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.bills_creator import BillOutcome
from firefly_bills_analyzer.config import Config, ConfigError
from firefly_bills_analyzer.household_spend import HouseholdSpendRecord, HouseholdSpendResult
from firefly_bills_analyzer.income import IncomeResult, IncomeSource

scenarios("../features/TASK-037-multi-format-export-support.feature")

BASE_ENV = {"FIREFLY_URL": "https://firefly.example.com", "FIREFLY_TOKEN": "tok"}

EMPTY_INCOME_RESULT = IncomeResult(sources=[], issues=[])
EMPTY_HOUSEHOLD_SPEND_RESULT = HouseholdSpendResult(
    records=[],
    one_off_purchases=[],
    unmatched_categories=[],
    unmatched_threshold_overrides=[],
    include_tag_count=0,
    exclude_tag_count=0,
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


def _income_source(income_account: str = "Salary Checking") -> IncomeSource:
    return IncomeSource(
        income_account=income_account,
        payer="Employer",
        observed_net_income=2500.0,
        observed_date="2026-01-01",
        occurrences=6,
        median_interval_days=30.0,
        amount_min=2400.0,
        amount_max=2600.0,
        amount_mean=2500.0,
        outlier_count=0,
    )


def _household_spend_record() -> HouseholdSpendRecord:
    return HouseholdSpendRecord(
        source_account="Checking",
        category="Groceries",
        month_count=6,
        monthly_totals=[250.0] * 6,
        median=250.0,
        mean=250.0,
        minimum=200.0,
        maximum=300.0,
    )


@contextmanager
def _pipeline(
    *,
    env: dict[str, str] | None,
    patterns: list[RecurringPattern],
    income_result: IncomeResult,
    household_spend_result: HouseholdSpendResult,
) -> Iterator[None]:
    """Patch every pipeline stage `__main__` delegates to, leaving `exporter`
    unmocked so real files land on disk."""
    full_env = {**BASE_ENV, **(env or {})}
    mod = "firefly_bills_analyzer.__main__"

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, full_env, clear=True))
        stack.enter_context(patch(f"{mod}.fetcher.fetch_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.fetcher.fetch_deposits", return_value=[]))
        stack.enter_context(patch(f"{mod}.category_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.account_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.payee_filter.filter_transactions", return_value=[]))
        stack.enter_context(patch(f"{mod}.analyzer.identify_recurring", return_value=patterns))
        stack.enter_context(patch(f"{mod}.income.detect_income", return_value=income_result))
        stack.enter_context(
            patch(
                f"{mod}.household_spend.aggregate_household_spend",
                return_value=household_spend_result,
            )
        )
        stack.enter_context(
            patch(
                f"{mod}.bills_creator.create_bills",
                return_value=[BillOutcome(name="Netflix", status="created", message="created")],
            )
        )
        stack.enter_context(patch(f"{mod}.FireflyClient"))
        yield


def _run_main(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    from firefly_bills_analyzer.__main__ import main

    with _pipeline(
        env=context["env"],
        patterns=context.get("patterns", []),
        income_result=context.get("income_result", EMPTY_INCOME_RESULT),
        household_spend_result=context.get("household_spend_result", EMPTY_HOUSEHOLD_SPEND_RESULT),
    ):
        code = main(["--dry-run", "--auto-approve"])
    captured = capsys.readouterr()
    return {"code": code, "stdout": captured.out, "tmp_path": context["tmp_path"]}


def _bills_files(tmp_path: Path, ext: str) -> list[Path]:
    return list(tmp_path.glob(f"firefly-bills-*.{ext}"))


def _income_files(tmp_path: Path, ext: str) -> list[Path]:
    return list(tmp_path.glob(f"firefly-income-*.{ext}"))


def _household_spend_files(tmp_path: Path, ext: str) -> list[Path]:
    return list(tmp_path.glob(f"firefly-household-spend-*.{ext}"))


# ---------------------------------------------------------------------------
# AC-1, AC-2, AC-3: single/multi-format exports of all three reports
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "EXPORT_FORMAT={fmt} configured and a dry-run analysis with patterns, income sources, "
        "and household spend to export"
    ),
    target_fixture="context",
)
def full_run_configured(
    fmt: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": fmt},
        "patterns": [_pattern()],
        "income_result": IncomeResult(sources=[_income_source()], issues=[]),
        "household_spend_result": HouseholdSpendResult(
            records=[_household_spend_record()],
            one_off_purchases=[],
            unmatched_categories=[],
            unmatched_threshold_overrides=[],
            include_tag_count=0,
            exclude_tag_count=0,
        ),
    }


@when("the analysis runs and exports complete", target_fixture="run_result")
def analysis_runs_and_exports_complete(
    context: dict[str, Any], capsys: pytest.CaptureFixture
) -> dict[str, Any]:
    return _run_main(context, capsys)


@then(parsers.parse("patterns are exported to a {fmt_word} file with .{ext} extension"))
def patterns_exported_to_extension(run_result: dict[str, Any], ext: str) -> None:
    files = _bills_files(run_result["tmp_path"], ext)
    assert len(files) == 1


@then(parsers.parse("income sources are exported to a {fmt_word} file with .{ext} extension"))
def income_exported_to_extension(run_result: dict[str, Any], ext: str) -> None:
    files = _income_files(run_result["tmp_path"], ext)
    assert len(files) == 1


@then(parsers.parse("household spend is exported to a {fmt_word} file with .{ext} extension"))
def household_spend_exported_to_extension(run_result: dict[str, Any], ext: str) -> None:
    files = _household_spend_files(run_result["tmp_path"], ext)
    assert len(files) == 1


@then("the path to each file is printed to the terminal")
def path_to_each_file_is_printed(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    all_files = [
        *_bills_files(tmp_path, "csv"),
        *_bills_files(tmp_path, "json"),
        *_income_files(tmp_path, "csv"),
        *_income_files(tmp_path, "json"),
        *_household_spend_files(tmp_path, "csv"),
        *_household_spend_files(tmp_path, "json"),
    ]
    assert all_files, "expected at least one exported file"
    for path in all_files:
        assert path.name in run_result["stdout"]


@then("patterns are exported to both a .csv file and a .json file")
def patterns_exported_to_both_formats(run_result: dict[str, Any]) -> None:
    assert len(_bills_files(run_result["tmp_path"], "csv")) == 1
    assert len(_bills_files(run_result["tmp_path"], "json")) == 1


@then("income sources are exported to both a .csv file and a .json file")
def income_exported_to_both_formats(run_result: dict[str, Any]) -> None:
    assert len(_income_files(run_result["tmp_path"], "csv")) == 1
    assert len(_income_files(run_result["tmp_path"], "json")) == 1


@then("household spend is exported to both a .csv file and a .json file")
def household_spend_exported_to_both_formats(run_result: dict[str, Any]) -> None:
    assert len(_household_spend_files(run_result["tmp_path"], "csv")) == 1
    assert len(_household_spend_files(run_result["tmp_path"], "json")) == 1


@then("the paths to all six files are printed to the terminal")
def paths_to_all_six_files_are_printed(run_result: dict[str, Any]) -> None:
    tmp_path = run_result["tmp_path"]
    all_files = [
        *_bills_files(tmp_path, "csv"),
        *_bills_files(tmp_path, "json"),
        *_income_files(tmp_path, "csv"),
        *_income_files(tmp_path, "json"),
        *_household_spend_files(tmp_path, "csv"),
        *_household_spend_files(tmp_path, "json"),
    ]
    assert len(all_files) == 6
    for path in all_files:
        assert path.name in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-4, AC-5, AC-6: invalid EXPORT_FORMAT configurations rejected at startup
# ---------------------------------------------------------------------------


@given(parsers.parse("EXPORT_FORMAT={fmt} configured"), target_fixture="context")
def export_format_configured(fmt: str) -> dict[str, Any]:
    return {"env": {"EXPORT_FORMAT": fmt}}


@when("the application is invoked", target_fixture="startup_result")
def application_is_invoked(context: dict[str, Any]) -> dict[str, Any]:
    full_env = {**BASE_ENV, **context["env"]}
    with patch.dict(os.environ, full_env, clear=True):
        try:
            Config.from_env()
        except ConfigError as exc:
            return {"error": exc}
    return {"error": None}


@then(
    parsers.parse(
        "startup fails with a ConfigError stating none cannot be combined with other export formats"
    )
)
def startup_fails_none_combined(startup_result: dict[str, Any]) -> None:
    assert startup_result["error"] is not None
    assert "none" in str(startup_result["error"])
    assert "combined" in str(startup_result["error"])


@then(
    parsers.parse("startup fails with a ConfigError naming {value} as an unsupported export format")
)
def startup_fails_unsupported_format(startup_result: dict[str, Any], value: str) -> None:
    assert startup_result["error"] is not None
    assert value in str(startup_result["error"])
    assert "unsupported" in str(startup_result["error"]) or "not a supported" in str(
        startup_result["error"]
    )


@then(
    parsers.parse(
        "startup fails with a ConfigError naming {value} as appearing more than once in "
        "EXPORT_FORMAT"
    )
)
def startup_fails_duplicate_format(startup_result: dict[str, Any], value: str) -> None:
    assert startup_result["error"] is not None
    assert value in str(startup_result["error"])
    assert "more than once" in str(startup_result["error"])


# ---------------------------------------------------------------------------
# AC-7: each exported file path is printed
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "EXPORT_FORMAT={fmt} configured and a dry-run analysis with patterns and income sources "
        "to export"
    ),
    target_fixture="context",
)
def run_with_patterns_and_income_configured(
    fmt: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "env": {"EXPORT_FORMAT": fmt},
        "patterns": [_pattern()],
        "income_result": IncomeResult(sources=[_income_source()], issues=[]),
        "household_spend_result": EMPTY_HOUSEHOLD_SPEND_RESULT,
    }


@when("the analysis runs", target_fixture="run_result")
def analysis_runs(context: dict[str, Any], capsys: pytest.CaptureFixture) -> dict[str, Any]:
    return _run_main(context, capsys)


@then("the printed output includes the path to the patterns export file")
def printed_output_includes_patterns_path(run_result: dict[str, Any]) -> None:
    files = _bills_files(run_result["tmp_path"], "csv")
    assert len(files) == 1
    assert files[0].name in run_result["stdout"]


@then("the printed output includes the path to the income export file")
def printed_output_includes_income_path(run_result: dict[str, Any]) -> None:
    files = _income_files(run_result["tmp_path"], "csv")
    assert len(files) == 1
    assert files[0].name in run_result["stdout"]


# ---------------------------------------------------------------------------
# AC-8: --help documents the comma-separated syntax
# ---------------------------------------------------------------------------


@when("the application is invoked with --help", target_fixture="help_text")
def application_invoked_with_help() -> str:
    from firefly_bills_analyzer.__main__ import build_arg_parser

    return build_arg_parser().format_help()


@then(
    "the help text shows EXPORT_FORMAT as accepting csv, json, none, or a comma-separated list "
    "such as csv,json"
)
def help_text_shows_comma_separated_syntax(help_text: str) -> None:
    assert "EXPORT_FORMAT" in help_text
    assert "csv" in help_text
    assert "json" in help_text
    assert "none" in help_text
    assert "csv,json" in help_text
