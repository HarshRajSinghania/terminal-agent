"""Data models for Task Contracts, Session State, Checkpoints, and Verification."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return timezone-aware current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    DONE = "DONE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class FailureCategory(str, Enum):
    WRONG_SOLUTION = "wrong_solution"
    TEST_FAILURE = "test_failure"
    SYNTAX_ERROR = "syntax_error"
    DEPENDENCY_ERROR = "dependency_error"
    COMMAND_FAILURE = "command_failure"
    TIMEOUT = "timeout"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    CONTEXT_OVERFLOW = "context_overflow"
    TOOL_ERROR = "tool_error"
    INCOMPLETE_TASK = "incomplete_task"
    UNKNOWN = "unknown"


class TaskContract(BaseModel):
    task_id: str = Field(description="Unique task identifier")
    task_description: str = Field(description="Raw user task description")
    goal: str = Field(description="Crisp statement of the final desired state")
    constraints: List[str] = Field(
        default_factory=list,
        description="Explicit constraints (e.g. do not modify tests, preserve public API)"
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Measurable conditions required for completion"
    )
    allowed_files: Optional[List[str]] = Field(
        default=None,
        description="Explicit file path whitelist if constrained"
    )
    verification_commands: List[str] = Field(
        default_factory=lambda: ["pytest"],
        description="Commands to execute to verify success criteria"
    )


class StepAction(BaseModel):
    step_number: int
    timestamp: str = Field(default_factory=utc_now_iso)
    action_type: str = Field(description="Type: tool_call, plan_update, verify, repair")
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    reason: str = Field(default="", description="Explainability reason for taking this action")
    output: Optional[str] = None
    status: str = Field(default="success", description="success | error | pending")
    duration_ms: Optional[int] = None


class CheckpointSnapshot(BaseModel):
    checkpoint_id: str
    name: str
    created_at: str = Field(default_factory=utc_now_iso)
    step_number: int
    git_commit: Optional[str] = None
    modified_files: List[str] = Field(default_factory=list)
    file_contents: Dict[str, str] = Field(
        default_factory=dict,
        description="Snapshot of tracked file relative paths to full content"
    )


class FailureRecord(BaseModel):
    step_number: int
    timestamp: str = Field(default_factory=utc_now_iso)
    failure_category: FailureCategory
    raw_output: str
    root_cause_hypothesis: str
    recovery_action: str
    recovery_result: Optional[str] = None


class AssertionResult(BaseModel):
    name: str
    passed: bool
    message: str


class VerificationResult(BaseModel):
    status: VerificationStatus = VerificationStatus.PENDING
    timestamp: str = Field(default_factory=utc_now_iso)
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_output: str = ""
    lint_passed: bool = True
    lint_output: Optional[str] = None
    files_changed_count: int = 0
    files_changed: List[str] = Field(default_factory=list)
    unintended_files_count: int = 0
    unintended_files: List[str] = Field(default_factory=list)
    assertions: List[AssertionResult] = Field(default_factory=list)
    passed_all: bool = False
    details: str = ""


class SessionMetrics(BaseModel):
    start_time: str = Field(default_factory=utc_now_iso)
    end_time: Optional[str] = None
    execution_time_seconds: float = 0.0
    tool_calls: int = 0
    commands_run: int = 0
    retries_attempted: int = 0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    files_changed: int = 0
    verification_status: str = "PENDING"
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class PlanItem(BaseModel):
    id: int
    description: str
    status: str = Field(default="TODO", description="TODO | IN_PROGRESS | COMPLETED | FAILED | SKIPPED")


class SessionState(BaseModel):
    session_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    working_dir: str
    task_description: str
    contract: Optional[TaskContract] = None
    plan: List[PlanItem] = Field(default_factory=list)
    completed_steps: List[StepAction] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    checkpoints: List[CheckpointSnapshot] = Field(default_factory=list)
    failures: List[FailureRecord] = Field(default_factory=list)
    last_verification: Optional[VerificationResult] = None
    current_status: VerificationStatus = VerificationStatus.PENDING
    next_step: str = "Initialize repository inspection"
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)
    proof_of_done: Optional[Dict[str, Any]] = None
