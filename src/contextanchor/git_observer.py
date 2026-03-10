"""
Git Observer component for ContextAnchor.

This module provides git activity monitoring and repository detection capabilities,
including repository root detection, git availability checking, remote URL extraction,
and repository ID generation.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import git
from git.exc import InvalidGitRepositoryError, GitCommandError


class GitObserver:
    """
    Observes git activity and provides repository detection capabilities.

    Responsibilities:
    - Detect repository root from any subdirectory
    - Check git availability
    - Extract remote URLs
    - Generate unique repository identifiers
    - Monitor git activity (commits, branches, diffs)
    """

    def __init__(self, repository_path: Optional[str] = None):
        """
        Initialize GitObserver.

        Args:
            repository_path: Path to repository (defaults to current directory)
        """
        self.repository_path = repository_path or os.getcwd()
        self._repo: Optional[git.Repo] = None

    def is_git_available(self) -> bool:
        """
        Check if git is available on the system.

        Returns:
            True if git command is available, False otherwise

        Validates: Requirements 7.4
        """
        try:
            git.Git().version()
            return True
        except (GitCommandError, Exception):
            return False

    def detect_repository_root(self) -> Optional[str]:
        """
        Detect the git repository root from the current or specified path.

        Searches upward from the given path to find the repository root.
        Works from any subdirectory within a repository.

        Returns:
            Absolute path to repository root, or None if not in a repository

        Validates: Requirements 1.5, 11.4
        """
        try:
            repo = git.Repo(self.repository_path, search_parent_directories=True)
            self._repo = repo
            # Ensure we return a string, not PathLike
            working_dir = repo.working_dir
            return str(working_dir) if working_dir else None
        except (InvalidGitRepositoryError, GitCommandError):
            return None

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """
        Extract the remote URL for the specified remote.

        Args:
            remote_name: Name of the remote (default: "origin")

        Returns:
            Remote URL string, or None if remote doesn't exist

        Validates: Requirements 1.5, 11.6
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return None

        # At this point, self._repo should be set by detect_repository_root
        if self._repo is None:
            return None

        try:
            remote = self._repo.remote(remote_name)
            # Get the first URL (remotes can have multiple URLs)
            urls = list(remote.urls)
            return urls[0] if urls else None
        except (ValueError, GitCommandError):
            return None

    def generate_repository_id(
        self, remote_url: Optional[str] = None, root_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate unique repository identifier using SHA-256 hash.

        The repository ID is generated from the canonical remote URL and root path
        to ensure uniqueness across different clones and repositories with the same name.

        Args:
            remote_url: Git remote URL (auto-detected if not provided)
            root_path: Repository root path (auto-detected if not provided)

        Returns:
            SHA-256 hash (64 hex characters), or None if repository cannot be detected

        Validates: Requirements 11.4, 11.6
        """
        # Auto-detect if not provided
        if root_path is None:
            root_path = self.detect_repository_root()
            if root_path is None:
                return None

        if remote_url is None:
            remote_url = self.get_remote_url()
            if remote_url is None:
                # If no remote, use root path only
                # This handles local-only repositories
                remote_url = ""

        # Normalize the remote URL
        canonical_remote = self._normalize_git_url(remote_url)

        # Normalize the root path
        canonical_path = os.path.realpath(root_path)

        # Combine and hash
        combined = f"{canonical_remote}|{canonical_path}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _normalize_git_url(self, url: str) -> str:
        """
        Normalize a git URL to a canonical form.

        Handles various git URL formats:
        - HTTPS: https://github.com/user/repo.git
        - SSH: git@github.com:user/repo.git
        - Git protocol: git://github.com/user/repo.git

        Args:
            url: Git remote URL in any format

        Returns:
            Normalized URL in canonical form
        """
        if not url:
            return ""

        # Remove trailing .git if present
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Handle SSH format (git@host:path)
        if "@" in url and "://" not in url:
            # Convert git@github.com:user/repo to https://github.com/user/repo
            parts = url.split("@", 1)
            if len(parts) == 2:
                host_path = parts[1].replace(":", "/", 1)
                url = f"https://{host_path}"

        # Parse and reconstruct to normalize
        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                # Reconstruct with https scheme for consistency
                path = parsed.path.rstrip("/")
                return f"https://{parsed.netloc}{path}"
        except Exception:
            pass

        # Return as-is if we can't parse it
        return url

    def get_current_branch(self) -> Optional[str]:
        """
        Get the name of the current branch.

        Returns:
            Current branch name, or None if detached HEAD or error

        Validates: Requirements 1.2, 3.3
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return None

        # At this point, self._repo should be set by detect_repository_root
        if self._repo is None:
            return None

        try:
            return self._repo.active_branch.name
        except (TypeError, GitCommandError):
            # Detached HEAD state or other error
            return None

        def capture_commit_signal(self) -> Optional["CommitInfo"]:
        """
        Extract signal from most recent commit.

        Returns:
            CommitInfo with hash, message, timestamp, and changed files,
            or None if no commits exist or error occurs

        Validates: Requirements 1.1
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return None

        if self._repo is None:
            return None

        try:
            # Get the most recent commit
            commit = self._repo.head.commit

            # Extract changed files from the commit
            files_changed = []
            if commit.parents:
                # Compare with parent to get changed files
                parent = commit.parents[0]
                diffs = parent.diff(commit)
                files_changed = [diff.a_path or diff.b_path for diff in diffs]
            else:
                # First commit - all files are new
                files_changed = [item.path for item in commit.tree.traverse()]

            # Import here to avoid circular dependency
            from contextanchor.models import CommitInfo

            return CommitInfo(
                hash=commit.hexsha,
                message=commit.message.strip(),
                timestamp=commit.committed_datetime,
                files_changed=files_changed,
            )
        except (ValueError, GitCommandError, AttributeError):
            return None

    def capture_branch_switch(
        self, from_branch: str, to_branch: str
    ) -> Optional[dict]:
        """
        Record branch switch event.

        Args:
            from_branch: Source branch name
            to_branch: Target branch name

        Returns:
            Dictionary with branch switch information including timestamp,
            or None if repository not detected

        Validates: Requirements 1.2
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return None

        return {
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": datetime.now(),
            "repository_id": self.generate_repository_id(),
        }

    def capture_uncommitted_changes(self) -> list:
    """
    Analyze staged and unstaged changes.

    Returns:
        List of FileChange objects representing both staged and unstaged changes,
        or empty list if no changes or error occurs

    Validates: Requirements 2.1, 2.6
    """
    if self._repo is None:
        root = self.detect_repository_root()
        if root is None:
            return []

    if self._repo is None:
        return []

    try:
        from contextanchor.models import FileChange

        changes = []

        # Get unstaged changes (working directory vs index)
        unstaged_diffs = self._repo.index.diff(None)
        for diff in unstaged_diffs:
            path = diff.a_path or diff.b_path
            status = self._get_change_status(diff)
            changes.append(
                FileChange(
                    path=path,
                    status=status,
                    lines_added=0,  # GitPython doesn't provide line counts for unstaged
                    lines_deleted=0,
                )
            )

        # Get staged changes (HEAD vs index)
        try:
            staged_diffs = self._repo.index.diff("HEAD")
            for diff in staged_diffs:
                path = diff.a_path or diff.b_path
                status = self._get_change_status(diff)
                changes.append(
                    FileChange(
                        path=path,
                        status=status,
                        lines_added=0,  # GitPython doesn't provide line counts easily
                        lines_deleted=0,
                    )
                )
        except GitCommandError:
            # No HEAD commit yet (empty repository)
            pass

        # Get untracked files
        untracked_files = self._repo.untracked_files
        for path in untracked_files:
            changes.append(
                FileChange(
                    path=path,
                    status="added",
                    lines_added=0,
                    lines_deleted=0,
                )
            )

        return changes
    except (GitCommandError, AttributeError):
        return []

def capture_diff_signal(self, source: str = "save_context") -> Optional[dict]:
    """
    Capture file paths and summary stats for current staged/unstaged diff.

    Args:
        source: Capture source identifier (default: "save_context")

    Returns:
        Dictionary with file paths, summary statistics, repository_id, and capture_source,
        or None if repository not detected

    Validates: Requirements 1.3, 1.5, 1.6
    """
    if self._repo is None:
        root = self.detect_repository_root()
        if root is None:
            return None

    if self._repo is None:
        return None

    try:
        file_changes = self.capture_uncommitted_changes()

        # Calculate summary statistics
        files_changed = len(file_changes)
        lines_added = sum(fc.lines_added for fc in file_changes)
        lines_deleted = sum(fc.lines_deleted for fc in file_changes)

        return {
            "file_paths": [fc.path for fc in file_changes],
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "repository_id": self.generate_repository_id(),
            "capture_source": source,
        }
    except (GitCommandError, AttributeError):
        return None

def _get_change_status(self, diff) -> str:
    """
    Determine the change status from a git diff object.

    Args:
        diff: GitPython diff object

    Returns:
        Status string: "modified", "added", "deleted", or "renamed"
    """
    if diff.new_file:
        return "added"
    elif diff.deleted_file:
        return "deleted"
    elif diff.renamed_file:
        return "renamed"
    else:
        return "modified"

