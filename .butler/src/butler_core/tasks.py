"""Task file data model and parse/list/create/update operations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TASKS_DIR = "docs/tasks"
VALID_STATUSES = ("todo", "in-progress", "done")


class TaskNotFoundError(FileNotFoundError):
    """Raised when no task file matches the requested task id."""


@dataclass
class AcceptanceCriterion:
    text: str
    checked: bool


@dataclass
class Completion:
    date: str = ""
    summary: str = ""
    files_changed: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str
    title: str
    status: str
    description: str
    branch_name: str
    switch_create_cmd: str
    stage_cmd: str
    commit_message: str
    acceptance_criteria: list[AcceptanceCriterion]
    completion: Completion | None = None


def _find_task_file(task_id: str, tasks_dir: str) -> Path:
    matches = sorted(Path(tasks_dir).glob(f"{task_id}*.md"))
    if not matches:
        raise TaskNotFoundError(f"No task file found matching '{task_id}' in {tasks_dir}")
    return matches[0]


def _section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_backtick(label: str, text: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}:\*\*.*?`([^`]*)`", text, re.MULTILINE)
    return match.group(1) if match else ""


def _parse_acceptance_criteria(criteria_section: str) -> list[AcceptanceCriterion]:
    pattern = r"^- \[( |x)\] (.+(?:\n(?![-\s]*\[|\s*$).*)*)"
    criteria = []
    for match in re.finditer(pattern, criteria_section, re.MULTILINE):
        raw_text = " ".join(line.strip() for line in match.group(2).split("\n"))
        criteria.append(AcceptanceCriterion(text=raw_text, checked=match.group(1) == "x"))
    return criteria


def _parse_completion(completion_section: str) -> Completion | None:
    date_match = re.search(r"^\*\*Date:\*\*[ \t]*(.*)", completion_section, re.MULTILINE)
    if not date_match or not date_match.group(1).strip():
        return None
    summary_match = re.search(r"^\*\*Summary:\*\*[ \t]*(.*)", completion_section, re.MULTILINE)
    files_match = re.search(
        r"^\*\*Files changed:\*\*(.*?)(?=^\*\*Branch:\*\*|\Z)",
        completion_section,
        re.MULTILINE | re.DOTALL,
    )
    files_changed = re.findall(r"`([^`]+)`", files_match.group(1)) if files_match else []
    return Completion(
        date=date_match.group(1).strip(),
        summary=summary_match.group(1).strip() if summary_match else "",
        files_changed=files_changed,
    )


def parse_task(text: str) -> Task:
    title_match = re.match(r"^#\s+(TASK-\d+)\s+(.*)", text)
    if not title_match:
        raise ValueError("Task file missing '# TASK-NNN Title' header")
    task_id, title = title_match.group(1), title_match.group(2).strip()

    status_match = re.search(r"^## Status\s*\n+(\S+)", text, re.MULTILINE)
    status = status_match.group(1) if status_match else ""

    description = _section(text, "Description")

    branch_section = _section(text, "Branch")
    branch_name = _extract_backtick("Branch name", branch_section)
    switch_create_cmd = _extract_backtick("Switch/create", branch_section)

    criteria_section = _section(text, "Acceptance criteria")
    acceptance_criteria = _parse_acceptance_criteria(criteria_section)

    completion_section = _section(text, "Completion")
    stage_cmd = _extract_backtick("Stage", completion_section)
    commit_match = re.search(
        r'^\*\*Commit:\*\*.*?`git commit -m "([^"]*)"`', completion_section, re.MULTILINE
    )
    commit_message = commit_match.group(1) if commit_match else ""
    completion = _parse_completion(completion_section)

    return Task(
        id=task_id,
        title=title,
        status=status,
        description=description,
        branch_name=branch_name,
        switch_create_cmd=switch_create_cmd,
        stage_cmd=stage_cmd,
        commit_message=commit_message,
        acceptance_criteria=acceptance_criteria,
        completion=completion,
    )


def render_task(task: Task) -> str:
    lines = [
        f"# {task.id} {task.title}",
        "",
        "## Status",
        "",
        task.status,
        "",
        "## Description",
        "",
        task.description,
        "",
        "## Branch",
        "",
        f"**Branch name:** `{task.branch_name}`",
        f"**Switch/create:** `{task.switch_create_cmd}`",
        f"**Make target:** `make branch-task f={task.id}`",
        "",
        "## Acceptance criteria",
        "",
    ]
    for criterion in task.acceptance_criteria:
        mark = "x" if criterion.checked else " "
        lines.append(f"- [{mark}] {criterion.text}")
    lines += ["", "## Completion", ""]
    completion = task.completion or Completion()
    lines.append(f"**Date:** {completion.date}")
    lines.append(f"**Summary:** {completion.summary}")
    lines.append("**Files changed:**")
    lines.append("")
    for changed_file in completion.files_changed:
        lines.append(f"- `{changed_file}`")
    lines.append("")
    lines.append(f"**Branch:** `git checkout {task.branch_name}`")
    lines.append(f"**Stage:** `{task.stage_cmd}`")
    lines.append(f'**Commit:** `git commit -m "{task.commit_message}"`')
    return "\n".join(lines) + "\n"


def read_task(task_id: str, tasks_dir: str = DEFAULT_TASKS_DIR) -> Task:
    path = _find_task_file(task_id, tasks_dir)
    return parse_task(path.read_text())


def list_tasks(tasks_dir: str = DEFAULT_TASKS_DIR, status: str | None = None) -> list[Task]:
    tasks = []
    for path in sorted(Path(tasks_dir).glob("TASK-*.md")):
        task = parse_task(path.read_text())
        if status is None or task.status == status:
            tasks.append(task)
    return tasks


def _next_task_number(tasks_dir: str) -> int:
    numbers = []
    for path in Path(tasks_dir).glob("TASK-*.md"):
        match = re.match(r"TASK-(\d+)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def create_task(title: str, description: str, tasks_dir: str = DEFAULT_TASKS_DIR) -> Task:
    number = _next_task_number(tasks_dir)
    task_id = f"TASK-{number:03d}"
    slug = _slugify(title)
    branch_name = f"task/{number:03d}-{slug}"
    filename = f"{task_id}-{slug}.md"
    path = Path(tasks_dir) / filename

    task = Task(
        id=task_id,
        title=title,
        status="todo",
        description=description,
        branch_name=branch_name,
        switch_create_cmd=f"git checkout -b {branch_name}",
        stage_cmd=f"git add {path} CHANGELOG.md",
        commit_message=title,
        acceptance_criteria=[],
        completion=None,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_task(task))
    return task


def check_criterion(
    task_id: str, index: int, tasks_dir: str = DEFAULT_TASKS_DIR, checked: bool = True
) -> None:
    path = _find_task_file(task_id, tasks_dir)
    text = path.read_text()
    criteria_matches = list(re.finditer(r"^- \[( |x)\] .+$", text, re.MULTILINE))
    if index >= len(criteria_matches):
        raise IndexError(f"No acceptance criterion at index {index} in {path}")
    target = criteria_matches[index]
    mark = "x" if checked else " "
    new_line = re.sub(r"^- \[( |x)\]", f"- [{mark}]", target.group(0))
    text = text[: target.start()] + new_line + text[target.end() :]
    path.write_text(text)


def set_status(task_id: str, status: str, tasks_dir: str = DEFAULT_TASKS_DIR) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}', must be one of {VALID_STATUSES}")
    path = _find_task_file(task_id, tasks_dir)
    text = path.read_text()
    match = re.search(r"(^## Status\s*\n+)(\S+)", text, re.MULTILINE)
    if not match:
        raise ValueError(f"No '## Status' section found in {path}")
    text = text[: match.start(2)] + status + text[match.end(2) :]
    path.write_text(text)
