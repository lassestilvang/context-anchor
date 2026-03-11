"""
Property-based tests for ContextSnapshot schema and validation.

Tests universal properties that must hold for all valid ContextSnapshot instances.
Uses Hypothesis for comprehensive input coverage.
"""

import pytest
import uuid
from datetime import datetime
from hypothesis import given, strategies as st, settings
from src.contextanchor.models import (
    ContextSnapshot,
    ACTION_VERBS,
)

# Hypothesis strategies for generating valid test data


def valid_uuid_string():
    """Generate a valid UUID string."""
    return st.builds(lambda: str(uuid.uuid4()))


def valid_repository_id():
    """Generate a valid repository ID (64 hex characters)."""
    return st.text(min_size=64, max_size=64, alphabet="0123456789abcdef")


@st.composite
def valid_branch_name(draw):
    """Generate a valid git branch name."""
    # Git branch names can contain letters, digits, -, _, /
    branch = draw(
        st.text(
            min_size=1,
            max_size=100,
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/",
        )
    )
    # Strip slashes and ensure not empty
    branch = branch.strip("/")
    if not branch:
        branch = "main"  # Default to main if empty after stripping
    return branch  # Remove leading/trailing slashes


def valid_developer_id():
    """Generate a valid developer ID."""
    return st.text(min_size=1, max_size=100)


def valid_goals():
    """Generate valid goals text (1-3 sentences, max 300 chars)."""
    return st.text(min_size=10, max_size=300)


def valid_rationale():
    """Generate valid rationale text (2-4 sentences, max 500 chars)."""
    return st.text(min_size=20, max_size=500)


def valid_open_questions():
    """Generate valid open questions list (2-5 items, each max 200 chars)."""
    return st.lists(st.text(min_size=5, max_size=200), min_size=2, max_size=5)


@st.composite
def action_verb_step(draw):
    """Generate a next step starting with a valid action verb."""
    verb = draw(st.sampled_from(sorted(ACTION_VERBS)))
    # Capitalize first letter
    verb = verb.capitalize()
    rest = draw(st.text(min_size=5, max_size=140, alphabet="abcdefghijklmnopqrstuvwxyz "))
    return f"{verb} {rest.strip()}"


@st.composite
def valid_next_steps(draw):
    """Generate valid next steps list (1-5 items, each starting with action verb)."""
    return draw(st.lists(action_verb_step(), min_size=1, max_size=5))


@st.composite
def valid_file_path(draw):
    """Generate a valid file path."""
    parts = draw(
        st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
            ),
            min_size=1,
            max_size=5,
        )
    )
    extension = draw(st.sampled_from(["py", "js", "ts", "java", "go", "rs", "md", "txt", "json"]))
    return "/".join(parts) + f".{extension}"


def valid_relevant_files():
    """Generate valid relevant files list (max 50 files)."""
    return st.lists(valid_file_path(), max_size=50)


def valid_pr_list():
    """Generate valid PR numbers list."""
    return st.lists(st.integers(min_value=1, max_value=99999), max_size=10)


def valid_issue_list():
    """Generate valid issue numbers list."""
    return st.lists(st.integers(min_value=1, max_value=99999), max_size=10)


@st.composite
def valid_context_snapshot(draw):
    """
    Generate a valid ContextSnapshot instance.

    This strategy ensures all fields meet the validation requirements:
    - snapshot_id: valid UUID
    - repository_id: 64 hex characters
    - branch: valid git branch name
    - captured_at: valid datetime
    - developer_id: non-empty string
    - goals: 10-300 characters
    - rationale: 20-500 characters
    - open_questions: 2-5 items, each 5-200 characters
    - next_steps: 1-5 items, each starting with action verb
    - relevant_files: list of file paths (max 50)
    - related_prs: list of positive integers
    - related_issues: list of positive integers
    - Total text content: under 2500 characters
    """
    # Generate fields with constraints to ensure total text stays under 2500 chars
    goals = draw(st.text(min_size=10, max_size=200))
    rationale = draw(st.text(min_size=20, max_size=300))
    open_questions = draw(st.lists(st.text(min_size=5, max_size=150), min_size=2, max_size=4))
    next_steps = draw(st.lists(action_verb_step(), min_size=1, max_size=3))

    return ContextSnapshot(
        snapshot_id=str(uuid.uuid4()),
        repository_id=draw(valid_repository_id()),
        branch=draw(valid_branch_name()),
        captured_at=draw(
            st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))
        ),
        developer_id=draw(valid_developer_id()),
        goals=goals,
        rationale=rationale,
        open_questions=open_questions,
        next_steps=next_steps,
        relevant_files=draw(valid_relevant_files()),
        related_prs=draw(valid_pr_list()),
        related_issues=draw(valid_issue_list()),
        deleted_at=None,
    )


