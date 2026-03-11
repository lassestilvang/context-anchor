"""
Unit tests for local storage and offline queue functionality.

Tests queue storage, retrieval, operation expiration, and cache functionality.
Validates Requirements 8.1, 8.4, 8.8.
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import sqlite3

from contextanchor.local_storage import LocalStorage
from contextanchor.models import ContextSnapshot, generate_snapshot_id


class TestLocalStorage:
    """Unit tests for LocalStorage class."""

    def setup_method(self):
        """Create temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.storage = LocalStorage(db_path=self.db_path)

    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_queue_operation_basic(self):
        """Test basic operation queuing."""
        # Requirement 8.1: Store operations locally when Context_Store unavailable
        payload = {"developer_intent": "Testing offline queue", "branch": "main", "signals": {}}

        op_id = self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload=payload
        )

        assert op_id is not None
        assert len(op_id) > 0

        # Verify operation is in queue
        pending = self.storage.get_pending_operations()
        assert len(pending) == 1
        assert pending[0].operation_id == op_id
        assert pending[0].operation_type == "save_context"
        assert pending[0].repository_id == "test_repo"
        assert pending[0].payload == payload

    def test_queue_multiple_operations(self):
        """Test queuing multiple operations."""
        # Requirement 8.4: Queue operations for retry when connectivity restored
        operations = []
        for i in range(5):
            op_id = self.storage.queue_operation(
                operation_type="save_context",
                repository_id=f"repo_{i % 2}",  # Two different repos
                payload={"sequence": i},
            )
            operations.append(op_id)

        pending = self.storage.get_pending_operations()
        assert len(pending) == 5

        # Verify all operation IDs are present
        pending_ids = [op.operation_id for op in pending]
        for op_id in operations:
            assert op_id in pending_ids

    def test_mark_operation_complete(self):
        """Test marking operations as complete."""
        op_id = self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload={"test": "data"}
        )

        # Verify operation is pending
        pending = self.storage.get_pending_operations()
        assert len(pending) == 1

        # Mark as complete
        result = self.storage.mark_operation_complete(op_id)
        assert result is True

        # Verify operation is no longer pending
        pending = self.storage.get_pending_operations()
        assert len(pending) == 0

    def test_mark_nonexistent_operation_complete(self):
        """Test marking non-existent operation as complete."""
        result = self.storage.mark_operation_complete("nonexistent_id")
        assert result is False

    def test_operation_expiration(self):
        """Test that operations expire after 24 hours."""
        # Requirement 8.7: Operations expire after 24 hours
        op_id = self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload={"test": "data"}
        )

        # Manually set expiration to past
        with sqlite3.connect(self.storage.db_path) as conn:
            past_time = datetime.now() - timedelta(hours=25)
            conn.execute(
                """
                UPDATE offline_queue
                SET expires_at = ?
                WHERE operation_id = ?
            """,
                (past_time.isoformat(), op_id),
            )
            conn.commit()

        # Verify operation is expired
        expired = self.storage.get_expired_operations()
        assert len(expired) == 1
        assert expired[0].operation_id == op_id

        # Verify expired operation is not in pending list
        pending = self.storage.get_pending_operations()
        assert len(pending) == 0

    def test_retry_operation_exponential_backoff(self):
        """Test exponential backoff calculation for retries."""
        # Requirement 8.7: Exponential backoff for retries
        self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload={"test": "data"}
        )

        pending = self.storage.get_pending_operations()
        operation = pending[0]

        # Initial state
        assert operation.retry_count == 0
        assert operation.next_retry_at is None

        # First retry: 2^1 = 2 seconds
        before = datetime.now()
        self.storage.retry_operation(operation)
        datetime.now()

        assert operation.retry_count == 1
        assert operation.next_retry_at is not None
        expected_delay = 2
        actual_delay = (operation.next_retry_at - before).total_seconds()
        assert expected_delay - 1 <= actual_delay <= expected_delay + 2

        # Second retry: 2^2 = 4 seconds
        before = datetime.now()
        self.storage.retry_operation(operation)

        assert operation.retry_count == 2
        expected_delay = 4
        actual_delay = (operation.next_retry_at - before).total_seconds()
        assert expected_delay - 1 <= actual_delay <= expected_delay + 2

    def test_retry_operation_max_backoff(self):
        """Test that backoff is capped at 3600 seconds (1 hour)."""
        self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload={"test": "data"}
        )

        pending = self.storage.get_pending_operations()
        operation = pending[0]

        # Simulate many retries to exceed max backoff
        for i in range(15):  # 2^15 = 32768 seconds, should be capped at 3600
            self.storage.retry_operation(operation)

        # Verify backoff is capped at 3600 seconds
        before = datetime.now()
        actual_delay = (operation.next_retry_at - before).total_seconds()
        assert actual_delay <= 3600

    def test_get_pending_operations_respects_retry_time(self):
        """Test that operations with future retry times are not returned."""
        op_id = self.storage.queue_operation(
            operation_type="save_context", repository_id="test_repo", payload={"test": "data"}
        )

        # Set next_retry_at to future
        with sqlite3.connect(self.storage.db_path) as conn:
            future_time = datetime.now() + timedelta(hours=1)
            conn.execute(
                """
                UPDATE offline_queue
                SET next_retry_at = ?
                WHERE operation_id = ?
            """,
                (future_time.isoformat(), op_id),
            )
            conn.commit()

        # Verify operation is not in pending list
        pending = self.storage.get_pending_operations()
        assert len(pending) == 0

    def test_count_queued_operations(self):
        """Test counting queued operations per repository."""
        # Queue operations for different repositories
        for i in range(3):
            self.storage.queue_operation(
                operation_type="save_context", repository_id="repo_a", payload={"sequence": i}
            )

        for i in range(2):
            self.storage.queue_operation(
                operation_type="save_context", repository_id="repo_b", payload={"sequence": i}
            )

        # Verify counts
        assert self.storage.count_queued_operations("repo_a") == 3
        assert self.storage.count_queued_operations("repo_b") == 2
        assert self.storage.count_queued_operations("repo_c") == 0

    def test_cleanup_expired_operations(self):
        """Test cleanup of expired operations."""
        # Create some operations
        op_ids = []
        for i in range(3):
            op_id = self.storage.queue_operation(
                operation_type="save_context", repository_id="test_repo", payload={"sequence": i}
            )
            op_ids.append(op_id)

        # Expire first two operations
        with sqlite3.connect(self.storage.db_path) as conn:
            past_time = datetime.now() - timedelta(hours=25)
            conn.execute(
                """
                UPDATE offline_queue
                SET expires_at = ?
                WHERE operation_id IN (?, ?)
            """,
                (past_time.isoformat(), op_ids[0], op_ids[1]),
            )
            conn.commit()

        # Cleanup expired operations
        removed_count = self.storage.cleanup_expired_operations()
        assert removed_count == 2

        # Verify only one operation remains
        pending = self.storage.get_pending_operations()
        assert len(pending) == 1
        assert pending[0].operation_id == op_ids[2]


