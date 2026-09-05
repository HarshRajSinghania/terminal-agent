"""Base tool abstraction, input validation, and execution results."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Structured output returned by every tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    duration_ms: int = 0
    reason: str = Field(default="", description="The stated reason for executing this tool")


class BaseTool(ABC):
    """Base class for all agent tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        """Execute the tool implementation."""
        pass

    def execute(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        """Execute with timing and input validation wrapper."""
        start = time.perf_counter()
        try:
            result = self.run(args, reason=reason)
            result.duration_ms = int((time.perf_counter() - start) * 1000)
            result.reason = reason
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{self.name}' failed with error: {str(e)}",
                duration_ms=duration_ms,
                reason=reason
            )

    def to_schema(self) -> Dict[str, Any]:
        """Generate OpenAI/Anthropic compatible function tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            }
        }