# Property-based tests


@settings(max_examples=100)
@given(snapshot=valid_context_snapshot())
def test_property_6_complete_context_snapshot_schema(snapshot):
    """
    Feature: context-anchor, Property 6: Complete Context Snapshot Schema

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7**

    For any generated Context_Snapshot, it must contain all required fields:
    - snapshot_id (valid UUID)
    - repository_id
    - branch
    - captured_at (valid timestamp)
    - developer_id
    - goals
    - rationale
    - open_questions (list)
    - next_steps (list)
    - relevant_files (list)
    - related_prs (list)
    - related_issues (list)
    """
    # Verify all required fields are present (not None)
    assert snapshot.snapshot_id is not None, "snapshot_id must be present"
    assert snapshot.repository_id is not None, "repository_id must be present"
    assert snapshot.branch is not None, "branch must be present"
    assert snapshot.captured_at is not None, "captured_at must be present"
    assert snapshot.developer_id is not None, "developer_id must be present"
    assert snapshot.goals is not None, "goals must be present"
    assert snapshot.rationale is not None, "rationale must be present"
    assert snapshot.open_questions is not None, "open_questions must be present"
    assert snapshot.next_steps is not None, "next_steps must be present"
    assert snapshot.relevant_files is not None, "relevant_files must be present"
    assert snapshot.related_prs is not None, "related_prs must be present"
    assert snapshot.related_issues is not None, "related_issues must be present"

    # Verify field types
    assert isinstance(snapshot.snapshot_id, str), "snapshot_id must be a string"
    assert isinstance(snapshot.repository_id, str), "repository_id must be a string"
    assert isinstance(snapshot.branch, str), "branch must be a string"
    assert isinstance(snapshot.captured_at, datetime), "captured_at must be a datetime"
    assert isinstance(snapshot.developer_id, str), "developer_id must be a string"
    assert isinstance(snapshot.goals, str), "goals must be a string"
    assert isinstance(snapshot.rationale, str), "rationale must be a string"
    assert isinstance(snapshot.open_questions, list), "open_questions must be a list"
    assert isinstance(snapshot.next_steps, list), "next_steps must be a list"
    assert isinstance(snapshot.relevant_files, list), "relevant_files must be a list"
    assert isinstance(snapshot.related_prs, list), "related_prs must be a list"
    assert isinstance(snapshot.related_issues, list), "related_issues must be a list"

    # Verify snapshot_id is a valid UUID format
    try:
        uuid.UUID(snapshot.snapshot_id)
    except ValueError:
        pytest.fail(f"snapshot_id '{snapshot.snapshot_id}' is not a valid UUID")

    # Verify list contents are of correct types
    assert all(
        isinstance(q, str) for q in snapshot.open_questions
    ), "All open_questions items must be strings"
    assert all(
        isinstance(s, str) for s in snapshot.next_steps
    ), "All next_steps items must be strings"
    assert all(
        isinstance(f, str) for f in snapshot.relevant_files
    ), "All relevant_files items must be strings"
    assert all(
        isinstance(pr, int) for pr in snapshot.related_prs
    ), "All related_prs items must be integers"
    assert all(
        isinstance(issue, int) for issue in snapshot.related_issues
    ), "All related_issues items must be integers"

    # Verify constraints from requirements
    assert len(snapshot.repository_id) == 64, "repository_id must be 64 characters (SHA-256 hash)"
    assert len(snapshot.branch) > 0, "branch must not be empty"
    assert len(snapshot.developer_id) > 0, "developer_id must not be empty"
    assert len(snapshot.goals) > 0, "goals must not be empty"
    assert len(snapshot.rationale) > 0, "rationale must not be empty"
    assert 2 <= len(snapshot.open_questions) <= 5, "open_questions must have 2-5 items"
    assert 1 <= len(snapshot.next_steps) <= 5, "next_steps must have 1-5 items"
    assert len(snapshot.relevant_files) <= 50, "relevant_files must have at most 50 items"

    # Verify next_steps start with action verbs (validated by __post_init__)
    for step in snapshot.next_steps:
        first_word = step.split()[0].lower()
        assert (
            first_word in ACTION_VERBS
        ), f"Next step must start with action verb, got: '{first_word}'"

    # Verify word limit constraint (validated by __post_init__)
    text_content = snapshot.to_text()
    assert (
        len(text_content) <= 2500
    ), f"Snapshot text must be under 2500 characters, got {len(text_content)}"


