"""Tests for butler_core.sync (TASK-045, REQUIREMENTS_TASK_WORKFLOW.md Requirement 3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from butler_core.sync import (
    DirtyWorkingTreeError,
    SyncResult,
    bundled_makefile_path,
    check_sync,
    sync_makefile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestBundledMakefilePath:
    def test_bundled_makefile_matches_repo_root_makefile(self) -> None:
        """Regression test: the copy shipped as package data must never drift from
        this repo's own root Makefile, which is the real source of truth vendored
        into consumer projects via `git subtree add --prefix=.butler`."""
        bundled = bundled_makefile_path().read_text()
        root = (REPO_ROOT / "Makefile").read_text()

        assert bundled == root, (
            "src/butler_core/data/Makefile has drifted from the repo root Makefile — "
            "re-copy the root Makefile into src/butler_core/data/Makefile"
        )

    def test_bundled_makefile_path_exists(self) -> None:
        assert bundled_makefile_path().is_file()


class TestCheckSync:
    def test_reports_up_to_date_when_content_matches(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text(bundled_makefile_path().read_text())

        result = check_sync(local)

        assert result.needs_update is False
        assert "up to date" in result.message

    def test_reports_difference_when_content_diverges(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = check_sync(local)

        assert result.needs_update is True
        assert "would overwrite" in result.message.lower()

    def test_message_includes_hashes_when_diverges(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = check_sync(local)

        assert result.local_hash != result.bundled_hash
        assert result.local_hash in result.message
        assert result.bundled_hash in result.message

    def test_treats_missing_local_makefile_as_needing_update(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"

        result = check_sync(local)

        assert result.needs_update is True


class TestSyncMakefileDryRun:
    @staticmethod
    def _clean(_root: Path) -> bool:
        return False

    def test_dry_run_does_not_modify_up_to_date_file(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text(bundled_makefile_path().read_text())

        result = sync_makefile(tmp_path, dry_run=True, dirty_check=self._clean)

        assert result.needs_update is False
        assert local.read_text() == bundled_makefile_path().read_text()

    def test_dry_run_does_not_modify_diverging_file(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = sync_makefile(tmp_path, dry_run=True, dirty_check=self._clean)

        assert result.needs_update is True
        assert local.read_text() == "stale content\n"

    def test_dry_run_does_not_require_clean_tree(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = sync_makefile(tmp_path, dry_run=True, dirty_check=lambda _root: True)

        assert result.needs_update is True
        assert local.read_text() == "stale content\n"


class TestSyncMakefileApply:
    @staticmethod
    def _clean(_root: Path) -> bool:
        return False

    def test_overwrites_makefile_when_content_differs(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = sync_makefile(tmp_path, dirty_check=self._clean)

        assert local.read_text() == bundled_makefile_path().read_text()
        assert result.needs_update is True
        assert "updated" in result.message.lower()

    def test_does_not_touch_makefile_when_content_matches(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text(bundled_makefile_path().read_text())
        mtime_before = local.stat().st_mtime_ns

        result = sync_makefile(tmp_path, dirty_check=self._clean)

        assert result.needs_update is False
        assert "up to date" in result.message
        assert local.stat().st_mtime_ns == mtime_before, (
            "an already up-to-date Makefile must not be rewritten"
        )

    def test_creates_local_makefile_when_absent(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()

        sync_makefile(tmp_path, dirty_check=self._clean)

        local = (tmp_path / ".butler" / "Makefile").read_text()
        assert local == bundled_makefile_path().read_text()

    def test_raises_dirty_working_tree_error_when_dirty_and_not_forced(
        self, tmp_path: Path
    ) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        with pytest.raises(DirtyWorkingTreeError):
            sync_makefile(tmp_path, dirty_check=lambda _root: True)

        assert local.read_text() == "stale content\n", (
            "nothing should be overwritten when the dirty-tree guard trips"
        )

    def test_proceeds_when_dirty_but_forced(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        sync_makefile(tmp_path, force=True, dirty_check=lambda _root: True)

        assert local.read_text() == bundled_makefile_path().read_text()

    def test_dry_run_and_force_together_still_does_not_modify_files(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")

        result = sync_makefile(tmp_path, dry_run=True, force=True, dirty_check=lambda _root: True)

        assert result.needs_update is True
        assert local.read_text() == "stale content\n"

    def test_dirty_check_receives_project_root_not_butler_dir(self, tmp_path: Path) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")
        received_roots: list[Path] = []

        def _spy(root: Path) -> bool:
            received_roots.append(root)
            return False

        sync_makefile(tmp_path, dirty_check=_spy)

        assert received_roots == [tmp_path]

    def test_default_dirty_check_uses_real_git_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        local = tmp_path / ".butler" / "Makefile"
        local.parent.mkdir(parents=True)
        local.write_text("stale content\n")
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=" M some_file.py\n"))
        monkeypatch.setattr("butler_core.sync.subprocess.run", mock_run)

        with pytest.raises(DirtyWorkingTreeError):
            sync_makefile(tmp_path)

        assert mock_run.called, "expected the default dirty-check to shell out to git status"


class TestSyncResult:
    def test_is_a_frozen_dataclass_like_value(self) -> None:
        result = SyncResult(needs_update=False, message="ok", local_hash="a", bundled_hash="a")
        assert result.needs_update is False
        assert result.message == "ok"
