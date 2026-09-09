---
name: Feature Request
about: Suggest a new feature, provider adapter, tool, or architectural improvement
title: "[FEATURE] "
labels: ["enhancement"]
assignees: ""
---

## Problem & Use Case
Is your feature request related to a specific limitation or problem? (e.g., "I want to verify Rust projects using cargo test parser...")

## Proposed Solution
A clear and concise description of what you want to happen and how it fits into the verify-first architecture.

## Alternatives Considered
Describe any alternative solutions or workarounds you have considered.

## Component Affected
- [ ] Agent Loop / Orchestrator (`src/terminal_agent/agent/`)
- [ ] Context Engine & Ranker (`src/terminal_agent/context/`)
- [ ] Independent Verifier (`src/terminal_agent/verifier/`)
- [ ] Security & Sandboxing (`src/terminal_agent/security/`, `src/terminal_agent/sandbox/`)
- [ ] Tool Registry (`src/terminal_agent/tools/`)
- [ ] Failure Classifier & Recovery (`src/terminal_agent/recovery/`)
- [ ] Model Providers (`src/terminal_agent/providers/`)
- [ ] CLI & UX (`src/terminal_agent/cli/`)
- [ ] Documentation / Benchmarks

## Additional Context
Add any other context, mockups, or references about the feature request here.
