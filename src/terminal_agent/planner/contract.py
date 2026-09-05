"""Task contract generator and validator for structured verification-first coding."""

import re
import uuid
from typing import List, Optional
from terminal_agent.session.models import TaskContract


class TaskContractGenerator:
    """Builds and validates structured task contracts."""

    @classmethod
    def generate_from_description(
        cls,
        task_description: str,
        custom_constraints: Optional[List[str]] = None,
        custom_criteria: Optional[List[str]] = None,
        verification_commands: Optional[List[str]] = None
    ) -> TaskContract:
        """Derive structured task contract from raw user request and defaults."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # Extract explicit goal
        goal = task_description.strip()
        if not goal.endswith("."):
            goal += "."

        # Default standard engineering constraints
        constraints = [
            "Do not modify tests unless explicitly requested.",
            "Preserve public API and backwards compatibility.",
            "Avoid modifying unrelated project files.",
            "Respect security policies and avoid secret exposure."
        ]
        if custom_constraints:
            constraints.extend(custom_constraints)

        # Success criteria
        criteria = [
            "All configured verification tests pass (exit code 0).",
            "No unintended files modified outside task scope.",
            "All contract assertions validated successfully.",
        ]
        if custom_criteria:
            criteria.extend(custom_criteria)

        # Derive test commands
        v_cmds = verification_commands or ["pytest"]

        return TaskContract(
            task_id=task_id,
            task_description=task_description,
            goal=goal,
            constraints=constraints,
            success_criteria=criteria,
            verification_commands=v_cmds
        )

