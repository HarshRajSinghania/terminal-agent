"""Base provider abstraction and common message formats for LLMs."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class LLMToolCall(BaseModel):
    """Structured representation of a function call requested by the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    """Normalized chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    tool_calls: Optional[List[LLMToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Standardized response from any model provider."""
    content: Optional[str] = None
    tool_calls: List[LLMToolCall] = Field(default_factory=list)
    finish_reason: str = "stop"  # "stop", "tool_calls", "length"
    usage: LLMUsage = Field(default_factory=LLMUsage)
    provider_name: str = ""
    model_name: str = ""


class ModelProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        """Generate a response, optionally choosing tool calls."""
        pass

    @abstractmethod
    def check_health(self) -> Tuple[bool, str]:
        """Check availability and connectivity of the model provider."""
        pass
