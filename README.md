# Terminal Agent

> **Build. Verify. Ship.**
> An autonomous terminal-based coding agent designed around verifiable software changes.

---

## What is Terminal Agent?

Terminal Agent is not a generic chatbot or conversational wrapper. It is a **verification-first autonomous coding agent** designed for professional software engineers.

When you ask Terminal Agent to fix a bug, implement a feature, or refactor code, it doesn't just modify files and claim completion. It follows a rigorous autonomous lifecycle:

```
UNDERSTAND  ->  PLAN  ->  EXECUTE  ->  TEST  ->  VERIFY  ->  REPAIR  ->  PROVE COMPLETION
```

A task is never marked completed until an independent verification engine confirms that tests pass, contract constraints hold, git diff limits are respected, and no unintended modifications were introduced.

---

## Key Features

- **Verify-First Paradigm**: Distinguishes between `DONE`, `VERIFIED`, `PARTIAL`, `FAILED`, and `BLOCKED`. Never accepts "tests weren't run but the code looks good".
- **Structured Task Contracts**: Automatically derives explicit goals, constraints, success criteria, and file scopes before making code changes.
- **Bounded Autonomous Loop**: Configurable step limits, retry limits, and timeout protection prevent runaway execution.
- **Command Safety & Sandbox**: Classifies commands into `SAFE`, `WRITE`, `DESTRUCTIVE`, `NETWORK`, and `PRIVILEGED`. Protects host secrets (`.env`, SSH keys, cloud credentials).
- **Checkpoints & Safe Rollback**: Automatic snapshots of file and session state before major modifications, with instant rollback.
- **Session Persistence & Resumption**: Stop anytime and `terminal-agent resume` seamlessly.
- **12-Category Failure Classifier & Targeted Recovery**: Categorizes failures (`wrong_solution`, `test_failure`, `syntax_error`, `dependency_error`, `timeout`, etc.) and devises targeted repair hypotheses.
- **Deterministic Context Engine**: Fast, token-efficient repository search and ranking without requiring heavy vector databases.
- **Model Agnostic**: Supports Ollama (local open models like `qwen2.5-coder`), OpenAI, Anthropic, Gemini, and Mock providers.
- **Proof of Done**: Outputs an indisputable verifiable certificate of success detailing tests, diffs, retries, and telemetry.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/terminal-agent.git
cd terminal-agent

# Install in editable mode
pip install -e .
```

---

## Quickstart

Run inside any software repository:

```bash
# Run a task directly
terminal-agent "Fix the token expiration bug in auth.py"

# Or run interactively
terminal-agent

# Run with a declarative task file
terminal-agent run --task task.yaml

# Check system health & dependencies
terminal-agent doctor

# Inspect session diff or status
terminal-agent diff
terminal-agent status

# Resume an interrupted session
terminal-agent resume <SESSION_ID>
```

---

## Configuration

Terminal Agent can be configured via `terminal-agent.config.yaml`:

```yaml
agent:
  max_steps: 40
  max_retries: 3
  timeout_seconds: 600

sandbox:
  mode: local # or docker
  timeout_seconds: 60
  network: disabled

verification:
  tests:
    - pytest
  assertions:
    - no_test_files_modified
    - api_contract_preserved
  diff:
    max_files_changed: 5

security:
  network: disabled
  require_confirmation_for:
    - destructive
    - privileged
    - network

provider:
  name: ollama
  model: qwen2.5-coder
```

---

## Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                               TERMINAL AGENT CLI                                  |
|   terminal-agent [run | resume | status | diff | test | checkpoint | doctor | ...]  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 CORE AGENT LOOP                                   |
|             Observe  --->  Plan  --->  Act  --->  Verify  --->  Repair            |
+--------------------+--------------------+--------------------+--------------------+
                     |                    |                    |
                     v                    v                    v
+--------------------------+ +--------------------------+ +-------------------------+
|     TASK CONTRACT &      | |      CONTEXT ENGINE      | |   MODEL PROVIDERS       |
|     SESSION MANAGER      | |  (Deterministic Ranking) | | (Ollama, OpenAI, Mock)  |
+--------------------------+ +--------------------------+ +-------------------------+
                     |                    |                    |
                     v                    v                    v
+-----------------------------------------------------------------------------------+
|                                   TOOL SYSTEM                                     |
|    read_file | write_file | edit_file | run_command | run_tests | git_diff ...    |
+--------------------+--------------------+--------------------+--------------------+
                     |                    |
                     v                    v
+-----------------------------------------+ +---------------------------------------+
|            COMMAND SAFETY               | |             SANDBOX                   |
|  (SAFE, WRITE, DESTRUCTIVE, PRIVILEGED) | |  (Subprocess & Docker isolation)      |
+-----------------------------------------+ +---------------------------------------+
                     |
                     v
+-----------------------------------------------------------------------------------+
|                          INDEPENDENT VERIFICATION ENGINE                          |
|             (Test suites, contract assertions, git diff bounds)                   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         FAILURE RECOVERY & PROOF OF DONE                          |
+-----------------------------------------------------------------------------------+
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

