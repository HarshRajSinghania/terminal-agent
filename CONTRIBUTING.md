# Contributing to Terminal Agent

Thank you for your interest in contributing to **Terminal Agent**!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/terminal-agent.git
   cd terminal-agent
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   ```

3. **Install in editable mode with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

Run the full automated test suite:
```bash
pytest tests/ -v
```

Run benchmark evaluations:
```bash
python -m benchmarks.runner
```

## Pull Request Guidelines

- Ensure all existing and new tests pass.
- Adhere to the verify-first architecture principle: every modification must be independently verifiable.
- Include unit/integration tests for any new tool, recovery rule, or provider adapter.
