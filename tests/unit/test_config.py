"""Unit tests for configuration loading and validation."""

import os
from pathlib import Path
import pytest
from terminal_agent.config.schema import ProviderType, SandboxMode, TerminalAgentConfig
from terminal_agent.config.settings import load_config, save_default_config


def test_default_config_schema():
    config = TerminalAgentConfig()
    assert config.agent.max_steps == 40
    assert config.agent.max_retries == 3
    assert config.sandbox.mode == SandboxMode.LOCAL
    assert config.security.network == "disabled"
    assert config.provider.name == ProviderType.MOCK
    assert "no_test_files_modified" in config.verification.assertions


def test_save_and_load_config(tmp_path: Path):
    config_file = tmp_path / "terminal-agent.config.yaml"
    save_default_config(config_file)
    assert config_file.exists()

    loaded = load_config(config_file)
    assert loaded.agent.max_steps == 40
    assert loaded.provider.model == "mock-model"


def test_env_var_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TERMINAL_AGENT_PROVIDER", "ollama")
    monkeypatch.setenv("TERMINAL_AGENT_MODEL", "qwen2.5-coder")
    
    config = load_config(tmp_path / "non_existent.yaml")
    assert config.provider.name == ProviderType.OLLAMA
    assert config.provider.model == "qwen2.5-coder"
