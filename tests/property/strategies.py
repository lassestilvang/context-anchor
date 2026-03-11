"""
Centralized Hypothesis strategies for ContextAnchor domain models.

Provides reusable strategies for generating valid test data for:
- ContextSnapshot
- CaptureSignals
- FileChange
- CommitInfo
- Repository
"""

from datetime import datetime
from hypothesis import strategies as st
from src.contextanchor.models import (
    ContextSnapshot,
    CaptureSignals,
    FileChange,
    CommitInfo,
    ACTION_VERBS,
    GitHubRepo,
)

# Basic primitive strategies


def valid_uuid_string():
    """Generate a valid UUID string."""
    return st.uuids().map(str)


def valid_repository_id():
    """Generate a valid repository ID (64 hex characters)."""
    return st.text(min_size=64, max_size=64, alphabet="0123456789abcdef")


@st.composite
def valid_branch_name(draw):
    """Generate a valid git branch name."""
    branch = draw(
        st.text(
            min_size=1,
            max_size=100,
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/",
        )
    )
    branch = branch.strip("/")
    if not branch:
        branch = "main"
    return branch


def valid_developer_id():
    """Generate a valid developer ID."""
    return st.text(min_size=1, max_size=100)


# Content strategies


@st.composite
def action_verb_step(draw):
    """Generate a next step starting with a valid action verb."""
    verb = draw(st.sampled_from(sorted(ACTION_VERBS)))
    verb = verb.capitalize()
    rest = draw(st.text(min_size=5, max_size=140, alphabet="abcdefghijklmnopqrstuvwxyz "))
    return f"{verb} {rest.strip()}"


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


# Model strategies


@st.composite
def valid_file_change(draw):
    """Generate a valid FileChange instance."""
    return FileChange(
        path=draw(valid_file_path()),
        status=draw(st.sampled_from(["modified", "added", "deleted", "renamed"])),
        lines_added=draw(st.integers(min_value=0, max_value=1000)),
        lines_deleted=draw(st.integers(min_value=0, max_value=1000)),
    )


@st.composite
def valid_commit_info(draw):
    """Generate a valid CommitInfo instance."""
    return CommitInfo(
        hash=draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        message=draw(st.text(min_size=10, max_size=200)),
        timestamp=draw(st.datetimes(min_value=datetime(2020, 1, 1))),
        files_changed=draw(st.lists(valid_file_path(), min_size=1, max_size=10)),
    )


@st.composite
def valid_github_repo(draw):
    """Generate a valid GitHubRepo instance."""
    owner = draw(st.text(min_size=1, max_size=39, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-"))
    name = draw(
        st.text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-._")
    )
    return GitHubRepo(
        owner=owner,
        name=name,
        remote_url=f"https://github.com/{owner}/{name}.git",
    )


@st.composite
def valid_capture_signals(draw):
    """Generate a valid CaptureSignals instance."""
    return CaptureSignals(
        repository_id=draw(valid_repository_id()),
        branch=draw(valid_branch_name()),
        uncommitted_files=draw(st.lists(valid_file_change(), max_size=10)),
        recent_commits=draw(st.lists(valid_commit_info(), max_size=5)),
        pr_references=draw(st.lists(st.integers(min_value=1, max_value=99999), max_size=5)),
        issue_references=draw(st.lists(st.integers(min_value=1, max_value=99999), max_size=5)),
        github_metadata=draw(st.one_of(st.none(), valid_github_repo())),
        capture_source=draw(st.sampled_from(["hook", "cli", "watcher"])),
    )


@st.composite
def valid_context_snapshot(draw):
    """Generate a valid ContextSnapshot instance."""
    # Ensure total text stays under 2500 chars for validation
    goals = draw(st.text(min_size=10, max_size=200))
    rationale = draw(st.text(min_size=20, max_size=300))
    open_questions = draw(st.lists(st.text(min_size=5, max_size=150), min_size=2, max_size=4))
    next_steps = draw(st.lists(action_verb_step(), min_size=1, max_size=3))

    return ContextSnapshot(
        snapshot_id=draw(valid_uuid_string()),
        repository_id=draw(valid_repository_id()),
        branch=draw(valid_branch_name()),
        captured_at=draw(st.datetimes(min_value=datetime(2020, 1, 1))),
        developer_id=draw(valid_developer_id()),
        goals=goals,
        rationale=rationale,
        open_questions=open_questions,
        next_steps=next_steps,
        relevant_files=draw(st.lists(valid_file_path(), max_size=20)),
        related_prs=draw(st.lists(st.integers(min_value=1, max_value=99999), max_size=5)),
        related_issues=draw(st.lists(st.integers(min_value=1, max_value=99999), max_size=5)),
        deleted_at=draw(st.one_of(st.none(), st.datetimes(min_value=datetime(2020, 1, 1)))),
    )
