"""Unit tests for Ollama detection, provider matrix auto-discovery, setup, and doctor commands."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from terminal_agent.cli.commands.doctor import doctor_command
from terminal_agent.cli.commands.setup import _append_or_update_env_file, _save_provider_config
from terminal_agent.config.schema import ProviderConfig, ProviderType, TerminalAgentConfig
from terminal_agent.providers.detector import (
    OllamaDetectionResult,
    OllamaStatus,
    ProviderInfo,
    ProviderStatus,
    detect_all_providers,
    detect_ollama,
    resolve_active_provider,
)


def test_ollama_not_installed():
    """When ollama CLI is not in PATH and server cannot be reached."""
    with patch("shutil.which", return_value=None):
        with patch("httpx.Client.get", side_effect=Exception("Connection refused")):
            result = detect_ollama(base_url="http://localhost:11434", target_model="qwen2.5-coder")
            assert result.status == OllamaStatus.OLLAMA_NOT_INSTALLED
            assert result.installed is False
            assert result.server_reachable is False
            assert result.target_model_installed is False
            assert "not installed" in result.message.lower()
            assert result.action_hint is not None


def test_ollama_installed_but_server_not_running():
    """When ollama executable exists but server port is offline."""
    with patch("shutil.which", return_value="/usr/local/bin/ollama"):
        with patch("httpx.Client.get", side_effect=Exception("Connection refused")):
            result = detect_ollama(base_url="http://localhost:11434", target_model="qwen2.5-coder")
            assert result.status == OllamaStatus.OLLAMA_NOT_RUNNING
            assert result.installed is True
            assert result.server_reachable is False
            assert "server is not running" in result.message.lower()
            assert "ollama serve" in result.action_hint


def test_ollama_ready_with_model():
    """When ollama server is online and the requested model is present."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "qwen2.5-coder:latest"},
            {"name": "llama3:8b"}
        ]
    }

    with patch("shutil.which", return_value="/usr/local/bin/ollama"):
        with patch("httpx.Client.get", return_value=mock_resp):
            result = detect_ollama(base_url="http://localhost:11434", target_model="qwen2.5-coder")
            assert result.status == OllamaStatus.OLLAMA_READY
            assert result.installed is True
            assert result.server_reachable is True
            assert result.target_model_installed is True
            assert "qwen2.5-coder:latest" in result.installed_models
            assert result.action_hint is None


def test_ollama_model_missing():
    """When ollama server is online but the requested model is not downloaded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "llama3:8b"},
            {"name": "mistral:latest"}
        ]
    }

    with patch("shutil.which", return_value="/usr/local/bin/ollama"):
        with patch("httpx.Client.get", return_value=mock_resp):
            result = detect_ollama(base_url="http://localhost:11434", target_model="qwen2.5-coder")
            assert result.status == OllamaStatus.OLLAMA_MODEL_MISSING
            assert result.installed is True
            assert result.server_reachable is True
            assert result.target_model_installed is False
            assert "not installed" in result.message.lower()
            assert "ollama pull qwen2.5-coder" in result.action_hint


def test_ollama_http_error():
    """When ollama endpoint returns an HTTP error status code."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("shutil.which", return_value="/usr/local/bin/ollama"):
        with patch("httpx.Client.get", return_value=mock_resp):
            result = detect_ollama(base_url="http://localhost:11434", target_model="qwen2.5-coder")
            assert result.status == OllamaStatus.OLLAMA_ERROR
            assert result.server_reachable is True
            assert result.target_model_installed is False
            assert "500" in result.message


