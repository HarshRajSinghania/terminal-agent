"""Unit tests for model provider normalization and factory."""

from terminal_agent.config.schema import ProviderConfig, ProviderType
from terminal_agent.providers.base import LLMMessage
from terminal_agent.providers.factory import create_provider
from terminal_agent.providers.mock_provider import MockProvider


def test_mock_provider_scripted_flow():
    provider = MockProvider()
    provider.queue_tool_call("read_file", {"path": "auth.py", "reason": "Inspect auth"})
    provider.queue_text_response("Done analysis.")

    # Call 1: Tool call
    res1 = provider.generate([LLMMessage(role="user", content="start")])
    assert len(res1.tool_calls) == 1
    assert res1.tool_calls[0].name == "read_file"

    # Call 2: Text response
    res2 = provider.generate([LLMMessage(role="user", content="next")])
    assert res2.content == "Done analysis."


def test_provider_factory():
    cfg_mock = ProviderConfig(name=ProviderType.MOCK, model="mock-test")
    p = create_provider(cfg_mock)
    assert isinstance(p, MockProvider)
    ok, msg = p.check_health()
    assert ok is True
