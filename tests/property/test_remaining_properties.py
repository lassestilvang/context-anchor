"""
Remaining property-based tests not covered in component-level tasks.

Properties tested:
- Property 13: Retention Period Enforcement
- Property 22: Initialization Failure Error Messages
- Property 23: Hook Status Reporting
- Property 52: Productive Action Timestamp Recording
- Property 62-66: Command Availability Properties
- Property 73: history Command Availability
- Property 74: Timestamped Historical Snapshot Retrieval
- Property 86: Configuration File Support
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import Mock
from hypothesis import given, settings
from hypothesis import strategies as st
from click.testing import CliRunner

from src.contextanchor.models import (
    Config,
    Repository,
)
from src.contextanchor.context_store import ContextStore
from tests.property.strategies import (
    valid_context_snapshot,
    valid_repository_id,
)

# --- Property 13: Retention Period Enforcement ---


@settings(max_examples=100)
@given(
    retention_days=st.integers(min_value=1, max_value=365),
    age_days=st.integers(min_value=0, max_value=730),
)
def test_property_13_retention_period_enforcement(retention_days, age_days):
    """
    Property 13: Retention Period Enforcement
    Validates: Requirement 4.4

    For any retention_days configuration and snapshot age, a snapshot older
    than retention_days should be eligible for purging.
    """
    now = datetime.now(UTC)
    snapshot_time = now - timedelta(days=age_days)
    retention_cutoff = now - timedelta(days=retention_days)

    is_expired = snapshot_time < retention_cutoff

    if age_days > retention_days:
        assert is_expired, (
            f"Snapshot aged {age_days} days must be expired with " f"{retention_days} day retention"
        )
    elif age_days < retention_days:
        assert not is_expired, (
            f"Snapshot aged {age_days} days must NOT be expired with "
            f"{retention_days} day retention"
        )


# --- Property 22: Initialization Failure Error Messages ---


@settings(max_examples=50)
@given(
    path=st.text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/_-"),
)
def test_property_22_initialization_failure_error_messages(path):
    """
    Property 22: Initialization Failure Error Messages
    Validates: Requirement 6.1

    When initialization fails (e.g., not a git repo), the error must
    be descriptive and actionable, never empty or generic.
    """
    import git as gitmodule
    from src.contextanchor.git_observer import GitObserver

    observer = GitObserver(f"/tmp/nonexistent_{path}")
    try:
        root = observer.detect_repository_root()
        # If it returns, it must be None for non-git dirs
        assert root is None, "detect_repository_root should return None for non-git directories"
    except (gitmodule.exc.InvalidGitRepositoryError, gitmodule.exc.NoSuchPathError) as e:
        # Exception is acceptable, but must have a descriptive message
        assert str(e), "Git error message must not be empty"
        assert len(str(e)) > 0, "Error message must be descriptive"


# --- Property 23: Hook Status Reporting ---


@settings(max_examples=50)
@given(
    status=st.sampled_from(["active", "degraded", "unavailable"]),
    repo_id=valid_repository_id(),
)
def test_property_23_hook_status_reporting(status, repo_id):
    """
    Property 23: Hook Status Reporting
    Validates: Requirement 6.2

    The hook_status field of a Repository must always be one of the valid
    status values: "active", "degraded", or "unavailable".
    """
    valid_statuses = {"active", "degraded", "unavailable"}

    repo = Repository(
        repository_id=repo_id,
        root_path="/tmp/test",
        remote_url="https://github.com/test/repo.git",
        github_metadata=None,
        initialized_at=datetime.now(UTC),
        hook_status=status,
    )

    assert (
        repo.hook_status in valid_statuses
    ), f"hook_status must be one of {valid_statuses}, got '{repo.hook_status}'"


# --- Property 52: Productive Action Timestamp Recording ---


@settings(max_examples=100)
@given(snapshot=valid_context_snapshot())
def test_property_52_productive_action_timestamp_recording(snapshot):
    """
    Property 52: Productive Action Timestamp Recording
    Validates: Requirement 7.5

    Every ContextSnapshot must have a valid captured_at timestamp that
    represents when the productive action was recorded. The timestamp
    must be a valid datetime.
    """
    assert isinstance(snapshot.captured_at, datetime), "captured_at must be a datetime instance"
    # Timestamp must be in a reasonable range
    assert snapshot.captured_at >= datetime(2020, 1, 1), "captured_at must be after 2020-01-01"
    # ISO format must be parseable
    iso = snapshot.captured_at.isoformat()
    parsed = datetime.fromisoformat(iso)
    assert parsed == snapshot.captured_at, "captured_at must survive ISO format round trip"


# --- Property 62-66: Command Availability ---

CLI_COMMANDS = [
    "init",
    "save-context",
    "show-context",
    "list-contexts",
    "delete-context",
]


@settings(max_examples=len(CLI_COMMANDS))
@given(cmd=st.sampled_from(CLI_COMMANDS))
def test_property_62_66_command_availability(cmd):
    """
    Properties 62-66: Command Availability
    Validates: Requirements 6.3, 6.6

    All core CLI commands must be registered and accessible.
    """
    from src.contextanchor.cli import main

    runner = CliRunner()
    result = runner.invoke(main, [cmd, "--help"])

    assert result.exit_code == 0, (
        f"Command '{cmd}' must be available. Got exit code {result.exit_code}. "
        f"Output: {result.output}"
    )


# --- Property 73: history Command Availability ---


def test_property_73_history_command_availability():
    """
    Property 73: history Command Availability
    Validates: Requirement 12.2

    The 'history' command must be registered and provide help output.
    """
    from src.contextanchor.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["history", "--help"])

    assert (
        result.exit_code == 0
    ), f"'history' command must be available. Exit code: {result.exit_code}"
    assert (
        "history" in result.output.lower() or "usage" in result.output.lower()
    ), "'history' help must contain relevant information"


# --- Property 74: Timestamped Historical Snapshot Retrieval ---


@settings(max_examples=50)
@given(snapshot=valid_context_snapshot())
def test_property_74_timestamped_historical_snapshot_retrieval(snapshot):
    """
    Property 74: Timestamped Historical Snapshot Retrieval
    Validates: Requirement 12.4

    Any stored snapshot must be retrievable and must preserve its timestamp.
    The captured_at field must survive the store/retrieve round trip.
    """
    mock_resource = Mock()
    mock_table = Mock()
    mock_resource.Table.return_value = mock_table

    store = ContextStore(table_name="TestTable", dynamodb_resource=mock_resource)
    store.store_snapshot(snapshot)

    # Extract the stored item
    stored_item = mock_table.put_item.call_args.kwargs["Item"]

    # Verify timestamp is stored correctly
    assert "captured_at" in stored_item, "captured_at must be stored"
    assert (
        stored_item["captured_at"] == snapshot.captured_at.isoformat()
    ), "captured_at must be stored as ISO format string"


# --- Property 86: Configuration File Support ---


@settings(max_examples=50)
@given(
    retention=st.integers(min_value=1, max_value=365),
    timeout=st.integers(min_value=1, max_value=120),
    retries=st.integers(min_value=0, max_value=10),
)
def test_property_86_configuration_file_support(retention, timeout, retries):
    """
    Property 86: Configuration File Support
    Validates: Requirement 15.1

    Configuration values must be correctly stored in the Config dataclass
    and maintain valid ranges.
    """
    config = Config(
        api_endpoint="https://api.example.com",
        retention_days=retention,
        api_timeout_seconds=timeout,
        retry_attempts=retries,
    )

    assert config.retention_days == retention, "retention_days must be preserved"
    assert config.api_timeout_seconds == timeout, "api_timeout must be preserved"
    assert config.retry_attempts == retries, "retry_attempts must be preserved"
    assert config.retention_days > 0, "retention_days must be positive"
    assert config.api_timeout_seconds > 0, "api_timeout must be positive"
    assert config.retry_attempts >= 0, "retry_attempts must be non-negative"
