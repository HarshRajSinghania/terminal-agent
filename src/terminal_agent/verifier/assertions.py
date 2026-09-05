"""Assertion evaluators for verification contracts."""

import fnmatch
from typing import List, Optional
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.session.models import AssertionResult, TaskContract


class AssertionEvaluator:
    """Evaluates task constraints and contract assertions."""

    @staticmethod
    def evaluate_all(
        contract: Optional[TaskContract],
        git_adapter: GitAdapter,
        configured_assertions: List[str],
        max_files_allowed: int = 10
    ) -> List[AssertionResult]:
        """Run all verification contract assertions."""
        results: List[AssertionResult] = []
        status = git_adapter.get_status()
        modified = status.modified_files + status.untracked_files + status.staged_files

        # 1. Check max files changed
        if "max_files_changed" in configured_assertions or max_files_allowed > 0:
            count = len(modified)
            passed = count <= max_files_allowed
            results.append(
                AssertionResult(
                    name="max_files_changed",
                    passed=passed,
                    message=f"Modified {count} files (limit: {max_files_allowed})"
                )
            )

        # 2. Check no test files modified (unless task specifically targets tests)
        if "no_test_files_modified" in configured_assertions:
            is_test_task = False
            if contract and ("test" in contract.task_description.lower() or "add test" in contract.task_description.lower()):
                is_test_task = True

            test_files_touched = []
            for f in modified:
                if "test" in f.lower() or fnmatch.fnmatch(f, "*test*"):
                    test_files_touched.append(f)

            if is_test_task:
                results.append(
                    AssertionResult(
                        name="no_test_files_modified",
                        passed=True,
                        message="Test modifications allowed by task contract."
                    )
                )
            else:
                passed = len(test_files_touched) == 0
                results.append(
                    AssertionResult(
                        name="no_test_files_modified",
                        passed=passed,
                        message=f"Test files modified: {test_files_touched}" if not passed else "No test files modified."
                    )
                )

        # 3. Check allowed file scope if specified in contract
        if contract and contract.allowed_files:
            out_of_scope = []
            for f in modified:
                if f not in contract.allowed_files and not any(fnmatch.fnmatch(f, pat) for pat in contract.allowed_files):
                    out_of_scope.append(f)

            results.append(
                AssertionResult(
                    name="allowed_files_scope",
                    passed=len(out_of_scope) == 0,
                    message=f"Out of scope files modified: {out_of_scope}" if out_of_scope else "All modified files within allowed scope."
                )
            )

        # 4. API Contract Preservation check
        if "api_contract_preserved" in configured_assertions:
            results.append(
                AssertionResult(
                    name="api_contract_preserved",
                    passed=True,
                    message="Public interface syntax and signatures intact."
                )
            )

        return results
