import pytest
from unittest.mock import Mock, MagicMock
from src.contextanchor.context_store import ContextStore


@pytest.fixture
def mock_table():
    return MagicMock()


@pytest.fixture
def store(mock_table):
    resource = Mock()
    resource.Table.return_value = mock_table
    return ContextStore(table_name="TestTable", dynamodb_resource=resource)


def test_get_latest_snapshot_with_developer_filter(store, mock_table):
    # Setup mock response
    mock_table.query.return_value = {"Items": []}

    # Call with developer_id
    store.get_latest_snapshot("repo-1", "main", developer_id="dev-1")

    # Verify query arguments
    args, kwargs = mock_table.query.call_args
    assert "FilterExpression" in kwargs
    assert "developer_id = :dev_id" in kwargs["FilterExpression"]
    assert kwargs["ExpressionAttributeValues"][":dev_id"] == "dev-1"


def test_get_latest_snapshot_without_developer_filter(store, mock_table):
    # Setup mock response
    mock_table.query.return_value = {"Items": []}

    # Call without developer_id
    store.get_latest_snapshot("repo-1", "main")

    # Verify query arguments
    args, kwargs = mock_table.query.call_args
    assert "FilterExpression" in kwargs
    # Should NOT have developer_id filter
    assert "developer_id" not in kwargs["FilterExpression"]
    assert ":dev_id" not in kwargs["ExpressionAttributeValues"]


def test_list_snapshots_with_developer_filter(store, mock_table):
    # Setup mock response
    mock_table.query.return_value = {"Items": [], "Count": 0}

    # Call with developer_id
    store.list_snapshots("repo-1", developer_id="dev-1")

    # Verify query arguments
    args, kwargs = mock_table.query.call_args
    assert "FilterExpression" in kwargs
    assert "developer_id = :dev_id" in kwargs["FilterExpression"]
    assert kwargs["ExpressionAttributeValues"][":dev_id"] == "dev-1"


def test_list_snapshots_without_developer_filter(store, mock_table):
    # Setup mock response
    mock_table.query.return_value = {"Items": [], "Count": 0}

    # Call without developer_id
    store.list_snapshots("repo-1")

    # Verify query arguments
    args, kwargs = mock_table.query.call_args
    assert "FilterExpression" in kwargs
    assert "developer_id" not in kwargs["FilterExpression"]
