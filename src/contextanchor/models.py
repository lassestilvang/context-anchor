"""
Domain models for ContextAnchor.

This module defines the core data structures used throughout the ContextAnchor system,
including context snapshots, git signals, repository metadata, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

# Action verbs allowed for next steps validation
ACTION_VERBS = {
    "add",
    "update",
    "fix",
    "remove",
    "refactor",
    "test",
    "document",
    "implement",
    "create",
    "verify",
    "investigate",
    "optimize",
    "migrate",
    "review",
    "ship",
    "develop",
}


@dataclass
class ContextSnapshot:
    """
    A snapshot of developer workflow state at a point in time.

    Captures the mental context including goals, rationale, open questions,
    and next steps, along with relevant git metadata.
    """

    snapshot_id: str  # UUID
    repository_id: str  # Unique repository identifier
    branch: str  # Git branch name
    captured_at: datetime  # Timestamp of capture
    developer_id: str  # Developer identifier
    goals: str  # What developer is trying to accomplish
    rationale: str  # Why this work matters
    open_questions: List[str]  # Unresolved questions or decisions
    next_steps: List[str]  # Concrete action items (1-5 items)
    relevant_files: List[str]  # File paths from git signals
    related_prs: List[int]  # PR numbers
    related_issues: List[int]  # Issue numbers
    github_metadata: Optional["GitHubRepo"] = None  # GitHub repository metadata
    deleted_at: Optional[datetime] = None  # Soft delete timestamp

    def __post_init__(self) -> None:
        """Validate snapshot constraints."""
        # Validate next_steps count
        if not (1 <= len(self.next_steps) <= 5):
            raise ValueError(f"Must have 1-5 next steps, got {len(self.next_steps)}")

        # Validate action verbs
        for step in self.next_steps:
            if not step or not step.strip():
                raise ValueError("Next step cannot be empty")
            first_word = step.split()[0].lower()
            if first_word not in ACTION_VERBS:
                raise ValueError(
                    f"Next step must start with an action verb, got: '{first_word}'. "
                    f"Valid verbs: {', '.join(sorted(ACTION_VERBS))}"
                )

        # Validate word limit (500 words ~= 2500 characters)
        text_content = self.to_text()
        if len(text_content) > 2500:
            raise ValueError(
                f"Snapshot text must be under 500 words (~2500 chars), "
                f"got {len(text_content)} chars"
            )

    def to_text(self) -> str:
        """Convert snapshot to text representation for word count validation."""
        parts = [
            self.goals,
            self.rationale,
            "\n".join(self.open_questions),
            "\n".join(self.next_steps),
        ]
        return "\n".join(parts)


@dataclass
class FileChange:
    """
    Represents a change to a file in the repository.
    """

    path: str  # File path relative to repository root
    status: str  # "modified", "added", "deleted", "renamed"
    lines_added: int  # Number of lines added
    lines_deleted: int  # Number of lines deleted


@dataclass
class CommitInfo:
    """
    Information about a git commit.
    """

    hash: str  # Commit hash
    message: str  # Commit message
    timestamp: datetime  # Commit timestamp
    files_changed: List[str]  # List of file paths changed in this commit


@dataclass
class CaptureSignals:
    """
    Collection of git activity signals captured during context capture.

    These signals are used by the Agent Core to synthesize a context snapshot.
    """

    repository_id: str  # Unique repository identifier
    branch: str  # Current branch name
    uncommitted_files: List[FileChange]  # Staged and unstaged changes
    recent_commits: List[CommitInfo]  # Recent commit history
    pr_references: List[int]  # PR numbers from commit messages
    issue_references: List[int]  # Issue numbers from commit messages
    github_metadata: Optional["GitHubRepo"]  # GitHub repository metadata if available
    capture_source: str  # "hook", "cli", "watcher"


@dataclass
class GitHubRepo:
    """
    GitHub-specific repository metadata.
    """

    owner: str  # GitHub repository owner
    name: str  # GitHub repository name
    remote_url: str  # Full GitHub remote URL


@dataclass
class Repository:
    """
    Represents a git repository monitored by ContextAnchor.
    """

    repository_id: str  # Hash of git remote URL + root path
    root_path: str  # Absolute path to repository root
    remote_url: str  # Primary git remote URL
    github_metadata: Optional[GitHubRepo]  # GitHub metadata if applicable
    initialized_at: datetime  # When ContextAnchor was initialized
    hook_status: str  # "active", "degraded", "unavailable"


@dataclass
class Config:
    """
    Configuration settings for ContextAnchor.

    Can be loaded from ~/.contextanchor/config.yaml or repository-specific config.
    """

    api_endpoint: str
    api_timeout_seconds: int = 30
    retry_attempts: int = 3
    capture_prompt: str = "What were you trying to solve right now?"
    retention_days: int = 90
    offline_queue_max: int = 200
    enabled_signals: List[str] = field(
        default_factory=lambda: ["commits", "branches", "diffs", "pr_references"]
    )
    redact_patterns: List[str] = field(default_factory=list)


@dataclass
class QueuedOperation:
    """
    Represents an operation queued for later execution when offline.

    Operations are retried with exponential backoff and expire after 24 hours.
    """

    operation_id: str  # Unique operation identifier
    operation_type: str  # "save_context", "delete_context"
    repository_id: str  # Repository this operation belongs to
    payload: Dict[str, Any]  # Operation-specific data
    created_at: datetime  # When operation was queued
    expires_at: datetime  # created_at + 24 hours
    retry_count: int = 0  # Number of retry attempts
    next_retry_at: Optional[datetime] = None  # When to retry next


def generate_snapshot_id() -> str:
    """Generate a unique snapshot ID."""
    return str(uuid.uuid4())


def generate_operation_id() -> str:
    """Generate a unique operation ID."""
    return str(uuid.uuid4())
