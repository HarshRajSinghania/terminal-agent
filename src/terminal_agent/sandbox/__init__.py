"""Sandbox package for Terminal Agent."""

from terminal_agent.sandbox.base import Sandbox, ExecutionResult
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.sandbox.docker import DockerSandbox

__all__ = [
    "Sandbox",
    "ExecutionResult",
    "LocalSandbox",
    "DockerSandbox",
]
