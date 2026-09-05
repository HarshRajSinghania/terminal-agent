"""Central ToolRegistry for dispatching agent tool executions."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.sandbox.base import Sandbox
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.tools.base import BaseTool, ToolResult
from terminal_agent.tools.checkpoint_tools import CreateCheckpointTool, RestoreCheckpointTool
from terminal_agent.tools.command_tools import RunCommandTool, RunTestsTool
from terminal_agent.tools.file_tools import (
    EditFileTool,
    ListFilesTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)
from terminal_agent.tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool


class ToolRegistry:
    """Manages the full suite of available agent tools."""

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        sandbox: Optional[Sandbox] = None,
        security_enforcer: Optional[SecurityPolicyEnforcer] = None,
        git_adapter: Optional[GitAdapter] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        secret_guard: Optional[SecretGuard] = None,
    ):
        self.working_dir = (working_dir or Path.cwd()).resolve()
        self.secret_guard = secret_guard or SecretGuard(working_dir=self.working_dir)
        self.git_adapter = git_adapter or GitAdapter(self.working_dir)
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(self.working_dir)

        if sandbox is None:
            from terminal_agent.sandbox.local import LocalSandbox
            self.sandbox = LocalSandbox(working_dir=self.working_dir, secret_guard=self.secret_guard)
        else:
            self.sandbox = sandbox

        if security_enforcer is None:
            self.security_enforcer = SecurityPolicyEnforcer(secret_guard=self.secret_guard)
        else:
            self.security_enforcer = security_enforcer

        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the 12 core tools."""
        # File tools
        self.register(ReadFileTool(self.working_dir, self.secret_guard))
        self.register(WriteFileTool(self.working_dir, self.secret_guard))
        self.register(EditFileTool(self.working_dir, self.secret_guard))
        self.register(ListFilesTool(self.working_dir, self.secret_guard))
        self.register(SearchFilesTool(self.working_dir, self.secret_guard))

        # Command tools
        self.register(RunCommandTool(self.sandbox, self.security_enforcer, self.working_dir))
        self.register(RunTestsTool(self.sandbox, self.security_enforcer, self.working_dir))

        # Git tools
        self.register(GitStatusTool(self.git_adapter))
        self.register(GitDiffTool(self.git_adapter))
        self.register(GitLogTool(self.git_adapter))

        # Checkpoint tools
        self.register(CreateCheckpointTool(self.checkpoint_manager))
        self.register(RestoreCheckpointTool(self.checkpoint_manager))

    def register(self, tool: BaseTool) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tool_names(self) -> List[str]:
        """List registered tool names."""
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return function tool definitions for model invocation."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, args: Dict[str, Any], reason: str = "") -> ToolResult:
        """Dispatch execution to target tool with explainability reason."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' not found. Available tools: {', '.join(self._tools.keys())}",
                reason=reason
            )

        # Ensure reason is passed
        if not reason and "reason" in args:
            reason = str(args["reason"])

        return tool.execute(args, reason=reason)
