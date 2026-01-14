# Contributing to PyEdgeTwin

Thank you for your interest in contributing to PyEdgeTwin! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/aeroshariati/PyEdgeTwin/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the behavior
   - Expected vs actual behavior
   - Your environment (OS, Python version, PyEdgeTwin version)
   - Relevant logs or error messages

### Suggesting Enhancements

1. Check existing issues and discussions for similar suggestions
2. Create a new issue with:
   - A clear description of the enhancement
   - Use case and motivation
   - Proposed implementation approach (if any)

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following our coding standards
4. Add tests for new functionality
5. Ensure all tests pass:
   ```bash
   pytest
   ```
6. Update documentation if needed
7. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/PyEdgeTwin.git
cd PyEdgeTwin

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,docs]"

# Install pre-commit hooks
pre-commit install
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints for all public functions
- Maximum line length: 100 characters
- Use [ruff](https://github.com/astral-sh/ruff) for linting

### Code Quality Checks

```bash
# Linting
ruff check src/

# Type checking
mypy src/pyedgetwin/

# Formatting
ruff format src/

# Run all tests
pytest

# Run with coverage
pytest --cov=pyedgetwin --cov-report=html
```

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep the first line under 72 characters
- Reference issues when relevant

Example:
```
Add CSV sink with configurable columns

- Implement CSVSink class with append mode support
- Add header writing for new files
- Include unit tests for CSV sink

Closes #42
```

### Documentation

- Use docstrings for all public classes and functions
- Follow [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) docstrings
- Update README.md for user-facing changes
- Add examples for new features

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires Docker)
pytest tests/integration/ -m integration

# With coverage report
pytest --cov=pyedgetwin --cov-report=term-missing
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_queue_drops_oldest_on_overflow`
- Use fixtures from `tests/conftest.py`

## Architecture Guidelines

### Model Blocks

When creating new model blocks:
- Inherit from `ModelBlock` ABC
- Implement all required methods: `init`, `process`, `shutdown`
- Return required keys: `raw_value`, `twin_estimate`, `anomaly_flag`
- Document parameters in docstrings

### Sinks

When creating new sinks:
- Inherit from `BaseSink` ABC
- Implement: `open`, `write`, `flush`, `close`
- Handle batching for performance if applicable
- Ensure proper cleanup in `close`

### Connectors

When creating new connectors:
- Inherit from `BaseConnector` ABC
- Implement reconnection logic with backoff
- Handle graceful shutdown

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml` and `src/pyedgetwin/__init__.py`
2. Update `CITATION.cff` with new version and date
3. Create a tagged release on GitHub
4. CI will publish to PyPI

## Questions?

Feel free to:
- Open a [Discussion](https://github.com/aeroshariati/PyEdgeTwin/discussions)
- Create an [Issue](https://github.com/aeroshariati/PyEdgeTwin/issues)

Thank you for contributing!
