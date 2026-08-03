"""Tests for exporter (UC5, FR-08): CSV/JSON export of analysis results."""

from __future__ import annotations

import csv
import json
import math
import tempfile
from dataclasses import asdict
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.exporter import export, export_household_spend, export_income
from firefly_bills_analyzer.household_spend import (
    HouseholdSpendRecord,
    HouseholdSpendResult,
    OneOffPurchase,
)
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


class TestIncomeUnsupportedFormat:
    def test_raises_value_error(self, tmp_path: Path) -> None:
        import pytest

        path = tmp_path / "out.xml"
        with pytest.raises(ValueError, match="xml"):
            export_income([_income_source()], [], "xml", path)


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


# ---------------------------------------------------------------------------
# TASK-029: household spend export (FR-51a, FR-51b, FR-51c, FR-48f, FR-50).
# `export_household_spend` writes household spend records, one-off purchases
# (TASK-028's `aggregate_household_spend` output), unmatched categories, and
# tag correction counts to a file separate from the pattern and income
# exports.
# ---------------------------------------------------------------------------

household_spend_record_strategy = st.builds(
    HouseholdSpendRecord,
    source_account=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    category=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    month_count=st.integers(min_value=0, max_value=24),
    monthly_totals=st.lists(
        st.floats(min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False),
        min_size=0,
        max_size=24,
    ),
    median=st.one_of(
        st.none(), st.floats(min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False)
    ),
    mean=st.one_of(
        st.none(), st.floats(min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False)
    ),
    minimum=st.one_of(
        st.none(), st.floats(min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False)
    ),
    maximum=st.one_of(
        st.none(), st.floats(min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False)
    ),
)

