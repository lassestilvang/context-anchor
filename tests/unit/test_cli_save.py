import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from src.contextanchor.cli import save_context


@pytest.fixture
def mock_deps():
    with (
        patch("src.contextanchor.cli._find_git_root") as mock_find_git,
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("src.contextanchor.api_client.APIClient") as mock_api_client_cls,
        patch("src.contextanchor.local_storage.LocalStorage") as mock_local_storage_cls,
        patch("src.contextanchor.config.load_config") as mock_load_config,
        patch("pathlib.Path.exists") as mock_exists,
    ):

        # Setup find git
        mock_find_git.return_value = Path("/mock/repo")
        mock_exists.return_value = True

        # Setup config
        mock_config = MagicMock()
        mock_config.enabled_signals = ["commits", "diffs"]
        mock_config.api_endpoint = "http://api.mock"
        mock_config.retry_attempts = 3
        mock_config.api_timeout_seconds = 30
        mock_config.capture_prompt = "What did you do?"
        mock_config.redact_patterns = [r"sk-[a-zA-Z0-9]+"]
        mock_load_config.return_value = mock_config

        # Setup git observer
        mock_git_obs = MagicMock()
        mock_git_obs.generate_repository_id.return_value = "repo1"
        mock_git_obs.get_current_branch.return_value = "main"
        mock_git_obs.capture_uncommitted_changes.return_value = []
        mock_git_obs.capture_commit_signal.return_value = None
        mock_git_obs_cls.return_value = mock_git_obs

        # Setup API client
        mock_api_client = MagicMock()
        mock_api_client.create_context.return_value = {"snapshot_id": "snap123"}
        mock_api_client_cls.return_value = mock_api_client

        # Setup Local storage
        mock_local_storage = MagicMock()
        mock_local_storage.queue_operation.return_value = "op123"
        mock_local_storage_cls.return_value = mock_local_storage

        yield {
            "find_git": mock_find_git,
            "config": mock_config,
            "git_obs": mock_git_obs,
            "api_client": mock_api_client,
            "local_storage": mock_local_storage,
        }


def test_save_context_success_with_message(mock_deps):
    runner = CliRunner()
    result = runner.invoke(save_context, ["-m", "Fixed bug sk-12345"])

    assert result.exit_code == 0
    assert "Context snapshot saved successfully" in result.output

    mock_deps["api_client"].create_context.assert_called_once()
    args, kwargs = mock_deps["api_client"].create_context.call_args
    assert args[0] == "repo1"
    assert args[1] == "main"
    assert args[2] == "Fixed bug [REDACTED]"  # Redaction property 34!


def test_save_context_offline_mode(mock_deps):
    mock_deps["api_client"].create_context.side_effect = ConnectionError("Offline")

    runner = CliRunner()
    result = runner.invoke(save_context, ["-m", "Offline work"])

    assert result.exit_code == 0
    assert "Queued operation for later. (Op ID: op123)" in result.output

    mock_deps["local_storage"].queue_operation.assert_called_once()
