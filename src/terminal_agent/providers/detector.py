"""Model provider auto-detection, Ollama health checking, and smart provider resolution."""

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

from terminal_agent.config.schema import ProviderConfig, ProviderType, TerminalAgentConfig


class OllamaStatus(str, Enum):
    OLLAMA_NOT_INSTALLED = "OLLAMA_NOT_INSTALLED"
    OLLAMA_NOT_RUNNING = "OLLAMA_NOT_RUNNING"
    OLLAMA_READY = "OLLAMA_READY"
    OLLAMA_MODEL_MISSING = "OLLAMA_MODEL_MISSING"
    OLLAMA_ERROR = "OLLAMA_ERROR"


@dataclass
class OllamaDetectionResult:
    status: OllamaStatus
    installed: bool
    cli_path: Optional[str]
    server_reachable: bool
    base_url: str
    installed_models: List[str]
    target_model: str
    target_model_installed: bool
    message: str
    action_hint: Optional[str] = None


def detect_ollama(
    base_url: Optional[str] = None,
    target_model: str = "qwen2.5-coder",
    timeout_seconds: float = 3.0
) -> OllamaDetectionResult:
    """Detect Ollama installation, daemon reachability, and model availability."""
    url = (base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    cli_path = shutil.which("ollama")
    is_installed = bool(cli_path)

    # 1. Try connecting to Ollama REST API
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            res = client.get(f"{url}/api/tags")
            if res.status_code == 200:
                data = res.json()
                models_raw = data.get("models", [])
                installed_models: List[str] = []
                for m in models_raw:
                    name = m.get("name", "")
                    if name:
                        installed_models.append(name)

                # Check if target model exists in installed models
                # Handle variants like 'qwen2.5-coder:latest', 'qwen2.5-coder:7b'
                model_match = any(
                    target_model == m or
                    m.startswith(f"{target_model}:") or
                    target_model.split(":")[0] == m.split(":")[0]
                    for m in installed_models
                )

                if model_match:
                    return OllamaDetectionResult(
                        status=OllamaStatus.OLLAMA_READY,
                        installed=is_installed,
                        cli_path=cli_path,
                        server_reachable=True,
                        base_url=url,
                        installed_models=installed_models,
                        target_model=target_model,
                        target_model_installed=True,
                        message=f"Ollama is running with model '{target_model}' installed.",
                        action_hint=None
                    )
                else:
                    return OllamaDetectionResult(
                        status=OllamaStatus.OLLAMA_MODEL_MISSING,
                        installed=is_installed,
                        cli_path=cli_path,
                        server_reachable=True,
                        base_url=url,
                        installed_models=installed_models,
                        target_model=target_model,
                        target_model_installed=False,
                        message=f"Ollama server is running, but model '{target_model}' is not installed.",
                        action_hint=f"ollama pull {target_model}"
                    )
            else:
                return OllamaDetectionResult(
                    status=OllamaStatus.OLLAMA_ERROR,
                    installed=is_installed,
                    cli_path=cli_path,
                    server_reachable=True,
                    base_url=url,
                    installed_models=[],
                    target_model=target_model,
                    target_model_installed=False,
                    message=f"Ollama returned HTTP status {res.status_code}.",
                    action_hint=f"Check Ollama server logs at {url}"
                )

    except Exception as e:
        # Server connection failed
        if is_installed:
            return OllamaDetectionResult(
                status=OllamaStatus.OLLAMA_NOT_RUNNING,
                installed=True,
                cli_path=cli_path,
                server_reachable=False,
                base_url=url,
                installed_models=[],
                target_model=target_model,
                target_model_installed=False,
                message="Ollama CLI is installed, but the Ollama server is not running.",
                action_hint="Start Ollama application or run 'ollama serve'"
            )
        else:
            return OllamaDetectionResult(
                status=OllamaStatus.OLLAMA_NOT_INSTALLED,
                installed=False,
                cli_path=None,
                server_reachable=False,
                base_url=url,
                installed_models=[],
                target_model=target_model,
                target_model_installed=False,
                message="Ollama is not installed on this machine (Optional).",
                action_hint="Install Ollama from https://ollama.com/download"
            )


class ProviderStatus(str, Enum):
    READY = "READY"
    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass
class ProviderInfo:
    name: str
    display_name: str
    status: ProviderStatus
    is_usable: bool
    details: str
    configured_model: Optional[str] = None
    action_hint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def detect_all_providers(
    config: Optional[TerminalAgentConfig] = None,
    working_dir: Optional[Path] = None
) -> Dict[str, ProviderInfo]:
    """Discover the status and availability of all supported model providers."""
    results: Dict[str, ProviderInfo] = {}

    target_config = config or TerminalAgentConfig()
    ollama_target_model = target_config.provider.model if target_config.provider.name == ProviderType.OLLAMA else "qwen2.5-coder"
    ollama_url = target_config.provider.base_url

    # 1. Ollama Detection
    ollama_res = detect_ollama(base_url=ollama_url, target_model=ollama_target_model)
    if ollama_res.status == OllamaStatus.OLLAMA_READY:
        results["ollama"] = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            status=ProviderStatus.READY,
            is_usable=True,
            details=f"Ready (Model: {ollama_target_model})",
            configured_model=ollama_target_model,
            metadata={"detection": ollama_res}
        )
    elif ollama_res.status == OllamaStatus.OLLAMA_MODEL_MISSING:
        results["ollama"] = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details=f"Server online, model '{ollama_target_model}' missing",
            configured_model=ollama_target_model,
            action_hint=ollama_res.action_hint,
            metadata={"detection": ollama_res}
        )
    elif ollama_res.status == OllamaStatus.OLLAMA_NOT_RUNNING:
        results["ollama"] = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details="CLI installed, server not running",
            configured_model=ollama_target_model,
            action_hint=ollama_res.action_hint,
            metadata={"detection": ollama_res}
        )
    elif ollama_res.status == OllamaStatus.OLLAMA_NOT_INSTALLED:
        results["ollama"] = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details="Not installed (Optional local provider)",
            configured_model=ollama_target_model,
            action_hint=ollama_res.action_hint,
            metadata={"detection": ollama_res}
        )
    else:
        results["ollama"] = ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            status=ProviderStatus.ERROR,
            is_usable=False,
            details=ollama_res.message,
            configured_model=ollama_target_model,
            action_hint=ollama_res.action_hint,
            metadata={"detection": ollama_res}
        )

    # 2. OpenAI Detection
    openai_key = os.environ.get("OPENAI_API_KEY") or (target_config.provider.api_key if target_config.provider.name == ProviderType.OPENAI else None)
    openai_model = target_config.provider.model if target_config.provider.name == ProviderType.OPENAI else "gpt-4o"
    if openai_key and len(openai_key.strip()) > 5:
        results["openai"] = ProviderInfo(
            name="openai",
            display_name="OpenAI",
            status=ProviderStatus.READY,
            is_usable=True,
            details=f"API key configured (Model: {openai_model})",
            configured_model=openai_model
        )
    else:
        results["openai"] = ProviderInfo(
            name="openai",
            display_name="OpenAI",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details="OPENAI_API_KEY not set",
            configured_model=openai_model,
            action_hint="export OPENAI_API_KEY=sk-..."
        )

    # 3. Anthropic Detection
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or (target_config.provider.api_key if target_config.provider.name == ProviderType.ANTHROPIC else None)
    anthropic_model = target_config.provider.model if target_config.provider.name == ProviderType.ANTHROPIC else "claude-3-5-sonnet-20241022"
    if anthropic_key and len(anthropic_key.strip()) > 5:
        results["anthropic"] = ProviderInfo(
            name="anthropic",
            display_name="Anthropic",
            status=ProviderStatus.READY,
            is_usable=True,
            details=f"API key configured (Model: {anthropic_model})",
            configured_model=anthropic_model
        )
    else:
        results["anthropic"] = ProviderInfo(
            name="anthropic",
            display_name="Anthropic",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details="ANTHROPIC_API_KEY not set",
            configured_model=anthropic_model,
            action_hint="export ANTHROPIC_API_KEY=sk-ant-..."
        )

    # 4. Gemini Detection
    gemini_key = os.environ.get("GEMINI_API_KEY") or (target_config.provider.api_key if target_config.provider.name == ProviderType.GEMINI else None)
    gemini_model = target_config.provider.model if target_config.provider.name == ProviderType.GEMINI else "gemini-1.5-pro"
    if gemini_key and len(gemini_key.strip()) > 5:
        results["gemini"] = ProviderInfo(
            name="gemini",
            display_name="Gemini",
            status=ProviderStatus.READY,
            is_usable=True,
            details=f"API key configured (Model: {gemini_model})",
            configured_model=gemini_model
        )
    else:
        results["gemini"] = ProviderInfo(
            name="gemini",
            display_name="Gemini",
            status=ProviderStatus.NOT_CONFIGURED,
            is_usable=False,
            details="GEMINI_API_KEY not set",
            configured_model=gemini_model,
            action_hint="export GEMINI_API_KEY=AIzaSy..."
        )

    # 5. Mock Provider (Always available for testing)
    results["mock"] = ProviderInfo(
        name="mock",
        display_name="Mock Provider",
        status=ProviderStatus.READY,
        is_usable=True,
        details="Deterministic testing provider",
        configured_model="mock-model"
    )

    return results


