"""Metrics aggregation for Agent sessions."""

from typing import Optional
from terminal_agent.session.models import SessionMetrics, SessionState, VerificationStatus


class MetricsCollector:
    """Calculates and updates session metrics."""

    @staticmethod
    def calculate_metrics(state: SessionState) -> SessionMetrics:
        """Derive real metrics from session state and events."""
        m = state.metrics

        # Count tool calls and commands
        tool_count = 0
        command_count = 0
        for step in state.completed_steps:
            if step.tool_name:
                tool_count += 1
                if step.tool_name in ("run_command", "run_tests"):
                    command_count += 1

        m.tool_calls = tool_count
        m.commands_run = command_count
        m.retries_attempted = len(state.failures)
        m.files_changed = len(state.modified_files)

        if state.last_verification:
            m.verification_status = state.last_verification.status.value
            m.tests_passed = state.last_verification.tests_passed
            m.tests_failed = state.last_verification.tests_failed
            m.tests_run = state.last_verification.tests_run
        else:
            m.verification_status = state.current_status.value

        return m

