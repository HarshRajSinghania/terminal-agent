"""Deterministic mock provider for offline testing, benchmarks, and predictable evaluation."""

import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, LLMUsage, ModelProvider


class MockProvider(ModelProvider):
    """
    Mock LLM provider that returns scripted responses or simulates an agent lifecycle.
    """

    def __init__(
        self,
        model_name: str = "mock-model",
        scripted_responses: Optional[List[LLMResponse]] = None,
        custom_handler: Optional[Callable[[List[LLMMessage]], LLMResponse]] = None
    ):
        self.model_name = model_name
        self.scripted_responses = scripted_responses or []
        self.response_index = 0
        self.custom_handler = custom_handler

    def check_health(self) -> Tuple[bool, str]:
        return True, "MockProvider is operational (offline mode)"

    def queue_response(self, response: LLMResponse) -> None:
        self.scripted_responses.append(response)

    def queue_tool_call(self, tool_name: str, arguments: Dict[str, Any], content: Optional[str] = None) -> None:
        call = LLMToolCall(id=f"call_{uuid.uuid4().hex[:6]}", name=tool_name, arguments=arguments)
        self.scripted_responses.append(
            LLMResponse(
                content=content,
                tool_calls=[call],
                finish_reason="tool_calls",
                usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150),
                provider_name="mock",
                model_name=self.model_name
            )
        )

    def queue_text_response(self, text: str) -> None:
        self.scripted_responses.append(
            LLMResponse(
                content=text,
                tool_calls=[],
                finish_reason="stop",
                usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150),
                provider_name="mock",
                model_name=self.model_name
            )
        )

    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        if self.custom_handler:
            return self.custom_handler(messages)

        if self.response_index < len(self.scripted_responses):
            resp = self.scripted_responses[self.response_index]
            self.response_index += 1
            return resp

        # Default fallback: If no more scripted responses, signal completion
        return LLMResponse(
            content="Task analysis complete. Ready for verification.",
            tool_calls=[],
            finish_reason="stop",
            usage=LLMUsage(input_tokens=50, output_tokens=20, total_tokens=70),
            provider_name="mock",
            model_name=self.model_name
        )

