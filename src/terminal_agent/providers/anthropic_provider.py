"""Anthropic Messages API model provider."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx

from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, LLMUsage, ModelProvider


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 120
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self.timeout = timeout_seconds

    def check_health(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY environment variable is not set."
        return True, "Anthropic credentials configured."

    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_prompt = ""
        claude_msgs = []

        for m in messages:
            if m.role == "system":
                system_prompt += (m.content or "") + "\n"
            elif m.role == "tool":
                claude_msgs.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id or "tool_call",
                            "content": m.content or ""
                        }
                    ]
                })
            elif m.role == "assistant" and m.tool_calls:
                content_blocks = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    })
                claude_msgs.append({"role": "assistant", "content": content_blocks})
            else:
                claude_msgs.append({"role": m.role, "content": m.content or ""})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": claude_msgs,
            "max_tokens": 4096,
            "temperature": temperature,
        }

        if system_prompt.strip():
            payload["system"] = system_prompt.strip()

        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "input_schema": fn.get("parameters", {})
                })
            payload["tools"] = anthropic_tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/messages", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                text_content = ""
                tool_calls: List[LLMToolCall] = []

                for block in data.get("content", []):
                    if block.get("type") == "text":
                        text_content += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append(
                            LLMToolCall(
                                id=block.get("id", ""),
                                name=block.get("name", ""),
                                arguments=block.get("input", {})
                            )
                        )

                usage_data = data.get("usage", {})
                usage = LLMUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                    total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
                )

                stop_reason = data.get("stop_reason", "end_turn")
                return LLMResponse(
                    content=text_content if text_content else None,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls" if tool_calls else stop_reason,
                    usage=usage,
                    provider_name="anthropic",
                    model_name=self.model_name
                )
        except Exception as e:
            return LLMResponse(
                content=f"[Anthropic Provider Error: {e}]",
                tool_calls=[],
                finish_reason="error",
                provider_name="anthropic",
                model_name=self.model_name
            )

