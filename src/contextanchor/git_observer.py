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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import CommitInfo

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

    def get_github_metadata(self) -> Optional["GitHubRepo"]:  # noqa: F821
        """
        Extract GitHub metadata from the remote URL.
        
        Returns:
            GitHubRepo object if the remote is a GitHub URL, None otherwise.
        """
        url = self.get_remote_url()
        if not url:
            return None
            
        # Standardize URL
        normalized = self._normalize_git_url(url)
        
        if "github.com" not in normalized:
            return None
            
        try:
            # Normalized is https://github.com/owner/repo
            path = urlparse(normalized).path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2:
                from contextanchor.models import GitHubRepo
                return GitHubRepo(
                    owner=parts[0],
                    name=parts[1],
                    remote_url=url
                )
        except Exception:
            pass
            
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
        except Exception:  # nosec
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

    def capture_commit_signal(self) -> Optional["CommitInfo"]:  # noqa: F821
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
                files_changed = [str(diff.a_path or diff.b_path) for diff in diffs if diff.a_path or diff.b_path]
            else:
                # First commit - all files are new
                files_changed = [str(getattr(item, "path")) for item in commit.tree.traverse() if getattr(item, "path", None)]

            # Import here to avoid circular dependency
            from contextanchor.models import CommitInfo

            message_str = commit.message
            if isinstance(message_str, bytes):
                message_str = message_str.decode("utf-8")
            
            message_str = message_str.strip()
            # Extract references
            refs = self.parse_references(message_str)

            return CommitInfo(
                hash=commit.hexsha,
                message=message_str,
                timestamp=commit.committed_datetime,
                files_changed=files_changed,
            )
        except (ValueError, GitCommandError, AttributeError):
            return None

    def parse_references(self, text: str) -> dict:
        """
        Parse issue and PR references from text using hardened patterns.
        
        Args:
            text: Text to parse (e.g., commit message)
            
        Returns:
            Dictionary with 'issue_references' and 'pr_references' lists.
        """
        import re
        # Look for # followed by digits, or GH- followed by digits
        pattern = re.compile(r'(?i)(?:#|gh-)(\d+)')
        matches = pattern.findall(text)
        
        # Extract PR references specifically from merge commits if possible
        # e.g. "Merge pull request #123 from..."
        pr_pattern = re.compile(r'(?i)pull request #(\d+)')
        pr_matches = pr_pattern.findall(text)
        
        unique_issues = list(set(int(m) for m in matches))
        unique_prs = list(set(int(m) for m in pr_matches))
        
        return {
            "issue_references": unique_issues,
            "pr_references": unique_prs
        }

    def capture_branch_switch(self, from_branch: str, to_branch: str) -> Optional[dict]:
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
                path = str(diff.a_path or diff.b_path)
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
                    path = str(diff.a_path or diff.b_path)
                    status = self._get_change_status(diff)
                    changes.append(
                        FileChange(
                            path=path,
                            status=status,
                            lines_added=0,  # GitPython doesn't provide line counts easily
                            lines_deleted=0,
                        )
                    )
            except (GitCommandError, Exception):
                # No HEAD commit yet (empty repository) or other git errors
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

    def _get_change_status(self, diff: Any) -> str:
        """
        Determine the change status from a git diff object.

        Args:
            diff: GitPython diff object

        Returns:
            Status string: "modified", "added", "deleted", or "renamed"
        """
        # When using index.diff("HEAD"), the diff shows changes FROM HEAD TO index
        # This means the change_type is inverted from what we'd expect:
        # - change_type='D' means file is in HEAD but not in index (deleted)
        # - change_type='A' means file is not in HEAD but in index (added)
        # But GitPython reports them backwards, so we need to invert

        if diff.renamed_file or (hasattr(diff, "rename_from") and diff.rename_from):
            return "renamed"
        elif diff.change_type == "D":
            # File deleted from HEAD's perspective = added to index
            return "added"
        elif diff.change_type == "A":
            # File added from HEAD's perspective = deleted from index
            return "deleted"
        elif diff.change_type == "M":
            return "modified"
        elif diff.change_type == "R":
            return "renamed"
        else:
            # Fallback logic
            if diff.a_path is None:
                return "added"
            elif diff.b_path is None:
                return "deleted"
            else:
                return "modified"

    def install_hooks(self) -> dict:
        """
        Install git hooks for automatic monitoring.

        Installs post-checkout and post-commit hooks to enable automatic
        branch switch detection and commit signal capture.

        Returns:
            Dictionary with installation result:
            - status: "active", "degraded", or "unavailable"
            - post_checkout_installed: bool
            - post_commit_installed: bool
            - error: Optional error message

        Validates: Requirements 5.6, 7.6
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return {
                    "status": "unavailable",
                    "post_checkout_installed": False,
                    "post_commit_installed": False,
                    "error": "Not in a git repository",
                }

        if self._repo is None:
            return {
                "status": "unavailable",
                "post_checkout_installed": False,
                "post_commit_installed": False,
                "error": "Repository not detected",
            }

        hooks_dir = os.path.join(self._repo.git_dir, "hooks")

        # Check if hooks directory exists and is writable
        if not os.path.exists(hooks_dir):
            try:
                os.makedirs(hooks_dir, mode=0o755)
            except (OSError, PermissionError) as e:
                return {
                    "status": "unavailable",
                    "post_checkout_installed": False,
                    "post_commit_installed": False,
                    "error": f"Cannot create hooks directory: {e}",
                }

        if not os.access(hooks_dir, os.W_OK):
            return {
                "status": "unavailable",
                "post_checkout_installed": False,
                "post_commit_installed": False,
                "error": "Hooks directory is not writable",
            }

        # Install post-checkout hook
        post_checkout_installed = self._install_post_checkout_hook(hooks_dir)

        # Install post-commit hook
        post_commit_installed = self._install_post_commit_hook(hooks_dir)

        # Determine overall status
        if post_checkout_installed and post_commit_installed:
            status = "active"
        elif post_checkout_installed or post_commit_installed:
            status = "degraded"
        else:
            status = "unavailable"

        return {
            "status": status,
            "post_checkout_installed": post_checkout_installed,
            "post_commit_installed": post_commit_installed,
        }

    def _install_post_checkout_hook(self, hooks_dir: str) -> bool:
        """
        Install post-checkout hook for branch switch detection.

        Args:
            hooks_dir: Path to .git/hooks directory

        Returns:
            True if hook was installed successfully, False otherwise
        """
        hook_path = os.path.join(hooks_dir, "post-checkout")

        # Hook template
        hook_content = """#!/bin/bash
