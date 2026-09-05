"""CLI resume command restoring and continuing an interrupted session."""

from pathlib import Path
from typing import Optional
import typer

from terminal_agent.agent.loop import AgentLoop
from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.cli.theme import SYM_CHECK, console
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
from terminal_agent.providers.factory import create_provider
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import VerificationStatus
from terminal_agent.telemetry.events import TelemetryLogger
from terminal_agent.tools.registry import ToolRegistry
from terminal_agent.verifier.engine import IndependentVerifier


def resume_command(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to resume (or latest if omitted)"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Resume an interrupted terminal agent session."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    session_mgr = SessionManager(target_dir)

    if session_id:
        state = session_mgr.load_session(session_id)
    else:
        state = session_mgr.get_latest_session()

    if not state:
        console.print(f"[agent.error]No resumable session found in {target_dir}.[/agent.error]")
        raise typer.Exit(1)

    console.print(f"\n[agent.accent]SESSION RESUMED: {state.session_id}[/agent.accent]")
    render_task_card(state.task_description, target_dir)

    if state.contract:
        render_contract_card(state.contract)
    if state.plan:
        render_plan(state.plan)

    console.print(f"[agent.muted]Completed steps: {len(state.completed_steps)}[/agent.muted]")
    console.print(f"[agent.muted]Modified files: {', '.join(state.modified_files) if state.modified_files else 'None'}[/agent.muted]")
    console.print(f"[agent.accent]Next: {state.next_step}[/agent.accent]\n")

    if state.current_status == VerificationStatus.VERIFIED:
        console.print("[agent.success]This session is already VERIFIED.[/agent.success]")
        if state.proof_of_done:
            render_proof_of_done(state.proof_of_done)
        return

    # Set up runtime to continue execution
    config = load_config(target_dir / "terminal-agent.config.yaml")
    secret_guard = SecretGuard(blocked_patterns=config.security.blocked_paths, working_dir=target_dir)
    security_enforcer = SecurityPolicyEnforcer(security_config=config.security, secret_guard=secret_guard)
    sandbox = LocalSandbox(working_dir=target_dir, default_timeout=config.sandbox.timeout_seconds, secret_guard=secret_guard)
    git_adapter = GitAdapter(target_dir)
    checkpoint_mgr = CheckpointManager(target_dir)
    context_engine = RepositoryContextEngine(target_dir, secret_guard=secret_guard)
    tool_registry = ToolRegistry(target_dir, sandbox, security_enforcer, git_adapter, checkpoint_mgr, secret_guard)
    verifier = IndependentVerifier(sandbox, git_adapter, config.verification, target_dir)
    provider = create_provider(config.provider)
    telemetry_logger = TelemetryLogger(state.session_id, working_dir=target_dir)

    def on_event(event_type: str, data):
        if event_type == "tool_completed":
            render_tool_event(
                tool_name=data.reason.split()[0] if data.reason else "tool",
                reason=data.reason,
                status="success" if data.success else "error",
                duration_ms=data.duration_ms
            )
        elif event_type == "verification_result":
            render_verification_result(data)
        elif event_type == "proof_of_done":
            render_proof_of_done(data, duration_seconds=state.metrics.execution_time_seconds)

    agent_loop = AgentLoop(
        session_state=state,
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

    agent_loop.run()

