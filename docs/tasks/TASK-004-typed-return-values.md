# TASK-004 Typed return values with TypedDict

## Status
done

## Description

Introduce `TypedDict` types for all structured data returned by `FireflyClient`
so that IDEs (VS Code / Pylance) can provide accurate code completion and
`mypy --strict` can verify consumer code end-to-end.

All types are defined in a new `firefly_python_api._types` module and re-exported
from `firefly_python_api` alongside the existing public symbols.

## Branch
**Branch name:** `task/004-typed-return-values`
**Switch/create:** `git checkout -b task/004-typed-return-values`
**Make target:** `make branch-task f=TASK-004`

## Acceptance criteria

- [x] `src/firefly_python_api/_types.py` defines:
  - `AssetAccount` — `TypedDict` with `id: str`, `name: str`
  - `TransactionPayload` — `TypedDict` with `type`, `date`, `amount`,
    `description` (required) and `source_id`, `destination_id`,
    `currency_code` (optional via `total=False` or a split TypedDict)
  - `BillData`, `BudgetData`, `BudgetLimitData`, `CategoryData` — each a
    `TypedDict` with `id: str` and `attributes: dict[str, Any]`
- [x] `get_asset_accounts()` return type is `list[AssetAccount]`
- [x] `create_transaction(payload)` parameter type is `TransactionPayload`
- [x] `get_bills()` returns `list[BillData]`
- [x] `get_budgets()` returns `list[BudgetData]`
- [x] `get_budget_limits()` returns `list[BudgetLimitData]`
- [x] `get_categories()` returns `list[CategoryData]`
- [x] All `TypedDict` types are importable from `firefly_python_api`
- [x] `mypy --strict` passes on `src/`
- [x] `make lint && make test` pass

## Completion
**Date:** 2026-04-30
**Summary:** Added TypedDict types for all structured data returned by FireflyClient. All types exportable from firefly_python_api. 53 tests, 100% coverage, mypy strict passes.
**Files changed:**
- `src/firefly_python_api/_types.py` — created
- `src/firefly_python_api/_client.py` — modified
- `src/firefly_python_api/__init__.py` — modified
- `tests/test_types.py` — created
- `docs/REQUIREMENTS.md` — modified
- `CHANGELOG.md` — modified
**Branch:** `task/004-typed-return-values`
**Stage:** `git add src/firefly_python_api/_types.py src/firefly_python_api/_client.py src/firefly_python_api/__init__.py tests/test_types.py docs/REQUIREMENTS.md docs/tasks/TASK-004-typed-return-values.md CHANGELOG.md`
**Commit:** `git commit -m "Add TypedDict types for IDE code completion (TASK-004)"`
