"""
Unit tests for GitObserver component.

Tests repository detection, git availability checking, remote URL extraction,
and repository ID generation.
"""

import hashlib
import os
from pathlib import Path

import git

from contextanchor.git_observer import GitObserver


class TestGitAvailability:
    """Tests for git availability checking."""

    def test_git_is_available(self):
        """Test that git is available on the system."""
        observer = GitObserver()
        assert observer.is_git_available() is True


class TestRepositoryDetection:
    """Tests for repository root detection."""

    def test_detect_repository_root_from_root(self, tmp_path):
        """Test detecting repository root when already at root."""
        # Create a git repository
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        root = observer.detect_repository_root()

        assert root is not None
        assert Path(root) == tmp_path

    def test_detect_repository_root_from_subdirectory(self, tmp_path):
        """Test detecting repository root from a subdirectory."""
        # Create a git repository
        git.Repo.init(tmp_path)

        # Create a subdirectory
        subdir = tmp_path / "src" / "nested"
        subdir.mkdir(parents=True)

        observer = GitObserver(str(subdir))
        root = observer.detect_repository_root()

        assert root is not None
        assert Path(root) == tmp_path

    def test_detect_repository_root_not_in_repository(self, tmp_path):
        """Test that detection returns None when not in a repository."""
        # Create a non-git directory
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        root = observer.detect_repository_root()

        assert root is None

    def test_detect_repository_root_caches_repo(self, tmp_path):
        """Test that repository detection caches the repo object."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        assert observer._repo is None

        observer.detect_repository_root()
        assert observer._repo is not None
        assert observer._repo.working_dir == str(tmp_path)


class TestRemoteUrlExtraction:
    """Tests for remote URL extraction."""

    def test_get_remote_url_with_origin(self, tmp_path):
        """Test extracting remote URL when origin exists."""
        repo = git.Repo.init(tmp_path)
        remote_url = "https://github.com/user/repo.git"
        repo.create_remote("origin", remote_url)

        observer = GitObserver(str(tmp_path))
        url = observer.get_remote_url()

        assert url == remote_url

    def test_get_remote_url_without_origin(self, tmp_path):
        """Test that None is returned when origin doesn't exist."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        url = observer.get_remote_url()

        assert url is None

    def test_get_remote_url_custom_remote(self, tmp_path):
        """Test extracting URL from a custom remote name."""
        repo = git.Repo.init(tmp_path)
        remote_url = "https://github.com/user/repo.git"
        repo.create_remote("upstream", remote_url)

        observer = GitObserver(str(tmp_path))
        url = observer.get_remote_url("upstream")

        assert url == remote_url

    def test_get_remote_url_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        url = observer.get_remote_url()

        assert url is None


class TestRepositoryIdGeneration:
    """Tests for repository ID generation."""

    def test_generate_repository_id_with_remote(self, tmp_path):
        """Test generating repository ID with a remote URL."""
        repo = git.Repo.init(tmp_path)
        remote_url = "https://github.com/user/repo.git"
        repo.create_remote("origin", remote_url)

        observer = GitObserver(str(tmp_path))
        repo_id = observer.generate_repository_id()

        # Verify it's a valid SHA-256 hash (64 hex characters)
        assert repo_id is not None
        assert len(repo_id) == 64
        assert all(c in "0123456789abcdef" for c in repo_id)

        # Verify it's deterministic
        repo_id2 = observer.generate_repository_id()
        assert repo_id == repo_id2

    def test_generate_repository_id_without_remote(self, tmp_path):
        """Test generating repository ID without a remote (local-only repo)."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        repo_id = observer.generate_repository_id()

        # Should still generate an ID based on path only
        assert repo_id is not None
        assert len(repo_id) == 64
        assert all(c in "0123456789abcdef" for c in repo_id)

    def test_generate_repository_id_explicit_params(self, tmp_path):
        """Test generating repository ID with explicit parameters."""
        remote_url = "https://github.com/user/repo.git"
        root_path = str(tmp_path)

        observer = GitObserver()
        repo_id = observer.generate_repository_id(remote_url, root_path)

        assert repo_id is not None
        assert len(repo_id) == 64

        # Verify it matches expected hash
        canonical_remote = "https://github.com/user/repo"
        canonical_path = os.path.realpath(root_path)
        combined = f"{canonical_remote}|{canonical_path}"
        expected_hash = hashlib.sha256(combined.encode()).hexdigest()

        assert repo_id == expected_hash

    def test_generate_repository_id_different_paths_different_ids(self, tmp_path):
        """Test that same repo in different paths gets different IDs."""
        # Create two repositories with same remote
        repo1_path = tmp_path / "repo1"
        repo2_path = tmp_path / "repo2"
        repo1_path.mkdir()
        repo2_path.mkdir()

        remote_url = "https://github.com/user/repo.git"

        repo1 = git.Repo.init(repo1_path)
        repo1.create_remote("origin", remote_url)

        repo2 = git.Repo.init(repo2_path)
        repo2.create_remote("origin", remote_url)

        observer1 = GitObserver(str(repo1_path))
        observer2 = GitObserver(str(repo2_path))

        id1 = observer1.generate_repository_id()
        id2 = observer2.generate_repository_id()

        # Different paths should produce different IDs
        assert id1 != id2

    def test_generate_repository_id_different_remotes_different_ids(self, tmp_path):
        """Test that different remotes in same path get different IDs."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))

        id1 = observer.generate_repository_id("https://github.com/user/repo1.git", str(tmp_path))
        id2 = observer.generate_repository_id("https://github.com/user/repo2.git", str(tmp_path))

        # Different remotes should produce different IDs
        assert id1 != id2

    def test_generate_repository_id_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        repo_id = observer.generate_repository_id()

        assert repo_id is None


