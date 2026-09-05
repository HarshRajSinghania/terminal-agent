"""Core bounded autonomous agent loop: Observe -> Plan -> Act -> Verify -> Repair -> Verify."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.config.schema import TerminalAgentConfig
from terminal_agent.context.engine import RepositoryContextEngine
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.planner.contract import TaskContractGenerator
from terminal_agent.planner.planner import ExecutionPlanner
from terminal_agent.providers.base import LLMMessage, LLMResponse, LLMToolCall, ModelProvider
from terminal_agent.recovery.classifier import FailureClassifier
from terminal_agent.recovery.strategies import RecoveryEngine
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import (
    FailureCategory,
    PlanItem,
    SessionState,
    StepAction,
    TaskContract,
    VerificationResult,
    VerificationStatus,
)
from terminal_agent.telemetry.events import TelemetryLogger
from terminal_agent.telemetry.metrics import MetricsCollector
from terminal_agent.tools.registry import ToolRegistry
from terminal_agent.verifier.engine import IndependentVerifier


SYSTEM_PROMPT = """You are TERMINAL AGENT, an autonomous verify-first terminal coding agent.
Tagline: Build. Verify. Ship.

CORE PRINCIPLE:
You do NOT simply modify code and claim completion.
A task is only complete when independently verified by running tests, validating contract assertions, and inspecting git diffs.

