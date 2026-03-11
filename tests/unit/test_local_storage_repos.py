"""
Unit tests for LocalStorage repository management.

Verifies that repository metadata can be registered, retrieved,
listed, and updated correctly.
"""

import pytest
import tempfile
from pathlib import Path

from src.contextanchor.local_storage import LocalStorage


@pytest.fixture
def storage():
    """Create a temporary LocalStorage instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_repos.db"
        storage = LocalStorage(db_path)
        yield storage


def test_register_and_get_repository(storage):
    """Test registering and retrieving repository metadata."""
    repo_id = "test-repo-id"
    name = "test-repo"
    root_path = "/path/to/repo"
    remote_url = "https://github.com/org/repo"

    storage.register_repository(repo_id, name, root_path, remote_url)

    repo = storage.get_repository(repo_id)
    assert repo is not None
    assert repo["repository_id"] == repo_id
    assert repo["name"] == name
    assert repo["root_path"] == root_path
    assert repo["remote_url"] == remote_url


def test_register_overwrite(storage):
    """Test that registering the same ID updates existing metadata."""
    repo_id = "test-repo-id"
    storage.register_repository(repo_id, "name1", "/path1", "remote1")
    storage.register_repository(repo_id, "name2", "/path2", "remote2")

    repo = storage.get_repository(repo_id)
    assert repo["name"] == "name2"
    assert repo["root_path"] == "/path2"


def test_list_repositories_ordering(storage):
    """Test that list_repositories returns items ordered by last_accessed_at."""
    storage.register_repository("id1", "repo1", "/path1")
    storage.register_repository("id2", "repo2", "/path2")

    # Update last_accessed_at for id1 to be newer
    storage.update_last_accessed("id1")

    repos = storage.list_repositories()
    assert len(repos) == 2
    # id1 should be first because it was accessed most recently
    assert repos[0]["repository_id"] == "id1"
    assert repos[1]["repository_id"] == "id2"


def test_get_nonexistent_repository(storage):
    """Test get_repository with an ID that doesn't exist."""
    assert storage.get_repository("nonexistent") is None


def test_update_last_accessed_nonexistent(storage):
    """Test updating last_accessed_at for a nonexistent repo (should not error)."""
    storage.update_last_accessed("nonexistent")
