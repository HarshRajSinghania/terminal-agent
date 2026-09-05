"""Execution plan generator and lifecycle tracker."""

from typing import List
from terminal_agent.session.models import PlanItem, TaskContract


class ExecutionPlanner:
    """Creates structured multi-step execution plans."""

    @classmethod
    def create_initial_plan(cls, contract: TaskContract) -> List[PlanItem]:
        """Generate initial step plan for the agent loop."""
        return [
            PlanItem(id=1, description="Inspect repository structure and discover relevant files", status="IN_PROGRESS"),
            PlanItem(id=2, description="Create baseline safety checkpoint", status="TODO"),
            PlanItem(id=3, description="Analyze source code and formulate required changes", status="TODO"),
            PlanItem(id=4, description="Apply code modifications to target files", status="TODO"),
            PlanItem(id=5, description="Execute test suite and evaluate independent verification contract", status="TODO"),
            PlanItem(id=6, description="Perform failure analysis and repair loop if needed", status="TODO"),
            PlanItem(id=7, description="Review git diff and generate final Proof of Done", status="TODO"),
        ]

    @classmethod
    def update_plan_step(cls, plan: List[PlanItem], step_id: int, new_status: str) -> None:
        """Update status of a specific step."""
        for item in plan:
            if item.id == step_id:
                item.status = new_status
                break
