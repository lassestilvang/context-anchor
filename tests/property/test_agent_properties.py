"""
Property tests for Agent Core
"""

from hypothesis import given, settings, strategies as st
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock
import json

from src.contextanchor.agent_core import AgentCore
from src.contextanchor.models import CaptureSignals, FileChange, CommitInfo


@st.composite
def capture_signals_strategy(draw):
    repo_id = draw(st.text(min_size=1, max_size=10, alphabet="abcdef0123456789"))
    branch = draw(st.text(min_size=1, max_size=10, alphabet="abcdef"))

    # Generate random paths
    paths = draw(st.lists(st.text(min_size=1, alphabet="abc", max_size=5), max_size=5, unique=True))

    # Split paths into uncommitted and commits
    mid = len(paths) // 2
    uncommitted = [
        FileChange(path=p, status="modified", lines_added=0, lines_deleted=0) for p in paths[:mid]
    ]
    commits = (
        [
            CommitInfo(
                hash="abc", message="msg", timestamp=datetime.now(UTC), files_changed=paths[mid:]
            )
        ]
        if len(paths) > mid
        else []
    )

    prs = draw(st.lists(st.integers(min_value=1, max_value=100), max_size=3))
    issues = draw(st.lists(st.integers(min_value=1, max_value=100), max_size=3))

    return CaptureSignals(
        repository_id=repo_id,
        branch=branch,
        uncommitted_files=uncommitted,
        recent_commits=commits,
        pr_references=prs,
        issue_references=issues,
        github_metadata=None,
        capture_source="cli",
    )


@settings(max_examples=100)
@given(signals=capture_signals_strategy())
def test_property_5_context_capture_includes_all_signals(signals):
    """
    Feature: context-anchor, Property 5: Context Capture Includes All Signal Types
    Validates: Requirements 2.1, 2.3, 2.4, 2.6
    Ensures that context capture correctly incorporates uncommitted files, commits, PRs, and issues.
    """
    mock_bedrock = Mock()
    mock_body = MagicMock()

    valid_response = {
        "content": [
            {
                "text": json.dumps(
                    {
                        "goals": "Testing signals",
                        "rationale": "Property 5 check",
                        "open_questions": ["Q1", "Q2"],
                        "next_steps": ["add tests", "verify code"],
                    }
                )
            }
        ]
    }
    mock_body.read.return_value = json.dumps(valid_response).encode("utf-8")
    mock_bedrock.invoke_model.return_value = {"body": mock_body}

    agent = AgentCore(bedrock_client=mock_bedrock)

    # This might fail internally if uncommitted files list causes issues, but we mock bedrock.
    snapshot = agent.synthesize_context(
        repository_id=signals.repository_id or "repo1",
        branch=signals.branch or "main",
        developer_id="devX",
        intent="Property evaluation",
        signals=signals,
    )

    expected_paths = set()
    for f in signals.uncommitted_files:
        expected_paths.add(f.path)
    for c in signals.recent_commits:
        for f in c.files_changed:
            expected_paths.add(f)

    assert set(snapshot.relevant_files) == expected_paths
    assert snapshot.related_prs == signals.pr_references
    assert snapshot.related_issues == signals.issue_references
