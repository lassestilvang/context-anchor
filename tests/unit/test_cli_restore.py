import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from src.contextanchor.cli import main, hook_branch_switch


@pytest.fixture
def mock_restore_deps():
    with (
        patch("src.contextanchor.cli._find_git_root") as mock_find_git,
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("src.contextanchor.api_client.APIClient") as mock_api_client_cls,
        patch("src.contextanchor.config.load_config") as mock_load_config,
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open") as mock_open,
        patch("src.contextanchor.logging.get_logger"),
        patch("src.contextanchor.local_storage.LocalStorage"),
    ):
        mock_find_git.return_value = Path("/mock/repo")

        mock_config = MagicMock()
        mock_config.api_endpoint = "http://api.mock"
        mock_config.retry_attempts = 1
        mock_config.api_timeout_seconds = 10
        mock_load_config.return_value = mock_config

        mock_git_obs = MagicMock()
        mock_git_obs.generate_repository_id.return_value = "repo1"
        mock_git_obs.get_current_branch.return_value = "feature-b"
        mock_git_obs_cls.return_value = mock_git_obs

        mock_api_client = MagicMock()
        mock_api_client.list_contexts.return_value = [
            {
                "snapshot_id": "snap-555",
                "developer_intent": "Feature B fixes",
                "captured_at": "2024-01-01T00:00:00Z",
            }
        ]
        mock_api_client_cls.return_value = mock_api_client

        # Mock state file contents
        mock_file = MagicMock()
        mock_file.read.return_value = '{"last_branch": "main"}'
        mock_open.return_value.__enter__.return_value = mock_file

        yield {"api_client": mock_api_client, "git_obs": mock_git_obs, "open": mock_open}


def test_fallback_branch_detection(mock_restore_deps):
    runner = CliRunner()
    # Invoke a command that isn't init or _hook-branch-switch
    result = runner.invoke(main, ["list-contexts"])

    # It should detect branch switch from main to feature-b
    assert "🔍 ContextAnchor: Detected switch to branch 'feature-b'" in result.output
    # It should fetch and render context
    assert "Context Snapshot: snap-555" in result.output
    # It should also run the list-contexts command (which prints a list)
    assert "Contexts (1)" in result.output


def test_hook_branch_switch_command(mock_restore_deps):
    runner = CliRunner()
    result = runner.invoke(hook_branch_switch, ["abc1234", "def5678"])

    assert result.exit_code == 0
    assert "🔍 ContextAnchor: Switched to branch 'feature-b'" in result.output
    assert "Context Snapshot: snap-555" in result.output

    mock_restore_deps["api_client"].list_contexts.assert_called_with("repo1", "feature-b", 1)


def test_fallback_no_context_found(mock_restore_deps):
    mock_restore_deps["api_client"].list_contexts.return_value = []

    runner = CliRunner()
    result = runner.invoke(main, ["list-contexts"])

    assert "🔍 ContextAnchor: Detected switch to branch 'feature-b'" in result.output
    assert "No saved context found for this branch." in result.output


def test_fallback_writes_state(mock_restore_deps):
    runner = CliRunner()
    runner.invoke(main, ["list-contexts"])

    # open() should be called to read and write state.json
    mock_open = mock_restore_deps["open"]
    write_calls = [c for c in mock_open.call_args_list if "w" in c[0]]
    assert len(write_calls) > 0
