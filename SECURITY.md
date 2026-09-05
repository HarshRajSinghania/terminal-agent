# Security Policy — Terminal Agent

Terminal Agent is an autonomous coding agent that executes commands and modifies code directly on developer environments and sandboxes. Safety is a first-class architectural pillar.

---

## 1. Threat Model & Sandboxing

Terminal Agent supports two execution environments:
- **Local Workspace Sandbox**: Commands run inside the designated workspace directory with strict timeouts, process tree termination, and environment variable sanitization.
- **Docker Sandbox**: Commands run in an isolated ephemeral Docker container (`--rm`, `--memory=1024m`, and `--network none` when network is disabled).

### Host Protection & Secret Redaction
Terminal Agent enforces automatic secret protection through `SecretGuard`. The following files and directories are strictly blocked from being read, written, or modified by the agent:
- `.env`, `.env.*`, `*.env`
- `*.pem`, `*.key`, `*.pfx`, `*.p12`
- `id_rsa*`, `id_ed25519*`, `id_dsa*`
- `.ssh/*`, `.aws/*`, `.gnupg/*`, `.netrc`

Any attempt by the agent or LLM tool to access paths matching these patterns or escaping the workspace root is blocked immediately.

---

## 2. Command Safety Classification

All commands dispatched by the agent are evaluated by `CommandClassifier` before execution and categorized into:

| Category | Description | Examples | Confirmation Default |
| :--- | :--- | :--- | :--- |
| **SAFE** | Read-only inspection, test execution, linters | `pytest`, `git status`, `git diff`, `cat`, `ls` | Auto-allowed |
| **WRITE** | Standard file and repository modifications | `mkdir`, `cp`, `git add`, `touch` | Auto-allowed |
| **DESTRUCTIVE** | Unrecoverable file or directory deletion | `rm -rf`, `del /s`, `format`, `dd` | Requires User Confirmation |
| **NETWORK** | External network transfers or repository push | `curl`, `wget`, `ssh`, `git push` | Requires User Confirmation |
| **PRIVILEGED** | Host elevation or system changes | `sudo`, `run-as`, `reg add`, `useradd` | Requires User Confirmation |

When interactive confirmation is disabled (e.g. headless CI runs), `DESTRUCTIVE` and `PRIVILEGED` commands are automatically rejected.

---

## 3. Sandboxing Untrusted Code

When working with untrusted repositories or third-party benchmarks:
1. Set `sandbox.mode: docker` in `terminal-agent.config.yaml`.
2. Set `security.network: disabled` to block outbound socket connections.
3. Review `git diff` before committing or running outside the sandbox.

---

## 4. Reporting a Vulnerability

If you discover a potential security vulnerability in Terminal Agent, please submit an advisory or contact the security team directly instead of opening a public issue.

