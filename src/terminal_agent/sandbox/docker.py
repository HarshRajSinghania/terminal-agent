"""Docker container sandbox runner with volume isolation and network disablement."""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from terminal_agent.sandbox.base import ExecutionResult, Sandbox
from terminal_agent.security.secrets import SecretGuard


class DockerSandbox(Sandbox):
    """Executes commands inside an isolated Docker container with mounted workspace."""

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        image: str = "python:3.12-slim",
        network: str = "disabled",
        default_timeout: int = 60,
        secret_guard: Optional[SecretGuard] = None,
        max_memory_mb: int = 1024
    ):
        self.working_dir = (working_dir or Path.cwd()).resolve()
        self.image = image
        self.network = network
        self.default_timeout = default_timeout
        self.secret_guard = secret_guard or SecretGuard(working_dir=self.working_dir)
        self.max_memory_mb = max_memory_mb

    @classmethod
    def is_docker_available(cls) -> bool:
        """Check if Docker CLI is installed and daemon is reachable."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute command in docker container."""
        if not self.is_docker_available():
            return ExecutionResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr="Docker daemon is not available or not running.",
                duration_ms=0,
                timed_out=False
            )

        exec_timeout = timeout or self.default_timeout
        sanitized_env = self.secret_guard.sanitize_env(env)
        start_time = time.perf_counter()

        # Build docker run args
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.working_dir}:/workspace",
            "-w", "/workspace",
            f"--memory={self.max_memory_mb}m",
        ]

        if self.network == "disabled":
            docker_cmd.extend(["--network", "none"])

        for k, v in sanitized_env.items():
            if k in ("PATH", "HOME", "USER", "LANG"):
                continue
            docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.extend([self.image, "sh", "-c", command])

        timed_out = False
        stdout_text = ""
        stderr_text = ""
        exit_code = -1

        try:
            res = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=exec_timeout
            )
            stdout_text = res.stdout
            stderr_text = res.stderr
            exit_code = res.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = 124
            stderr_text = f"Docker command timed out after {exec_timeout} seconds."
        except Exception as e:
            exit_code = 1
            stderr_text = f"Docker execution error: {str(e)}"
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)

        return ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration_ms,
            timed_out=timed_out
        )

    def cleanup(self) -> None:
        """Docker containers run with --rm so they auto-cleanup."""
        pass

