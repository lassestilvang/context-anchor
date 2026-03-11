"""
Unit tests for Lambda handlers.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.contextanchor import handlers
from src.contextanchor.models import ContextSnapshot
from datetime import datetime


@pytest.fixture
def mock_agent_core():
    with patch("src.contextanchor.handlers.get_agent_core") as mock:
        yield mock.return_value


@pytest.fixture
def mock_context_store():
    with patch("src.contextanchor.handlers.get_context_store") as mock:
        yield mock.return_value


def test_capture_context_handler_success(mock_agent_core, mock_context_store):
    mock_snapshot = MagicMock()
    mock_snapshot.captured_at.isoformat.return_value = "2023-10-10T10:00:00Z"
    mock_agent_core.synthesize_context.return_value = mock_snapshot
    mock_context_store.store_snapshot.return_value = "snap123"

    event = {
        "body": json.dumps(
            {
                "repository_id": "repo1",
                "branch": "main",
                "developer_intent": "fixing bugs",
                "signals": {"uncommitted_files": [{"path": "main.py", "status": "modified"}]},
            }
        )
    }

    response = handlers.capture_context_handler(event, None)
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["snapshot_id"] == "snap123"
    assert body["captured_at"] == "2023-10-10T10:00:00Z"


def test_capture_context_handler_missing_fields():
    event = {"body": json.dumps({"repository_id": "repo1"})}  # Missing branch, intent
    response = handlers.capture_context_handler(event, None)
    assert response["statusCode"] == 400
    assert "Missing required fields" in response["body"]


def test_get_latest_context_handler_success(mock_context_store):
    snapshot = ContextSnapshot(
        snapshot_id="snap123",
        repository_id="repo1",
        branch="main",
        captured_at=datetime(2023, 10, 10, 10, 0, 0),
        developer_id="dev1",
        goals="goals",
        rationale="rationale",
        open_questions=["q1"],
        next_steps=["add tests"],
        relevant_files=[],
        related_prs=[],
        related_issues=[],
        deleted_at=None
    )
    mock_context_store.get_latest_snapshot.return_value = snapshot

    event = {"queryStringParameters": {"repository_id": "repo1", "branch": "main"}}

    response = handlers.get_latest_context_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["snapshot_id"] == "snap123"


def test_get_latest_context_handler_not_found(mock_context_store):
    mock_context_store.get_latest_snapshot.return_value = None

    event = {"queryStringParameters": {"repository_id": "repo1", "branch": "main"}}

    response = handlers.get_latest_context_handler(event, None)
    assert response["statusCode"] == 404


def test_health_check_handler_success(mock_context_store):
    mock_context_store.table.table_status = "ACTIVE"

    response = handlers.health_check_handler({}, None)
    assert response["statusCode"] == 200
    assert "healthy" in response["body"]