def resolve_active_provider(
    config: TerminalAgentConfig,
    explicit_provider: Optional[str] = None,
    explicit_model: Optional[str] = None,
    working_dir: Optional[Path] = None
) -> Tuple[ProviderConfig, ProviderInfo]:
    """
    Smart resolution of the active provider following the fallback precedence:
    1. Explicit CLI argument (--provider)
    2. Explicit environment variable (TERMINAL_AGENT_PROVIDER)
    3. Project configuration file (if provider.name is explicitly set to non-default or mock)
    4. Local ready Ollama provider (if Ollama is running and has model)
    5. Configured cloud provider (OpenAI -> Anthropic -> Gemini)
    6. Default / Mock provider fallback with usability state.
    """
    all_providers = detect_all_providers(config=config, working_dir=working_dir)

    # 1. Explicit override
    if explicit_provider:
        prov_key = explicit_provider.lower()
        prov_info = all_providers.get(prov_key)
        target_model = explicit_model or (prov_info.configured_model if prov_info else config.provider.model)
        resolved_cfg = ProviderConfig(
            name=ProviderType(prov_key) if prov_key in [p.value for p in ProviderType] else ProviderType.CUSTOM,
            model=target_model or "default",
            base_url=config.provider.base_url,
            api_key=config.provider.api_key
        )
        info = prov_info or ProviderInfo(
            name=prov_key,
            display_name=prov_key.capitalize(),
            status=ProviderStatus.CONFIGURED,
            is_usable=True,
            details=f"Explicitly requested provider '{prov_key}'",
            configured_model=target_model
        )
        return resolved_cfg, info

    # 2. Environment variable override
    env_prov = os.environ.get("TERMINAL_AGENT_PROVIDER", "").lower()
    if env_prov and env_prov in all_providers:
        prov_info = all_providers[env_prov]
        target_model = os.environ.get("TERMINAL_AGENT_MODEL") or prov_info.configured_model or config.provider.model
        resolved_cfg = ProviderConfig(
            name=ProviderType(env_prov),
            model=target_model,
            base_url=config.provider.base_url,
            api_key=config.provider.api_key
        )
        return resolved_cfg, prov_info

    # 3. Config file specified provider (if configured)
    cfg_name = config.provider.name.value if hasattr(config.provider.name, "value") else str(config.provider.name)
    if cfg_name in all_providers and cfg_name != "mock":
        prov_info = all_providers[cfg_name]
        return config.provider, prov_info

    # 4. Check if local Ollama is ready
    if all_providers["ollama"].is_usable:
        ollama_cfg = ProviderConfig(
            name=ProviderType.OLLAMA,
            model=all_providers["ollama"].configured_model or "qwen2.5-coder",
            base_url=config.provider.base_url
        )
        return ollama_cfg, all_providers["ollama"]

    # 5. Check if any cloud provider has API key configured
    for cloud_name in ["openai", "anthropic", "gemini"]:
        if all_providers[cloud_name].is_usable:
            cloud_cfg = ProviderConfig(
                name=ProviderType(cloud_name),
                model=all_providers[cloud_name].configured_model or "default",
                base_url=config.provider.base_url
            )
            return cloud_cfg, all_providers[cloud_name]

    # 6. Fallback to mock provider or unconfigured state
    if cfg_name == "mock":
        return config.provider, all_providers["mock"]

    # Return default config with unconfigured notice
    unconfigured_info = ProviderInfo(
        name="none",
        display_name="No Provider Configured",
        status=ProviderStatus.NOT_CONFIGURED,
        is_usable=False,
        details="No usable local Ollama instance or cloud API key detected.",
        action_hint="terminal-agent setup"
    )
    return config.provider, unconfigured_info
