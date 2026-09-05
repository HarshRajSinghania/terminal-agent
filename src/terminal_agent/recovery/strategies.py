"""Recovery engine for diagnosing root causes and generating targeted repair strategies."""

import re
from typing import Tuple
from terminal_agent.recovery.classifier import FailureClassifier
from terminal_agent.session.models import FailureCategory, FailureRecord, SessionState


class RecoveryEngine:
    """Diagnoses root cause of failures and generates targeted repair strategies."""

    @classmethod
    def analyze_and_plan_recovery(
        cls,
        category: FailureCategory,
        raw_output: str,
        state: SessionState
    ) -> Tuple[str, str]:
        """
        Analyze failure and return (root_cause_hypothesis, recovery_action_description).
        """
        if category == FailureCategory.SYNTAX_ERROR:
            # Extract syntax error line if possible
            line_match = re.search(r"File \"(.*?)\", line (\d+)", raw_output)
            loc = f" in {line_match.group(1)}:L{line_match.group(2)}" if line_match else ""
            hypothesis = f"Syntax or indentation error{loc} preventing compilation/parsing."
            action = "Inspect target file around the error line, repair syntax structure, and re-run tests."

        elif category == FailureCategory.TEST_FAILURE:
            # Extract assertion details
            assert_match = re.search(r"(assert\s+.*)", raw_output)
            diff_match = re.search(r"E\s+(.*)", raw_output)
            detail = diff_match.group(1) if diff_match else (assert_match.group(1) if assert_match else "Assertion mismatch")
            hypothesis = f"Test assertion failed: {detail[:120]}. Implementation logic does not satisfy test contract."
            action = "Read failing test trace, trace implementation logic in target file, adjust return values or state handling, and verify again."

        elif category == FailureCategory.DEPENDENCY_ERROR:
            missing_mod = re.search(r"No module named ['\"](.*?)['\"]", raw_output)
            mod_name = missing_mod.group(1) if missing_mod else "unknown"
            hypothesis = f"Missing import or dependency '{mod_name}'."
            action = f"Add missing import or check standard library alternatives for '{mod_name}' without modifying test files."

        elif category == FailureCategory.WRONG_SOLUTION:
            exc_match = re.search(r"([A-Za-z]+Error: .*)", raw_output)
            exc_text = exc_match.group(1) if exc_match else "Runtime exception encountered"
            hypothesis = f"Runtime logic exception: {exc_text[:120]}."
            action = "Inspect variable types, null/empty checks, and exception guards in modified code."

        elif category == FailureCategory.TIMEOUT:
            hypothesis = "Execution exceeded time limit due to possible infinite loop or heavy I/O."
            action = "Inspect loops, termination conditions, and ensure fast execution."

        elif category == FailureCategory.TOOL_ERROR:
            hypothesis = "Tool invocation error or invalid arguments/paths."
            action = "Check file existence and correct tool arguments."

        else:
            hypothesis = "Execution failed with non-zero exit code or unmet criteria."
            action = "Inspect command error output, review latest changes, and apply fix."

        return hypothesis, action

