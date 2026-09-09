"""Interactive CLI setup command for configuring model providers."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, SYM_WARN, console
from terminal_agent.cli.ui import render_header
from terminal_agent.config.schema import ProviderConfig, ProviderType, TerminalAgentConfig
from terminal_agent.config.settings import load_config
from terminal_agent.providers.detector import OllamaStatus, detect_ollama, detect_all_providers
import yaml


def setup_command(
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Interactively configure the model provider (Ollama, OpenAI, Anthropic, Gemini)."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    config_file = target_dir / "terminal-agent.config.yaml"
    config = load_config(config_file)

    panel_text = (
        "[bold agent.accent]Terminal Agent Model Provider Setup[/bold agent.accent]\n"
        "[agent.muted]Configure your local or cloud LLM provider to start using Terminal Agent.[/agent.muted]"
    )
    console.print(Panel(panel_text, border_style="agent.border"))

    console.print("\n[agent.accent]Select a model provider:[/agent.accent]")
    console.print("  [bold]1.[/bold] Ollama (Local open-source models, Free, Private)")
    console.print("  [bold]2.[/bold] OpenAI (GPT-4o, GPT-4o-mini)")
    console.print("  [bold]3.[/bold] Anthropic Claude (Claude 3.5 Sonnet)")
    console.print("  [bold]4.[/bold] Google Gemini (Gemini 1.5 Pro/Flash)")
    console.print("  [bold]5.[/bold] Mock Provider (Deterministic Testing/Offline)")

    choice = Prompt.ask("\nChoose option", choices=["1", "2", "3", "4", "5"], default="1")

    if choice == "1":
        _setup_ollama(config, config_file, target_dir)
    elif choice == "2":
        _setup_cloud_provider(
            provider_type=ProviderType.OPENAI,
            provider_name="OpenAI",
            env_var_name="OPENAI_API_KEY",
            default_model="gpt-4o",
            config=config,
            config_file=config_file,
            target_dir=target_dir
        )
    elif choice == "3":
        _setup_cloud_provider(
            provider_type=ProviderType.ANTHROPIC,
            provider_name="Anthropic",
            env_var_name="ANTHROPIC_API_KEY",
            default_model="claude-3-5-sonnet-20241022",
            config=config,
            config_file=config_file,
            target_dir=target_dir
        )
    elif choice == "4":
        _setup_cloud_provider(
            provider_type=ProviderType.GEMINI,
            provider_name="Google Gemini",
            env_var_name="GEMINI_API_KEY",
            default_model="gemini-1.5-pro",
            config=config,
            config_file=config_file,
            target_dir=target_dir
        )
    elif choice == "5":
        _save_provider_config(config, config_file, ProviderType.MOCK, "mock-model")
        console.print(f"\n{SYM_CHECK} [agent.success]Configured Mock Provider for deterministic offline testing.[/agent.success]")


def _setup_ollama(config: TerminalAgentConfig, config_file: Path, target_dir: Path) -> None:
    """Setup and diagnostic flow for Ollama local provider."""
    console.print("\n[agent.accent]Checking local Ollama installation...[/agent.accent]")
    target_model = Prompt.ask("Enter target Ollama model name", default="qwen2.5-coder")
    
    ollama_res = detect_ollama(target_model=target_model)

    if ollama_res.status == OllamaStatus.OLLAMA_NOT_INSTALLED:
        console.print(f"\n{SYM_WARN} [agent.warning]Ollama executable was not found in your PATH.[/agent.warning]")
        console.print("[agent.muted]To install Ollama, visit:[/agent.muted] [bold cyan]https://ollama.com/download[/bold cyan]")
        console.print(f"\nAfter installing, start Ollama and run: [agent.accent]ollama pull {target_model}[/agent.accent]")
        
        save_anyway = Confirm.ask("Do you want to save Ollama as the configured provider anyway?", default=True)
        if save_anyway:
            _save_provider_config(config, config_file, ProviderType.OLLAMA, target_model)
            console.print(f"{SYM_CHECK} [agent.success]Saved Ollama configuration.[/agent.success]")
        return

    elif ollama_res.status == OllamaStatus.OLLAMA_NOT_RUNNING:
        console.print(f"\n{SYM_WARN} [agent.warning]Ollama is installed ({ollama_res.cli_path}), but the Ollama server is not running.[/agent.warning]")
        console.print("[agent.muted]Please start the Ollama application or run in a terminal:[/agent.muted]")
        console.print("  [bold agent.accent]ollama serve[/bold agent.accent]\n")
        
        _save_provider_config(config, config_file, ProviderType.OLLAMA, target_model)
        console.print(f"{SYM_CHECK} [agent.success]Saved Ollama configuration with model '{target_model}'.[/agent.success]")
        return

    elif ollama_res.status == OllamaStatus.OLLAMA_MODEL_MISSING:
        console.print(f"\n{SYM_WARN} [agent.warning]Ollama server is online, but model '{target_model}' is not installed locally.[/agent.warning]")
        if ollama_res.installed_models:
            console.print(f"[agent.muted]Currently installed models:[/agent.muted] {', '.join(ollama_res.installed_models)}")
        
        should_pull = Confirm.ask(f"Would you like to run 'ollama pull {target_model}' now?", default=False)
        if should_pull:
            console.print(f"\n[agent.accent]Pulling model '{target_model}' via Ollama CLI...[/agent.accent]")
            try:
                subprocess.run(["ollama", "pull", target_model], check=True)
                console.print(f"{SYM_CHECK} [agent.success]Successfully pulled model '{target_model}'![/agent.success]")
            except Exception as e:
                console.print(f"{SYM_CROSS} [agent.error]Failed to pull model: {e}[/agent.error]")
                console.print(f"You can pull it manually later with: [bold]ollama pull {target_model}[/bold]")
        else:
            console.print(f"[agent.muted]You can pull it manually with: [bold]ollama pull {target_model}[/bold][/agent.muted]")

        _save_provider_config(config, config_file, ProviderType.OLLAMA, target_model)
        console.print(f"\n{SYM_CHECK} [agent.success]Configured Ollama with model '{target_model}'.[/agent.success]")

    elif ollama_res.status == OllamaStatus.OLLAMA_READY:
        console.print(f"\n{SYM_CHECK} [agent.success]Ollama server is online and model '{target_model}' is ready to use.[/agent.success]")
        _save_provider_config(config, config_file, ProviderType.OLLAMA, target_model)
        console.print(f"{SYM_CHECK} [agent.success]Configured Ollama with model '{target_model}'.[/agent.success]")

    else:
        console.print(f"\n{SYM_CROSS} [agent.error]Ollama check returned error: {ollama_res.message}[/agent.error]")
        _save_provider_config(config, config_file, ProviderType.OLLAMA, target_model)


def _setup_cloud_provider(
    provider_type: ProviderType,
    provider_name: str,
    env_var_name: str,
    default_model: str,
    config: TerminalAgentConfig,
    config_file: Path,
    target_dir: Path
) -> None:
    """Setup flow for cloud API providers (OpenAI, Anthropic, Gemini)."""
    console.print(f"\n[agent.accent]Configuring {provider_name}...[/agent.accent]")
    
    # Check existing environment variable
    existing_key = os.environ.get(env_var_name)
    model = Prompt.ask("Model identifier", default=default_model)

    if existing_key and len(existing_key.strip()) > 5:
        masked = existing_key[:4] + "..." + existing_key[-4:] if len(existing_key) > 8 else "****"
        console.print(f"{SYM_CHECK} Found {env_var_name} in environment: [bold agent.muted]{masked}[/bold agent.muted]")
    else:
        console.print(f"[agent.muted]No {env_var_name} detected in your current shell environment.[/agent.muted]")
        api_key = typer.prompt(f"Enter your {provider_name} API Key (input will be hidden)", hide_input=True)
        
        if api_key and len(api_key.strip()) > 5:
            save_to_env = Confirm.ask(f"Save this key to local '.env' file in {target_dir.name}? (Excluded from git)", default=True)
            if save_to_env:
                env_file = target_dir / ".env"
                _append_or_update_env_file(env_file, env_var_name, api_key.strip())
                console.print(f"{SYM_CHECK} [agent.success]Saved {env_var_name} to {env_file.name}.[/agent.success]")
            else:
                console.print("[agent.muted]To set this manually in your shell, run:[/agent.muted]")
                console.print(f"  [bold]export {env_var_name}='your-api-key'[/bold] (Linux/macOS)")
                console.print(f"  [bold]$env:{env_var_name}='your-api-key'[/bold] (Windows PowerShell)")

    _save_provider_config(config, config_file, provider_type, model)
    console.print(f"\n{SYM_CHECK} [agent.success]Successfully configured {provider_name} (Model: {model}).[/agent.success]")
    console.print("[agent.muted]Next step: Run [bold]terminal-agent doctor[/bold] or start a task with [bold]terminal-agent run \"...\"[/bold][/agent.muted]")


def _append_or_update_env_file(env_file: Path, key: str, value: str) -> None:
    """Helper to safely write or update key-value in a local .env file."""
    lines: list[str] = []
    found = False
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}=") or line.strip().startswith(f"export {key}="):
                lines[i] = f"{key}={value}"
                found = True
                break

    if not found:
        lines.append(f"{key}={value}")

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_provider_config(
    config: TerminalAgentConfig,
    config_file: Path,
    provider_type: ProviderType,
    model: str
) -> None:
    """Persist non-secret provider preferences into terminal-agent.config.yaml."""
    config.provider.name = provider_type
    config.provider.model = model

    raw_data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_data = loaded
        except Exception:
            raw_data = {}

    if "provider" not in raw_data:
        raw_data["provider"] = {}

    raw_data["provider"]["name"] = provider_type.value
    raw_data["provider"]["model"] = model

    if not raw_data or len(raw_data) <= 1:
        raw_data = config.model_dump(mode="json")
        raw_data["provider"]["name"] = provider_type.value
        raw_data["provider"]["model"] = model
        if "api_key" in raw_data["provider"] and raw_data["provider"]["api_key"]:
            raw_data["provider"]["api_key"] = None

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(raw_data, f, sort_keys=False, indent=2)
