"""Ollama local model provider using Ollama REST API."""

import json
from typing import Any, Dict, List, Optional, Tuple
import httpx

from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, LLMUsage, ModelProvider


class OllamaProvider(ModelProvider):
    """Local Ollama provider for open models (e.g. qwen2.5-coder, deepseek-coder)."""

    def __init__(
        self,
        model_name: str = "qwen2.5-coder",
        base_url: Optional[str] = None,
        timeout_seconds: int = 120
    ):
        self.model_name = model_name
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.timeout = timeout_seconds

    def check_health(self) -> Tuple[bool, str]:
        """Check if Ollama server is running and model is downloaded."""
        try:
            with httpx.Client(timeout=5) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    match = any(self.model_name in m for m in models)
                    if match:
                        return True, f"Ollama is online and model '{self.model_name}' is installed."
                    return True, f"Ollama is online, but model '{self.model_name}' was not found in installed models: {models}"
                return False, f"Ollama returned HTTP status {res.status_code}"
        except Exception as e:
            return False, f"Could not connect to Ollama at {self.base_url}: {e}"

    def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        # Convert internal messages to Ollama format
        ollama_msgs = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    }
                    for tc in m.tool_calls
                ]
            ollama_msgs.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": ollama_msgs,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if tools:
            # Transform tools into Ollama schema
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()

                msg = data.get("message", {})
                content = msg.get("content")
                tool_calls: List[LLMToolCall] = []

                if "tool_calls" in msg and msg["tool_calls"]:
                    for idx, tc in enumerate(msg["tool_calls"]):
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        tool_calls.append(
                            LLMToolCall(
                                id=f"call_ollama_{idx}",
                                name=fn.get("name", ""),
                                arguments=args
                            )
                        )

                prompt_eval_count = data.get("prompt_eval_count", 0)
                eval_count = data.get("eval_count", 0)

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls" if tool_calls else "stop",
                    usage=LLMUsage(
                        input_tokens=prompt_eval_count,
                        output_tokens=eval_count,
                        total_tokens=prompt_eval_count + eval_count
                    ),
                    provider_name="ollama",
                    model_name=self.model_name
                )
        except Exception as e:
            return LLMResponse(
                content=f"[Error communicating with Ollama: {e}]",
                tool_calls=[],
                finish_reason="error",
                provider_name="ollama",
                model_name=self.model_name
            )
