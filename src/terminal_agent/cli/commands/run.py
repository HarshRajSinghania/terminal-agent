"""CLI run command executing autonomous coding tasks."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import typer
import yaml

from terminal_agent.agent.loop import AgentLoop
from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, console
from terminal_agent.cli.ui import (
    render_contract_card,
    render_header,
    render_plan,
    render_proof_of_done,
    render_task_card,
    render_tool_event,
    render_verification_result,
)
from terminal_agent.config.settings import load_config
from terminal_agent.context.engine import RepositoryContextEngine
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.planner.contract import TaskContractGenerator
from terminal_agent.providers.detector import ProviderStatus, resolve_active_provider
from terminal_agent.providers.factory import create_provider
from terminal_agent.sandbox.docker import DockerSandbox
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import VerificationStatus
from terminal_agent.telemetry.events import TelemetryLogger
from terminal_agent.tools.registry import ToolRegistry
from terminal_agent.verifier.engine import IndependentVerifier


def run_command(
    task: Optional[str] = typer.Argument(None, help="The coding task description to execute autonomously"),
    task_file: Optional[Path] = typer.Option(None, "--task", "-t", help="Path to declarative task YAML file"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
    provider_name: Optional[str] = typer.Option(None, "--provider", "-p", help="Override model provider"),
    model_name: Optional[str] = typer.Option(None, "--model", "-m", help="Override model name"),
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Auto-approve confirmation prompts"),
) -> None:
    """Execute an autonomous verify-first coding session."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()

    task_desc = task
    if task_file and task_file.exists():
        try:
            content = yaml.safe_load(task_file.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                task_desc = content.get("prompt") or content.get("task") or str(content)
            else:
                task_desc = str(content)
        except Exception as e:
            console.print(f"[agent.error]Error reading task file: {e}[/agent.error]")
            raise typer.Exit(1)

    if not task_desc:
        task_desc = typer.prompt("Describe the coding task")

    render_task_card(task_desc, target_dir)

    # Load configuration & resolve active provider
    config = load_config(target_dir / "terminal-agent.config.yaml")
    resolved_prov_cfg, prov_info = resolve_active_provider(
        config=config,
        explicit_provider=provider_name,
        explicit_model=model_name,
        working_dir=target_dir
    )
    config.provider = resolved_prov_cfg

    # Initialize subsystems
    secret_guard = SecretGuard(blocked_patterns=config.security.blocked_paths, working_dir=target_dir)

    def confirmation_cb(cmd: str, category, reason: str) -> bool:
        if auto_approve:
            return True
        console.print(f"\n[agent.warning]Security Warning: {category.value.upper()} command[/agent.warning]")
        console.print(f"Command: [agent.accent]{cmd}[/agent.accent]")
        console.print(f"Reason:  [agent.muted]{reason}[/agent.muted]")
        return typer.confirm("Allow execution?")

    security_enforcer = SecurityPolicyEnforcer(
        security_config=config.security,
        secret_guard=secret_guard,
        confirmation_callback=confirmation_cb
    )

    if config.sandbox.mode == "docker" and DockerSandbox.is_docker_available():
        sandbox = DockerSandbox(
            working_dir=target_dir,
            image=config.sandbox.image,
            network=config.sandbox.network,
            timeout_seconds=config.sandbox.timeout_seconds,
            secret_guard=secret_guard
        )
    else:
        sandbox = LocalSandbox(
            working_dir=target_dir,
            default_timeout=config.sandbox.timeout_seconds,
            secret_guard=secret_guard
        )

    git_adapter = GitAdapter(target_dir)
    checkpoint_mgr = CheckpointManager(target_dir)
    session_mgr = SessionManager(target_dir)
    context_engine = RepositoryContextEngine(target_dir, secret_guard=secret_guard)

    tool_registry = ToolRegistry(
        working_dir=target_dir,
        sandbox=sandbox,
        security_enforcer=security_enforcer,
        git_adapter=git_adapter,
        checkpoint_manager=checkpoint_mgr,
        secret_guard=secret_guard
    )

    verifier = IndependentVerifier(
        sandbox=sandbox,
        git_adapter=git_adapter,
        config=config.verification,
        working_dir=target_dir
    )

    # Initialize Provider
    provider = create_provider(config.provider)
    health_ok, health_msg = provider.check_health()
    if not health_ok and config.provider.name.value != "mock":
        console.print(f"[agent.warning]Provider Notice ({prov_info.display_name}): {health_msg}[/agent.warning]")
        if prov_info.action_hint:
            console.print(f"[agent.accent]Suggested Action: {prov_info.action_hint}[/agent.accent]")
        if not prov_info.is_usable:
            console.print("\n[agent.muted]To configure or switch model providers, run: [bold]terminal-agent setup[/bold][/agent.muted]\n")

    # Create Session
    session_state = session_mgr.create_session(task_description=task_desc)
    telemetry_logger = TelemetryLogger(session_state.session_id, working_dir=target_dir)

    # Step callback for live display
    def on_event(event_type: str, data: Any):
        if event_type == "contract_ready":
            render_contract_card(data)
            if session_state.plan:
                render_plan(session_state.plan)
        elif event_type == "checkpoint_created":
            console.print(f"{SYM_CHECK} [agent.muted]Created baseline checkpoint '{data.checkpoint_id}'[/agent.muted]")
        elif event_type == "tool_completed":
            render_tool_event(
                tool_name=data.reason.split()[0] if data.reason else "tool",
                reason=data.reason,
                status="success" if data.success else "error",
                duration_ms=data.duration_ms
            )
        elif event_type == "verification_result":
            render_verification_result(data)
        elif event_type == "repair_plan":
            console.print(f"[agent.warning]Recovery Plan: Category '{data.failure_category.value}' -> {data.recovery_action}[/agent.warning]")
        elif event_type == "proof_of_done":
            render_proof_of_done(data, duration_seconds=session_state.metrics.execution_time_seconds)

    agent_loop = AgentLoop(
        session_state=session_state,
        config=config,
        provider=provider,
        tool_registry=tool_registry,
        verifier=verifier,
        context_engine=context_engine,
        checkpoint_manager=checkpoint_mgr,
        session_manager=session_mgr,
        telemetry_logger=telemetry_logger,
        step_callback=on_event
    )

    # Run Loop
    final_state = agent_loop.run()

    if final_state.current_status == VerificationStatus.VERIFIED:
        console.print(f"\n[agent.success]Task successfully VERIFIED. Session: {final_state.session_id}[/agent.success]")
    else:
        console.print(f"\n[agent.error]Task concluded with status: {final_state.current_status.value}[/agent.error]")