# .git/hooks/post-checkout
# Installed by ContextAnchor init command

PREV_HEAD=$1
NEW_HEAD=$2
BRANCH_SWITCH=$3

if [ "$BRANCH_SWITCH" = "1" ]; then
    # Branch switch detected, trigger context restoration
    contextanchor _hook-branch-switch "$PREV_HEAD" "$NEW_HEAD" &
fi
"""

        try:
            # Check if hook already exists
            if os.path.exists(hook_path):
                # Read existing hook
                with open(hook_path, "r") as f:
                    existing_content = f.read()

                # Check if our hook is already installed
                if "contextanchor _hook-branch-switch" in existing_content:
                    # Already installed
                    return True

                # Backup existing hook
                backup_path = hook_path + ".backup"
                with open(backup_path, "w") as f:
                    f.write(existing_content)

            # Write hook
            with open(hook_path, "w") as f:
                f.write(hook_content)

            # Make executable
            os.chmod(hook_path, 0o755)  # nosec

            return True
        except (OSError, PermissionError):
            return False

    def _install_post_commit_hook(self, hooks_dir: str) -> bool:
        """
        Install post-commit hook for commit signal capture.

        Args:
            hooks_dir: Path to .git/hooks directory

        Returns:
            True if hook was installed successfully, False otherwise
        """
        hook_path = os.path.join(hooks_dir, "post-commit")

        # Hook template
        hook_content = """#!/bin/bash
