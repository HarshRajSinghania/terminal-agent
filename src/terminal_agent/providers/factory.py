"""Provider factory for instantiating model providers."""

from terminal_agent.config.schema import ProviderConfig, ProviderType
from terminal_agent.providers.anthropic_provider import AnthropicProvider
from terminal_agent.providers.base import ModelProvider
from terminal_agent.providers.gemini_provider import GeminiProvider
from terminal_agent.providers.mock_provider import MockProvider
from terminal_agent.providers.ollama_provider import OllamaProvider
from terminal_agent.providers.openai_provider import OpenAIProvider


def create_provider(config: ProviderConfig) -> ModelProvider:
    """Instantiate model provider from configuration."""
    provider_name = config.name

    if provider_name == ProviderType.MOCK:
        return MockProvider(model_name=config.model)
    elif provider_name == ProviderType.OLLAMA:
        return OllamaProvider(model_name=config.model, base_url=config.base_url)
    elif provider_name == ProviderType.OPENAI:
        return OpenAIProvider(model_name=config.model, api_key=config.api_key, base_url=config.base_url)
    elif provider_name == ProviderType.ANTHROPIC:
        return AnthropicProvider(model_name=config.model, api_key=config.api_key, base_url=config.base_url)
    elif provider_name == ProviderType.GEMINI:
        return GeminiProvider(model_name=config.model, api_key=config.api_key)
    else:
        # Default fallback to MockProvider
        return MockProvider(model_name=config.model)