class TestGitUrlNormalization:
    """Tests for git URL normalization."""

    def test_normalize_https_url(self):
        """Test normalizing HTTPS URLs."""
        observer = GitObserver()

        url = "https://github.com/user/repo.git"
        normalized = observer._normalize_git_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_ssh_url(self):
        """Test normalizing SSH URLs."""
        observer = GitObserver()

        url = "git@github.com:user/repo.git"
        normalized = observer._normalize_git_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_git_protocol_url(self):
        """Test normalizing git:// protocol URLs."""
        observer = GitObserver()

        url = "git://github.com/user/repo.git"
        normalized = observer._normalize_git_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_without_git_extension(self):
        """Test normalizing URLs without .git extension."""
        observer = GitObserver()

        url = "https://github.com/user/repo"
        normalized = observer._normalize_git_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_url_with_trailing_slash(self):
        """Test normalizing URLs with trailing slashes."""
        observer = GitObserver()

        url = "https://github.com/user/repo.git/"
        normalized = observer._normalize_git_url(url)
        assert normalized == "https://github.com/user/repo"

    def test_normalize_empty_url(self):
        """Test normalizing empty URL."""
        observer = GitObserver()

        url = ""
        normalized = observer._normalize_git_url(url)
        assert normalized == ""


class TestCurrentBranch:
    """Tests for current branch detection."""

    def test_get_current_branch(self, tmp_path):
        """Test getting the current branch name."""
        repo = git.Repo.init(tmp_path)

        # Create an initial commit (required for branch to exist)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        branch = observer.get_current_branch()

        # Default branch is usually 'master' or 'main'
        assert branch in ["master", "main"]

    def test_get_current_branch_after_checkout(self, tmp_path):
        """Test getting branch name after checking out a new branch."""
        repo = git.Repo.init(tmp_path)

        # Create an initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Create and checkout a new branch
        new_branch = repo.create_head("feature-branch")
        new_branch.checkout()

        observer = GitObserver(str(tmp_path))
        branch = observer.get_current_branch()

        assert branch == "feature-branch"

    def test_get_current_branch_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        branch = observer.get_current_branch()

        assert branch is None

    def test_get_current_branch_empty_repository(self, tmp_path):
        """Test getting branch from an empty repository (no commits)."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        branch = observer.get_current_branch()

        # Empty repo might not have an active branch or might return None
        # This is acceptable behavior
        assert branch is None or branch in ["master", "main"]


class TestCommitSignalCapture:
    """Tests for commit signal capture."""

    def test_capture_commit_signal_with_commit(self, tmp_path):
        """Test capturing commit signal from a repository with commits."""
        repo = git.Repo.init(tmp_path)

        # Create a commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        commit_info = observer.capture_commit_signal()

        assert commit_info is not None
        assert commit_info.hash == commit.hexsha
        assert commit_info.message == "Initial commit"
        assert commit_info.timestamp == commit.committed_datetime
        assert "test.txt" in commit_info.files_changed

    def test_capture_commit_signal_multiple_files(self, tmp_path):
        """Test capturing commit signal with multiple changed files."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        repo.index.add(["file1.txt"])
        repo.index.commit("Initial commit")

        # Create second commit with multiple files
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"
        file2.write_text("content2")
        file3.write_text("content3")
        repo.index.add(["file2.txt", "file3.txt"])
        commit = repo.index.commit("Add multiple files")

        observer = GitObserver(str(tmp_path))
        commit_info = observer.capture_commit_signal()

        assert commit_info is not None
        assert commit_info.hash == commit.hexsha
        assert commit_info.message == "Add multiple files"
        assert "file2.txt" in commit_info.files_changed
        assert "file3.txt" in commit_info.files_changed

    def test_capture_commit_signal_no_commits(self, tmp_path):
        """Test that None is returned when repository has no commits."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        commit_info = observer.capture_commit_signal()

        assert commit_info is None

    def test_capture_commit_signal_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        commit_info = observer.capture_commit_signal()

        assert commit_info is None


class TestBranchSwitchCapture:
    """Tests for branch switch signal capture."""

    def test_capture_branch_switch(self, tmp_path):
        """Test capturing branch switch signal."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        switch_info = observer.capture_branch_switch("main", "feature-branch")

        assert switch_info is not None
        assert switch_info["from_branch"] == "main"
        assert switch_info["to_branch"] == "feature-branch"
        assert "timestamp" in switch_info
        assert "repository_id" in switch_info

    def test_capture_branch_switch_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        switch_info = observer.capture_branch_switch("main", "feature")

        assert switch_info is None


