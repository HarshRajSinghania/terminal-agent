"""Failure classification engine analyzing execution and test errors."""

import re
from typing import Tuple
from terminal_agent.session.models import FailureCategory


class FailureClassifier:
    """Classifies errors and test failures into 12 structured failure categories."""

    @classmethod
    def classify(cls, error_output: str, exit_code: int = 1, timed_out: bool = False) -> Tuple[FailureCategory, str]:
        """Analyze stdout/stderr/traceback and determine primary failure category."""
        if timed_out or "timed out" in error_output.lower():
            return FailureCategory.TIMEOUT, "Execution exceeded allocated timeout."

        output_lower = error_output.lower()

        # 1. Syntax Error
        if "syntaxerror" in output_lower or "indentationerror" in output_lower or "taberror" in output_lower:
            return FailureCategory.SYNTAX_ERROR, "Detected Python syntax or indentation error in source code."

        # 2. Dependency Error / ModuleNotFoundError / ImportError
        if "modulenotfounderror" in output_lower or "importerror" in output_lower or "no module named" in output_lower:
            return FailureCategory.DEPENDENCY_ERROR, "Missing module or import dependency."

        # 3. Permission Error
        if "permissionerror" in output_lower or "permissiondenied" in output_lower or "permission denied" in output_lower or "access denied" in output_lower or "access is denied" in output_lower or "operation not permitted" in output_lower:
            return FailureCategory.PERMISSION_ERROR, "Insufficient permissions to read, write, or execute."

        # 4. Network Error
        if "connection refused" in output_lower or "nameresolutionerror" in output_lower or "could not resolve host" in output_lower or "network is unreachable" in output_lower or "connectionerror" in output_lower:
            return FailureCategory.NETWORK_ERROR, "Network connection failure or network policy block."

        # 5. Context Overflow
        if "context_length_exceeded" in output_lower or "maximum context length" in output_lower or "token limit" in output_lower:
            return FailureCategory.CONTEXT_OVERFLOW, "Context window limit exceeded."

        # 6. Tool Error
        if "tool '" in output_lower and "failed with error" in output_lower:
            return FailureCategory.TOOL_ERROR, "Tool execution parameter or precondition error."

        # 7. Test Failure (AssertionError, test failures in pytest/unittest)
        if "assertionerror" in output_lower or "failed (" in output_lower or "failure:" in output_lower or " assert " in output_lower or "failures=" in output_lower:
            return FailureCategory.TEST_FAILURE, "Test assertions failed during verification."

        # 8. Command Failure
        if "command not found" in output_lower or "is not recognized as an internal or external command" in output_lower:
            return FailureCategory.COMMAND_FAILURE, "Shell command or executable not found on system."

        # 9. Wrong Solution / Logic Error
        if "typeerror" in output_lower or "valueerror" in output_lower or "keyerror" in output_lower or "indexerror" in output_lower or "attributeerror" in output_lower:
            return FailureCategory.WRONG_SOLUTION, "Runtime exception or improper data handling in implementation."

        # 10. Incomplete Task
        if "incomplete" in output_lower or "todo" in output_lower:
            return FailureCategory.INCOMPLETE_TASK, "Implementation or verification requirements partially fulfilled."

        # Default fallback
        if exit_code != 0:
            return FailureCategory.TEST_FAILURE if "pytest" in output_lower or "test" in output_lower else FailureCategory.COMMAND_FAILURE, "Nonzero command exit status."

        return FailureCategory.UNKNOWN, "Unknown failure condition."

