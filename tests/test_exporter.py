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
from firefly_bills_analyzer.exporter import export

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
)


def _pattern(
    name: str = "Netflix",
    category_name: str | None = "Subscriptions",
    source_account_name: str | None = None,
    source_account_varies: bool = False,
) -> RecurringPattern:
    return RecurringPattern(
        destination_name=name,
        category_name=category_name,
        occurrences=4,
        amount_min=9.0,
        amount_max=11.0,
        amount_mean=10.0,
        median_interval_days=30.0,
        frequency="monthly",
        confidence=0.9,
        source_account_name=source_account_name,
        source_account_varies=source_account_varies,
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
