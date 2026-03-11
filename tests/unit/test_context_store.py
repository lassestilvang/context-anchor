"""
Unit tests for ContextStore component.

Tests basic CRUD operations, pagination, and error handling.
Requirements: 4.1, 4.2, 4.3, 4.5, 12.6
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
import json
import base64

from contextanchor import ContextStore, ContextSnapshot
from contextanchor.models import generate_snapshot_id


@pytest.fixture
def mock_dynamodb():
    """Create mock DynamoDB resource and table."""
    mock_resource = Mock()
    mock_table = Mock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


@pytest.fixture
def context_store(mock_dynamodb):
    """Create ContextStore with mocked DynamoDB."""
    mock_resource, mock_table = mock_dynamodb
    store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)
    return store, mock_table


@pytest.fixture
def sample_snapshot():
    """Create a sample ContextSnapshot for testing."""
    return ContextSnapshot(
        snapshot_id=generate_snapshot_id(),
        repository_id="a" * 64,  # SHA-256 hash format
        branch="main",
        captured_at=datetime.utcnow(),
        developer_id="dev123",
        goals="Implement user authentication",
        rationale="Users need secure access to the application",
        open_questions=["Which OAuth provider to use?", "How to handle token refresh?"],
        next_steps=["Add login endpoint", "Implement JWT validation"],
        relevant_files=["src/auth.py", "src/middleware.py"],
        related_prs=[123, 456],
        related_issues=[789],
    )


class TestContextStoreInitialization:
    """Test ContextStore initialization."""

    def test_init_with_table_name(self, mock_dynamodb):
        """Test initialization with explicit table name."""
        mock_resource, _ = mock_dynamodb
        store = ContextStore(table_name="CustomTable", dynamodb_resource=mock_resource)

        assert store.table_name == "CustomTable"
        mock_resource.Table.assert_called_once_with("CustomTable")

    def test_init_with_env_var(self, mock_dynamodb, monkeypatch):
        """Test initialization with TABLE_NAME environment variable."""
        monkeypatch.setenv("TABLE_NAME", "EnvTable")
        mock_resource, _ = mock_dynamodb
        store = ContextStore(dynamodb_resource=mock_resource)

        assert store.table_name == "EnvTable"

    def test_init_default_table_name(self, mock_dynamodb, monkeypatch):
        """Test initialization with default table name."""
        monkeypatch.delenv("TABLE_NAME", raising=False)
        mock_resource, _ = mock_dynamodb
        store = ContextStore(dynamodb_resource=mock_resource)

        assert store.table_name == "ContextSnapshots"


class TestStoreSnapshot:
    """Test store_snapshot method."""

    def test_store_snapshot_success(self, context_store, sample_snapshot):
        """Test successful snapshot storage."""
        store, mock_table = context_store

        snapshot_id = store.store_snapshot(sample_snapshot)

        # Verify snapshot_id is returned
        assert snapshot_id == sample_snapshot.snapshot_id

        # Verify put_item was called
        mock_table.put_item.assert_called_once()

        # Verify item structure
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        # Check primary keys
        assert item["PK"] == f"REPO#{sample_snapshot.repository_id}"
        assert item["SK"].startswith(f"BRANCH#{sample_snapshot.branch}#TS#")

        # Check GSI keys
        assert item["GSI1PK"] == f"DEV#{sample_snapshot.developer_id}"
        assert item["GSI2PK"] == f"SNAPSHOT#{sample_snapshot.snapshot_id}"

        # Check attributes
        assert item["snapshot_id"] == sample_snapshot.snapshot_id
        assert item["repository_id"] == sample_snapshot.repository_id
        assert item["branch"] == sample_snapshot.branch
        assert item["developer_id"] == sample_snapshot.developer_id
        assert item["goals"] == sample_snapshot.goals
        assert item["rationale"] == sample_snapshot.rationale
        assert item["open_questions"] == sample_snapshot.open_questions
        assert item["next_steps"] == sample_snapshot.next_steps
        assert item["relevant_files"] == sample_snapshot.relevant_files
        assert item["related_prs"] == sample_snapshot.related_prs
        assert item["related_issues"] == sample_snapshot.related_issues

        # Check deletion tracking
        assert item["is_deleted"] is False
        assert "deleted_at" not in item

        # Check TTL
        assert "retention_expires_at" in item
        assert item["retention_expires_at"] > 0

    def test_store_snapshot_with_deleted_at(self, context_store, sample_snapshot):
        """Test storing a snapshot with deleted_at timestamp."""
        store, mock_table = context_store

        # Set deleted_at
        sample_snapshot.deleted_at = datetime.utcnow()

        store.store_snapshot(sample_snapshot)

        # Verify item includes deletion fields
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["is_deleted"] is True
        assert "deleted_at" in item
        assert "purge_after_delete_at" in item


class TestGetSnapshotById:
    """Test get_snapshot_by_id method."""

    def test_get_snapshot_by_id_found(self, context_store, sample_snapshot):
        """Test retrieving an existing snapshot by ID."""
        store, mock_table = context_store

        # Mock query response
        mock_table.query.return_value = {
            "Items": [
                {
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "repository_id": sample_snapshot.repository_id,
                    "branch": sample_snapshot.branch,
                    "developer_id": sample_snapshot.developer_id,
                    "captured_at": sample_snapshot.captured_at.isoformat(),
                    "goals": sample_snapshot.goals,
                    "rationale": sample_snapshot.rationale,
                    "open_questions": sample_snapshot.open_questions,
                    "next_steps": sample_snapshot.next_steps,
                    "relevant_files": sample_snapshot.relevant_files,
                    "related_prs": sample_snapshot.related_prs,
                    "related_issues": sample_snapshot.related_issues,
                    "is_deleted": False,
                }
            ]
        }

        result = store.get_snapshot_by_id(sample_snapshot.snapshot_id)

        # Verify query was called with correct parameters
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs["IndexName"] == "BySnapshotId"

        # Verify result
        assert result is not None
        assert result.snapshot_id == sample_snapshot.snapshot_id
        assert result.repository_id == sample_snapshot.repository_id
        assert result.branch == sample_snapshot.branch
        assert result.goals == sample_snapshot.goals

    def test_get_snapshot_by_id_not_found(self, context_store):
        """Test retrieving a non-existent snapshot."""
        store, mock_table = context_store

        # Mock empty response
        mock_table.query.return_value = {"Items": []}

        result = store.get_snapshot_by_id("nonexistent-id")

        assert result is None

    def test_get_snapshot_by_id_filters_deleted(self, context_store):
        """Test that deleted snapshots are not returned."""
        store, mock_table = context_store

        # Mock response with deleted snapshot
        mock_table.query.return_value = {"Items": []}

        result = store.get_snapshot_by_id("deleted-snapshot-id")

        # Verify filter expression excludes deleted items
        call_kwargs = mock_table.query.call_args.kwargs
        assert "FilterExpression" in call_kwargs

        assert result is None


class TestGetLatestSnapshot:
    """Test get_latest_snapshot method."""

    def test_get_latest_snapshot_found(self, context_store, sample_snapshot):
        """Test retrieving the latest snapshot for a branch."""
        store, mock_table = context_store

        # Mock query response
        mock_table.query.return_value = {
            "Items": [
                {
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "repository_id": sample_snapshot.repository_id,
                    "branch": sample_snapshot.branch,
                    "developer_id": sample_snapshot.developer_id,
                    "captured_at": sample_snapshot.captured_at.isoformat(),
                    "goals": sample_snapshot.goals,
                    "rationale": sample_snapshot.rationale,
                    "open_questions": sample_snapshot.open_questions,
                    "next_steps": sample_snapshot.next_steps,
                    "relevant_files": sample_snapshot.relevant_files,
                    "related_prs": sample_snapshot.related_prs,
                    "related_issues": sample_snapshot.related_issues,
                    "is_deleted": False,
                }
            ]
        }

        result = store.get_latest_snapshot(sample_snapshot.repository_id, sample_snapshot.branch)

        # Verify query parameters
        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs["ScanIndexForward"] is False  # Descending order
        assert call_kwargs["Limit"] == 1

        # Verify result
        assert result is not None
        assert result.snapshot_id == sample_snapshot.snapshot_id

    def test_get_latest_snapshot_not_found(self, context_store):
        """Test retrieving latest snapshot when none exists."""
        store, mock_table = context_store

        # Mock empty response
        mock_table.query.return_value = {"Items": []}

        result = store.get_latest_snapshot("repo123", "feature-branch")

        assert result is None


class TestListSnapshots:
    """Test list_snapshots method."""

    def test_list_snapshots_basic(self, context_store, sample_snapshot):
        """Test listing snapshots without filters."""
        store, mock_table = context_store

        # Mock query response
        mock_table.query.return_value = {
            "Items": [
                {
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "repository_id": sample_snapshot.repository_id,
                    "branch": sample_snapshot.branch,
                    "developer_id": sample_snapshot.developer_id,
                    "captured_at": sample_snapshot.captured_at.isoformat(),
                    "goals": sample_snapshot.goals,
                    "rationale": sample_snapshot.rationale,
                    "open_questions": sample_snapshot.open_questions,
                    "next_steps": sample_snapshot.next_steps,
                    "relevant_files": sample_snapshot.relevant_files,
                    "related_prs": sample_snapshot.related_prs,
                    "related_issues": sample_snapshot.related_issues,
                    "is_deleted": False,
                }
            ]
        }

        result = store.list_snapshots(sample_snapshot.repository_id)

        # Verify result structure
        assert "snapshots" in result
        assert "count" in result
        assert result["count"] == 1
        assert len(result["snapshots"]) == 1
        assert result["snapshots"][0].snapshot_id == sample_snapshot.snapshot_id

    def test_list_snapshots_with_branch_filter(self, context_store):
        """Test listing snapshots filtered by branch."""
        store, mock_table = context_store

        mock_table.query.return_value = {"Items": []}

        store.list_snapshots("repo123", branch="main")

        # Verify query includes branch filter
        call_kwargs = mock_table.query.call_args.kwargs
        # KeyConditionExpression should include branch prefix
        assert "KeyConditionExpression" in call_kwargs

    def test_list_snapshots_with_pagination(self, context_store):
        """Test listing snapshots with pagination token."""
        store, mock_table = context_store

        # Create pagination token
        last_key = {"PK": "REPO#test", "SK": "BRANCH#main#TS#2024-01-01"}
        next_token = base64.b64encode(json.dumps(last_key).encode()).decode()

        mock_table.query.return_value = {"Items": []}

        store.list_snapshots("repo123", next_token=next_token)

        # Verify ExclusiveStartKey was set
        call_kwargs = mock_table.query.call_args.kwargs
        assert "ExclusiveStartKey" in call_kwargs
        assert call_kwargs["ExclusiveStartKey"] == last_key

    def test_list_snapshots_returns_next_token(self, context_store, sample_snapshot):
        """Test that next_token is returned when more results exist."""
        store, mock_table = context_store

        # Mock response with LastEvaluatedKey
        mock_table.query.return_value = {
            "Items": [
                {
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "repository_id": sample_snapshot.repository_id,
                    "branch": sample_snapshot.branch,
                    "developer_id": sample_snapshot.developer_id,
                    "captured_at": sample_snapshot.captured_at.isoformat(),
                    "goals": sample_snapshot.goals,
                    "rationale": sample_snapshot.rationale,
                    "open_questions": sample_snapshot.open_questions,
                    "next_steps": sample_snapshot.next_steps,
                    "relevant_files": sample_snapshot.relevant_files,
                    "related_prs": sample_snapshot.related_prs,
                    "related_issues": sample_snapshot.related_issues,
                    "is_deleted": False,
                }
            ],
            "LastEvaluatedKey": {"PK": "REPO#test", "SK": "BRANCH#main#TS#2024-01-01"},
        }

        result = store.list_snapshots("repo123")

        # Verify next_token is present
        assert "next_token" in result
        assert result["next_token"] is not None

    def test_list_snapshots_limit_enforcement(self, context_store):
        """Test that limit is capped at 100."""
        store, mock_table = context_store

        mock_table.query.return_value = {"Items": []}

        # Request more than max limit
        store.list_snapshots("repo123", limit=500)

        # Verify limit was capped
        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs["Limit"] == 100

    def test_list_snapshots_empty_result(self, context_store):
        """Test listing snapshots when none exist."""
        store, mock_table = context_store

        mock_table.query.return_value = {"Items": []}

        result = store.list_snapshots("repo123")

        assert result["count"] == 0
        assert len(result["snapshots"]) == 0
        assert "next_token" not in result

    def test_list_snapshots_invalid_token(self, context_store):
        """Test that invalid pagination token is ignored."""
        store, mock_table = context_store

        mock_table.query.return_value = {"Items": []}

        # Use invalid token
        store.list_snapshots("repo123", next_token="invalid-token")

        # Should not raise error, just ignore token
        call_kwargs = mock_table.query.call_args.kwargs
        assert "ExclusiveStartKey" not in call_kwargs


class TestItemToSnapshot:
    """Test _item_to_snapshot conversion method."""

    def test_item_to_snapshot_complete(self, context_store, sample_snapshot):
        """Test converting complete DynamoDB item to snapshot."""
        store, _ = context_store

        item = {
            "snapshot_id": sample_snapshot.snapshot_id,
            "repository_id": sample_snapshot.repository_id,
            "branch": sample_snapshot.branch,
            "developer_id": sample_snapshot.developer_id,
            "captured_at": sample_snapshot.captured_at.isoformat(),
            "goals": sample_snapshot.goals,
            "rationale": sample_snapshot.rationale,
            "open_questions": sample_snapshot.open_questions,
            "next_steps": sample_snapshot.next_steps,
            "relevant_files": sample_snapshot.relevant_files,
            "related_prs": sample_snapshot.related_prs,
            "related_issues": sample_snapshot.related_issues,
        }

        result = store._item_to_snapshot(item)

        assert result.snapshot_id == sample_snapshot.snapshot_id
        assert result.repository_id == sample_snapshot.repository_id
        assert result.branch == sample_snapshot.branch
        assert result.developer_id == sample_snapshot.developer_id
        assert result.goals == sample_snapshot.goals
        assert result.rationale == sample_snapshot.rationale
        assert result.open_questions == sample_snapshot.open_questions
        assert result.next_steps == sample_snapshot.next_steps
        assert result.relevant_files == sample_snapshot.relevant_files
        assert result.related_prs == sample_snapshot.related_prs
        assert result.related_issues == sample_snapshot.related_issues
        assert result.deleted_at is None

    def test_item_to_snapshot_with_deleted_at(self, context_store, sample_snapshot):
        """Test converting item with deleted_at timestamp."""
        store, _ = context_store

        deleted_time = datetime.utcnow()
        item = {
            "snapshot_id": sample_snapshot.snapshot_id,
            "repository_id": sample_snapshot.repository_id,
            "branch": sample_snapshot.branch,
            "developer_id": sample_snapshot.developer_id,
            "captured_at": sample_snapshot.captured_at.isoformat(),
            "goals": sample_snapshot.goals,
            "rationale": sample_snapshot.rationale,
            "open_questions": sample_snapshot.open_questions,
            "next_steps": sample_snapshot.next_steps,
            "relevant_files": sample_snapshot.relevant_files,
            "related_prs": sample_snapshot.related_prs,
            "related_issues": sample_snapshot.related_issues,
            "deleted_at": deleted_time.isoformat(),
        }

        result = store._item_to_snapshot(item)

        assert result.deleted_at is not None
        assert result.deleted_at.isoformat() == deleted_time.isoformat()
        """Tests for soft_delete_snapshot method."""


class TestSoftDeleteSnapshot:
    """Tests for soft_delete_snapshot method."""

    def test_soft_delete_snapshot_success(self, context_store, sample_snapshot):
        """Test successful soft deletion of a snapshot."""
        store, mock_table = context_store

        # Mock the query response for finding the snapshot
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}",
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "repository_id": sample_snapshot.repository_id,
                    "branch": sample_snapshot.branch,
                    "developer_id": sample_snapshot.developer_id,
                    "captured_at": sample_snapshot.captured_at.isoformat(),
                    "goals": sample_snapshot.goals,
                    "rationale": sample_snapshot.rationale,
                    "open_questions": sample_snapshot.open_questions,
                    "next_steps": sample_snapshot.next_steps,
                    "relevant_files": sample_snapshot.relevant_files,
                    "related_prs": sample_snapshot.related_prs,
                    "related_issues": sample_snapshot.related_issues,
                    "is_deleted": False,
                }
            ]
        }

        # Soft delete it
        result = store.soft_delete_snapshot(sample_snapshot.snapshot_id)

        # Verify result
        assert result["deleted"] is True
        assert result["snapshot_id"] == sample_snapshot.snapshot_id
        assert "purge_after" in result

        # Verify update_item was called
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert (
            call_kwargs["UpdateExpression"]
            == "SET is_deleted = :true, deleted_at = :deleted_at, purge_after_delete_at = :purge_after"
        )

    def test_soft_delete_snapshot_not_found(self, context_store):
        """Test soft deletion of non-existent snapshot."""
        store, mock_table = context_store

        # Mock empty response
        mock_table.query.return_value = {"Items": []}

        result = store.soft_delete_snapshot("non-existent-id")

        assert result["deleted"] is False
        assert "error" in result
        assert result["error"] == "Snapshot not found"
        assert result["snapshot_id"] == "non-existent-id"

    def test_soft_delete_sets_correct_fields(self, context_store, sample_snapshot):
        """Test that soft delete sets is_deleted, deleted_at, and purge_after_delete_at."""
        store, mock_table = context_store

        # Mock the query response
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}",
                    "snapshot_id": sample_snapshot.snapshot_id,
                }
            ]
        }

        # Soft delete it
        store.soft_delete_snapshot(sample_snapshot.snapshot_id)

        # Verify update_item was called with correct parameters
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs

        assert "Key" in call_kwargs
        assert call_kwargs["Key"]["PK"] == f"REPO#{sample_snapshot.repository_id}"
        assert (
            call_kwargs["Key"]["SK"]
            == f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}"
        )

        assert (
            call_kwargs["UpdateExpression"]
            == "SET is_deleted = :true, deleted_at = :deleted_at, purge_after_delete_at = :purge_after"
        )

        # Verify the expression attribute values
        values = call_kwargs["ExpressionAttributeValues"]
        assert values[":true"] is True
        assert ":deleted_at" in values
        assert ":purge_after" in values

        # Verify purge_after is approximately 7 days from deleted_at
        deleted_at_str = values[":deleted_at"]
        purge_after = values[":purge_after"]
        deleted_at = datetime.fromisoformat(deleted_at_str)
        expected_purge = deleted_at.timestamp() + (7 * 24 * 60 * 60)

        # Allow 1 second tolerance
        assert abs(purge_after - expected_purge) < 1

    def test_soft_delete_multiple_snapshots(self, context_store, sample_snapshot):
        """Test soft deleting multiple snapshots independently."""
        from datetime import timedelta

        store, mock_table = context_store

        # Create second snapshot
        _ = ContextSnapshot(
            snapshot_id="test-snapshot-2",
            repository_id=sample_snapshot.repository_id,
            branch=sample_snapshot.branch,
            developer_id=sample_snapshot.developer_id,
            captured_at=sample_snapshot.captured_at + timedelta(hours=1),
            goals="Different goals",
            rationale="Different rationale",
            open_questions=["Question 1"],
            next_steps=["Fix something"],
            relevant_files=["file2.py"],
            related_prs=[],
            related_issues=[],
        )

        # Mock query response for first snapshot
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}",
                    "snapshot_id": sample_snapshot.snapshot_id,
                }
            ]
        }

        # Soft delete only the first one
        result1 = store.soft_delete_snapshot(sample_snapshot.snapshot_id)
        assert result1["deleted"] is True

        # Verify update_item was called
        assert mock_table.update_item.called


class TestPurgeDeletedSnapshots:
    """Tests for purge_deleted_snapshots method."""

    def test_purge_deleted_snapshots_removes_expired(self, context_store, sample_snapshot):
        """Test that purge removes snapshots past their purge deadline."""
        from datetime import timedelta

        store, mock_table = context_store

        # Mock scan response with one expired snapshot
        past_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        mock_table.scan.return_value = {
            "Items": [
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}",
                    "snapshot_id": sample_snapshot.snapshot_id,
                    "is_deleted": True,
                    "deleted_at": (datetime.utcnow() - timedelta(days=8)).isoformat(),
                    "purge_after_delete_at": past_timestamp,
                }
            ]
        }

        # Run purge
        purged_count = store.purge_deleted_snapshots()

        # Verify the snapshot was purged
        assert purged_count == 1

        # Verify delete_item was called
        mock_table.delete_item.assert_called_once()
        call_kwargs = mock_table.delete_item.call_args.kwargs
        assert "Key" in call_kwargs
        assert call_kwargs["Key"]["PK"] == f"REPO#{sample_snapshot.repository_id}"

    def test_purge_deleted_snapshots_keeps_recent(self, context_store, sample_snapshot):
        """Test that purge keeps snapshots not yet past their deadline."""
        from datetime import timedelta

        store, mock_table = context_store

        # Mock scan response with no expired snapshots (future purge deadline)
        _ = int((datetime.utcnow() + timedelta(days=6)).timestamp())
        mock_table.scan.return_value = {
            "Items": []  # Filter expression excludes items with future purge_after_delete_at
        }

        # Run purge
        purged_count = store.purge_deleted_snapshots()

        # Verify nothing was purged
        assert purged_count == 0
        mock_table.delete_item.assert_not_called()

    def test_purge_deleted_snapshots_keeps_active(self, context_store, sample_snapshot):
        """Test that purge doesn't affect active (non-deleted) snapshots."""
        store, mock_table = context_store

        # Mock scan response with no items (active snapshots don't have purge_after_delete_at)
        mock_table.scan.return_value = {"Items": []}

        # Run purge
        purged_count = store.purge_deleted_snapshots()

        # Verify nothing was purged
        assert purged_count == 0
        mock_table.delete_item.assert_not_called()

    def test_purge_deleted_snapshots_multiple(self, context_store, sample_snapshot):
        """Test purging multiple expired snapshots."""
        from datetime import timedelta

        store, mock_table = context_store

        # Mock scan response with multiple expired snapshots
        past_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        mock_table.scan.return_value = {
            "Items": [
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{sample_snapshot.captured_at.isoformat()}",
                    "snapshot_id": "test-snapshot-0",
                    "purge_after_delete_at": past_timestamp,
                },
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{(sample_snapshot.captured_at + timedelta(hours=1)).isoformat()}",
                    "snapshot_id": "test-snapshot-1",
                    "purge_after_delete_at": past_timestamp,
                },
                {
                    "PK": f"REPO#{sample_snapshot.repository_id}",
                    "SK": f"BRANCH#{sample_snapshot.branch}#TS#{(sample_snapshot.captured_at + timedelta(hours=2)).isoformat()}",
                    "snapshot_id": "test-snapshot-2",
                    "purge_after_delete_at": past_timestamp,
                },
            ]
        }

        # Run purge
        purged_count = store.purge_deleted_snapshots()

        # Verify all were purged
        assert purged_count == 3
        assert mock_table.delete_item.call_count == 3

    def test_purge_deleted_snapshots_empty_table(self, context_store):
        """Test purge on empty table returns 0."""
        store, mock_table = context_store

        # Mock empty scan response
        mock_table.scan.return_value = {"Items": []}

        purged_count = store.purge_deleted_snapshots()
        assert purged_count == 0
        mock_table.delete_item.assert_not_called()
