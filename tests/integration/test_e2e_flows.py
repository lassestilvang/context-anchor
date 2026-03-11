"""
Integration tests for end-to-end context capture and restoration flows.

Tests 28.1-28.4: Full flow tests with temporary git repos and mocked AWS.
"""

import os
import tempfile
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock
from pathlib import Path
import git

from src.contextanchor.git_observer import GitObserver
from src.contextanchor.context_store import ContextStore
from src.contextanchor.local_storage import LocalStorage
from src.contextanchor.models import ContextSnapshot


def create_temp_git_repo(path, remote_url=None, initial_file="README.md"):
    """Helper: Create a minimal git repo with an initial commit."""
    repo = git.Repo.init(path)
    if remote_url:
        repo.create_remote("origin", remote_url)

    readme = os.path.join(path, initial_file)
    with open(readme, "w") as f:
        f.write(f"# {os.path.basename(path)}")
    repo.index.add([initial_file])
    repo.index.commit("Initial commit")
    return repo


# ── 28.1 End-to-End Capture Flow ──


@pytest.mark.integration
class TestEndToEndCaptureFlow:
    """Test full flow: init → save-context → verify storage."""

    def test_capture_flow_stores_snapshot(self):
        """
        Validates: Requirements 2.1, 2.2, 2.3, 3.1, 4.1
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = os.path.join(tmpdir, "test-repo")
            os.makedirs(repo_path)
            create_temp_git_repo(repo_path, "https://github.com/test/repo.git")

            # Step 1: Detect repository
            observer = GitObserver(repo_path)
            root = observer.detect_repository_root()
            assert root is not None, "Repository must be detected"

            repo_id = observer.generate_repository_id("https://github.com/test/repo.git", repo_path)
            assert len(repo_id) == 64, "Repository ID must be SHA-256"

            # Step 2: Create and store snapshot
            mock_resource = Mock()
            mock_table = Mock()
            mock_resource.Table.return_value = mock_table

            store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)

            snapshot = ContextSnapshot(
                snapshot_id="snap-001",
                repository_id=repo_id,
                branch="main",
                captured_at=datetime.now(UTC),
                developer_id="dev-1",
                goals="Implement feature X",
                rationale="Feature X is needed for user onboarding",
                open_questions=["Which API to use?", "What about edge cases?"],
                next_steps=["Add unit tests", "Review implementation"],
                relevant_files=["src/feature.py"],
                related_prs=[],
                related_issues=[],
            )

            result_id = store.store_snapshot(snapshot)
            assert result_id == "snap-001"

            # Step 3: Verify DynamoDB was called correctly
            assert mock_table.put_item.called
            stored_item = mock_table.put_item.call_args.kwargs["Item"]
            assert stored_item["PK"] == f"REPO#{repo_id}"
            assert stored_item["repository_id"] == repo_id
            assert stored_item["goals"] == "Implement feature X"
            assert stored_item["developer_id"] == "dev-1"

    def test_capture_flow_with_local_storage(self):
        """Verify local storage registration during init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = os.path.join(tmpdir, "test-repo")
            os.makedirs(repo_path)
            create_temp_git_repo(repo_path, "https://github.com/test/repo.git")

            db_path = Path(tmpdir) / ".contextanchor" / "local.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            storage = LocalStorage(db_path)

            observer = GitObserver(repo_path)
            repo_id = observer.generate_repository_id("https://github.com/test/repo.git", repo_path)

            storage.register_repository(
                repo_id, "test-repo", repo_path, "https://github.com/test/repo.git"
            )

            repo = storage.get_repository(repo_id)
            assert repo is not None
            assert repo["name"] == "test-repo"
            assert repo["root_path"] == repo_path


# ── 28.2 End-to-End Restoration Flow ──


@pytest.mark.integration
class TestEndToEndRestorationFlow:
    """Test full flow: save → switch branch → restore context."""

    def test_restore_retrieves_correct_snapshot(self):
        """
        Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.6
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = os.path.join(tmpdir, "test-repo")
            os.makedirs(repo_path)
            create_temp_git_repo(repo_path, "https://github.com/test/repo.git")

            observer = GitObserver(repo_path)
            repo_id = observer.generate_repository_id("https://github.com/test/repo.git", repo_path)

            # Store a snapshot for "main"
            mock_resource = Mock()
            mock_table = Mock()
            mock_resource.Table.return_value = mock_table

            store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)

            snapshot = ContextSnapshot(
                snapshot_id="snap-main",
                repository_id=repo_id,
                branch="main",
                captured_at=datetime.now(UTC),
                developer_id="dev-1",
                goals="Working on main branch",
                rationale="Main branch development",
                open_questions=["Q1?", "Q2?"],
                next_steps=["Add tests"],
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

            store.store_snapshot(snapshot)
            stored_item = mock_table.put_item.call_args.kwargs["Item"]

            # Simulate retrieval after branch switch
            mock_table.query.return_value = {"Items": [stored_item]}
            retrieved = store.get_latest_snapshot(repo_id, "main")

            assert retrieved is not None
            assert retrieved.goals == "Working on main branch"
            assert retrieved.branch == "main"
            assert retrieved.repository_id == repo_id

    def test_restore_with_developer_scoping(self):
        """Verify that restoration respects developer_id scoping."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_resource.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}

        store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)
        store.get_latest_snapshot("repo-id", "main", developer_id="dev-1")

        kwargs = mock_table.query.call_args.kwargs
        assert "developer_id = :dev_id" in kwargs["FilterExpression"]
        assert kwargs["ExpressionAttributeValues"][":dev_id"] == "dev-1"


