
import json
import pytest
from contextanchor.handlers import (
    capture_context_handler,
    get_latest_context_handler,
    list_contexts_handler,
    delete_context_handler
)

class MockContext:
    function_name = "test-function"

@pytest.fixture
def mock_aws(mocker):
    mocker.patch("boto3.resource")
    mocker.patch("boto3.client")
    # Mock DynamoDB table
    mock_table = mocker.Mock()
    mocker.patch("contextanchor.context_store.ContextStore.table", mock_table)
    return mock_table

def test_handlers_consolidated_flow(mocker):
    # Mock dependencies
    mocker.patch("contextanchor.handlers.get_agent_core")
    mock_store = mocker.patch("contextanchor.handlers.get_context_store")
    
    # Test List Contexts
    event = {
        "queryStringParameters": {"repository_id": "test-repo"}
    }
    mock_store.return_value.list_snapshots.return_value = {
        "snapshots": [],
        "count": 0
    }
    
    response = list_contexts_handler(event, MockContext())
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "snapshots" in body

def test_handler_scoping_enforcement(mocker):
    mock_store = mocker.patch("contextanchor.handlers.get_context_store")
    
    # Mock a snapshot with a specific developer_id
    mock_snapshot = mocker.Mock()
    mock_snapshot.developer_id = "dev-1"
    mock_snapshot.snapshot_id = "snap-1"
    mock_snapshot.captured_at.isoformat.return_value = "2026-03-11T00:00:00"
    # Need more fields for _snapshot_to_dict
    mock_snapshot.repository_id = "repo-1"
    mock_snapshot.branch = "main"
    mock_snapshot.goals = "test"
    mock_snapshot.rationale = "test"
    mock_snapshot.open_questions = []
    mock_snapshot.next_steps = []
    mock_snapshot.relevant_files = []
    mock_snapshot.related_prs = []
    mock_snapshot.related_issues = []
    mock_snapshot.deleted_at = None
    
    mock_store.return_value.get_snapshot_by_id.return_value = mock_snapshot
    
    # Request with WRONG developer_id
    event = {
        "pathParameters": {"snapshot_id": "snap-1"},
        "queryStringParameters": {"developer_id": "dev-2"}
    }
    
    from contextanchor.handlers import get_context_handler
    response = get_context_handler(event, MockContext())
    
    assert response["statusCode"] == 403
    assert "Access denied" in json.loads(response["body"])["error"]
