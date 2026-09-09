# Security Policy

Terminal Agent executes commands, runs test suites, and modifies source code directly within developer environments and sandboxes. Security, safety, and strict execution boundaries are foundational architectural pillars.

---

## 1. Supported Versions

We release patches and security fixes for the following versions:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| `0.1.x` | Yes | Current Active Release |
| `< 0.1` | No                 | Unsupported |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability in Terminal Agent, please report it **privately**. 

**DO NOT disclose vulnerabilities through public GitHub issues, discussions, or pull requests.**

### Reporting Procedure

1. Send an email to: **picadolabs@gmail.com**
2. Include the subject prefix: `[SECURITY VULNERABILITY] Terminal Agent: <Brief Description>`
3. Provide as much detail as possible to help us reproduce and remediate the issue promptly:
   - **Type of Issue**: (e.g., Sandbox Escape, Path Traversal, Arbitrary Code Execution beyond Sandbox, Secret Exposure, Command Injection).
   - **Affected Component**: (e.g., `LocalSandbox`, `DockerSandbox`, `SecretGuard`, `CommandClassifier`, `ToolRegistry`).
   - **Steps to Reproduce**: Detailed step-by-step reproduction instructions or a minimal reproducible repository.
   - **Proof of Concept (PoC)**: Reproduction script or task prompt triggering the vulnerability.
   - **Impact Assessment**: How an attacker could exploit this vulnerability and the potential severity.
   - **Proposed Mitigation**: Suggested fix or patch if available.

### Response Timeline

- **Acknowledgment**: Within 48 hours of receipt.
- **Triage & Confirmation**: Within 5 business days.
- **Remediation & Patch Release**: Coordinated disclosure with a patch release and advisory.

---

## 3. Threat Model & Sandboxing Architecture

Terminal Agent enforces multiple defense-in-depth isolation layers:

### Execution Sandboxes
- **Local Sandbox (`LocalSandbox`)**: Runs commands within the local workspace directory with strict execution timeouts, process-tree termination via `psutil` to prevent runaway child processes, and environment variable sanitization.
- **Docker Sandbox (`DockerSandbox`)**: Runs commands inside an ephemeral, resource-constrained container with non-root privileges and optional network isolation (`--network none`).

### Secret Guard & Path Traversal Protection
The `SecretGuard` component continuously monitors all file system operations and tool outputs:
- **Blocked Files**: `.env`, `.env.*`, `*.env`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `id_rsa*`, `id_ed25519*`, `.ssh/*`, `.aws/*`, `.gnupg/*`, `.netrc`.
- **Path Traversal Guard**: Prevents path escaping outside the designated workspace root directory (`../..`).
- **Secret Redaction**: Real-time linear-time scanner detecting sensitive token prefixes (`sk-`, `ghp_`, `xoxb-`, `AIzaSy`) and high-entropy secret patterns, redacting them to `[REDACTED_SECRET]` before passing tool outputs back to LLM providers.

### Command Risk Classification
All shell commands are evaluated by `CommandClassifier` before dispatch:
- **SAFE / WRITE**: Read-only operations, linters, tests, and standard workspace file changes (auto-allowed).
- **DESTRUCTIVE / PRIVILEGED / NETWORK**: High-risk system commands (`rm -rf /`, `mkfs`, `format`, `dd`, `sudo`, `reg add`, `curl`, `wget`). In headless or non-interactive environments, destructive and privileged commands are denied automatically.

---

## 4. Security Inquiries & Contact

For general security questions or vulnerability reports, contact:
- **Organization**: PicadoLabs
- **Email**: picadolabs@gmail.com
- **Website**: https://picadolabs.me
