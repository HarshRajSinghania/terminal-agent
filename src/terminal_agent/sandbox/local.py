"""Local subprocess execution sandbox with timeout, process cleanup, and environment sanitization."""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional
import psutil

from terminal_agent.sandbox.base import ExecutionResult, Sandbox
from terminal_agent.security.secrets import SecretGuard


class LocalSandbox(Sandbox):
    """Executes commands on local machine within controlled workspace boundaries."""

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        default_timeout: int = 60,
        secret_guard: Optional[SecretGuard] = None
    ):
        self.working_dir = (working_dir or Path.cwd()).resolve()
        self.default_timeout = default_timeout
        self.secret_guard = secret_guard or SecretGuard(working_dir=self.working_dir)

    def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute command synchronously with strict timeout and process tree killing."""
        exec_cwd = (cwd or self.working_dir).resolve()
        exec_timeout = timeout or self.default_timeout
        sanitized_env = self.secret_guard.sanitize_env(env)

        # Ensure cwd is in PYTHONPATH so local modules can be imported across all platforms
        existing_pythonpath = sanitized_env.get("PYTHONPATH", "")
        if existing_pythonpath:
            sanitized_env["PYTHONPATH"] = f"{str(exec_cwd)}{os.pathsep}{existing_pythonpath}"
        else:
            sanitized_env["PYTHONPATH"] = str(exec_cwd)

        start_time = time.perf_counter()
        timed_out = False
        stdout_text = ""
        stderr_text = ""
        exit_code = -1

        # Use shell execution
        # On Windows, use shell=True; on Unix, shell=True
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = None
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(exec_cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=sanitized_env,
                creationflags=creationflags
            )

            stdout_text, stderr_text = process.communicate(timeout=exec_timeout)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = 124
            stderr_text = f"Command timed out after {exec_timeout} seconds."
            self._kill_process_tree(process)
            try:
                if process:
                    out, err = process.communicate(timeout=2)
                    stdout_text += (out or "")
                    stderr_text += f"\n{err or ''}"
            except Exception:
                pass
        except Exception as e:
            exit_code = 1
            stderr_text = f"Execution error: {str(e)}"
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)

        return ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_text or "",
            stderr=stderr_text or "",
            duration_ms=duration_ms,
            timed_out=timed_out
        )

    def _kill_process_tree(self, proc: Optional[subprocess.Popen]) -> None:
        """Kill process and all its children safely."""
        if not proc or proc.poll() is not None:
            return
        try:
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def cleanup(self) -> None:
        """No persistent daemon resources for local sandbox."""
        pass

