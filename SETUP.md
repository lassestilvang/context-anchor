# ContextAnchor Development Environment Setup

This document describes the project structure and development environment setup completed for ContextAnchor.

## Project Structure

```
context-anchor/
├── src/
│   └── contextanchor/          # Main package directory
│       ├── __init__.py         # Package initialization
│       └── cli.py              # CLI entry point
├── tests/
│   ├── unit/                   # Unit tests
│   ├── property/               # Property-based tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test fixtures
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD pipeline
├── pyproject.toml              # Project configuration and dependencies
├── pytest.ini                  # Pytest configuration
├── mypy.ini                    # Type checking configuration
├── .flake8                     # Linting configuration
├── .bandit                     # Security scanning configuration
├── .gitignore                  # Git ignore patterns
├── Makefile                    # Development commands
├── setup.sh                    # Setup script
├── requirements-dev.txt        # Development dependencies
└── README.md                   # Project documentation
```

## Dependencies Installed

### Core Dependencies
- **click** (>=8.1.0): CLI framework for command-line interface
- **gitpython** (>=3.1.0): Git integration library
- **boto3** (>=1.34.0): AWS SDK for Python (DynamoDB, Bedrock, S3)
- **pyyaml** (>=6.0): YAML configuration file support
- **requests** (>=2.31.0): HTTP library for API calls

### Development Dependencies
- **pytest** (>=7.4.0): Testing framework
- **pytest-cov** (>=4.1.0): Code coverage plugin
- **hypothesis** (>=6.92.0): Property-based testing framework
- **black** (>=23.12.0): Code formatter
- **flake8** (>=7.0.0): Linting tool
- **mypy** (>=1.8.0): Static type checker
- **bandit** (>=1.7.0): Security vulnerability scanner
- **types-pyyaml** (>=6.0.0): Type stubs for PyYAML
- **types-requests** (>=2.31.0): Type stubs for requests

## Development Tools Configuration

### Black (Code Formatter)
- Line length: 100 characters
- Target version: Python 3.11+

### Flake8 (Linter)
- Max line length: 100 characters
- Ignores: E203, W503 (for Black compatibility)

### Mypy (Type Checker)
- Python version: 3.11
- Strict type checking enabled
- Disallows untyped definitions

### Bandit (Security Scanner)
- Excludes test directories
- Skips B101 (assert usage in tests)

### Pytest
- Test paths: tests/
- Coverage reporting enabled
- Markers: unit, property, integration, slow

## Virtual Environment

A Python virtual environment has been created and configured:
- Location: `./venv/`
- Python version: 3.14.3 (compatible with 3.11+ requirement)
- All dependencies installed in editable mode

## CLI Tool

The CLI tool is installed and accessible:
```bash
contextanchor --version  # Shows version 0.1.0
contextanchor --help     # Shows available commands
```

## Development Commands

### Using Make
```bash
make install    # Install package and dependencies
make test       # Run all tests
make lint       # Run linting checks
make format     # Format code with black
make security   # Run security scan
make clean      # Remove build artifacts
```

### Using Setup Script
```bash
./setup.sh      # Complete environment setup
```

### Manual Commands
```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest
pytest -m unit          # Unit tests only
pytest -m property      # Property-based tests only
pytest -m integration   # Integration tests only

# Run linting
flake8 src tests
mypy src
bandit -r src

# Format code
black src tests
```

## CI/CD Pipeline

GitHub Actions workflow configured:
- Runs on: Ubuntu latest
- Python versions: 3.11, 3.12
- Steps:
  1. Lint with flake8
  2. Type check with mypy
  3. Security scan with bandit
  4. Run unit tests with coverage
  5. Run property-based tests
  6. Upload coverage to Codecov

## Verification

All tools have been verified to work correctly:
- ✅ CLI tool runs and shows version
- ✅ Black formatting passes
- ✅ Flake8 linting passes
- ✅ Mypy type checking passes
- ✅ Bandit security scan passes
- ✅ Pytest runs successfully (2 tests passing)
- ✅ Code coverage: 75%

## Next Steps

The development environment is ready for implementation. The next tasks will involve:
1. Implementing core domain models (Task 2)
2. Building CLI commands (Task 3)
3. Implementing Git Observer component (Task 4)
4. Setting up AWS infrastructure (Task 5)
5. And continuing with remaining tasks...

## Requirements Validated

This setup satisfies the following requirements from the spec:
- **R14.1**: Python 3.11+ for CLI tool ✅
- **R14.2**: boto3 for AWS services (DynamoDB, Bedrock, S3) ✅
- **R14.3**: GitPython for git integration ✅
- **R14.4**: Click for CLI framework ✅
- Property-based testing with Hypothesis ✅
- Development tools: black, flake8, mypy, bandit ✅
