import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from src.contextanchor.cli import list_contexts, history, delete_context


@pytest.fixture
def mock_cmd_deps():
    with (
        patch("src.contextanchor.cli._find_git_root") as mock_find_git,
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("src.contextanchor.api_client.APIClient") as mock_api_client_cls,
        patch("src.contextanchor.config.load_config") as mock_load_config,
        patch("src.contextanchor.local_storage.LocalStorage"),
    ):
        mock_find_git.return_value = Path("/mock/repo")

        mock_config = MagicMock()
        mock_config.api_endpoint = "http://api.mock"
        mock_config.retry_attempts = 1
        mock_load_config.return_value = mock_config

        mock_git_obs = MagicMock()
        mock_git_obs.generate_repository_id.return_value = "repo1"
        mock_git_obs.get_current_branch.return_value = "main"
        mock_git_obs_cls.return_value = mock_git_obs

        mock_api_client = MagicMock()
        mock_api_client.list_contexts.return_value = [
            {
                "snapshot_id": "snap-123",
                "developer_intent": "Int1",
                "captured_at": "2024-01-01T00:00:00Z",
            },
            {
                "snapshot_id": "snap-124",
                "developer_intent": "Int2",
                "captured_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_api_client_cls.return_value = mock_api_client

        yield {
            "api_client": mock_api_client,
        }


def test_list_contexts(mock_cmd_deps):
    runner = CliRunner()
    result = runner.invoke(list_contexts, ["-l", "5"])
    assert result.exit_code == 0
    assert "Contexts (2)" in result.output
    mock_cmd_deps["api_client"].list_contexts.assert_called_with("repo1", None, 5)


def test_history(mock_cmd_deps):
    runner = CliRunner()
    result = runner.invoke(history, ["-b", "feature-x", "-l", "10"])
    assert result.exit_code == 0
    assert "Contexts (2)" in result.output
    mock_cmd_deps["api_client"].list_contexts.assert_called_with("repo1", "feature-x", 10)


def test_delete_context(mock_cmd_deps):
    runner = CliRunner()
    result = runner.invoke(delete_context, ["snap-124"])
    assert result.exit_code == 0
    assert "marked for deletion" in result.output
    mock_cmd_deps["api_client"].delete_context.assert_called_with("snap-124")
