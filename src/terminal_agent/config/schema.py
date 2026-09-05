"""Configuration schemas for Terminal Agent."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SandboxMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"


class ProviderType(str, Enum):
    MOCK = "mock"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    CUSTOM = "custom"


class CommandCategory(str, Enum):
    SAFE = "safe"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    NETWORK = "network"
    PRIVILEGED = "privileged"


class AgentConfig(BaseModel):
    max_steps: int = Field(default=40, description="Maximum steps allowed per task execution")
    max_retries: int = Field(default=3, description="Maximum repair retries on verification failure")
    timeout_seconds: int = Field(default=600, description="Overall task execution timeout in seconds")
    token_budget: int = Field(default=128000, description="Maximum token budget for context")


class SandboxConfig(BaseModel):
    mode: SandboxMode = Field(default=SandboxMode.LOCAL, description="Sandbox isolation mode (local or docker)")
    image: str = Field(default="python:3.12-slim", description="Docker image if docker mode is enabled")
    timeout_seconds: int = Field(default=60, description="Per-command timeout in seconds")
    network: str = Field(default="disabled", description="Network access policy: 'disabled' or 'enabled'")
    max_memory_mb: int = Field(default=1024, description="Memory limit for docker sandbox in MB")


class DiffConstraints(BaseModel):
    max_files_changed: int = Field(default=10, description="Maximum allowed modified files in diff")
    allow_untracked_files: bool = Field(default=True, description="Whether new files are permitted")


class VerificationConfig(BaseModel):
    tests: List[str] = Field(default_factory=lambda: ["pytest"], description="Test commands to execute for verification")
    lint: List[str] = Field(default_factory=list, description="Lint/static check commands")
    assertions: List[str] = Field(
        default_factory=lambda: ["no_test_files_modified", "api_contract_preserved"],
        description="Verification contract assertion checks"
    )
    diff: DiffConstraints = Field(default_factory=DiffConstraints, description="Git diff constraints")
    auto_rollback_on_failure: bool = Field(default=False, description="Whether to rollback git changes on failure")


class SecurityConfig(BaseModel):
    network: str = Field(default="disabled", description="Global network policy")
    require_confirmation_for: List[CommandCategory] = Field(
        default_factory=lambda: [
            CommandCategory.DESTRUCTIVE,
            CommandCategory.PRIVILEGED,
            CommandCategory.NETWORK
        ],
        description="Command categories that require explicit user confirmation"
    )
    blocked_paths: List[str] = Field(
        default_factory=lambda: [
            ".env",
            ".env.*",
            "**/*.pem",
            "**/*.key",
            "**/.ssh/*",
            "**/.aws/*",
            "**/id_rsa*",
            "**/secrets.*"
        ],
        description="File patterns blocked from read/write to protect host secrets"
    )


class ProviderConfig(BaseModel):
    name: ProviderType = Field(default=ProviderType.MOCK, description="Model provider name")
    model: str = Field(default="mock-model", description="Model identifier")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL if needed")
    api_key: Optional[str] = Field(default=None, description="API key or retrieved via environment variable")
    temperature: float = Field(default=0.2, description="Sampling temperature")


class TerminalAgentConfig(BaseModel):
    agent: AgentConfig = Field(default_factory=AgentConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)