@settings(max_examples=100)
@given(snapshot=valid_context_snapshot())
def test_property_7_snapshot_word_limit_constraint(snapshot):
    """
    Feature: context-anchor, Property 7: Snapshot Word Limit Constraint

    **Validates: Requirements 3.6**

    For any generated Context_Snapshot, the combined text of goals, rationale,
    open_questions, and next_steps must not exceed 500 words (~2500 characters).
    """
    # Get the combined text content
    text_content = snapshot.to_text()

    # Verify the text content does not exceed 2500 characters (500 words)
    assert len(text_content) <= 2500, (
        f"Snapshot text must be under 500 words (~2500 chars), " f"got {len(text_content)} chars"
    )

    # Additional verification: count actual words
    # A word is defined as a sequence of non-whitespace characters
    words = text_content.split()
    word_count = len(words)

    # 500 words is approximately 2500 characters (5 chars per word average)
    # We verify the character limit is enforced, which is the primary constraint
    assert len(text_content) <= 2500, (
        f"Snapshot exceeded character limit: {len(text_content)} chars "
        f"(approximately {word_count} words)"
    )

    # Verify to_text() includes all required sections
    assert snapshot.goals in text_content, "goals must be included in text content"
    assert snapshot.rationale in text_content, "rationale must be included in text content"
    for question in snapshot.open_questions:
        assert (
            question in text_content
        ), f"open_question '{question}' must be included in text content"
    for step in snapshot.next_steps:
        assert step in text_content, f"next_step '{step}' must be included in text content"


@settings(max_examples=100)
@given(snapshot=valid_context_snapshot())
def test_property_9_next_steps_format_validation(snapshot):
    """
    Feature: context-anchor, Property 9: Next Steps Format Validation

    **Validates: Requirements 3.9**

    For any generated Context_Snapshot, the next_steps list must contain between
    1 and 5 items, and each item must begin with a recognized action verb.
    """
    # Verify next_steps count is within valid range
    assert (
        1 <= len(snapshot.next_steps) <= 5
    ), f"next_steps must contain 1-5 items, got {len(snapshot.next_steps)}"

    # Verify each next step starts with a recognized action verb
    for step in snapshot.next_steps:
        # Extract the first word from the step
        words = step.split()
        assert len(words) > 0, f"Next step cannot be empty: '{step}'"

        first_word = words[0].lower()

        # Verify the first word is a recognized action verb
        assert first_word in ACTION_VERBS, (
            f"Next step must start with a recognized action verb. "
            f"Got: '{first_word}' in step: '{step}'. "
            f"Valid verbs: {', '.join(sorted(ACTION_VERBS))}"
        )

    # Verify all next_steps are non-empty strings
    for step in snapshot.next_steps:
        assert isinstance(step, str), f"Next step must be a string, got {type(step)}"
        assert len(step.strip()) > 0, "Next step cannot be empty or whitespace only"
