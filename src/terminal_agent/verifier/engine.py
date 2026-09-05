"""Independent Verification Engine for validating code correctness and contract compliance."""

from pathlib import Path
from typing import List, Optional

from terminal_agent.config.schema import VerificationConfig
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.sandbox.base import Sandbox
from terminal_agent.session.models import TaskContract, VerificationResult, VerificationStatus
from terminal_agent.verifier.assertions import AssertionEvaluator
from terminal_agent.verifier.runners import TestOutputParser


class IndependentVerifier:
    """Independent verification engine that certifies or rejects code changes."""

    def __init__(
        self,
        sandbox: Sandbox,
        git_adapter: GitAdapter,
        config: Optional[VerificationConfig] = None,
        working_dir: Optional[Path] = None
    ):
        self.sandbox = sandbox
        self.git_adapter = git_adapter
        self.config = config or VerificationConfig()
        self.working_dir = (working_dir or Path.cwd()).resolve()

    def verify(
        self,
        contract: Optional[TaskContract] = None,
        custom_test_cmd: Optional[str] = None
    ) -> VerificationResult:
        """
        Execute full independent verification protocol.
        1. Run configured test commands
        2. Run lint if configured
        3. Inspect git diff and modified files
        4. Evaluate contract assertions
        5. Synthesize final VerificationStatus
        """
        test_cmds = [custom_test_cmd] if custom_test_cmd else (contract.verification_commands if contract and contract.verification_commands else self.config.tests)

        total_passed = 0
        total_failed = 0
        combined_test_output = []
        all_tests_succeeded = True

        for cmd in test_cmds:
            exec_res = self.sandbox.execute(cmd, cwd=self.working_dir, timeout=120)
            combined_output = exec_res.stdout + ("\n" + exec_res.stderr if exec_res.stderr else "")
            combined_test_output.append(f"=== TEST RUN: {cmd} (Exit Code: {exec_res.exit_code}) ===\n{combined_output}")

            parsed = TestOutputParser.parse(combined_output, exec_res.exit_code)
            total_passed += parsed.passed
            total_failed += (parsed.failed + parsed.errors)

            if not exec_res.is_success or (parsed.failed + parsed.errors) > 0:
                all_tests_succeeded = False

        # Run lint if configured
        lint_passed = True
        lint_output_parts = []
        for lint_cmd in self.config.lint:
            l_res = self.sandbox.execute(lint_cmd, cwd=self.working_dir, timeout=60)
            if not l_res.is_success:
                lint_passed = False
            lint_output_parts.append(f"=== LINT: {lint_cmd} ===\n{l_res.stdout}\n{l_res.stderr}")

        # Inspect Git Diff
        diff_stats = self.git_adapter.get_diff_stats()
        status = self.git_adapter.get_status()
        modified_files = diff_stats.modified_files

        # Evaluate Assertions
        assertions = AssertionEvaluator.evaluate_all(
            contract=contract,
            git_adapter=self.git_adapter,
            configured_assertions=self.config.assertions,
            max_files_allowed=self.config.diff.max_files_changed
        )
        assertions_passed = all(a.passed for a in assertions)

        # Unintended files check
        unintended_files = []
        if contract and contract.allowed_files:
            for f in modified_files:
                if f not in contract.allowed_files:
                    unintended_files.append(f)

        # Determine Verification Status
        if all_tests_succeeded and assertions_passed and lint_passed:
            final_status = VerificationStatus.VERIFIED
        elif all_tests_succeeded and not assertions_passed:
            final_status = VerificationStatus.PARTIAL
        elif total_passed > 0 and total_failed > 0:
            final_status = VerificationStatus.PARTIAL
        elif total_failed > 0:
            final_status = VerificationStatus.FAILED
        else:
            final_status = VerificationStatus.FAILED

        details = (
            f"Tests: {total_passed} passed, {total_failed} failed. "
            f"Files changed: {len(modified_files)}. "
            f"Assertions passed: {sum(1 for a in assertions if a.passed)}/{len(assertions)}."
        )

        return VerificationResult(
            status=final_status,
            tests_run=total_passed + total_failed,
            tests_passed=total_passed,
            tests_failed=total_failed,
            test_output="\n\n".join(combined_test_output),
            lint_passed=lint_passed,
            lint_output="\n\n".join(lint_output_parts) if lint_output_parts else None,
            files_changed_count=len(modified_files),
            files_changed=modified_files,
            unintended_files_count=len(unintended_files),
            unintended_files=unintended_files,
            assertions=assertions,
            passed_all=(final_status == VerificationStatus.VERIFIED),
            details=details
        )

