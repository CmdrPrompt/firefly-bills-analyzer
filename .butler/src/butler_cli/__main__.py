"""Thin argparse CLI wrapper over butler_core.tasks and butler_core.git_ops."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from butler_core.git_ops import (
    GitOpsError,
    branch_for,
    commit_for,
    merge_pr_for,
    open_pr_for,
    stage_for,
)
from butler_core.tasks import (
    DEFAULT_TASKS_DIR,
    TaskNotFoundError,
    check_criterion,
    create_task,
    list_tasks,
    read_task,
)
from butler_core.uninstall import (
    DirtyWorkingTreeError,
    InvalidCategoryError,
    apply_uninstall,
    plan_uninstall,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="butler")
    parser.add_argument("--tasks-dir", default=DEFAULT_TASKS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    task_parser = subparsers.add_parser("task")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)

    list_parser = task_subparsers.add_parser("list")
    list_parser.add_argument("--status", choices=("todo", "in-progress", "done"), default=None)

    show_parser = task_subparsers.add_parser("show")
    show_parser.add_argument("task_id")

    create_parser = task_subparsers.add_parser("create")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--description", required=True)

    check_parser = task_subparsers.add_parser("check")
    check_parser.add_argument("task_id")
    check_parser.add_argument("--criterion", type=int, required=True)

    for name in ("branch", "stage", "commit", "pr", "merge"):
        sub = task_subparsers.add_parser(name)
        sub.add_argument("task_id")

    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("--categories", required=True)
    uninstall_parser.add_argument("--project-root", default=".")
    uninstall_parser.add_argument("--dry-run", action="store_true")
    uninstall_parser.add_argument("--force", action="store_true")

    return parser


def _cmd_list(args: argparse.Namespace) -> None:
    for task in list_tasks(tasks_dir=args.tasks_dir, status=args.status):
        print(f"{task.id} [{task.status}] {task.title}")


def _cmd_show(args: argparse.Namespace) -> None:
    task = read_task(args.task_id, tasks_dir=args.tasks_dir)
    print(f"{task.id} {task.title}")
    print(f"Status: {task.status}")
    print(f"Branch: {task.branch_name}")
    print(f"Description: {task.description}")
    print("Acceptance criteria:")
    for criterion in task.acceptance_criteria:
        mark = "x" if criterion.checked else " "
        print(f"  [{mark}] {criterion.text}")
    if task.completion is not None:
        print(f"Completion date: {task.completion.date}")
        print(f"Completion summary: {task.completion.summary}")


def _cmd_create(args: argparse.Namespace) -> None:
    task = create_task(args.title, args.description, tasks_dir=args.tasks_dir)
    print(task.id)


def _cmd_check(args: argparse.Namespace) -> None:
    check_criterion(args.task_id, args.criterion - 1, tasks_dir=args.tasks_dir)


def _cmd_branch(args: argparse.Namespace) -> None:
    branch_for(read_task(args.task_id, tasks_dir=args.tasks_dir))


def _cmd_stage(args: argparse.Namespace) -> None:
    stage_for(read_task(args.task_id, tasks_dir=args.tasks_dir))


def _cmd_commit(args: argparse.Namespace) -> None:
    commit_for(read_task(args.task_id, tasks_dir=args.tasks_dir))


def _cmd_pr(args: argparse.Namespace) -> None:
    open_pr_for(read_task(args.task_id, tasks_dir=args.tasks_dir), tasks_dir=args.tasks_dir)


def _cmd_merge(args: argparse.Namespace) -> None:
    merge_pr_for(read_task(args.task_id, tasks_dir=args.tasks_dir))


def _cmd_uninstall(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root)
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if args.dry_run:
        for action in plan_uninstall(project_root, categories):
            print(f"Would {action}")
        return
    for action in apply_uninstall(project_root, categories, force=args.force):
        print(action)


_TASK_HANDLERS = {
    "list": _cmd_list,
    "show": _cmd_show,
    "create": _cmd_create,
    "check": _cmd_check,
    "branch": _cmd_branch,
    "stage": _cmd_stage,
    "commit": _cmd_commit,
    "pr": _cmd_pr,
    "merge": _cmd_merge,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        if args.command == "uninstall":
            _cmd_uninstall(args)
        else:
            _TASK_HANDLERS[args.task_command](args)
    except (
        TaskNotFoundError,
        GitOpsError,
        ValueError,
        IndexError,
        DirtyWorkingTreeError,
        InvalidCategoryError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
