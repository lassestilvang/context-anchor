"""
Unit tests for domain models.

Tests the core data structures and their validation logic.
"""

import pytest
from datetime import datetime, timedelta
from src.contextanchor.models import (
    ContextSnapshot,
    FileChange,
    CommitInfo,
    CaptureSignals,
    GitHubRepo,
    Repository,
    Config,
    QueuedOperation,
    generate_snapshot_id,
    generate_operation_id,
)


class TestContextSnapshot:
    """Tests for ContextSnapshot model and validation."""

    def test_valid_snapshot_creation(self):
        """Test creating a valid context snapshot."""
        snapshot = ContextSnapshot(
            snapshot_id="test-id-123",
            repository_id="repo-abc",
            branch="main",
            captured_at=datetime.now(),
            developer_id="dev-1",
            goals="Implement user authentication",
            rationale="Users need secure access to the system",
            open_questions=["Which OAuth provider to use?", "How to handle token refresh?"],
            next_steps=["Add login endpoint", "Implement JWT validation"],
            relevant_files=["src/auth.py", "src/middleware.py"],
            related_prs=[123, 456],
            related_issues=[789],
        )

        assert snapshot.snapshot_id == "test-id-123"
        assert snapshot.branch == "main"
        assert len(snapshot.next_steps) == 2

    def test_snapshot_requires_1_to_5_next_steps(self):
        """Test that snapshots must have 1-5 next steps."""
        # Test with 0 next steps
        with pytest.raises(ValueError, match="Must have 1-5 next steps"):
            ContextSnapshot(
                snapshot_id="test-id",
                repository_id="repo-abc",
                branch="main",
                captured_at=datetime.now(),
                developer_id="dev-1",
                goals="Test goals",
                rationale="Test rationale",
                open_questions=["Question 1", "Question 2"],
                next_steps=[],  # Empty list
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

        # Test with 6 next steps
        with pytest.raises(ValueError, match="Must have 1-5 next steps"):
            ContextSnapshot(
                snapshot_id="test-id",
                repository_id="repo-abc",
                branch="main",
                captured_at=datetime.now(),
                developer_id="dev-1",
                goals="Test goals",
                rationale="Test rationale",
                open_questions=["Question 1", "Question 2"],
                next_steps=["Add feature"] * 6,  # 6 items
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

    def test_snapshot_next_steps_must_start_with_action_verb(self):
        """Test that next steps must start with valid action verbs."""
        with pytest.raises(ValueError, match="must start with an action verb"):
            ContextSnapshot(
                snapshot_id="test-id",
                repository_id="repo-abc",
                branch="main",
                captured_at=datetime.now(),
                developer_id="dev-1",
                goals="Test goals",
                rationale="Test rationale",
                open_questions=["Question 1", "Question 2"],
                next_steps=["Invalid verb here"],  # "invalid" is not an action verb
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

    def test_snapshot_accepts_all_valid_action_verbs(self):
        """Test that all documented action verbs are accepted."""
        valid_verbs = [
            "Add",
            "Update",
            "Fix",
            "Remove",
            "Refactor",
            "Test",
            "Document",
            "Implement",
            "Create",
            "Verify",
            "Investigate",
            "Optimize",
            "Migrate",
            "Review",
            "Ship",
        ]

        for verb in valid_verbs:
            snapshot = ContextSnapshot(
                snapshot_id="test-id",
                repository_id="repo-abc",
                branch="main",
                captured_at=datetime.now(),
                developer_id="dev-1",
                goals="Test goals",
                rationale="Test rationale",
                open_questions=["Question 1", "Question 2"],
                next_steps=[f"{verb} something useful"],
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )
            assert len(snapshot.next_steps) == 1

    def test_snapshot_word_limit_validation(self):
        """Test that snapshot text must be under 2500 characters."""
        # Create a snapshot that exceeds the word limit
        long_text = "x" * 1000  # 1000 characters

        with pytest.raises(ValueError, match="must be under 500 words"):
            ContextSnapshot(
                snapshot_id="test-id",
                repository_id="repo-abc",
                branch="main",
                captured_at=datetime.now(),
                developer_id="dev-1",
                goals=long_text,
                rationale=long_text,
                open_questions=[long_text],
                next_steps=["Add feature"],
                relevant_files=[],
                related_prs=[],
                related_issues=[],
            )

    def test_snapshot_to_text(self):
        """Test the to_text method for word count validation."""
        snapshot = ContextSnapshot(
            snapshot_id="test-id",
            repository_id="repo-abc",
            branch="main",
            captured_at=datetime.now(),
            developer_id="dev-1",
            goals="Implement authentication",
            rationale="Security is important",
            open_questions=["Which provider?", "Token expiry?"],
            next_steps=["Add login", "Test security"],
            relevant_files=[],
            related_prs=[],
            related_issues=[],
        )

        text = snapshot.to_text()
        assert "Implement authentication" in text
        assert "Security is important" in text
        assert "Which provider?" in text
        assert "Add login" in text


class TestFileChange:
    """Tests for FileChange model."""

    def test_file_change_creation(self):
        """Test creating a file change."""
        change = FileChange(
            path="src/auth.py",
            status="modified",
            lines_added=10,
            lines_deleted=5,
        )

        assert change.path == "src/auth.py"
        assert change.status == "modified"
        assert change.lines_added == 10
        assert change.lines_deleted == 5


class TestCommitInfo:
    """Tests for CommitInfo model."""

    def test_commit_info_creation(self):
        """Test creating commit info."""
        commit = CommitInfo(
            hash="abc123def456",
            message="Add authentication feature",
            timestamp=datetime.now(),
            files_changed=["src/auth.py", "tests/test_auth.py"],
        )

        assert commit.hash == "abc123def456"
        assert "authentication" in commit.message
        assert len(commit.files_changed) == 2


class TestCaptureSignals:
    """Tests for CaptureSignals model."""

    def test_capture_signals_creation(self):
        """Test creating capture signals."""
        signals = CaptureSignals(
            repository_id="repo-123",
            branch="feature/auth",
            uncommitted_files=[FileChange("src/auth.py", "modified", 10, 5)],
            recent_commits=[CommitInfo("abc123", "Initial commit", datetime.now(), ["README.md"])],
            pr_references=[123],
            issue_references=[456],
            github_metadata=GitHubRepo("owner", "repo", "https://github.com/owner/repo"),
            capture_source="cli",
        )

        assert signals.repository_id == "repo-123"
        assert signals.branch == "feature/auth"
        assert signals.capture_source == "cli"
        assert len(signals.uncommitted_files) == 1
        assert len(signals.recent_commits) == 1


class TestGitHubRepo:
    """Tests for GitHubRepo model."""

    def test_github_repo_creation(self):
        """Test creating GitHub repo metadata."""
        repo = GitHubRepo(
            owner="contextanchor",
            name="cli",
            remote_url="https://github.com/contextanchor/cli.git",
        )

        assert repo.owner == "contextanchor"
        assert repo.name == "cli"
        assert "github.com" in repo.remote_url


class TestRepository:
    """Tests for Repository model."""

    def test_repository_creation(self):
        """Test creating repository metadata."""
        repo = Repository(
            repository_id="repo-hash-123",
            root_path="/home/user/projects/myrepo",
            remote_url="https://github.com/user/myrepo.git",
            github_metadata=GitHubRepo("user", "myrepo", "https://github.com/user/myrepo.git"),
            initialized_at=datetime.now(),
            hook_status="active",
        )

        assert repo.repository_id == "repo-hash-123"
        assert repo.hook_status == "active"
        assert repo.github_metadata is not None


class TestConfig:
    """Tests for Config model."""

    def test_config_with_defaults(self):
        """Test creating config with default values."""
        config = Config(api_endpoint="https://api.contextanchor.example.com")

        assert config.api_endpoint == "https://api.contextanchor.example.com"
        assert config.api_timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.capture_prompt == "What were you trying to solve right now?"
        assert config.retention_days == 90
        assert config.offline_queue_max == 200
        assert "commits" in config.enabled_signals
        assert "branches" in config.enabled_signals

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = Config(
            api_endpoint="https://custom.api.com",
            api_timeout_seconds=60,
            capture_prompt="What are you working on?",
            retention_days=30,
            enabled_signals=["commits"],
            redact_patterns=[r"api[_-]?key"],
        )

        assert config.api_timeout_seconds == 60
        assert config.capture_prompt == "What are you working on?"
        assert config.retention_days == 30
        assert config.enabled_signals == ["commits"]
        assert len(config.redact_patterns) == 1


class TestQueuedOperation:
    """Tests for QueuedOperation model."""

    def test_queued_operation_creation(self):
        """Test creating a queued operation."""
        now = datetime.now()
        expires = now + timedelta(hours=24)

        operation = QueuedOperation(
            operation_id="op-123",
            operation_type="save_context",
            repository_id="repo-abc",
            payload={"branch": "main", "intent": "Fix bug"},
            created_at=now,
            expires_at=expires,
            retry_count=0,
        )

        assert operation.operation_id == "op-123"
        assert operation.operation_type == "save_context"
        assert operation.retry_count == 0
        assert operation.next_retry_at is None

    def test_queued_operation_with_retry(self):
        """Test queued operation with retry information."""
        now = datetime.now()
        next_retry = now + timedelta(seconds=30)

        operation = QueuedOperation(
            operation_id="op-456",
            operation_type="delete_context",
            repository_id="repo-xyz",
            payload={"snapshot_id": "snap-123"},
            created_at=now,
            expires_at=now + timedelta(hours=24),
            retry_count=2,
            next_retry_at=next_retry,
        )

        assert operation.retry_count == 2
        assert operation.next_retry_at == next_retry


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_snapshot_id(self):
        """Test snapshot ID generation."""
        id1 = generate_snapshot_id()
        id2 = generate_snapshot_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format
        assert "-" in id1

    def test_generate_operation_id(self):
        """Test operation ID generation."""
        id1 = generate_operation_id()
        id2 = generate_operation_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format
        assert "-" in id1
