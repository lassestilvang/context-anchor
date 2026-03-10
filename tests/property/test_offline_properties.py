"""
Property-based tests for offline queue and local storage.

Tests Properties 29 and 30 from the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from contextanchor.local_storage import LocalStorage


@st.composite
def operation_payloads(draw):
    """Generate valid operation payloads."""
    return {
        "developer_intent": draw(st.text(min_size=10, max_size=500)),
        "branch": draw(st.text(min_size=1, max_size=100)),
        "signals": {
            "uncommitted_files": draw(st.integers(min_value=0, max_value=50)),
            "recent_commits": draw(st.integers(min_value=0, max_value=10))
        }
    }


class TestOfflineQueueProperties:
    """Property-based tests for offline queue functionality."""
    
    def setup_method(self):
        """Create temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.storage = LocalStorage(db_path=self.db_path)
    
    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @given(
        operation_count=st.integers(min_value=1, max_value=250),
        payload=operation_payloads()
    )
    @settings(max_examples=100, deadline=1000)  # Allow up to 1 second per example
    def test_offline_queue_capacity(self, operation_count, payload):
        """
        Feature: context-anchor, Property 29: Offline Queue Capacity
        
        **Validates: Requirements 8.6**
        
        For any repository, the offline operation queue must accept at least 200
        operations before applying backpressure controls.
        
        This test verifies that:
        1. The queue can store at least 200 operations
        2. Operations can be queued and retrieved
        3. The count accurately reflects queued operations
        """
        # Use unique repository ID for each test run to avoid interference
        import uuid
        repository_id = "test_repo_" + str(uuid.uuid4())[:8]
        
        # Queue operations
        operation_ids = []
        for i in range(operation_count):
            op_id = self.storage.queue_operation(
                operation_type="save_context",
                repository_id=repository_id,
                payload={**payload, "sequence": i}
            )
            operation_ids.append(op_id)
        
        # Verify all operations were queued
        assert len(operation_ids) == operation_count
        
        # Verify count matches
        count = self.storage.count_queued_operations(repository_id)
        assert count == operation_count
        
        # Verify we can retrieve pending operations
        pending = self.storage.get_pending_operations()
        pending_for_repo = [op for op in pending if op.repository_id == repository_id]
        assert len(pending_for_repo) == operation_count
        
        # Property: Queue must accept at least 200 operations
        if operation_count <= 200:
            # All operations should be successfully queued
            assert count == operation_count
            assert len(pending_for_repo) == operation_count

    @given(
        retry_count=st.integers(min_value=0, max_value=15),
        payload=operation_payloads()
    )
    @settings(max_examples=100, deadline=1000)  # Allow up to 1 second per example
    def test_exponential_backoff_and_expiration(self, retry_count, payload):
        """
        Feature: context-anchor, Property 30: Exponential Backoff and Expiration
        
        **Validates: Requirements 8.7**
        
        For any queued operation, retries must use exponential backoff, and the
        operation must expire after 24 hours with a recovery message surfaced to
        the user.
        
        This test verifies that:
        1. Exponential backoff is calculated correctly (2^n seconds, max 3600)
        2. Operations expire after 24 hours
        3. next_retry_at is set appropriately
        """
        repository_id = "test_repo_backoff"
        
        # Queue an operation
        op_id = self.storage.queue_operation(
            operation_type="save_context",
            repository_id=repository_id,
            payload=payload
        )
        
        # Get the operation
        pending = self.storage.get_pending_operations()
        operation = next(op for op in pending if op.operation_id == op_id)
        
        # Verify initial state
        assert operation.retry_count == 0
        assert operation.next_retry_at is None
        
        # Verify expiration is set to 24 hours from creation
        expected_expiration = operation.created_at + timedelta(hours=24)
        assert abs((operation.expires_at - expected_expiration).total_seconds()) < 1
        
        # Simulate retries and verify exponential backoff
        for i in range(retry_count):
            before_retry = datetime.now()
            self.storage.retry_operation(operation)
            after_retry = datetime.now()
            
            # Verify retry count incremented
            assert operation.retry_count == i + 1
            
            # Verify exponential backoff calculation
            expected_backoff = min(2 ** (i + 1), 3600)
            assert operation.next_retry_at is not None
            
            # next_retry_at should be approximately now + backoff_seconds
            time_diff = (operation.next_retry_at - before_retry).total_seconds()
            
            # Allow some tolerance for execution time
            assert expected_backoff - 1 <= time_diff <= expected_backoff + 2
            
            # Verify backoff doesn't exceed 1 hour (3600 seconds) with small tolerance
            assert time_diff <= 3601  # Allow 1 second tolerance for floating point
        
        # Test expiration detection
        # Create an operation that's already expired
        expired_op_id = self.storage.queue_operation(
            operation_type="save_context",
            repository_id=repository_id,
            payload=payload
        )
        
        # Manually update the database to set expiration in the past
        import sqlite3
        with sqlite3.connect(self.storage.db_path) as conn:
            past_time = datetime.now() - timedelta(hours=25)
            conn.execute("""
                UPDATE offline_queue
                SET expires_at = ?
                WHERE operation_id = ?
            """, (past_time.isoformat(), expired_op_id))
            conn.commit()
        
        # Verify expired operations are detected
        expired_ops = self.storage.get_expired_operations()
        expired_ids = [op.operation_id for op in expired_ops]
        assert expired_op_id in expired_ids
        
        # Verify expired operations are not in pending list
        pending = self.storage.get_pending_operations()
        pending_ids = [op.operation_id for op in pending]
        assert expired_op_id not in pending_ids