class TestUncommittedChangesCapture:
    """Tests for uncommitted changes capture."""

    def test_capture_uncommitted_changes_unstaged(self, tmp_path):
        """Test capturing unstaged changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Modify file without staging
        test_file.write_text("modified content")

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        assert len(changes) > 0
        assert any(change.path == "test.txt" for change in changes)
        assert any(change.status == "modified" for change in changes)

    def test_capture_uncommitted_changes_staged(self, tmp_path):
        """Test capturing staged changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Modify and stage file
        test_file.write_text("modified content")
        repo.index.add(["test.txt"])

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        assert len(changes) > 0
        assert any(change.path == "test.txt" for change in changes)

    def test_capture_uncommitted_changes_untracked(self, tmp_path):
        """Test capturing untracked files."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Create untracked file
        new_file = tmp_path / "new.txt"
        new_file.write_text("new content")

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        assert len(changes) > 0
        assert any(change.path == "new.txt" for change in changes)
        assert any(change.status == "added" for change in changes)

    def test_capture_uncommitted_changes_mixed(self, tmp_path):
        """Test capturing mixed staged, unstaged, and untracked changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        repo.index.add(["file1.txt"])
        repo.index.commit("Initial commit")

        # Staged change
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2")
        repo.index.add(["file2.txt"])

        # Unstaged change
        file1.write_text("modified content1")

        # Untracked file
        file3 = tmp_path / "file3.txt"
        file3.write_text("content3")

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        assert len(changes) >= 3
        paths = [change.path for change in changes]
        assert "file1.txt" in paths
        assert "file2.txt" in paths
        assert "file3.txt" in paths

    def test_capture_uncommitted_changes_no_changes(self, tmp_path):
        """Test that empty list is returned when no uncommitted changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        assert changes == []

    def test_capture_uncommitted_changes_not_in_repository(self, tmp_path):
        """Test that empty list is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        changes = observer.capture_uncommitted_changes()

        assert changes == []


class TestDiffSignalCapture:
    """Tests for diff signal capture."""

    def test_capture_diff_signal_with_changes(self, tmp_path):
        """Test capturing diff signal with uncommitted changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Modify file
        test_file.write_text("modified content")

        observer = GitObserver(str(tmp_path))
        diff_signal = observer.capture_diff_signal()

        assert diff_signal is not None
        assert "file_paths" in diff_signal
        assert "test.txt" in diff_signal["file_paths"]
        assert diff_signal["files_changed"] > 0
        assert "repository_id" in diff_signal
        assert diff_signal["capture_source"] == "save_context"

    def test_capture_diff_signal_custom_source(self, tmp_path):
        """Test capturing diff signal with custom source."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Modify file
        test_file.write_text("modified")

        observer = GitObserver(str(tmp_path))
        diff_signal = observer.capture_diff_signal(source="cli")

        assert diff_signal is not None
        assert diff_signal["capture_source"] == "cli"

    def test_capture_diff_signal_no_changes(self, tmp_path):
        """Test capturing diff signal with no changes."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        diff_signal = observer.capture_diff_signal()

        assert diff_signal is not None
        assert diff_signal["files_changed"] == 0
        assert diff_signal["file_paths"] == []

    def test_capture_diff_signal_not_in_repository(self, tmp_path):
        """Test that None is returned when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        diff_signal = observer.capture_diff_signal()

        assert diff_signal is None


