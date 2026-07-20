"""Tests for __main__ (UC3 terminal flow, UC5 dry-run/export): CLI pipeline
orchestration, review flow, and dry-run.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from firefly_python_api import TransactionRead

from firefly_bills_analyzer import cache as cache_module
from firefly_bills_analyzer.__main__ import _format_suggestion, main
from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.bills_creator import BillOutcome

BASE_ENV = {"FIREFLY_URL": "https://firefly.example.com", "FIREFLY_TOKEN": "tok"}

_TRANSACTION: TransactionRead = TransactionRead(
    date="2026-01-01", amount="10.00", destination_name="Netflix", category_name="Entertainment"
)


def _pattern(
    name: str = "Netflix",
    confidence: float = 0.9,
    source_account_name: str | None = None,
    source_account_varies: bool = False,
) -> RecurringPattern:
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
        source_account_name=source_account_name,
        source_account_varies=source_account_varies,
    )


@contextmanager
def _pipeline(
    patterns: list[RecurringPattern] | None = None, env: dict[str, str] | None = None
) -> Iterator[dict[str, MagicMock]]:
    """Patch every pipeline module __main__ delegates to, and set up .env vars."""
    patterns = [_pattern()] if patterns is None else patterns
    full_env = {**BASE_ENV, "EXPORT_FORMAT": "none", **(env or {})}
    mod = "firefly_bills_analyzer.__main__"
    with (
        patch.dict(os.environ, full_env, clear=True),
        patch(f"{mod}.fetcher.fetch_transactions", return_value=[_TRANSACTION]) as fetch,
        patch(f"{mod}.category_filter.filter_transactions", return_value=[_TRANSACTION]) as filt,
        patch(
            f"{mod}.account_filter.filter_transactions", return_value=[_TRANSACTION]
        ) as account_filt,
        patch(f"{mod}.analyzer.identify_recurring", return_value=patterns) as analyze,
        patch(
            f"{mod}.bills_creator.create_bills",
            return_value=[BillOutcome(name="Netflix", status="created", message="created")],
        ) as create,
        patch(f"{mod}.exporter.export") as export,
        patch(f"{mod}.FireflyClient") as client,
    ):
        yield {
            "fetch": fetch,
            "filter": filt,
            "account_filter": account_filt,
            "analyze": analyze,
            "create": create,
            "export": export,
            "client": client,
        }


class TestFormatSuggestionSourceAccount:
    def test_includes_account_name_when_resolved_and_not_varying(self) -> None:
        pattern = _pattern(source_account_name="Checking", source_account_varies=False)

        assert "from Checking" in _format_suggestion(pattern)

    def test_includes_varies_indicator_when_source_account_varies(self) -> None:
        pattern = _pattern(source_account_name="Checking", source_account_varies=True)

        assert "from (varies)" in _format_suggestion(pattern)

    def test_omits_source_account_text_when_not_resolved(self) -> None:
        pattern = _pattern(source_account_name=None, source_account_varies=False)

        formatted = _format_suggestion(pattern)

        assert "from " not in formatted
        assert pattern.destination_name in formatted


class TestConfigError:
    def test_missing_config_prints_message_and_returns_nonzero(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        with patch.dict(os.environ, {}, clear=True):
            code = main([])
        assert code != 0
        captured = capsys.readouterr()
        assert "FIREFLY_URL" in captured.err
        # NFR-04: a plain message, not a stack trace.
        assert "Traceback" not in captured.err


class TestPipelineWiring:
    def test_calls_filter_between_fetch_and_analyze(self) -> None:
        with _pipeline() as mocks:
            code = main(["--auto-approve"])

        assert code == 0
        mocks["filter"].assert_called_once_with([_TRANSACTION], mocks["filter"].call_args.args[1])
        mocks["account_filter"].assert_called_once_with(
            [_TRANSACTION], mocks["account_filter"].call_args.args[1]
        )
        mocks["analyze"].assert_called_once_with([_TRANSACTION], mocks["analyze"].call_args.args[1])

    def test_no_patterns_found_prints_message_and_creates_nothing(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        with _pipeline(patterns=[]) as mocks:
            code = main(["--auto-approve"])

        assert code == 0
        mocks["create"].assert_not_called()
        assert "No recurring payment patterns found" in capsys.readouterr().out


class TestAutoApprove:
    def test_approves_all_above_threshold_without_prompting(self) -> None:
        patterns = [_pattern("Netflix", confidence=0.9), _pattern("Spotify", confidence=0.5)]
        env = {"HIGH_CONFIDENCE_THRESHOLD": "0.8"}
        with _pipeline(patterns=patterns, env=env) as mocks, patch("builtins.input") as mock_input:
            code = main(["--auto-approve"])

        assert code == 0
        mock_input.assert_not_called()
        approved = mocks["create"].call_args.args[0]
        assert [p.destination_name for p in approved] == ["Netflix"]

    def test_prints_source_account_name_for_each_suggestion(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        patterns = [_pattern("Netflix", confidence=0.9, source_account_name="Checking")]
        with _pipeline(patterns=patterns):
            code = main(["--auto-approve"])

        assert code == 0
        assert "from Checking" in capsys.readouterr().out


class TestInteractiveReview:
    def test_yes_approves_entry(self) -> None:
        patterns = [_pattern("Netflix", confidence=0.9)]
        with _pipeline(patterns=patterns) as mocks, patch("builtins.input", return_value="y"):
            code = main([])

        assert code == 0
        approved = mocks["create"].call_args.args[0]
        assert [p.destination_name for p in approved] == ["Netflix"]

    def test_no_or_empty_answer_rejects_entry(self) -> None:
        patterns = [_pattern("Netflix", confidence=0.9)]
        with _pipeline(patterns=patterns) as mocks, patch("builtins.input", return_value=""):
            code = main([])

        assert code == 0
        mocks["create"].assert_not_called()

    def test_all_approves_remaining_without_further_prompting(self) -> None:
        patterns = [_pattern("Netflix", confidence=0.9), _pattern("Spotify", confidence=0.9)]
        with (
            _pipeline(patterns=patterns) as mocks,
            patch("builtins.input", return_value="a") as mock_input,
        ):
            code = main([])

        assert code == 0
        assert mock_input.call_count == 1
        approved = mocks["create"].call_args.args[0]
        assert [p.destination_name for p in approved] == ["Netflix", "Spotify"]

    def test_quit_stops_reviewing_remaining_entries(self) -> None:
        patterns = [_pattern("Netflix", confidence=0.9), _pattern("Spotify", confidence=0.9)]
        with _pipeline(patterns=patterns) as mocks, patch("builtins.input", return_value="q"):
            code = main([])

        assert code == 0
        mocks["create"].assert_not_called()

    def test_prints_source_account_name_for_each_suggestion(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        patterns = [_pattern("Netflix", confidence=0.9, source_account_name="Checking")]
        with _pipeline(patterns=patterns), patch("builtins.input", return_value="y"):
            code = main([])

        assert code == 0
        assert "from Checking" in capsys.readouterr().out


class TestDryRun:
    def test_passes_dry_run_true_to_create_bills(self) -> None:
        with _pipeline() as mocks:
            code = main(["--dry-run", "--auto-approve"])

        assert code == 0
        assert mocks["create"].call_args.kwargs["dry_run"] is True

    def test_exports_when_export_format_set(self) -> None:
        with _pipeline(env={"EXPORT_FORMAT": "csv"}) as mocks:
            code = main(["--dry-run", "--auto-approve"])

        assert code == 0
        mocks["export"].assert_called_once()
        assert mocks["export"].call_args.args[1] == "csv"

    def test_prints_exported_file_path(self, capsys: pytest.CaptureFixture) -> None:
        with _pipeline(env={"EXPORT_FORMAT": "csv"}) as mocks:
            code = main(["--dry-run", "--auto-approve"])

        assert code == 0
        exported_path = mocks["export"].call_args.args[2]
        assert f"Exported 1 pattern(s) to {exported_path}" in capsys.readouterr().out


class TestClearCache:
    def test_clears_cache_directory_and_prints_confirmation(
        self, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        cache_module.write("transactions", [1, 2, 3], tmp_path)

        with _pipeline(env={"CACHE_DIR": str(tmp_path)}):
            code = main(["--clear-cache", "--auto-approve"])

        assert code == 0
        assert cache_module.read("transactions", 3600, tmp_path) is None
        assert str(tmp_path) in capsys.readouterr().out


class TestBillOutcomesPrinted:
    def test_outcomes_are_printed(self, capsys: pytest.CaptureFixture) -> None:
        with _pipeline():
            code = main(["--auto-approve"])

        assert code == 0
        assert "Netflix" in capsys.readouterr().out


def test_no_network_calls_made(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: the mocked pipeline must never touch a real requests.Session."""

    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected network call during a mocked test run")

    monkeypatch.setattr("requests.sessions.Session.request", _fail)

    with _pipeline():
        code = main(["--auto-approve"])

    assert code == 0
