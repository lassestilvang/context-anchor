"""Unit tests for CLI module."""

import os
import pytest
from click.testing import CliRunner

from contextanchor.cli import main
from src.contextanchor.cli import init


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
    assert result.exit_code == 0
    assert "ContextAnchor" in result.output


def test_init_success(tmp_path):
    runner = CliRunner()

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(init)

        assert result.exit_code == 0
        assert "Initialized ContextAnchor" in result.output
        assert "Hook status: active" in result.output

        assert (tmp_path / ".contextanchor" / "config.yaml").exists()

        assert (hooks_dir / "post-commit").exists()
        assert os.access(hooks_dir / "post-commit", os.X_OK)


def test_init_already_initialized(tmp_path):
    runner = CliRunner()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    config_dir = tmp_path / ".contextanchor"
    config_dir.mkdir()
    (config_dir / "config.yaml").touch()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(init)

        assert result.exit_code != 0
        assert "already initialized" in result.output


def test_init_not_in_git_repo(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(init)

        assert result.exit_code != 0
        assert "Not inside a git repository" in result.output
