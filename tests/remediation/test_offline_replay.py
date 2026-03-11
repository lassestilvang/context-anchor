import responses
import pytest
import yaml
import json
from datetime import datetime
from click.testing import CliRunner
from contextanchor.cli import main
from contextanchor.local_storage import LocalStorage
from contextanchor.models import CommitInfo
from rich.console import Console
import os
import tempfile
import shutil
from pathlib import Path


class TestOfflineReplay:
    def setup_method(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

        # Patch HOME so LocalStorage (and CLI) uses our temp dir
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_dir

        # Create config file
        self.dot_dir = Path(self.temp_dir) / ".contextanchor"
        self.dot_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.dot_dir / "config.yaml"
        with open(self.config_path, "w") as f:
            yaml.dump({
                "api_endpoint": "https://api.contextanchor.com",
                "api_timeout_seconds": 30,
                "retry_attempts": 0,
                "enabled_signals": ["commits", "branches", "diffs", "pr_references"]
            }, f)

        # Create state file
        self.state_path = self.dot_dir / "state.json"
        with open(self.state_path, "w") as f:
            json.dump({"last_branch": "main"}, f)

        # Path where CLI will look for the db
        self.db_path = self.dot_dir / "local.db"
        
        # Initialize storage
        self.storage = LocalStorage(db_path=self.db_path)
        self.storage.register_repository("repo-1", "test-repo", self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
        if self.old_home:
            os.environ["HOME"] = self.old_home

    @responses.activate
    def test_sync_command_manual(self, mocker):
        # Suppress Rich colors by patching top-level console in cli.py
        mock_console = Console(force_terminal=False, no_color=True, width=120)
        mocker.patch("contextanchor.cli.console", mock_console)

        # 1. Queue an operation
        payload = {
            "repository_id": "repo-1",
            "branch": "main",
            "developer_intent": "Test sync",
            "signals": {"uncommitted_files": []}
        }
        self.storage.queue_operation("save_context", "repo-1", payload)

        # 2. Mock API
        responses.add(
            responses.POST,
            "https://api.contextanchor.com/v1/contexts",
            json={"snapshot_id": "snap-1"},
            status=201
        )

        # 3. Mocks
        mocker.patch("contextanchor.cli._find_git_root", return_value=Path(self.temp_dir))
        mocker.patch("contextanchor.local_storage.LocalStorage", return_value=self.storage)
        mocker.patch("contextanchor.cli.LocalStorage", return_value=self.storage, create=True)
        
        mock_git = mocker.patch("contextanchor.git_observer.GitObserver")
        mock_git.return_value.generate_repository_id.return_value = "repo-1"
        mock_git.return_value.get_current_branch.return_value = "main"

        # 4. Run sync
        result = self.runner.invoke(main, ["sync"])

        assert result.exit_code == 0
        assert "Successfully synced 1 operations" in result.output
        assert self.storage.count_queued_operations("repo-1") == 0

    @responses.activate
    def test_automatic_replay_on_save(self, mocker):
        # Suppress Rich colors
        mock_console = Console(force_terminal=False, no_color=True, width=120)
        mocker.patch("contextanchor.cli.console", mock_console)

        # 1. Queue an existing operation
        payload = {
            "repository_id": "repo-1",
            "branch": "main",
            "developer_intent": "Old intent",
            "signals": {"uncommitted_files": []}
        }
        self.storage.queue_operation("save_context", "repo-1", payload)

        # 2. Mock API
        responses.add(
            responses.POST,
            "https://api.contextanchor.com/v1/contexts",
            json={"snapshot_id": "snap-1"},
            status=201
        )

        # 3. Mocks
        mocker.patch("contextanchor.cli._find_git_root", return_value=Path(self.temp_dir))
        mocker.patch("contextanchor.local_storage.LocalStorage", return_value=self.storage)
        mocker.patch("contextanchor.cli.LocalStorage", return_value=self.storage, create=True)
        
        mock_git = mocker.patch("contextanchor.git_observer.GitObserver")
        inst = mock_git.return_value
        inst.generate_repository_id.return_value = "repo-1"
        inst.get_current_branch.return_value = "main"
        
        inst.capture_uncommitted_changes.return_value = []
        inst.capture_commit_signal.return_value = CommitInfo(
            hash="abc", 
            message="fix: something #123", 
            timestamp=datetime.now(),
            files_changed=[]
        )
        inst.parse_references.return_value = {"pr_references": [123], "issue_references": []}
        inst.get_github_metadata.return_value = None

        # 4. Run save-context
        result = self.runner.invoke(main, ["save-context", "-m", "New intent"])

        assert result.exit_code == 0
        assert self.storage.count_queued_operations("repo-1") == 0
        assert len(responses.calls) == 2
