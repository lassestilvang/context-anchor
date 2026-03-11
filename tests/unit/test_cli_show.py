import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from pathlib import Path
import json

from src.contextanchor.cli import show_context


@pytest.fixture
def mock_show_deps():
    with (
        patch("src.contextanchor.cli._find_git_root") as mock_find_git,
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("src.contextanchor.api_client.APIClient") as mock_api_client_cls,
        patch("src.contextanchor.local_storage.LocalStorage") as mock_local_storage_cls,
        patch("src.contextanchor.config.load_config") as mock_load_config,
        patch("pathlib.Path.exists") as mock_exists,
    ):

        mock_find_git.return_value = Path("/mock/repo")
        mock_exists.return_value = True

        mock_config = MagicMock()
        mock_config.api_endpoint = "http://api.mock"
        mock_config.retry_attempts = 1
        mock_config.api_timeout_seconds = 10
        mock_load_config.return_value = mock_config

        mock_git_obs = MagicMock()
        mock_git_obs.generate_repository_id.return_value = "repo1"
        mock_git_obs.get_current_branch.return_value = "main"
        mock_git_obs_cls.return_value = mock_git_obs

        mock_api_client = MagicMock()
        mock_api_client.get_context_by_id.return_value = {
            "snapshot_id": "snap-123",
            "goals": "Test goals",
            "captured_at": "2024-01-01T00:00:00Z",
            "developer_id": "dev-1",
        }
        mock_api_client.list_contexts.return_value = [
            {
                "snapshot_id": "snap-123",
                "developer_intent": "Fixing things",
                "captured_at": "2024-01-01T00:00:00Z",
            },
            {
                "snapshot_id": "snap-124",
                "developer_intent": "More fixes",
                "captured_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_api_client_cls.return_value = mock_api_client

        mock_local_storage = MagicMock()
        mock_cached = MagicMock()
        mock_cached.snapshot_id = "snap-cached"
        mock_cached.goals = "Cached goals"
        mock_local_storage.get_cached_snapshot.return_value = mock_cached
        mock_local_storage_cls.return_value = mock_local_storage

        yield {
            "api_client": mock_api_client,
            "local_storage": mock_local_storage,
        }


def test_show_context_by_id(mock_show_deps):
    runner = CliRunner()
    result = runner.invoke(show_context, ["snap-123"])

    assert result.exit_code == 0
    assert "Context Snapshot: snap-123" in result.output
    assert "Goals:" in result.output
    assert "Test goals" in result.output

    mock_show_deps["api_client"].get_context_by_id.assert_called_with("snap-123")


def test_show_context_list(mock_show_deps):
    runner = CliRunner()
    result = runner.invoke(show_context, ["--limit", "2"])

    assert result.exit_code == 0
    assert "Recent Contexts (2):" in result.output
    assert "[snap-123]" in result.output
    assert "Fixing things" in result.output

    mock_show_deps["api_client"].list_contexts.assert_called_with("repo1", "main", 2)


def test_show_context_json_format(mock_show_deps):
    runner = CliRunner()
    result = runner.invoke(show_context, ["snap-123", "-f", "json"])

    assert result.exit_code == 0
    # ensure valid json
    data = json.loads(result.output)
    assert data["snapshot_id"] == "snap-123"


def test_show_context_offline_fallback(mock_show_deps):
    mock_show_deps["api_client"].get_context_by_id.side_effect = ConnectionError("Offline")
    mock_show_deps["api_client"].list_contexts.side_effect = ConnectionError("Offline")

    runner = CliRunner()
    result = runner.invoke(show_context)

    assert result.exit_code == 0
    assert "Network unavailable. Falling back to local cache." in result.output
    assert "snap-cached" in result.output

    # ID provided in offline mode
    result2 = runner.invoke(show_context, ["snap-123"])
    assert result2.exit_code == 0
    assert "Cannot fetch specific historical snapshots while offline" in result2.output