one_off_purchase_strategy = st.builds(
    OneOffPurchase,
    date=st.just("2026-01-15"),
    amount=st.floats(min_value=0.01, max_value=100_000, allow_nan=False, allow_infinity=False),
    payee=st.one_of(st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")),
    category=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    source_account=st.one_of(
        st.none(), st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
    ),
    threshold=st.floats(min_value=0.0, max_value=100_000, allow_nan=False, allow_infinity=False),
)


def _household_spend_record(
    source_account: str | None = "Checking",
    category: str | None = "Groceries",
    month_count: int = 6,
    median: float | None = 250.0,
) -> HouseholdSpendRecord:
    return HouseholdSpendRecord(
        source_account=source_account,
        category=category,
        month_count=month_count,
        monthly_totals=[250.0] * month_count,
        median=median,
        mean=250.0,
        minimum=200.0,
        maximum=300.0,
    )


def _one_off_purchase(
    date: str = "2026-01-15",
    amount: float = 1200.0,
    payee: str | None = "Furniture Shop",
    category: str | None = "Household",
    source_account: str | None = "Checking",
    threshold: float = 2000.0,
) -> OneOffPurchase:
    return OneOffPurchase(
        date=date,
        amount=amount,
        payee=payee,
        category=category,
        source_account=source_account,
        threshold=threshold,
    )


def _household_spend_result(
    records: list[HouseholdSpendRecord] | None = None,
    one_off_purchases: list[OneOffPurchase] | None = None,
    unmatched_categories: list[str] | None = None,
    unmatched_threshold_overrides: list[str] | None = None,
    include_tag_count: int = 0,
    exclude_tag_count: int = 0,
) -> HouseholdSpendResult:
    return HouseholdSpendResult(
        records=records or [],
        one_off_purchases=one_off_purchases or [],
        unmatched_categories=unmatched_categories or [],
        unmatched_threshold_overrides=unmatched_threshold_overrides or [],
        include_tag_count=include_tag_count,
        exclude_tag_count=exclude_tag_count,
    )


class TestHouseholdSpendNoneFormat:
    def test_is_a_noop(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        result = _household_spend_result(records=[_household_spend_record()])
        export_household_spend(result, "none", path)
        assert not path.exists()


class TestHouseholdSpendUnsupportedFormat:
    def test_raises_value_error(self, tmp_path: Path) -> None:
        import pytest

        path = tmp_path / "out.xml"
        with pytest.raises(ValueError, match="xml"):
            export_household_spend(_household_spend_result(), "xml", path)


class TestHouseholdSpendRecordRows:
    def test_record_row_has_record_type_household_spend(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(records=[_household_spend_record()]), "csv", path
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        household_rows = [r for r in rows if r["record_type"] == "household-spend"]
        assert len(household_rows) == 1
        assert household_rows[0]["source_account_name"] == "Checking"
        assert household_rows[0]["category_name"] == "Groceries"
        assert household_rows[0]["median_monthly"] == "250.0"
        assert household_rows[0]["complete_months"] == "6"

    def test_median_is_empty_for_a_record_with_too_few_months(self, tmp_path: Path) -> None:
        """FR-49e/AC-6: fewer than the minimum complete months yields a
        record with its month count and an empty median."""
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(records=[_household_spend_record(month_count=2, median=None)]),
            "csv",
            path,
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        household_rows = [r for r in rows if r["record_type"] == "household-spend"]
        assert household_rows[0]["median_monthly"] == ""
        assert household_rows[0]["complete_months"] == "2"

    def test_median_is_null_in_json_for_a_record_with_too_few_months(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export_household_spend(
            _household_spend_result(records=[_household_spend_record(month_count=2, median=None)]),
            "json",
            path,
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        household_rows = [r for r in data if r["record_type"] == "household-spend"]
        assert household_rows[0]["median_monthly"] is None


class TestOneOffPurchaseRows:
    def test_one_off_row_has_record_type_one_off(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(one_off_purchases=[_one_off_purchase()]), "csv", path
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        one_off_rows = [r for r in rows if r["record_type"] == "one-off"]
        assert len(one_off_rows) == 1
        assert one_off_rows[0]["date"] == "2026-01-15"
        assert one_off_rows[0]["amount"] == "1200.0"
        assert one_off_rows[0]["destination_name"] == "Furniture Shop"
        assert one_off_rows[0]["category_name"] == "Household"
        assert one_off_rows[0]["source_account_name"] == "Checking"

    def test_one_off_row_carries_the_threshold_that_excluded_it(self, tmp_path: Path) -> None:
        """FR-47f/FR-48c/FR-51c: the per-category (or default) threshold that
        excluded the purchase is exported alongside it."""
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(one_off_purchases=[_one_off_purchase(threshold=6000.0)]),
            "csv",
            path,
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        one_off_rows = [r for r in rows if r["record_type"] == "one-off"]
        assert one_off_rows[0]["threshold"] == "6000.0"

    def test_one_off_row_carries_the_threshold_in_json(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export_household_spend(
            _household_spend_result(one_off_purchases=[_one_off_purchase(threshold=6000.0)]),
            "json",
            path,
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        one_off_rows = [r for r in data if r["record_type"] == "one-off"]
        assert one_off_rows[0]["threshold"] == 6000.0

    def test_household_spend_and_one_off_rows_are_distinguishable(self, tmp_path: Path) -> None:
        """FR-51c: distinguishable via `record_type`, not via which fields
        are empty."""
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(
                records=[_household_spend_record()], one_off_purchases=[_one_off_purchase()]
            ),
            "csv",
            path,
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        record_types = {row["record_type"] for row in rows}
        assert "household-spend" in record_types
        assert "one-off" in record_types


class TestUnmatchedCategoriesAndTagCounts:
    def test_unmatched_category_appears_as_its_own_row(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(unmatched_categories=["Home Improvement"]), "csv", path
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        unmatched_rows = [r for r in rows if r["record_type"] == "unmatched-category"]
        assert len(unmatched_rows) == 1
        assert unmatched_rows[0]["category_name"] == "Home Improvement"

    def test_unmatched_category_appears_as_its_own_row_in_json(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export_household_spend(
            _household_spend_result(unmatched_categories=["Home Improvement"]), "json", path
        )

        data = json.loads(path.read_text(encoding="utf-8"))

        unmatched_rows = [r for r in data if r["record_type"] == "unmatched-category"]
        assert len(unmatched_rows) == 1
        assert unmatched_rows[0]["category_name"] == "Home Improvement"

    def test_unmatched_threshold_override_appears_as_its_own_row(self, tmp_path: Path) -> None:
        """FR-47f: reported on the same terms FR-50 reports an unmatched
        household spend category — its own `record_type`, distinct from
        `unmatched-category`."""
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(unmatched_threshold_overrides=["Nonexistent Category"]),
            "csv",
            path,
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        unmatched_rows = [r for r in rows if r["record_type"] == "unmatched-threshold-override"]
        assert len(unmatched_rows) == 1
        assert unmatched_rows[0]["category_name"] == "Nonexistent Category"

    def test_unmatched_threshold_override_appears_as_its_own_row_in_json(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "out.json"
        export_household_spend(
            _household_spend_result(unmatched_threshold_overrides=["Nonexistent Category"]),
            "json",
            path,
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        unmatched_rows = [r for r in data if r["record_type"] == "unmatched-threshold-override"]
        assert len(unmatched_rows) == 1
        assert unmatched_rows[0]["category_name"] == "Nonexistent Category"

    def test_tag_counts_appear_in_a_row(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(include_tag_count=2, exclude_tag_count=1), "csv", path
        )

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        tag_rows = [r for r in rows if r["record_type"] == "tag-counts"]
        assert len(tag_rows) == 1
        assert tag_rows[0]["include_tag_count"] == "2"
        assert tag_rows[0]["exclude_tag_count"] == "1"

    def test_tag_counts_appear_in_a_row_in_json(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        export_household_spend(
            _household_spend_result(include_tag_count=2, exclude_tag_count=1), "json", path
        )

        data = json.loads(path.read_text(encoding="utf-8"))

        tag_rows = [r for r in data if r["record_type"] == "tag-counts"]
        assert len(tag_rows) == 1
        assert tag_rows[0]["include_tag_count"] == 2
        assert tag_rows[0]["exclude_tag_count"] == 1


class TestHouseholdSpendFieldDerivation:
    """The field list is derived from `HouseholdSpendRecord` and
    `OneOffPurchase`'s own fields (excluding the internal `monthly_totals`),
    matching how `_FIELDNAMES`/`_INCOME_FIELDNAMES` are derived, so a later
    field addition flows through without an exporter change."""

    def test_csv_header_excludes_internal_monthly_totals(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        export_household_spend(
            _household_spend_result(records=[_household_spend_record()]), "csv", path
        )

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        assert fieldnames is not None
        assert "monthly_totals" not in fieldnames
        assert "record_type" in fieldnames
        for name in (
            "source_account_name",
            "category_name",
            "median_monthly",
            "mean_monthly",
            "min_monthly",
            "max_monthly",
            "complete_months",
            "date",
            "amount",
            "destination_name",
            "threshold",
            "include_tag_count",
            "exclude_tag_count",
        ):
            assert name in fieldnames


@given(st.lists(household_spend_record_strategy, min_size=0, max_size=10))
def test_household_spend_csv_round_trip_preserves_records(
    records: list[HouseholdSpendRecord],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.csv"
        export_household_spend(_household_spend_result(records=records), "csv", path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        household_rows = [r for r in rows if r["record_type"] == "household-spend"]
        assert len(household_rows) == len(records)
        for row, record in zip(household_rows, records, strict=True):
            expected_category = record.category if record.category is not None else ""
            assert row["category_name"] == expected_category
            assert row["complete_months"] == str(record.month_count)
            for csv_field, value in (
                ("median_monthly", record.median),
                ("mean_monthly", record.mean),
                ("min_monthly", record.minimum),
                ("max_monthly", record.maximum),
            ):
                if value is None:
                    assert row[csv_field] == ""
                else:
                    assert math.isclose(float(row[csv_field]), value, rel_tol=1e-9, abs_tol=1e-9)


@given(st.lists(household_spend_record_strategy, min_size=0, max_size=10))
def test_household_spend_json_round_trip_preserves_records(
    records: list[HouseholdSpendRecord],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.json"
        export_household_spend(_household_spend_result(records=records), "json", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        household_rows = [r for r in data if r["record_type"] == "household-spend"]
        assert len(household_rows) == len(records)
        for row, record in zip(household_rows, records, strict=True):
            assert row["category_name"] == record.category
            assert row["median_monthly"] == record.median


@given(st.lists(one_off_purchase_strategy, min_size=0, max_size=10))
def test_household_spend_one_off_csv_round_trip_preserves_purchases(
    purchases: list[OneOffPurchase],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.csv"
        export_household_spend(_household_spend_result(one_off_purchases=purchases), "csv", path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        one_off_rows = [r for r in rows if r["record_type"] == "one-off"]
        assert len(one_off_rows) == len(purchases)
        for row, purchase in zip(one_off_rows, purchases, strict=True):
            expected_payee = purchase.payee if purchase.payee is not None else ""
            expected_category = purchase.category if purchase.category is not None else ""
            expected_source_account = (
                purchase.source_account if purchase.source_account is not None else ""
            )
            assert row["destination_name"] == expected_payee
            assert row["category_name"] == expected_category
            assert row["source_account_name"] == expected_source_account
            assert row["date"] == purchase.date
            assert math.isclose(float(row["amount"]), purchase.amount, rel_tol=1e-9, abs_tol=1e-9)
            assert math.isclose(
                float(row["threshold"]), purchase.threshold, rel_tol=1e-9, abs_tol=1e-9
            )
