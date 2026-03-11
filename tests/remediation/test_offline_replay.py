
import pytest
import responses
from click.testing import CliRunner
from contextanchor.cli import main
from contextanchor.local_storage import LocalStorage
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
        
        # Path where CLI will look for the db
        self.db_path = Path(self.temp_dir) / ".contextanchor" / "local.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage at the SAME path the CLI will use
        self.storage = LocalStorage(db_path=self.db_path)
        self.storage.register_repository("repo-1", "test-repo", self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
        if self.old_home:
            os.environ["HOME"] = self.old_home

    @responses.activate
    def test_sync_command_drains_queue(self, mocker):
        # 1. Queue an operation
        payload = {
            "repository_id": "repo-1",
            "branch": "main",
            "developer_intent": "Deferred intent",
            "signals": {"uncommitted_files": []}
        }
        self.storage.queue_operation("save_context", "repo-1", payload)
        assert self.storage.count_queued_operations("repo-1") == 1

        # 2. Mock API
        responses.add(
            responses.POST,
            "https://api.contextanchor.example.com/v1/contexts",
            json={"snapshot_id": "snap-123"},
            status=201
        )

        # 3. Mocks for Git discovery
        mocker.patch("contextanchor.cli._find_git_root", return_value=Path(self.temp_dir))

        # 4. Run sync
        result = self.runner.invoke(main, ["sync"])
        
        assert result.exit_code == 0
        assert "Successfully synced 1 operations" in result.output
        assert self.storage.count_queued_operations("repo-1") == 0

    @responses.activate
    def test_auto_replay_on_save_context(self, mocker):
        # 1. Queue an operation
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
            "https://api.contextanchor.example.com/v1/contexts",
            json={"snapshot_id": "snap-old"},
            status=201
        )
        responses.add(
            responses.POST,
            "https://api.contextanchor.example.com/v1/contexts",
            json={"snapshot_id": "snap-new"},
            status=201
        )

        # 3. Mocks
        mocker.patch("contextanchor.cli._find_git_root", return_value=Path(self.temp_dir))
        
        # Mock GitObserver signals
        mocker.patch("contextanchor.git_observer.GitObserver.generate_repository_id", return_value="repo-1")
        mocker.patch("contextanchor.git_observer.GitObserver.get_current_branch", return_value="main")
        mocker.patch("contextanchor.git_observer.GitObserver.capture_uncommitted_changes", return_value=[])
        mocker.patch("contextanchor.git_observer.GitObserver.capture_commit_signal", return_value=None)

        # Mock config
        config_dir = Path(self.temp_dir) / ".contextanchor"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yaml").write_text("api_endpoint: https://api.contextanchor.example.com\nenabled_signals: []")

        # 4. Run save-context
        result = self.runner.invoke(main, ["save-context", "-m", "New intent"])
        
        assert result.exit_code == 0
        assert len(responses.calls) == 2
        assert self.storage.count_queued_operations("repo-1") == 0
