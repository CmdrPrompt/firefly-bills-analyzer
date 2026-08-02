"""TASK-019 step definitions for normalized monthly equivalent per pattern.

Demonstrates pytest-bdd scenario binding. Scenarios are loaded from the
feature file but step implementations are not yet bound — the scenario
calls will show as XFAIL (deliberately pending) rather than failing CI.
Step implementation follows during the implementation-worker's TDD Red phase.
"""

import pytest
from pytest_bdd import scenarios

scenarios("../features/TASK-019-monthly-equivalent.feature")

pytestmark = pytest.mark.xfail(
    reason="TASK-019 step bindings not yet implemented",
    strict=False,
)