def test_detect_all_providers_with_environment():
    """Verify detection of multiple providers based on env vars and mocked Ollama."""
    config = TerminalAgentConfig()

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-proj-test1234567890", "ANTHROPIC_API_KEY": ""}, clear=False):
        with patch("terminal_agent.providers.detector.detect_ollama") as mock_det:
            mock_det.return_value = OllamaDetectionResult(
                status=OllamaStatus.OLLAMA_READY,
                installed=True,
                cli_path="/bin/ollama",
                server_reachable=True,
                base_url="http://localhost:11434",
                installed_models=["qwen2.5-coder"],
                target_model="qwen2.5-coder",
                target_model_installed=True,
                message="Ready"
            )

            providers = detect_all_providers(config=config)
            
            assert providers["ollama"].status == ProviderStatus.READY
            assert providers["ollama"].is_usable is True

            assert providers["openai"].status == ProviderStatus.READY
            assert providers["openai"].is_usable is True

            assert providers["anthropic"].status == ProviderStatus.NOT_CONFIGURED
            assert providers["anthropic"].is_usable is False

            assert providers["mock"].status == ProviderStatus.READY
            assert providers["mock"].is_usable is True


def test_resolve_active_provider_explicit_override():
    """Explicit CLI argument has highest priority."""
    config = TerminalAgentConfig(provider=ProviderConfig(name=ProviderType.MOCK))
    resolved_cfg, info = resolve_active_provider(
        config=config,
        explicit_provider="anthropic",
        explicit_model="claude-3-opus-20240229"
    )
    assert resolved_cfg.name == ProviderType.ANTHROPIC
    assert resolved_cfg.model == "claude-3-opus-20240229"


def test_resolve_active_provider_fallback_to_ready_ollama():
    """If default is mock/none but Ollama is ready, local Ollama is detected."""
    config = TerminalAgentConfig(provider=ProviderConfig(name=ProviderType.MOCK))
    
    with patch.dict(os.environ, {}, clear=True):
        with patch("terminal_agent.providers.detector.detect_ollama") as mock_det:
            mock_det.return_value = OllamaDetectionResult(
                status=OllamaStatus.OLLAMA_READY,
                installed=True,
                cli_path="/bin/ollama",
                server_reachable=True,
                base_url="http://localhost:11434",
                installed_models=["qwen2.5-coder"],
                target_model="qwen2.5-coder",
                target_model_installed=True,
                message="Ready"
            )

            config_ollama = TerminalAgentConfig(provider=ProviderConfig(name=ProviderType.OLLAMA, model="qwen2.5-coder"))
            resolved_cfg, info = resolve_active_provider(config=config_ollama)
            assert resolved_cfg.name == ProviderType.OLLAMA
            assert info.is_usable is True


def test_doctor_command_runs_without_crashing(tmp_path: Path):
    """Doctor command executes cleanly even when Ollama and cloud keys are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("terminal_agent.providers.detector.detect_ollama") as mock_det:
                mock_det.return_value = OllamaDetectionResult(
                    status=OllamaStatus.OLLAMA_NOT_INSTALLED,
                    installed=False,
                    cli_path=None,
                    server_reachable=False,
                    base_url="http://localhost:11434",
                    installed_models=[],
                    target_model="qwen2.5-coder",
                    target_model_installed=False,
                    message="Not installed"
                )

                # Should execute without throwing any exception
                doctor_command(working_dir=tmp_path)


def test_setup_helpers(tmp_path: Path):
    """Verify setup file writing and .env file updating helpers."""
    config_file = tmp_path / "terminal-agent.config.yaml"
    config = TerminalAgentConfig()

    _save_provider_config(config, config_file, ProviderType.OPENAI, "gpt-4o")
    assert config_file.exists()
    assert "openai" in config_file.read_text(encoding="utf-8")

    env_file = tmp_path / ".env"
    _append_or_update_env_file(env_file, "OPENAI_API_KEY", "sk-test-key-12345")
    assert env_file.exists()
    assert "OPENAI_API_KEY=sk-test-key-12345" in env_file.read_text(encoding="utf-8")

    # Update existing key
    _append_or_update_env_file(env_file, "OPENAI_API_KEY", "sk-new-key-67890")
    assert "sk-new-key-67890" in env_file.read_text(encoding="utf-8")