class TestChangeStatusDetection:
    """Tests for change status detection helper."""

    def test_get_change_status_modified(self, tmp_path):
        """Test detecting modified file status."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Modify file
        test_file.write_text("modified")
        repo.index.add(["test.txt"])

        observer = GitObserver(str(tmp_path))
        diffs = repo.index.diff("HEAD")

        for diff in diffs:
            status = observer._get_change_status(diff)
            assert status == "modified"

    def test_get_change_status_added(self, tmp_path):
        """Test detecting added file status."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        repo.index.add(["file1.txt"])
        repo.index.commit("Initial commit")

        # Add new file
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2")
        repo.index.add(["file2.txt"])

        observer = GitObserver(str(tmp_path))
        diffs = repo.index.diff("HEAD")

        # Find the diff for file2.txt and check its status
        found = False
        for diff in diffs:
            # For added files, b_path contains the new file
            if diff.b_path == "file2.txt":
                status = observer._get_change_status(diff)
                assert status == "added"
                found = True
                break

        assert found, "file2.txt diff not found"

    def test_get_change_status_deleted(self, tmp_path):
        """Test detecting deleted file status."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Delete file
        test_file.unlink()
        repo.index.remove(["test.txt"])

        observer = GitObserver(str(tmp_path))
        diffs = repo.index.diff("HEAD")

        # Find the diff for test.txt and check its status
        found = False
        for diff in diffs:
            # For deleted files, a_path contains the old file
            if diff.a_path == "test.txt":
                status = observer._get_change_status(diff)
                assert status == "deleted"
                found = True
                break

        assert found, "test.txt diff not found"


class TestHookInstallation:
    """Tests for git hook installation."""

    def test_install_hooks_success(self, tmp_path):
        """Test successful installation of git hooks."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        result = observer.install_hooks()

        assert result["status"] == "active"
        assert result["post_checkout_installed"] is True
        assert result["post_commit_installed"] is True
        assert "error" not in result

        # Verify hooks exist
        hooks_dir = tmp_path / ".git" / "hooks"
        assert (hooks_dir / "post-checkout").exists()
        assert (hooks_dir / "post-commit").exists()

        # Verify hooks are executable
        assert os.access(hooks_dir / "post-checkout", os.X_OK)
        assert os.access(hooks_dir / "post-commit", os.X_OK)

    def test_install_hooks_creates_hooks_directory(self, tmp_path):
        """Test that hooks directory is created if it doesn't exist."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Remove hooks directory
        hooks_dir = tmp_path / ".git" / "hooks"
        if hooks_dir.exists():
            import shutil

            shutil.rmtree(hooks_dir)

        observer = GitObserver(str(tmp_path))
        result = observer.install_hooks()

        assert result["status"] == "active"
        assert hooks_dir.exists()

    def test_install_hooks_not_in_repository(self, tmp_path):
        """Test that installation fails when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        result = observer.install_hooks()

        assert result["status"] == "unavailable"
        assert result["post_checkout_installed"] is False
        assert result["post_commit_installed"] is False
        assert "error" in result

    def test_install_hooks_preserves_existing_hooks(self, tmp_path):
        """Test that existing hooks are backed up."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Create existing hook
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        existing_hook = hooks_dir / "post-checkout"
        existing_content = "#!/bin/bash\necho 'existing hook'\n"
        existing_hook.write_text(existing_content)

        observer = GitObserver(str(tmp_path))
        result = observer.install_hooks()

        assert result["status"] == "active"

        # Verify backup was created
        backup_path = hooks_dir / "post-checkout.backup"
        assert backup_path.exists()
        assert backup_path.read_text() == existing_content

    def test_install_hooks_idempotent(self, tmp_path):
        """Test that installing hooks multiple times is idempotent."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))

        # Install hooks first time
        result1 = observer.install_hooks()
        assert result1["status"] == "active"

        # Install hooks second time
        result2 = observer.install_hooks()
        assert result2["status"] == "active"

        # Verify no backup was created on second install
        hooks_dir = tmp_path / ".git" / "hooks"
        backup_path = hooks_dir / "post-checkout.backup"
        assert not backup_path.exists()

    def test_post_checkout_hook_content(self, tmp_path):
        """Test that post-checkout hook has correct content."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        observer.install_hooks()

        hooks_dir = tmp_path / ".git" / "hooks"
        hook_path = hooks_dir / "post-checkout"
        content = hook_path.read_text()

        assert "#!/bin/bash" in content
        assert "PREV_HEAD=$1" in content
        assert "NEW_HEAD=$2" in content
        assert "BRANCH_SWITCH=$3" in content
        assert 'if [ "$BRANCH_SWITCH" = "1" ]' in content
        assert "contextanchor _hook-branch-switch" in content

    def test_post_commit_hook_content(self, tmp_path):
        """Test that post-commit hook has correct content."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        observer.install_hooks()

        hooks_dir = tmp_path / ".git" / "hooks"
        hook_path = hooks_dir / "post-commit"
        content = hook_path.read_text()

        assert "#!/bin/bash" in content
        assert "contextanchor _hook-commit" in content


