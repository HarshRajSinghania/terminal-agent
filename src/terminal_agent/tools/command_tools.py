"""Command and test execution tools with sandbox isolation and policy enforcement."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from terminal_agent.sandbox.base import Sandbox
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.tools.base import BaseTool, ToolResult


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Execute a shell command inside the workspace sandbox. Requires an explicit reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (optional, default 60)"},
            "reason": {"type": "string", "description": "Explainability reason for running this command"}
        },
        "required": ["command", "reason"]
    }

    def __init__(
        self,
        sandbox: Sandbox,
        security_enforcer: SecurityPolicyEnforcer,
        working_dir: Path
    ):
        self.sandbox = sandbox
        self.security_enforcer = security_enforcer
        self.working_dir = working_dir

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        command = args.get("command", "").strip()
        timeout = args.get("timeout", None)

        if not command:
            return ToolResult(success=False, output="", error="Command cannot be empty", reason=reason)

        # Enforce security policy
        allowed, policy_reason, category = self.security_enforcer.check_command(command)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Security Policy Denied: {policy_reason}",
                data={"category": category.value, "denied": True},
                reason=reason
            )

        exec_res = self.sandbox.execute(command, cwd=self.working_dir, timeout=timeout)
        combined_output = ""
        if exec_res.stdout:
            combined_output += exec_res.stdout
        if exec_res.stderr:
            if combined_output:
                combined_output += "\n--- STDERR ---\n"
            combined_output += exec_res.stderr

        return ToolResult(
            success=exec_res.is_success,
            output=combined_output,
            error=None if exec_res.is_success else f"Command failed with exit code {exec_res.exit_code}",
            data={
                "command": command,
                "exit_code": exec_res.exit_code,
                "timed_out": exec_res.timed_out,
                "duration_ms": exec_res.duration_ms
            },
            reason=reason
        )


class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Run test suite (e.g. pytest) inside sandbox and collect structured test results. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "test_command": {"type": "string", "description": "Test command (e.g., 'pytest', 'pytest tests/test_auth.py')"},
            "reason": {"type": "string", "description": "Explainability reason for executing tests"}
        },
        "required": ["reason"]
    }

    def __init__(
        self,
        sandbox: Sandbox,
        security_enforcer: SecurityPolicyEnforcer,
        working_dir: Path,
        default_test_cmd: str = "pytest"
    ):
        self.sandbox = sandbox
        self.security_enforcer = security_enforcer
        self.working_dir = working_dir
        self.default_test_cmd = default_test_cmd

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        test_cmd = args.get("test_command") or self.default_test_cmd

        allowed, policy_reason, _ = self.security_enforcer.check_command(test_cmd)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Security Policy Denied: {policy_reason}",
                reason=reason
            )

        exec_res = self.sandbox.execute(test_cmd, cwd=self.working_dir, timeout=120)
        output = exec_res.stdout + ("\n" + exec_res.stderr if exec_res.stderr else "")

        return ToolResult(
            success=exec_res.is_success,
            output=output,
            error=None if exec_res.is_success else f"Test run failed with exit code {exec_res.exit_code}",
            data={
                "test_command": test_cmd,
                "exit_code": exec_res.exit_code,
                "duration_ms": exec_res.duration_ms
            },
            reason=reason
        )
