---
name: Bug Report
about: Create a report to help us reproduce and resolve an issue
title: "[BUG] "
labels: ["bug"]
assignees: ""
---

## Description
A clear and concise description of the bug.

## Steps to Reproduce
1. Run command: `terminal-agent run "..."`
2. Configure provider: `...`
3. Execute step: `...`
4. Observe failure.

## Expected Behavior
What should have occurred (e.g., successful repair, specific failure category classification, or clean rollback).

## Actual Behavior
What actually occurred (include error messages or stack traces).

## Environment Details
- **Operating System**: (e.g., Linux Ubuntu 22.04, macOS 14.4, Windows 11)
- **Python Version**: (`python --version`, e.g., 3.11.8)
- **Terminal Agent Version**: (`terminal-agent --version` or git commit SHA)
- **Model Provider**: (e.g., Ollama / OpenAI / Anthropic / Gemini / Mock)
- **Sandbox Mode**: (e.g., Local / Docker)

## Logs & Trace Output
```bash
# Attach output of 'terminal-agent doctor' or 'terminal-agent trace <session_id>' if available
```

## Additional Context
Add any other context, repository layout, or screenshots about the problem here.
