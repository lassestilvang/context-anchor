
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
from contextanchor.cli import main, save_context, list_contexts

@pytest.fixture
def mock_repo_a(tmp_path):
    repo_a = tmp_path / "repo_a"
    repo_a.mkdir()
    (repo_a / ".git").mkdir()
    (repo_a / ".contextanchor").mkdir()
    with open(repo_a / ".contextanchor" / "config.yaml", "w") as f:
        f.write("api_endpoint: http://api.test\nretry_attempts: 3\n")
    return repo_a

@pytest.fixture
def mock_repo_b(tmp_path):
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    (repo_b / ".git").mkdir()
    (repo_b / ".contextanchor").mkdir()
    with open(repo_b / ".contextanchor" / "config.yaml", "w") as f:
        f.write("api_endpoint: http://api.test\nretry_attempts: 3\n")
    return repo_b

def test_cli_isolation_between_repos(mock_repo_a, mock_repo_b):
    runner = CliRunner()
    
    # Mock dependencies
    with patch("contextanchor.cli._find_git_root") as mock_find_root, \
         patch("contextanchor.config.load_config") as mock_load_config, \
         patch("contextanchor.git_observer.GitObserver") as mock_git_obs_class, \
         patch("contextanchor.api_client.APIClient") as mock_api_client_class, \
         patch("contextanchor.local_storage.LocalStorage") as mock_local_storage_class:
        
        # Setup common mocks
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_load_config.return_value = MagicMock(api_endpoint="http://api", retry_attempts=3)
        mock_git_obs = MagicMock()
        mock_git_obs_class.return_value = mock_git_obs
        
        # Setup Repo A
        mock_find_root.return_value = mock_repo_a
        mock_git_obs.generate_repository_id.return_value = "id-repo-a"
        mock_git_obs.get_current_branch.return_value = "main"
        
        # Run list-contexts in Repo A
        result_a = runner.invoke(main, ["list-contexts"])
        assert result_a.exit_code == 0
        
        # Verify Repo A ID was used
        mock_api_client.list_contexts.assert_called_with("id-repo-a", None, 20)
        
        # Switch context to Repo B
        mock_find_root.return_value = mock_repo_b
        mock_git_obs.generate_repository_id.return_value = "id-repo-b"
        
        # Run list-contexts in Repo B
        result_b = runner.invoke(main, ["list-contexts"])
        assert result_b.exit_code == 0
        
        # Verify Repo B ID was used
        # We check the most recent call
        assert mock_api_client.list_contexts.call_count == 2
        last_call_args = mock_api_client.list_contexts.call_args
        assert last_call_args[0][0] == "id-repo-b"
