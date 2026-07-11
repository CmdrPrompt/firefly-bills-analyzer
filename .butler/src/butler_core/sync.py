"""Refresh a consumer project's vendored `.butler/Makefile`.

See REQUIREMENTS_TASK_WORKFLOW.md Requirement 3.
"""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404 -- used only to invoke the fixed `git status` CLI command
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from butler_core.uninstall import DirtyWorkingTreeError

__all__ = [
    "DirtyWorkingTreeError",
    "SyncResult",
    "bundled_makefile_path",
    "check_sync",
    "sync_makefile",
]


@dataclass(frozen=True)
class SyncResult:
    needs_update: bool
    message: str
    local_hash: str
    bundled_hash: str


def bundled_makefile_path() -> Path:
    """Return the path to the `.butler/Makefile` bundled with the installed butler_core package."""
    return resources.files("butler_core").joinpath("data", "Makefile")  # type: ignore[return-value]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _is_working_tree_dirty(project_root: Path) -> bool:
    result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation, no shell/user input
        ["git", "status", "--porcelain"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def check_sync(local_makefile: Path) -> SyncResult:
    """Compare `local_makefile` against the bundled version, without touching the filesystem."""
    bundled_text = bundled_makefile_path().read_text()
    bundled_hash = _hash(bundled_text)
    local_text = local_makefile.read_text() if local_makefile.exists() else ""
    local_hash = _hash(local_text)

    if local_hash == bundled_hash:
        return SyncResult(
            needs_update=False,
            message=".butler/Makefile is already up to date; nothing to do",
            local_hash=local_hash,
            bundled_hash=bundled_hash,
        )
    return SyncResult(
        needs_update=True,
        message=(
            f"would overwrite .butler/Makefile "
            f"(local hash {local_hash} != bundled hash {bundled_hash})"
        ),
        local_hash=local_hash,
        bundled_hash=bundled_hash,
    )


def sync_makefile(
    project_root: Path,
    dry_run: bool = False,
    force: bool = False,
    dirty_check: Callable[[Path], bool] = _is_working_tree_dirty,
) -> SyncResult:
    """Overwrite `project_root/.butler/Makefile` with the bundled version if content differs."""
    local_makefile = project_root / ".butler" / "Makefile"
    result = check_sync(local_makefile)

    if dry_run or not result.needs_update:
        return result

    if not force and dirty_check(project_root):
        raise DirtyWorkingTreeError(
            "working tree has uncommitted changes. Commit/stash first, or pass --force."
        )

    local_makefile.parent.mkdir(parents=True, exist_ok=True)
    local_makefile.write_text(bundled_makefile_path().read_text())
    return SyncResult(
        needs_update=True,
        message="Updated .butler/Makefile",
        local_hash=result.local_hash,
        bundled_hash=result.bundled_hash,
    )