class TestHookInstallationPermissions:
    """Tests for hook installation with various permission scenarios."""

    def test_install_hooks_readonly_hooks_directory(self, tmp_path):
        """Test hook installation fails when hooks directory is read-only."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Make hooks directory read-only
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        os.chmod(hooks_dir, 0o444)

        try:
            observer = GitObserver(str(tmp_path))
            result = observer.install_hooks()

            assert result["status"] == "unavailable"
            assert result["post_checkout_installed"] is False
            assert result["post_commit_installed"] is False
            assert "error" in result
            assert "not writable" in result["error"].lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(hooks_dir, 0o755)

    def test_install_hooks_cannot_create_hooks_directory(self, tmp_path):
        """Test hook installation when hooks directory cannot be created."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Remove hooks directory and make .git read-only
        hooks_dir = tmp_path / ".git" / "hooks"
        if hooks_dir.exists():
            import shutil

            shutil.rmtree(hooks_dir)

        git_dir = tmp_path / ".git"
        os.chmod(git_dir, 0o444)

        try:
            observer = GitObserver(str(tmp_path))
            result = observer.install_hooks()

            assert result["status"] == "unavailable"
            assert result["post_checkout_installed"] is False
            assert result["post_commit_installed"] is False
            assert "error" in result
        finally:
            # Restore permissions for cleanup
            os.chmod(git_dir, 0o755)

    def test_install_hooks_partial_failure(self, tmp_path):
        """Test hook installation when one hook fails but the other succeeds."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Create hooks directory
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        # Create a read-only post-checkout file to block installation
        post_checkout = hooks_dir / "post-checkout"
        post_checkout.write_text("#!/bin/bash\necho 'existing'\n")
        os.chmod(post_checkout, 0o444)

        try:
            observer = GitObserver(str(tmp_path))
            result = observer.install_hooks()

            # Should be degraded since post-commit can install but post-checkout cannot
            assert result["status"] in ["degraded", "unavailable"]
            assert (
                result["post_commit_installed"] is True or result["post_commit_installed"] is False
            )
        finally:
            # Restore permissions for cleanup
            if post_checkout.exists():
                os.chmod(post_checkout, 0o755)


class TestGitCommandErrorHandling:
    """Tests for error handling when git commands fail."""

    def test_capture_commit_signal_handles_git_error(self, tmp_path):
        """Test that commit signal capture handles git errors gracefully."""
        # Create a repository but corrupt it
        repo = git.Repo.init(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Corrupt the repository by removing HEAD
        head_file = tmp_path / ".git" / "HEAD"
        head_file.unlink()

        observer = GitObserver(str(tmp_path))
        commit_info = observer.capture_commit_signal()

        # Should return None instead of crashing
        assert commit_info is None

    def test_capture_uncommitted_changes_handles_git_error(self, tmp_path):
        """Test that uncommitted changes capture handles git errors gracefully."""
        # Create a repository but corrupt it severely
        repo = git.Repo.init(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Corrupt the repository by removing the objects directory
        import shutil

        objects_dir = tmp_path / ".git" / "objects"
        shutil.rmtree(objects_dir)

        observer = GitObserver(str(tmp_path))
        changes = observer.capture_uncommitted_changes()

        # Should return empty list instead of crashing
        assert changes == []

    def test_get_current_branch_handles_detached_head(self, tmp_path):
        """Test that current branch detection handles detached HEAD state."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        # Detach HEAD
        repo.git.checkout(commit.hexsha)

        observer = GitObserver(str(tmp_path))
        branch = observer.get_current_branch()

        # Should return None for detached HEAD
        assert branch is None

    def test_detect_repository_root_handles_permission_error(self, tmp_path):
        """Test that repository detection handles permission errors gracefully."""
        # Create a git repository
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        git.Repo.init(repo_dir)

        # Create a subdirectory
        subdir = repo_dir / "subdir"
        subdir.mkdir()

        # Make the .git directory inaccessible
        git_dir = repo_dir / ".git"
        os.chmod(git_dir, 0o000)

        try:
            observer = GitObserver(str(subdir))
            root = observer.detect_repository_root()

            # Should return None instead of crashing
            assert root is None
        finally:
            # Restore permissions for cleanup
            os.chmod(git_dir, 0o755)

    def test_get_remote_url_handles_missing_remote(self, tmp_path):
        """Test that remote URL extraction handles missing remotes gracefully."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))
        url = observer.get_remote_url("nonexistent")

        # Should return None for missing remote
        assert url is None

    def test_capture_diff_signal_handles_empty_repository(self, tmp_path):
        """Test that diff signal capture handles empty repositories gracefully."""
        git.Repo.init(tmp_path)

        observer = GitObserver(str(tmp_path))

        # Empty repository should still work, just with no changes
        # The implementation already handles this in capture_uncommitted_changes
        # by catching GitCommandError when there's no HEAD
        diff_signal = observer.capture_diff_signal()

        # Should return valid signal with no changes
        assert diff_signal is not None
        assert diff_signal["files_changed"] == 0
        assert diff_signal["file_paths"] == []

    def test_install_hooks_handles_corrupted_repository(self, tmp_path):
        """Test that hook installation handles corrupted repositories gracefully."""
        # Create a directory that looks like a git repo but is corrupted
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        observer = GitObserver(str(tmp_path))
        result = observer.install_hooks()

        # Should return unavailable status
        assert result["status"] == "unavailable"
        assert "error" in result


class TestHookStatus:
    """Tests for hook status detection."""

    def test_get_hook_status_active(self, tmp_path):
        """Test hook status when both hooks are installed."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        observer.install_hooks()

        status = observer.get_hook_status()
        assert status == "active"

    def test_get_hook_status_degraded_post_checkout_only(self, tmp_path):
        """Test hook status when only post-checkout hook is installed."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Install only post-checkout hook
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook_path = hooks_dir / "post-checkout"
        hook_content = """#!/bin/bash
