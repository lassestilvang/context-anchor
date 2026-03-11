"""
Property-based tests for Context Store storage operations.

Tests universal properties that must hold for all storage operations.
Uses Hypothesis for comprehensive input coverage.
"""

import pytest
from hypothesis import given, settings
from unittest.mock import Mock

from src.contextanchor.context_store import ContextStore
from tests.property.test_snapshot_properties import valid_context_snapshot


@pytest.fixture
def mock_dynamodb_for_property():
    """Create mock DynamoDB resource and table for property tests."""
    mock_resource = Mock()
    mock_table = Mock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


@settings(max_examples=100)
@given(snapshot=valid_context_snapshot())
def test_property_10_context_storage_round_trip(snapshot):
    """
    Feature: context-anchor, Property 10: Context Storage Round Trip

    **Validates: Requirements 4.1**

    For any Context_Snapshot stored in the Context_Store, retrieving it by
    snapshot_id must return an equivalent snapshot with all fields preserved.

    This property ensures that:
    1. Storage preserves all snapshot fields
    2. Retrieval reconstructs the snapshot correctly
    3. No data is lost or corrupted in the round trip
    """
    # Create mock DynamoDB
    mock_resource = Mock()
    mock_table = Mock()
    mock_resource.Table.return_value = mock_table

    # Create ContextStore with mocked DynamoDB
    store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)

    # Store the snapshot
    returned_id = store.store_snapshot(snapshot)

    # Verify the snapshot_id was returned
    assert returned_id == snapshot.snapshot_id, "store_snapshot must return the snapshot_id"

    # Verify put_item was called
    assert mock_table.put_item.called, "put_item must be called to store snapshot"

    # Extract the stored item from the put_item call
    call_args = mock_table.put_item.call_args
    stored_item = call_args.kwargs["Item"]

    # Mock the query response to return the stored item
    mock_table.query.return_value = {"Items": [stored_item]}

    # Retrieve the snapshot by ID
    retrieved = store.get_snapshot_by_id(snapshot.snapshot_id)

    # Verify the snapshot was retrieved
    assert (
        retrieved is not None
    ), "get_snapshot_by_id must return a snapshot for a stored snapshot_id"

    # Verify all fields are preserved (round trip property)
    assert retrieved.snapshot_id == snapshot.snapshot_id, "snapshot_id must be preserved"
    assert retrieved.repository_id == snapshot.repository_id, "repository_id must be preserved"
    assert retrieved.branch == snapshot.branch, "branch must be preserved"
    assert retrieved.developer_id == snapshot.developer_id, "developer_id must be preserved"
    assert retrieved.goals == snapshot.goals, "goals must be preserved"
    assert retrieved.rationale == snapshot.rationale, "rationale must be preserved"
    assert retrieved.open_questions == snapshot.open_questions, "open_questions must be preserved"
    assert retrieved.next_steps == snapshot.next_steps, "next_steps must be preserved"
    assert retrieved.relevant_files == snapshot.relevant_files, "relevant_files must be preserved"
    assert retrieved.related_prs == snapshot.related_prs, "related_prs must be preserved"
    assert retrieved.related_issues == snapshot.related_issues, "related_issues must be preserved"

    # Verify timestamp is preserved (with tolerance for serialization)
    # DynamoDB stores timestamps as ISO strings, so we compare ISO representations
    assert (
        retrieved.captured_at.isoformat() == snapshot.captured_at.isoformat()
    ), "captured_at timestamp must be preserved"

    # Verify deleted_at is preserved (should be None for new snapshots)
    if snapshot.deleted_at is None:
        assert retrieved.deleted_at is None, "deleted_at must be None when not set"
    else:
        assert (
            retrieved.deleted_at.isoformat() == snapshot.deleted_at.isoformat()
        ), "deleted_at timestamp must be preserved when set"

    # Verify the stored item has correct DynamoDB structure
    assert (
        stored_item["PK"] == f"REPO#{snapshot.repository_id}"
    ), "Primary key must follow REPO# pattern"
    assert stored_item["SK"].startswith(
        f"BRANCH#{snapshot.branch}#TS#"
    ), "Sort key must follow BRANCH#branch#TS# pattern"
    assert (
        stored_item["GSI1PK"] == f"DEV#{snapshot.developer_id}"
    ), "GSI1 partition key must follow DEV# pattern"
    assert (
        stored_item["GSI2PK"] == f"SNAPSHOT#{snapshot.snapshot_id}"
    ), "GSI2 partition key must follow SNAPSHOT# pattern"

    # Verify deletion tracking fields
    assert stored_item["is_deleted"] is False, "New snapshots must have is_deleted=False"
    assert (
        "deleted_at" not in stored_item or stored_item.get("deleted_at") is None
    ), "New snapshots must not have deleted_at set"

    # Verify TTL field is present and valid
    assert (
        "retention_expires_at" in stored_item
    ), "Stored item must have retention_expires_at for TTL"
    assert isinstance(
        stored_item["retention_expires_at"], int
    ), "retention_expires_at must be an integer timestamp"
    assert (
        stored_item["retention_expires_at"] > 0
    ), "retention_expires_at must be a positive timestamp"

    # Verify query was called with correct parameters
    mock_table.query.assert_called_once()
    query_kwargs = mock_table.query.call_args.kwargs
    assert query_kwargs["IndexName"] == "BySnapshotId", "Query must use BySnapshotId GSI"

    # Verify the query filters out deleted snapshots
    assert "FilterExpression" in query_kwargs, "Query must filter out deleted snapshots"
