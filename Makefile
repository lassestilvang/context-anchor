.PHONY: help install test lint format security clean

help:
	@echo "ContextAnchor Development Commands"
	@echo "  make install    - Install package and dependencies"
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run linting checks"
	@echo "  make format     - Format code with black"
	@echo "  make security   - Run security scan"
	@echo "  make clean      - Remove build artifacts"

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	flake8 src tests
	mypy src

format:
	black src tests

security:
	bandit -r src

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .hypothesis .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