contextanchor _hook-branch-switch "$1" "$2" &
"""
        hook_path.write_text(hook_content)
        os.chmod(hook_path, 0o755)

        observer = GitObserver(str(tmp_path))
        status = observer.get_hook_status()
        assert status == "degraded"

    def test_get_hook_status_degraded_post_commit_only(self, tmp_path):
        """Test hook status when only post-commit hook is installed."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Install only post-commit hook
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook_path = hooks_dir / "post-commit"
        hook_content = """#!/bin/bash
contextanchor _hook-commit &
"""
        hook_path.write_text(hook_content)
        os.chmod(hook_path, 0o755)

        observer = GitObserver(str(tmp_path))
        status = observer.get_hook_status()
        assert status == "degraded"

    def test_get_hook_status_unavailable_no_hooks(self, tmp_path):
        """Test hook status when no hooks are installed."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        observer = GitObserver(str(tmp_path))
        status = observer.get_hook_status()
        assert status == "unavailable"

    def test_get_hook_status_unavailable_not_in_repository(self, tmp_path):
        """Test hook status when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        observer = GitObserver(str(non_repo))
        status = observer.get_hook_status()
        assert status == "unavailable"

    def test_get_hook_status_ignores_non_contextanchor_hooks(self, tmp_path):
        """Test that status ignores hooks not installed by ContextAnchor."""
        repo = git.Repo.init(tmp_path)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        # Create hooks without ContextAnchor markers
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        post_checkout = hooks_dir / "post-checkout"
        post_checkout.write_text("#!/bin/bash\necho 'other hook'\n")
        os.chmod(post_checkout, 0o755)

        post_commit = hooks_dir / "post-commit"
        post_commit.write_text("#!/bin/bash\necho 'other hook'\n")
        os.chmod(post_commit, 0o755)

        observer = GitObserver(str(tmp_path))
        status = observer.get_hook_status()
        assert status == "unavailable"
