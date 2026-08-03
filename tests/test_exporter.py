"""Tests for exporter (UC5, FR-08): CSV/JSON export of analysis results."""

from __future__ import annotations

import csv
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.exporter import export, export_income
from firefly_bills_analyzer.income import IncomeAccountIssue, IncomeCandidateSummary, IncomeSource

pattern_strategy = st.builds(
    RecurringPattern,
    destination_name=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
    category_name=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    occurrences=st.integers(min_value=2, max_value=50),
    amount_min=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    amount_max=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    amount_mean=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    median_interval_days=st.floats(
        min_value=0, max_value=400, allow_nan=False, allow_infinity=False
    ),
    frequency=st.sampled_from(["monthly", "quarterly", "half-yearly", "yearly", "irregular"]),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    source_account_name=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    source_account_varies=st.booleans(),
    monthly_equivalent=st.one_of(
        st.none(),
        st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    ),
)


def _pattern(
    name: str = "Netflix",
    category_name: str | None = "Subscriptions",
    source_account_name: str | None = None,
    source_account_varies: bool = False,
    frequency: str = "monthly",
    monthly_equivalent: float | None = None,
) -> RecurringPattern:
    return RecurringPattern(
        destination_name=name,
        category_name=category_name,
        occurrences=4,
        amount_min=9.0,
        amount_max=11.0,
        amount_mean=10.0,
        median_interval_days=30.0,
        frequency=frequency,
        confidence=0.9,
        source_account_name=source_account_name,
        source_account_varies=source_account_varies,
        monthly_equivalent=monthly_equivalent,
    )


