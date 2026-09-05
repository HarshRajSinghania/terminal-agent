"""Google Gemini REST API model provider."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx

from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, LLMUsage, ModelProvider


class GeminiProvider(ModelProvider):
    """Google Gemini API provider."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        timeout_seconds: int = 120
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.timeout = timeout_seconds

    def check_health(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "GEMINI_API_KEY environment variable is not set."
        return True, "Gemini credentials configured."

    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        contents = []
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            parts = []
            if m.content:
                parts.append({"text": m.content})
            if m.tool_calls:
                for tc in m.tool_calls:
                    parts.append({
                        "functionCall": {
                            "name": tc.name,
                            "args": tc.arguments
                        }
                    })
            if m.role == "tool":
                role = "function"
                parts = [{
                    "functionResponse": {
                        "name": m.name or "function",
                        "response": {"output": m.content or ""}
                    }
                }]
            if parts:
                contents.append({"role": role, "parts": parts})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature
            }
        }

        if tools:
            gemini_tools = []
            for t in tools:
                fn = t.get("function", {})
                gemini_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "parameters": fn.get("parameters", {})
                })
            payload["tools"] = [{"functionDeclarations": gemini_tools}]

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()

                candidates = data.get("candidates", [{}])
                cand = candidates[0] if candidates else {}
                content_obj = cand.get("content", {})
                parts = content_obj.get("parts", [])

                text_content = ""
                tool_calls: List[LLMToolCall] = []

                for part in parts:
                    if "text" in part:
                        text_content += part["text"]
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        tool_calls.append(
                            LLMToolCall(
                                id=f"call_gemini_{len(tool_calls)}",
                                name=fc.get("name", ""),
                                arguments=fc.get("args", {})
                            )
                        )

                usage_meta = data.get("usageMetadata", {})
                usage = LLMUsage(
                    input_tokens=usage_meta.get("promptTokenCount", 0),
                    output_tokens=usage_meta.get("candidatesTokenCount", 0),
                    total_tokens=usage_meta.get("totalTokenCount", 0)
                )

                return LLMResponse(
                    content=text_content if text_content else None,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls" if tool_calls else "stop",
                    usage=usage,
                    provider_name="gemini",
                    model_name=self.model_name
                )
        except Exception as e:
            return LLMResponse(
                content=f"[Gemini Provider Error: {e}]",
                tool_calls=[],
                finish_reason="error",
                provider_name="gemini",
                model_name=self.model_name
            )

