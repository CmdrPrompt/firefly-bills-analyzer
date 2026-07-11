"""Tests for cache (UC7): generic TTL-aware JSON file cache."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from firefly_bills_analyzer import cache


class TestRead:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert cache.read("transactions", 3600, tmp_path) is None

    def test_fresh_entry_returns_data(self, tmp_path: Path) -> None:
        cache.write("transactions", {"a": 1}, tmp_path)
        assert cache.read("transactions", 3600, tmp_path) == {"a": 1}

    def test_stale_entry_returns_none(self, tmp_path: Path) -> None:
        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0):
            cache.write("transactions", {"a": 1}, tmp_path)

        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0 + 3601):
            assert cache.read("transactions", 3600, tmp_path) is None

    def test_entry_at_exact_ttl_boundary_is_still_fresh(self, tmp_path: Path) -> None:
        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0):
            cache.write("transactions", {"a": 1}, tmp_path)

        with patch("firefly_bills_analyzer.cache.time.time", return_value=1_000_000.0 + 3600):
            assert cache.read("transactions", 3600, tmp_path) == {"a": 1}

    def test_corrupt_file_returns_none(self, tmp_path: Path) -> None:
        cache_dir = tmp_path
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "transactions.json").write_text("not json")

        assert cache.read("transactions", 3600, tmp_path) is None


class TestWrite:
    def test_creates_cache_dir_if_missing(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "nested" / "cache"
        assert not cache_dir.exists()

        cache.write("transactions", [1, 2, 3], cache_dir)

        assert cache_dir.exists()
        assert cache.read("transactions", 3600, cache_dir) == [1, 2, 3]

    def test_write_then_read_round_trip(self, tmp_path: Path) -> None:
        data = [{"date": "2026-01-01", "amount": "9.99"}]
        cache.write("bills", data, tmp_path)
        assert cache.read("bills", 3600, tmp_path) == data

    def test_stores_a_timestamp(self, tmp_path: Path) -> None:
        before = time.time()
        cache.write("transactions", {}, tmp_path)
        after = time.time()

        payload = json.loads((tmp_path / "transactions.json").read_text())
        assert before <= payload["timestamp"] <= after


class TestInvalidate:
    def test_deletes_existing_entry(self, tmp_path: Path) -> None:
        cache.write("bills", [1], tmp_path)
        cache.invalidate("bills", tmp_path)
        assert cache.read("bills", 3600, tmp_path) is None

    def test_missing_entry_is_a_noop(self, tmp_path: Path) -> None:
        cache.invalidate("bills", tmp_path)  # must not raise


class TestClearAll:
    def test_deletes_all_cache_files(self, tmp_path: Path) -> None:
        cache.write("transactions", [1], tmp_path)
        cache.write("bills", [2], tmp_path)

        cache.clear_all(tmp_path)

        assert cache.read("transactions", 3600, tmp_path) is None
        assert cache.read("bills", 3600, tmp_path) is None

    def test_missing_cache_dir_is_a_noop(self, tmp_path: Path) -> None:
        cache.clear_all(tmp_path / "does-not-exist")  # must not raise

    def test_leaves_other_files_in_cache_dir_untouched(self, tmp_path: Path) -> None:
        cache.write("transactions", [1], tmp_path)
        other_file = tmp_path / "notes.txt"
        other_file.write_text("keep me")

        cache.clear_all(tmp_path)

        assert other_file.exists()
