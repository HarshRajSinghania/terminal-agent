"""Settings loader and configuration manager for Terminal Agent."""

import os
from pathlib import Path
from typing import Optional
import yaml
from terminal_agent.config.schema import TerminalAgentConfig, ProviderType


DEFAULT_CONFIG_FILENAMES = [
    "terminal-agent.config.yaml",
    "terminal-agent.config.yml",
    ".terminal-agent.yaml",
    ".terminal-agent.yml",
]


def find_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find configuration file by searching current and parent directories."""
    current = start_dir or Path.cwd()
    root = Path(current.anchor)

    while current != root:
        for filename in DEFAULT_CONFIG_FILENAMES:
            candidate = current / filename
            if candidate.is_file():
                return candidate
        current = current.parent

    for filename in DEFAULT_CONFIG_FILENAMES:
        candidate = root / filename
        if candidate.is_file():
            return candidate

    return None


def load_config(config_path: Optional[Path] = None) -> TerminalAgentConfig:
    """Load configuration from file or defaults, applying environment variables."""
    target_path = config_path or find_config_file()

    raw_data = {}
    if target_path and target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                raw_data = loaded

    # Environment variable overrides
    if "TERMINAL_AGENT_PROVIDER" in os.environ:
        provider_name = os.environ["TERMINAL_AGENT_PROVIDER"].lower()
        if "provider" not in raw_data:
            raw_data["provider"] = {}
        raw_data["provider"]["name"] = provider_name

    if "TERMINAL_AGENT_MODEL" in os.environ:
        if "provider" not in raw_data:
            raw_data["provider"] = {}
        raw_data["provider"]["model"] = os.environ["TERMINAL_AGENT_MODEL"]

    if "OLLAMA_HOST" in os.environ and "provider" in raw_data and raw_data["provider"].get("name") == "ollama":
        raw_data["provider"]["base_url"] = os.environ["OLLAMA_HOST"]

    if "OPENAI_API_KEY" in os.environ:
        if "provider" in raw_data and raw_data["provider"].get("name") == "openai":
            raw_data["provider"]["api_key"] = os.environ["OPENAI_API_KEY"]

    if "ANTHROPIC_API_KEY" in os.environ:
        if "provider" in raw_data and raw_data["provider"].get("name") == "anthropic":
            raw_data["provider"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]

    if "GEMINI_API_KEY" in os.environ:
        if "provider" in raw_data and raw_data["provider"].get("name") == "gemini":
            raw_data["provider"]["api_key"] = os.environ["GEMINI_API_KEY"]

    return TerminalAgentConfig.model_validate(raw_data)


def save_default_config(destination: Path) -> Path:
    """Write default configuration YAML template to destination."""
    default_config = TerminalAgentConfig()
    yaml_content = yaml.dump(default_config.model_dump(mode="json"), sort_keys=False, indent=2)
    destination.write_text(yaml_content, encoding="utf-8")
    return destination

