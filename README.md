# ContextAnchor

Developer workflow state management system that eliminates context-switching overhead.

## Overview

ContextAnchor monitors git activity and enables developers to capture their mental state before switching tasks, then instantly restores that context when they return.

## Features

- **Passive Observation**: Monitors git operations (commits, branches, diffs)
- **Intent Capture**: Prompts developers to articulate their current mental state
- **AI Synthesis**: Uses Amazon Bedrock to transform raw signals into structured context snapshots
- **Automatic Restoration**: Surfaces saved context when returning to branches or projects
- **Offline Resilient**: Core functionality works without network connectivity

## Requirements

- Python 3.11 or higher
- Git
- AWS account (for cloud features)

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Development

### Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black src tests
flake8 src tests
mypy src

# Run security scan
bandit -r src
```

### Testing

The project uses both unit tests and property-based tests:

- **Unit tests**: Located in `tests/unit/`
- **Property-based tests**: Located in `tests/property/`
- **Integration tests**: Located in `tests/integration/`

Run specific test categories:

```bash
pytest -m unit
pytest -m property
pytest -m integration
```

## License

MIT
