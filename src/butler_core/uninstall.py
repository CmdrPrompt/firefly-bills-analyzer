"""Category-based removal of butler's footprint from an adopting project."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 -- used only to invoke the fixed `git status` CLI command
from collections.abc import Callable
from pathlib import Path

CATEGORIES = ("subtree", "makefile", "governance")

_INCLUDE_LINE = "include .butler/Makefile"

_GOVERNANCE_PATHS = (
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    ".github/agents",
    ".claude/agents",
)


class InvalidCategoryError(ValueError):
    """Raised when an unknown uninstall category is requested."""


class DirtyWorkingTreeError(RuntimeError):
    """Raised when uninstall is attempted on an unclean working tree without force=True."""


def _validate_categories(categories: list[str]) -> None:
    unknown = [c for c in categories if c not in CATEGORIES]
    if unknown:
        raise InvalidCategoryError(f"Unknown categories: {unknown}, must be one of {CATEGORIES}")


def remove_makefile_include(makefile_text: str) -> str:
    """Remove every `include .butler/Makefile` line, preserving all other content."""
    lines = makefile_text.split("\n")
    kept = [line for line in lines if line.strip() != _INCLUDE_LINE]
    return "\n".join(kept)


def _is_working_tree_dirty(project_root: Path) -> bool:
    result = subprocess.run(  # nosec B603 B607 -- fixed git CLI invocation, no shell/user input
        ["git", "status", "--porcelain"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def plan_uninstall(project_root: Path, categories: list[str]) -> list[str]:
    """Return the human-readable actions that would be taken, without touching the filesystem."""
    _validate_categories(categories)
    actions = []
    if "subtree" in categories and (project_root / ".butler").exists():
        actions.append("remove .butler/")
    if "makefile" in categories:
        makefile_path = project_root / "Makefile"
        if makefile_path.exists() and _INCLUDE_LINE in makefile_path.read_text():
            actions.append("remove 'include .butler/Makefile' line from Makefile")
    if "governance" in categories:
        for rel in _GOVERNANCE_PATHS:
            if (project_root / rel).exists():
                actions.append(f"remove {rel}")
    return actions


def apply_uninstall(
    project_root: Path,
    categories: list[str],
    force: bool = False,
    dirty_check: Callable[[Path], bool] = _is_working_tree_dirty,
) -> list[str]:
    """Remove the selected categories from `project_root`. Never touches `docs/tasks/`."""
    _validate_categories(categories)
    if not force and dirty_check(project_root):
        raise DirtyWorkingTreeError(
            "working tree has uncommitted changes. Commit/stash first, or pass --force."
        )

    actions = plan_uninstall(project_root, categories)

    if "subtree" in categories:
        butler_dir = project_root / ".butler"
        if butler_dir.exists():
            shutil.rmtree(butler_dir)

    if "makefile" in categories:
        makefile_path = project_root / "Makefile"
        if makefile_path.exists():
            makefile_path.write_text(remove_makefile_include(makefile_path.read_text()))

    if "governance" in categories:
        for rel in _GOVERNANCE_PATHS:
            path = project_root / rel
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    return actions
