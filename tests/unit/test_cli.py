"""Unit tests for CLI module."""

import pytest
from click.testing import CliRunner

from contextanchor.cli import main


@pytest.mark.unit
def test_cli_version():
    """Test that CLI version command works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


@pytest.mark.unit
def test_cli_help():
    """Test that CLI help command works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ContextAnchor" in result.output
