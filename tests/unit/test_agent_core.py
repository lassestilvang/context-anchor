"""
Unit tests for AgentCore
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock

from contextanchor.agent_core import AgentCore
from contextanchor.models import CaptureSignals, FileChange, CommitInfo


@pytest.fixture
def mock_bedrock():
    mock = Mock()
    mock_body = MagicMock()

    valid_response = {
        "content": [
            {
                "text": json.dumps(
                    {
                        "goals": "Implement feature X",
                        "rationale": "Customer request",
                        "open_questions": ["How to scale?"],
                        "next_steps": ["implement the api", "test the endpoints"],
                    }
                )
            }
        ]
    }
    mock_body.read.return_value = json.dumps(valid_response).encode("utf-8")
    mock.invoke_model.return_value = {"body": mock_body}
    return mock


@pytest.fixture
def sample_signals():
    return CaptureSignals(
        repository_id="repo123",
        branch="main",
        uncommitted_files=[
            FileChange(path="src/main.py", status="modified", lines_added=10, lines_deleted=5)
        ],
        recent_commits=[
            CommitInfo(
                hash="abc",
                message="Initial commit",
                timestamp=datetime.utcnow(),
                files_changed=["README.md"],
            )
        ],
        pr_references=[12],
        issue_references=[34],
        github_metadata=None,
        capture_source="cli",
    )


def test_synthesize_context_success(mock_bedrock, sample_signals):
    agent = AgentCore(bedrock_client=mock_bedrock)
    snapshot = agent.synthesize_context(
        repository_id="repo123",
        branch="main",
        developer_id="dev1",
        intent="Working on user auth",
        signals=sample_signals,
    )

    assert snapshot.repository_id == "repo123"
    assert snapshot.goals == "Implement feature X"
    assert "implement the api" in snapshot.next_steps
    assert "src/main.py" in snapshot.relevant_files
    assert "README.md" in snapshot.relevant_files
    assert snapshot.related_prs == [12]
    assert snapshot.related_issues == [34]


def test_synthesize_context_validation_failure(mock_bedrock, sample_signals):
    # Mock invalid next step verb
    invalid_response = {
        "content": [
            {
                "text": json.dumps(
                    {
                        "goals": "Implement feature X",
                        "rationale": "Customer request",
                        "open_questions": [],
                        "next_steps": ["invalidverb something"],
                    }
                )
            }
        ]
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(invalid_response).encode("utf-8")
    mock_bedrock.invoke_model.return_value = {"body": mock_body}

    agent = AgentCore(bedrock_client=mock_bedrock)
    with pytest.raises(ValueError, match="Failed to synthesize context or validation failed:"):
        agent.synthesize_context(
            repository_id="repo123",
            branch="main",
            developer_id="dev1",
            intent="Working on user auth",
            signals=sample_signals,
        )


def test_parse_bedrock_response_with_conversational_text(mock_bedrock, sample_signals):
    noisy_response = {
        "content": [
            {
                "text": "Here is the JSON you requested:\n```json\n"
                + json.dumps(
                    {
                        "goals": "Implement feature X",
                        "rationale": "Customer request",
                        "open_questions": [],
                        "next_steps": ["fix bugs"],
                    }
                )
                + "\n```\nHope this helps!"
            }
        ]
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(noisy_response).encode("utf-8")
    mock_bedrock.invoke_model.return_value = {"body": mock_body}

    agent = AgentCore(bedrock_client=mock_bedrock)
    snapshot = agent.synthesize_context(
        repository_id="repo123",
        branch="main",
        developer_id="dev1",
        intent="intent",
        signals=sample_signals,
    )
    assert snapshot.goals == "Implement feature X"


def test_synthesize_context_api_error(mock_bedrock, sample_signals):
    mock_bedrock.invoke_model.side_effect = Exception("AWS API Error")
    agent = AgentCore(bedrock_client=mock_bedrock)
    with pytest.raises(
        ValueError, match="Failed to synthesize context or validation failed: AWS API Error"
    ):
        agent.synthesize_context(
            repository_id="repo123",
            branch="main",
            developer_id="dev1",
            intent="Working on user auth",
            signals=sample_signals,
        )
