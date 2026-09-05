"""OpenAI and OpenAI-compatible API model provider."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx

from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, LLMUsage, ModelProvider


class OpenAIProvider(ModelProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 120
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout_seconds

    def check_health(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY environment variable is not set."
        return True, "OpenAI credentials configured."

    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        openai_msgs = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role}
            if m.content is not None:
                msg_dict["content"] = m.content
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)
                        }
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            openai_msgs.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": openai_msgs,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content")
                finish_reason = choice.get("finish_reason", "stop")

                tool_calls: List[LLMToolCall] = []
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {})
                    args_str = fn.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                    except Exception:
                        args = {}
                    tool_calls.append(
                        LLMToolCall(
                            id=tc.get("id", ""),
                            name=fn.get("name", ""),
                            arguments=args
                        )
                    )

                usage_data = data.get("usage", {})
                usage = LLMUsage(
                    input_tokens=usage_data.get("prompt_tokens", 0),
                    output_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0)
                )

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls" if tool_calls else finish_reason,
                    usage=usage,
                    provider_name="openai",
                    model_name=self.model_name
                )
        except Exception as e:
            return LLMResponse(
                content=f"[OpenAI Provider Error: {e}]",
                tool_calls=[],
                finish_reason="error",
                provider_name="openai",
                model_name=self.model_name
            )