# .git/hooks/post-commit
# Installed by ContextAnchor init command

# Capture commit signal in background
contextanchor _hook-commit &
"""

        try:
            # Check if hook already exists
            if os.path.exists(hook_path):
                # Read existing hook
                with open(hook_path, "r") as f:
                    existing_content = f.read()

                # Check if our hook is already installed
                if "contextanchor _hook-commit" in existing_content:
                    # Already installed
                    return True

                # Backup existing hook
                backup_path = hook_path + ".backup"
                with open(backup_path, "w") as f:
                    f.write(existing_content)

            # Write hook
            with open(hook_path, "w") as f:
                f.write(hook_content)

            # Make executable
            os.chmod(hook_path, 0o755)  # nosec

            return True
        except (OSError, PermissionError):
            return False

    def get_hook_status(self) -> str:
        """
        Detect the status of installed git hooks.

        Returns:
            Hook status: "active", "degraded", or "unavailable"
            - "active": Both hooks installed and working
            - "degraded": Only one hook installed
            - "unavailable": No hooks installed or cannot install

        Validates: Requirements 7.6
        """
        if self._repo is None:
            root = self.detect_repository_root()
            if root is None:
                return "unavailable"

        if self._repo is None:
            return "unavailable"

        hooks_dir = os.path.join(self._repo.git_dir, "hooks")

        # Check if hooks directory exists and is writable
        if not os.path.exists(hooks_dir) or not os.access(hooks_dir, os.W_OK):
            return "unavailable"

        # Check post-checkout hook
        post_checkout_path = os.path.join(hooks_dir, "post-checkout")
        post_checkout_installed = False
        if os.path.exists(post_checkout_path):
            try:
                with open(post_checkout_path, "r") as f:
                    content = f.read()
                    if "contextanchor _hook-branch-switch" in content:
                        post_checkout_installed = True
            except (OSError, PermissionError):
                pass

        # Check post-commit hook
        post_commit_path = os.path.join(hooks_dir, "post-commit")
        post_commit_installed = False
        if os.path.exists(post_commit_path):
            try:
                with open(post_commit_path, "r") as f:
                    content = f.read()
                    if "contextanchor _hook-commit" in content:
                        post_commit_installed = True
            except (OSError, PermissionError):
                pass

        # Determine status
        if post_checkout_installed and post_commit_installed:
            return "active"
        elif post_checkout_installed or post_commit_installed:
            return "degraded"
        else:
            return "unavailable"

    def has_productive_action_since(self, since_timestamp: datetime) -> bool:
        """
        Check if any productive action (staged changes or new commits)
        has occurred since the given timestamp.

        Args:
            since_timestamp: The starting timestamp (UTC)

        Returns:
            True if staged changes or new commits exist, False otherwise
        """
        if self._repo is None:
            if self.detect_repository_root() is None:
                return False

        if self._repo is None:
            return False

        # Check for staged changes
        try:
            if len(self._repo.index.diff("HEAD")) > 0:
                return True
        except (GitCommandError, Exception):
            # Might be empty repo or detached head
            pass

        # Check for new commits
        try:
            # Iter commits on current branch
            # Limit to last 10 should be enough for a quick check
            for commit in self._repo.iter_commits(max_count=10):
                # commit.committed_datetime is offset-aware
                # Convert since_timestamp to be offset-aware if it's naive (assuming UTC)
                from datetime import timezone

                if since_timestamp.tzinfo is None:
                    since_ts = since_timestamp.replace(tzinfo=timezone.utc)
                else:
                    since_ts = since_timestamp

                if commit.committed_datetime > since_ts:
                    return True
                else:
                    # Since iter_commits is in reverse chronological order,
                    # we can stop once we hit a commit older than the timestamp
                    break
        except (GitCommandError, Exception):
            pass

        return False