RULES:
1. Every tool call MUST include a clear, concise 'reason' explaining what you are doing and why.
2. Read and analyze files before making changes.
3. Keep changes minimal and focused directly on the user's task contract.
4. When you believe your changes are in place, run verification tests.
5. If tests fail, analyze the error trace, determine root cause, and apply targeted repairs.
6. Never modify test files unless the user explicitly requested test changes.
"""


class AgentLoop:
    """Orchestrates the autonomous verify-first coding cycle."""

    def __init__(
        self,
        session_state: SessionState,
        config: TerminalAgentConfig,
        provider: ModelProvider,
        tool_registry: ToolRegistry,
        verifier: IndependentVerifier,
        context_engine: RepositoryContextEngine,
        checkpoint_manager: CheckpointManager,
        session_manager: SessionManager,
        telemetry_logger: TelemetryLogger,
        step_callback: Optional[Callable[[str, Any], None]] = None
    ):
        self.state = session_state
        self.config = config
        self.provider = provider
        self.tools = tool_registry
        self.verifier = verifier
        self.context = context_engine
        self.checkpoints = checkpoint_manager
        self.session_mgr = session_manager
        self.telemetry = telemetry_logger
        self.step_callback = step_callback or (lambda event, data: None)
        self.start_time = time.time()

    def _notify(self, event_type: str, data: Any = None) -> None:
        """Send UI update notification."""
        try:
            self.step_callback(event_type, data)
        except Exception:
            pass

    def run(self) -> SessionState:
        """Execute the bounded autonomous loop."""
        self._notify("start", self.state)

        # 1. OBSERVE & INITIALIZE CONTRACT
        if not self.state.contract:
            self._notify("observe_start", "Inspecting repository...")
            contract = TaskContractGenerator.generate_from_description(
                task_description=self.state.task_description,
                verification_commands=self.config.verification.tests
            )
            self.state.contract = contract
            self.state.plan = ExecutionPlanner.create_initial_plan(contract)
            self.session_mgr.save_session(self.state)
            self._notify("contract_ready", contract)

        # 2. CREATE BASELINE CHECKPOINT
        if not self.state.checkpoints:
            self._notify("checkpoint_creating", "Creating baseline checkpoint...")
            baseline_chk = self.checkpoints.create_checkpoint(name="baseline_before_changes")
            self.state.checkpoints.append(baseline_chk)
            self.session_mgr.save_session(self.state)
            self._notify("checkpoint_created", baseline_chk)

        # 3. BUILD INITIAL CONTEXT & MESSAGES
        repo_context = self.context.build_initial_context(
            task_description=self.state.task_description,
            contract=self.state.contract
        )

        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=(
                    f"TASK CONTRACT:\n"
                    f"Goal: {self.state.contract.goal}\n"
                    f"Constraints:\n" + "\n".join(f"- {c}" for c in self.state.contract.constraints) + "\n\n"
                    f"Success Criteria:\n" + "\n".join(f"- {sc}" for sc in self.state.contract.success_criteria) + "\n\n"
                    f"REPOSITORY CONTEXT:\n{repo_context}\n\n"
                    f"Please begin by inspecting the relevant code and formulating your changes."
                )
            )
        ]

        # Replay completed steps if resuming
        for past_step in self.state.completed_steps:
            if past_step.tool_name:
                messages.append(
                    LLMMessage(
                        role="assistant",
                        tool_calls=[
                            LLMToolCall(
                                id=f"call_{past_step.step_number}",
                                name=past_step.tool_name,
                                arguments=past_step.tool_args or {}
                            )
                        ]
                    )
                )
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=past_step.tool_name,
                        tool_call_id=f"call_{past_step.step_number}",
                        content=past_step.output or ""
                    )
                )

        step_count = len(self.state.completed_steps)
        retry_count = len(self.state.failures)
        max_steps = self.config.agent.max_steps
        max_retries = self.config.agent.max_retries
        timeout_sec = self.config.agent.timeout_seconds

        # 4. BOUNDED AGENT LOOP
        while step_count < max_steps:
            # Check overall timeout
            elapsed = time.time() - self.start_time
            if elapsed > timeout_sec:
                self.state.current_status = VerificationStatus.FAILED
                self.session_mgr.record_step(
                    self.state,
                    action_type="timeout",
                    reason=f"Task timed out after {elapsed:.1f} seconds.",
                    status="error"
                )
                self._notify("timeout", f"Execution exceeded {timeout_sec}s limit.")
                break

            step_count += 1
            self.state.next_step = f"Executing step {step_count}..."
            self._notify("step_start", {"step": step_count, "retries": retry_count})

            # Query Model Provider
            tool_schemas = self.tools.get_schemas()
            try:
                response: LLMResponse = self.provider.generate(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=self.config.provider.temperature
                )
            except Exception as e:
                self.session_mgr.record_step(
                    self.state,
                    action_type="provider_error",
                    reason=f"Model provider error: {e}",
                    status="error"
                )
                self._notify("error", f"Model provider failed: {e}")
                break

            # Handle model message and tool calls
            if response.content:
                self._notify("agent_thought", response.content)

            if not response.tool_calls:
                # Model stopped or claims completion without tool calls -> Trigger Independent Verification
                self._notify("verification_triggered", "Model requested verification / completed actions.")
                v_result = self.verifier.verify(contract=self.state.contract)
                self.session_mgr.record_verification(self.state, v_result)
                self._notify("verification_result", v_result)

                if v_result.status == VerificationStatus.VERIFIED:
                    self._finalize_success(v_result)
                    break
                else:
                    # Verification failed -> enter repair logic
                    retry_count += 1
                    if retry_count > max_retries:
                        self.state.current_status = VerificationStatus.FAILED
                        self._notify("max_retries_exceeded", f"Failed verification after {max_retries} repair retries.")
                        break

                    # Classify failure & formulate repair
                    cat, cat_reason = FailureClassifier.classify(v_result.test_output)
                    hypothesis, repair_action = RecoveryEngine.analyze_and_plan_recovery(cat, v_result.test_output, self.state)
                    failure_record = self.session_mgr.record_failure(
                        self.state,
                        category=cat,
                        raw_output=v_result.test_output,
                        root_cause_hypothesis=hypothesis,
                        recovery_action=repair_action
                    )
                    self._notify("repair_plan", failure_record)

                    # Append failure diagnostics to conversation
                    messages.append(
                        LLMMessage(
                            role="user",
                            content=(
                                f"INDEPENDENT VERIFICATION FAILED (Status: {v_result.status.value})\n"
                                f"Test Failures: {v_result.tests_failed}/{v_result.tests_run}\n"
                                f"Primary Failure Category: {cat.value}\n"
                                f"Root Cause Hypothesis: {hypothesis}\n"
                                f"Recommended Repair: {repair_action}\n\n"
                                f"Test Output Trace:\n{v_result.test_output[-2000:]}\n\n"
                                f"Please repair the issue in the target files and re-test."
                            )
                        )
                    )
                    continue

            # Execute tool calls
            for tc in response.tool_calls:
                tool_name = tc.name
                tool_args = tc.arguments or {}
                reason = str(tool_args.get("reason", response.content or "Executing tool action"))

                self._notify("tool_executing", {"tool": tool_name, "args": tool_args, "reason": reason})

                tool_result = self.tools.execute(tool_name, tool_args, reason=reason)
                
                # Track modified files
                if tool_name in ("write_file", "edit_file") and tool_result.success:
                    p = tool_args.get("path")
                    if p and p not in self.state.modified_files:
                        self.state.modified_files.append(p)

                # Record step and telemetry
                self.session_mgr.record_step(
                    self.state,
                    action_type="tool_call",
                    tool_name=tool_name,
                    tool_args=tool_args,
                    reason=reason,
                    output=tool_result.output if tool_result.success else tool_result.error,
                    status="success" if tool_result.success else "error",
                    duration_ms=tool_result.duration_ms
                )

                self.telemetry.log_event(
                    step=step_count,
                    event_type="tool_call",
                    tool=tool_name,
                    reason=reason,
                    duration_ms=tool_result.duration_ms,
                    status="success" if tool_result.success else "error",
                    data=tool_args
                )

                self._notify("tool_completed", tool_result)

                # Append tool exchange to LLM history
                messages.append(
                    LLMMessage(
                        role="assistant",
                        tool_calls=[tc]
                    )
                )
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=tool_name,
                        tool_call_id=tc.id,
                        content=tool_result.output if tool_result.success else f"ERROR: {tool_result.error}"
                    )
                )

        # End of loop: update final metrics
        MetricsCollector.calculate_metrics(self.state)
        self.session_mgr.save_session(self.state)
        self._notify("finish", self.state)
        return self.state

    def _finalize_success(self, v_result: VerificationResult) -> None:
        """Mark session as VERIFIED and synthesize final Proof of Done."""
        self.state.current_status = VerificationStatus.VERIFIED
        diff_stats = self.verifier.git_adapter.get_diff_stats()
        
        # Build structured Proof of Done
        pod = {
            "session_id": self.state.session_id,
            "task": self.state.task_description,
            "result": "VERIFIED ✓",
            "tests_passed": f"{v_result.tests_passed}/{v_result.tests_run}",
            "lint": "PASS" if v_result.lint_passed else "FAIL",
            "files_changed_count": len(self.state.modified_files),
            "files_changed": self.state.modified_files,
            "unintended_files_count": v_result.unintended_files_count,
            "retries_count": len(self.state.failures),
            "git_diff_reviewed": True,
            "success_criteria_passed": f"{sum(1 for a in v_result.assertions if a.passed)}/{len(v_result.assertions)}",
            "summary": {
                "what_changed": f"Modified files: {', '.join(self.state.modified_files) if self.state.modified_files else 'None'}",
                "why_it_changed": self.state.contract.goal if self.state.contract else "Fulfilled task requirements",
                "what_was_verified": f"Independent test suite ({v_result.tests_passed} tests passed)",
                "remaining_limitations": "None detected under verified test suite."
            }
        }
        self.state.proof_of_done = pod
        self.session_mgr.save_session(self.state)
        self._notify("proof_of_done", pod)