class TestSnapshotCache:
    """Unit tests for snapshot caching functionality."""

    def setup_method(self):
        """Create temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.storage = LocalStorage(db_path=self.db_path)

    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_snapshot(self):
        """Test caching a context snapshot."""
        # Requirement 8.1: Cache snapshots locally
        snapshot = ContextSnapshot(
            snapshot_id=generate_snapshot_id(),
            repository_id="test_repo",
            branch="main",
            captured_at=datetime.now(),
            developer_id="dev123",
            goals="Test caching",
            rationale="Verify offline cache works",
            open_questions=["Does it work?", "Is it fast?"],
            next_steps=["Test retrieval", "Verify data"],
            relevant_files=["test.py", "cache.py"],
            related_prs=[123, 456],
            related_issues=[789],
        )

        self.storage.cache_snapshot(snapshot)

        # Retrieve cached snapshot
        cached = self.storage.get_cached_snapshot("test_repo", "main")

        assert cached is not None
        assert cached.snapshot_id == snapshot.snapshot_id
        assert cached.repository_id == snapshot.repository_id
        assert cached.branch == snapshot.branch
        assert cached.developer_id == snapshot.developer_id
        assert cached.goals == snapshot.goals
        assert cached.rationale == snapshot.rationale
        assert cached.open_questions == snapshot.open_questions
        assert cached.next_steps == snapshot.next_steps
        assert cached.relevant_files == snapshot.relevant_files
        assert cached.related_prs == snapshot.related_prs
        assert cached.related_issues == snapshot.related_issues

    def test_get_cached_snapshot_not_found(self):
        """Test retrieving non-existent cached snapshot."""
        cached = self.storage.get_cached_snapshot("nonexistent_repo", "main")
        assert cached is None

    def test_cache_multiple_snapshots_same_branch(self):
        """Test caching multiple snapshots for same branch returns most recent."""
        # Requirement 8.8: Support local history operations
        snapshots = []
        for i in range(3):
            snapshot = ContextSnapshot(
                snapshot_id=generate_snapshot_id(),
                repository_id="test_repo",
                branch="main",
                captured_at=datetime.now() + timedelta(minutes=i),
                developer_id="dev123",
                goals=f"Goal {i}",
                rationale=f"Rationale {i}",
                open_questions=[f"Question {i}"],
                next_steps=[f"Test step {i}"],
                relevant_files=[f"file{i}.py"],
                related_prs=[],
                related_issues=[],
            )
            snapshots.append(snapshot)
            self.storage.cache_snapshot(snapshot)

        # Retrieve should return most recent
        cached = self.storage.get_cached_snapshot("test_repo", "main")
        assert cached is not None
        assert cached.snapshot_id == snapshots[2].snapshot_id
        assert cached.goals == "Goal 2"

    def test_cache_snapshots_different_branches(self):
        """Test caching snapshots for different branches."""
        snapshot_main = ContextSnapshot(
            snapshot_id=generate_snapshot_id(),
            repository_id="test_repo",
            branch="main",
            captured_at=datetime.now(),
            developer_id="dev123",
            goals="Main branch work",
            rationale="Testing main",
            open_questions=["Main question"],
            next_steps=["Test main"],
            relevant_files=["main.py"],
            related_prs=[],
            related_issues=[],
        )

        snapshot_feature = ContextSnapshot(
            snapshot_id=generate_snapshot_id(),
            repository_id="test_repo",
            branch="feature/test",
            captured_at=datetime.now(),
            developer_id="dev123",
            goals="Feature branch work",
            rationale="Testing feature",
            open_questions=["Feature question"],
            next_steps=["Test feature"],
            relevant_files=["feature.py"],
            related_prs=[],
            related_issues=[],
        )

        self.storage.cache_snapshot(snapshot_main)
        self.storage.cache_snapshot(snapshot_feature)

        # Retrieve each branch separately
        cached_main = self.storage.get_cached_snapshot("test_repo", "main")
        cached_feature = self.storage.get_cached_snapshot("test_repo", "feature/test")

        assert cached_main is not None
        assert cached_main.goals == "Main branch work"

        assert cached_feature is not None
        assert cached_feature.goals == "Feature branch work"

    def test_cache_snapshot_with_deleted_at(self):
        """Test caching snapshot with deleted_at timestamp."""
        snapshot = ContextSnapshot(
            snapshot_id=generate_snapshot_id(),
            repository_id="test_repo",
            branch="main",
            captured_at=datetime.now(),
            developer_id="dev123",
            goals="Deleted snapshot",
            rationale="Testing soft delete",
            open_questions=["Is it deleted?"],
            next_steps=["Verify deletion"],
            relevant_files=["deleted.py"],
            related_prs=[],
            related_issues=[],
            deleted_at=datetime.now(),
        )

        self.storage.cache_snapshot(snapshot)

        cached = self.storage.get_cached_snapshot("test_repo", "main")
        assert cached is not None
        assert cached.deleted_at is not None