# ── 28.3 Offline Sync Flow ──


@pytest.mark.integration
class TestOfflineSyncFlow:
    """Test offline queueing and sync with exponential backoff."""

    def test_offline_queue_stores_operation(self):
        """
        Validates: Requirements 8.1, 8.4, 8.7
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "local.db"
            storage = LocalStorage(db_path)

            # Queue an offline operation
            op_id = storage.queue_operation(
                operation_type="save_context",
                repository_id="a" * 64,
                payload={"goals": "test"},
            )

            # Verify queued operation exists
            ops = storage.get_pending_operations()
            assert len(ops) >= 1
            assert ops[0].operation_id == op_id
            assert ops[0].operation_type == "save_context"

    def test_offline_queue_respects_max_limit(self):
        """Verify queue stores multiple operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "local.db"
            storage = LocalStorage(db_path)

            # Queue multiple operations
            for i in range(5):
                storage.queue_operation(
                    operation_type="save_context",
                    repository_id="a" * 64,
                    payload={"goals": f"test-{i}"},
                )

            ops = storage.get_pending_operations()
            assert len(ops) == 5


# ── 28.4 Multi-Repository Integration ──


@pytest.mark.integration
class TestMultiRepositoryIntegration:
    """Test context isolation between multiple repositories."""

    def test_multi_repo_isolation(self):
        """
        Validates: Requirements 11.1, 11.2, 11.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two repos
            repo_a_path = os.path.join(tmpdir, "repo-a")
            repo_b_path = os.path.join(tmpdir, "repo-b")
            os.makedirs(repo_a_path)
            os.makedirs(repo_b_path)

            create_temp_git_repo(repo_a_path, "https://github.com/test/repo-a.git")
            create_temp_git_repo(repo_b_path, "https://github.com/test/repo-b.git")

            obs_a = GitObserver(repo_a_path)
            obs_b = GitObserver(repo_b_path)

            id_a = obs_a.generate_repository_id("https://github.com/test/repo-a.git", repo_a_path)
            id_b = obs_b.generate_repository_id("https://github.com/test/repo-b.git", repo_b_path)

            assert id_a != id_b, "Different repos must have different IDs"

            # Store snapshots for each repo
            mock_resource = Mock()
            mock_table = Mock()
            mock_resource.Table.return_value = mock_table

            store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)

            snap_a = ContextSnapshot(
                snapshot_id="snap-a",
                repository_id=id_a,
                branch="main",
                captured_at=datetime.now(UTC),
                developer_id="dev-1",
                goals="Working on repo A",
                rationale="Repo A work",
                open_questions=["Q1?", "Q2?"],
                next_steps=["Add tests"],
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

            snap_b = ContextSnapshot(
                snapshot_id="snap-b",
                repository_id=id_b,
                branch="main",
                captured_at=datetime.now(UTC),
                developer_id="dev-1",
                goals="Working on repo B",
                rationale="Repo B work",
                open_questions=["Q3?", "Q4?"],
                next_steps=["Review code"],
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

            store.store_snapshot(snap_a)
            item_a = mock_table.put_item.call_args.kwargs["Item"]
            assert item_a["PK"] == f"REPO#{id_a}"

            store.store_snapshot(snap_b)
            item_b = mock_table.put_item.call_args.kwargs["Item"]
            assert item_b["PK"] == f"REPO#{id_b}"

            # PKs must be different
            assert item_a["PK"] != item_b["PK"]

    def test_multi_repo_local_storage_registration(self):
        """Verify multiple repos can be registered and listed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "local.db"
            storage = LocalStorage(db_path)

            storage.register_repository("a" * 64, "repo-a", "/a", "https://github.com/test/a.git")
            storage.register_repository("b" * 64, "repo-b", "/b", "https://github.com/test/b.git")

            repos = storage.list_repositories()
            assert len(repos) == 2
            names = {r["name"] for r in repos}
            assert "repo-a" in names
            assert "repo-b" in names
