"""
Property tests for Lambda handlers
"""

import json
from unittest.mock import patch
from hypothesis import given, settings, strategies as st
from src.contextanchor import handlers


@patch("src.contextanchor.handlers.get_agent_core")
@patch("src.contextanchor.handlers.get_context_store")
@given(
    repository_id=st.text(min_size=1, max_size=100),
    branch=st.text(min_size=1, max_size=100),
    intent=st.text(min_size=1, max_size=500),
)
@settings(max_examples=50)
def test_capture_handler_required_fields(mock_store, mock_agent, repository_id, branch, intent):
    """Property: Capture handler rejects missing required fields but accepts valid minimally required ones."""
    # Test missing fields
    event = {"body": json.dumps({"repository_id": repository_id})}
    resp = handlers.capture_context_handler(event, None)
    assert resp["statusCode"] == 400
    assert "Missing required fields" in resp["body"]

    event = {"body": json.dumps({"branch": branch, "developer_intent": intent})}
    resp = handlers.capture_context_handler(event, None)
    assert resp["statusCode"] == 400
    assert "Missing required fields" in resp["body"]
