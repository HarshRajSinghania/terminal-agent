# Contributing to Terminal Agent

Thank you for your interest in contributing to **Terminal Agent** by **PicadoLabs**!

Terminal Agent is built on the **Verify-First** architectural paradigm. We welcome contributions that improve reliability, enhance provider integrations, strengthen security sandboxing, or extend autonomous verification capabilities.

---

## 1. Code of Conduct

All contributors and participants must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## 2. Prerequisites

Ensure you have the following installed on your development machine:
- **Python**: Version `3.10`, `3.11`, or `3.12`
- **Git**: Version `2.30+`
- **Optional (for container sandboxing)**: Docker Engine
- **Optional (for local LLM inference)**: [Ollama](https://ollama.com)

---

## 3. Local Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/PicadoLabs/terminal-agent.git
   cd terminal-agent
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv

   # On Linux / macOS:
   source .venv/bin/activate

   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   ```

3. **Install the package in editable mode with development dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

4. **Verify the installation**:
   ```bash
   terminal-agent --help
   terminal-agent doctor
   ```

---

## 4. Branching Strategy & Workflow

1. Create a dedicated branch from `main`:
   ```bash
   git checkout -b feat/add-new-verifier-runner
   # or
   git checkout -b fix/resolve-windows-path-traversal
   ```

2. Follow semantic branch naming:
   - `feat/<feature-name>`: New feature or capability.
   - `fix/<bug-description>`: Bug fix or error resolution.
   - `docs/<documentation-change>`: Documentation improvements.
   - `test/<test-suite>`: New test cases or benchmark tasks.
   - `refactor/<component>`: Internal refactoring with preserved functionality.

---

## 5. Development & Code Quality Guidelines

### Architectural Principles
- **Verify-First Autonomy**: Any code modification mechanism must be verifiable through external, objective tests. The agent must never declare completion without test confirmation.
- **Defense in Depth**: All tool executions must route through `SecurityPolicyEnforcer` and `SecretGuard`. Never bypass sandboxing boundaries.
- **Deterministic Context**: Keep context discovery fast, bounded by token budgets, and deterministic.

### Typing & Code Style
- Use standard Python type annotations (`typing` and Python 3.10+ union types).
- Use Pydantic v2 models for structured schemas and configuration.
- Preserve backward compatibility with Python 3.10+.

---

## 6. Testing & Validation

Before submitting changes, run the full test and benchmark suite locally:

### Run Automated Unit and Integration Tests
```bash
pytest tests/ -v
```

### Run Full SWE Benchmark Evaluation Suite
```bash
python -m benchmarks.runner
```

### Run Type and Syntax Sanity
```bash
python -m py_compile src/terminal_agent/**/*.py
```

All 37 test cases and 10 benchmark evaluation tasks must pass cleanly.

---

## 7. Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

### Examples:
- `feat(verifier): add support for rust cargo test parser`
- `fix(sandbox): terminate child processes on local timeout`
- `docs(readme): add docker sandboxing guide`
- `test(security): add test for path traversal with symlinks`

---

## 8. Submitting a Pull Request (PR)

1. Ensure your branch is rebased on the latest `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. Push your branch to your fork:
   ```bash
   git push origin feat/my-feature
   ```
3. Open a Pull Request on GitHub against `PicadoLabs/terminal-agent:main`.
4. Fill out the [Pull Request Template](.github/pull_request_template.md) completely:
   - Provide a clear summary of what was changed and why.
   - Attach test execution results and commands run.
   - Highlight any potential breaking changes.

---

## 9. Reporting Issues

- **Bug Reports**: Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md). Include your OS, Python version, steps to reproduce, and terminal output.
- **Feature Requests**: Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md). Explain the problem, proposed solution, and alternatives considered.
- **Security Vulnerabilities**: **DO NOT** file public issues. Follow the private disclosure process in [SECURITY.md](SECURITY.md) by contacting `picadolabs@gmail.com`.

---

## 10. Community & Organization

Terminal Agent is maintained by **PicadoLabs**.

- **Organization**: [https://github.com/PicadoLabs](https://github.com/PicadoLabs)
- **Website**: [https://picadolabs.me](https://picadolabs.me)
- **Contact**: [picadolabs@gmail.com](mailto:picadolabs@gmail.com)
