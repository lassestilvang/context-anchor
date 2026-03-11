
import pytest
import shutil
import os
from pathlib import Path
from contextanchor.local_storage import LocalStorage

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    return db_path

def test_register_and_get_repository(temp_db):
    storage = LocalStorage(temp_db)
    
    repo_id = "repo-123"
    name = "test-repo"
    root_path = "/path/to/repo"
    remote_url = "https://github.com/user/repo.git"
    
    storage.register_repository(repo_id, name, root_path, remote_url)
    
    repo = storage.get_repository(repo_id)
    assert repo is not None
    assert repo["repository_id"] == repo_id
    assert repo["name"] == name
    assert repo["root_path"] == root_path
    assert repo["remote_url"] == remote_url
    assert "last_accessed_at" in repo

def test_list_repositories_order(temp_db):
    storage = LocalStorage(temp_db)
    
    storage.register_repository("id-1", "repo-1", "/path/1")
    storage.register_repository("id-2", "repo-2", "/path/2")
    
    # Update id-1 to be most recently accessed
    storage.update_last_accessed("id-1")
    
    repos = storage.list_repositories()
    assert len(repos) == 2
    assert repos[0]["repository_id"] == "id-1"
    assert repos[1]["repository_id"] == "id-2"

def test_update_last_accessed(temp_db):
    storage = LocalStorage(temp_db)
    repo_id = "repo-1"
    storage.register_repository(repo_id, "repo-1", "/path/1")
    
    repo_before = storage.get_repository(repo_id)
    
    import time
    time.sleep(0.1) # Ensure timestamp changes
    storage.update_last_accessed(repo_id)
    
    repo_after = storage.get_repository(repo_id)
    assert repo_after["last_accessed_at"] > repo_before["last_accessed_at"]