class TestNoneFormat:
    def test_is_a_noop(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export([_pattern()], "none", path)
        assert not path.exists()


class TestCsv:
    def test_writes_header_and_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        patterns = [_pattern("Netflix", "Subscriptions"), _pattern("Spotify", None)]
        export(patterns, "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 2
        assert rows[0]["destination_name"] == "Netflix"
        assert rows[0]["category_name"] == "Subscriptions"
        assert rows[1]["destination_name"] == "Spotify"
        assert rows[1]["category_name"] == ""

    def test_empty_list_writes_header_only(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export([], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows == []

    def test_includes_source_account_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        patterns = [
            _pattern("Netflix", source_account_name="Checking", source_account_varies=False),
            _pattern("Spotify", source_account_name="Checking", source_account_varies=True),
        ]
        export(patterns, "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames is not None
            assert "source_account_name" in reader.fieldnames
            assert "source_account_varies" in reader.fieldnames
            rows = list(reader)

        assert rows[0]["source_account_name"] == "Checking"
        assert rows[0]["source_account_varies"] == "False"
        assert rows[1]["source_account_varies"] == "True"

    def test_monthly_equivalent_column_serializes_value_and_none(self, tmp_path: Path) -> None:
        """FR-37: a `None` monthly_equivalent serializes as an empty CSV cell,
        and a computed value serializes as its plain value."""
        path = tmp_path / "out.csv"
        patterns = [
            _pattern("Water Bill", frequency="quarterly", monthly_equivalent=30.0),
            _pattern("Corner Shop", frequency="irregular", monthly_equivalent=None),
        ]
        export(patterns, "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames is not None
            assert "monthly_equivalent" in reader.fieldnames
            rows = list(reader)

        by_name = {row["destination_name"]: row for row in rows}
        assert by_name["Water Bill"]["monthly_equivalent"] == "30.0"
        assert by_name["Corner Shop"]["monthly_equivalent"] == ""


class TestJson:
    def test_writes_list_of_objects(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        patterns = [_pattern("Netflix", "Subscriptions")]
        export(patterns, "json", path)

        data = json.loads(path.read_text(encoding="utf-8"))

        assert data == [asdict(patterns[0])]

    def test_empty_list_writes_empty_array(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export([], "json", path)

        assert json.loads(path.read_text(encoding="utf-8")) == []

    def test_includes_source_account_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        patterns = [
            _pattern("Netflix", source_account_name="Checking", source_account_varies=True),
        ]
        export(patterns, "json", path)

        data = json.loads(path.read_text(encoding="utf-8"))

        assert data[0]["source_account_name"] == "Checking"
        assert data[0]["source_account_varies"] is True

    def test_monthly_equivalent_key_serializes_value_and_null(self, tmp_path: Path) -> None:
        """FR-37: a `None` monthly_equivalent serializes as JSON `null`, and a
        computed value serializes as its numeric value."""
        path = tmp_path / "out.json"
        patterns = [
            _pattern("Water Bill", frequency="quarterly", monthly_equivalent=30.0),
            _pattern("Corner Shop", frequency="irregular", monthly_equivalent=None),
        ]
        export(patterns, "json", path)

        data = json.loads(path.read_text(encoding="utf-8"))

        by_name = {obj["destination_name"]: obj for obj in data}
        assert by_name["Water Bill"]["monthly_equivalent"] == 30.0
        assert by_name["Corner Shop"]["monthly_equivalent"] is None


class TestUnsupportedFormat:
    def test_raises_value_error(self, tmp_path: Path) -> None:
        import pytest

        path = tmp_path / "out.xml"
        with pytest.raises(ValueError, match="xml"):
            export([_pattern()], "xml", path)


@given(st.lists(pattern_strategy, min_size=0, max_size=10))
def test_csv_round_trip_preserves_destination_names(patterns: list[RecurringPattern]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.csv"
        export(patterns, "csv", path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert [r["destination_name"] for r in rows] == [p.destination_name for p in patterns]


@given(st.lists(pattern_strategy, min_size=0, max_size=10))
def test_json_round_trip_preserves_all_fields(patterns: list[RecurringPattern]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.json"
        export(patterns, "json", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == [asdict(p) for p in patterns]


# ---------------------------------------------------------------------------
# TASK-027: income export (FR-45a, FR-45b, FR-45c). `export_income` writes
# income sources and reported-issue accounts (from TASK-026's `detect_income`)
# to a file separate from the pattern export.
# ---------------------------------------------------------------------------

income_source_strategy = st.builds(
    IncomeSource,
    income_account=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
    payer=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
    observed_net_income=st.floats(
        min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False
    ),
    observed_date=st.just("2026-01-01"),
    occurrences=st.integers(min_value=1, max_value=50),
    median_interval_days=st.floats(
        min_value=0, max_value=400, allow_nan=False, allow_infinity=False
    ),
    amount_min=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    amount_max=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    amount_mean=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
    outlier_count=st.integers(min_value=0, max_value=50),
)


def _income_source(
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


def _ambiguous_issue(income_account: str = "Shared Checking") -> IncomeAccountIssue:
    return IncomeAccountIssue(
        income_account=income_account,
        reason="ambiguous",
        candidates=[
            IncomeCandidateSummary(payer="Employer A", occurrences=4, frequency="monthly"),
            IncomeCandidateSummary(payer="Employer B", occurrences=4, frequency="monthly"),
        ],
    )


def _no_qualifying_issue(income_account: str = "Quarterly Account") -> IncomeAccountIssue:
    return IncomeAccountIssue(
        income_account=income_account,
        reason="no-qualifying-candidate",
        candidates=[
            IncomeCandidateSummary(payer="Pension Fund", occurrences=4, frequency="quarterly"),
        ],
    )


class TestIncomeExportFieldDerivation:
    """FR-45b: the field list is derived from `IncomeSource`'s own fields
    (matching how `_FIELDNAMES` is built for the pattern export), plus the
    `status` column FR-45c adds, rather than a hard-coded list."""

    def test_csv_header_is_dataclass_fields_plus_status(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([_income_source()], [], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        from dataclasses import fields as dataclass_fields

        expected = [f.name for f in dataclass_fields(IncomeSource)] + ["status"]
        assert fieldnames == expected

    def test_json_object_keys_are_dataclass_fields_plus_status(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export_income([_income_source()], [], "json", path)

        data = json.loads(path.read_text(encoding="utf-8"))

        from dataclasses import fields as dataclass_fields

        expected = {f.name for f in dataclass_fields(IncomeSource)} | {"status"}
        assert set(data[0].keys()) == expected


class TestIncomeSourceRows:
    def test_source_row_has_status_ok(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([_income_source()], [], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        assert rows[0]["status"] == "ok"

    def test_source_row_carries_observed_net_income(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([_income_source()], [], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["observed_net_income"] == "2500.0"


class TestIncomeIssueRows:
    """FR-45c: accounts reported under FR-42b/FR-42c appear as rows with an
    empty payer and observed net income, and a status explaining why."""

    def test_ambiguous_issue_row_has_empty_payer(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([], [_ambiguous_issue()], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        assert rows[0]["payer"] == ""

    def test_ambiguous_issue_row_has_empty_observed_net_income(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([], [_ambiguous_issue()], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["observed_net_income"] == ""

    def test_ambiguous_issue_row_status_names_both_candidate_payers(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([], [_ambiguous_issue()], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        row_text = " ".join(rows[0].values())
        assert "ambiguous" in rows[0]["status"]
        assert "Employer A" in row_text
        assert "Employer B" in row_text

    def test_no_qualifying_candidate_row_status(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([], [_no_qualifying_issue()], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["status"] == "no-qualifying-candidate" or rows[0]["status"].startswith(
            "no-qualifying-candidate"
        )

    def test_sources_and_issues_both_appear_in_one_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([_income_source()], [_ambiguous_issue()], "csv", path)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 2
        statuses = {row["status"] for row in rows}
        assert "ok" in statuses


class TestIncomeExportNoneFormat:
    def test_is_a_noop(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_income([_income_source()], [], "none", path)
        assert not path.exists()


@given(st.lists(income_source_strategy, min_size=0, max_size=10))
def test_income_csv_round_trip_preserves_income_accounts(sources: list[IncomeSource]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.csv"
        export_income(sources, [], "csv", path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert [r["income_account"] for r in rows] == [s.income_account for s in sources]
        assert all(r["status"] == "ok" for r in rows)


@given(st.lists(income_source_strategy, min_size=0, max_size=10))
def test_income_json_round_trip_preserves_income_accounts(sources: list[IncomeSource]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.json"
        export_income(sources, [], "json", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert [obj["income_account"] for obj in data] == [s.income_account for s in sources]
