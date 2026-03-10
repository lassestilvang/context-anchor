"""
GitHub Integration Component for ContextAnchor.

This module provides functionality to:
- Extract GitHub repository metadata from git remote URLs
- Parse PR and issue references from commit messages
- Generate GitHub links for PRs and issues

Requirements: 10.1, 10.2, 10.3, 10.6
"""

import re
from typing import List, Optional
from urllib.parse import urlparse

from .models import GitHubRepo


# Regex patterns for parsing PR references
PR_PATTERNS = [
    r'#(\d+)',                    # #123
    r'PR\s*#(\d+)',              # PR #123
    r'pull request\s*#(\d+)',    # pull request #123
]

# Regex patterns for parsing issue references with keywords
ISSUE_PATTERNS = [
    r'(?:fixes|closes|resolves|refs)\s+#(\d+)',  # fixes #456
    r'(?:fix|close|resolve|ref)\s+#(\d+)',       # fix #456
]


class GitHubIntegration:
    """
    GitHub integration component for parsing repository metadata and references.
    
    This class provides methods to extract GitHub-specific information from
    git remotes and commit messages, enabling rich context linking.
    """

    def parse_remote_url(self, remote_url: str) -> Optional[GitHubRepo]:
        """
        Extract owner/repo from GitHub remote URL.
        
        Handles various GitHub URL formats:
        - HTTPS: https://github.com/user/repo.git
        - SSH: git@github.com:user/repo.git
        - Git protocol: git://github.com/user/repo.git
        
        Args:
            remote_url: Git remote URL to parse
            
        Returns:
            GitHubRepo object with owner, name, and remote_url if the URL is a
            valid GitHub URL, None otherwise
            
        Requirements: 10.1
        """
        if not remote_url:
            return None
            
        # Normalize the URL to extract owner/repo
        normalized_url = self._normalize_github_url(remote_url)
        if not normalized_url:
            return None
            
        # Extract owner and repo from normalized URL
        # Format: https://github.com/owner/repo
        try:
            parsed = urlparse(normalized_url)
            if parsed.netloc != "github.com":
                return None
                
            # Path should be /owner/repo
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) != 2:
                return None
                
            owner, repo = path_parts
            if not owner or not repo:
                return None
                
            return GitHubRepo(
                owner=owner,
                name=repo,
                remote_url=remote_url
            )
        except Exception:
            return None

    def _normalize_github_url(self, url: str) -> Optional[str]:
        """
        Normalize various GitHub URL formats to a standard HTTPS format.
        
        Args:
            url: Git remote URL in any format
            
        Returns:
            Normalized HTTPS URL (https://github.com/owner/repo) or None if not a GitHub URL
        """
        if not url:
            return None
            
        # Remove trailing slashes and .git extension
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
            
        # Handle SSH format (git@github.com:user/repo)
        if "@" in url and "://" not in url:
            # Convert git@github.com:user/repo to https://github.com/user/repo
            parts = url.split("@", 1)
            if len(parts) == 2:
                host_path = parts[1].replace(":", "/", 1)
                url = f"https://{host_path}"
                
        # Handle git:// protocol
        if url.startswith("git://"):
            url = url.replace("git://", "https://", 1)
            
        # Verify it's a GitHub URL
        if "github.com" not in url:
            return None
            
        # Ensure it's HTTPS
        if not url.startswith("https://"):
            return None
            
        return url

    def parse_pr_references(self, text: str) -> List[int]:
        """
        Extract PR numbers from text using regex patterns.
        
        Matches patterns like:
        - #123
        - PR #123
        - pull request #123
        
        Args:
            text: Text to search for PR references (e.g., commit message)
            
        Returns:
            List of unique PR numbers found in the text
            
        Requirements: 10.2
        """
        if not text:
            return []
            
        pr_numbers = set()
        
        for pattern in PR_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                pr_number = int(match.group(1))
                pr_numbers.add(pr_number)
                
        return sorted(list(pr_numbers))

    def parse_issue_references(self, text: str) -> List[int]:
        """
        Extract issue numbers from text with keywords.
        
        Matches patterns like:
        - fixes #456
        - closes #456
        - resolves #456
        - refs #456
        - fix #456
        - close #456
        - resolve #456
        - ref #456
        
        Args:
            text: Text to search for issue references (e.g., commit message)
            
        Returns:
            List of unique issue numbers found in the text
            
        Requirements: 10.3, 10.6
        """
        if not text:
            return []
            
        issue_numbers = set()
        
        for pattern in ISSUE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issue_number = int(match.group(1))
                issue_numbers.add(issue_number)
                
        return sorted(list(issue_numbers))

    def format_pr_link(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Generate GitHub PR URL.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            pr_number: Pull request number
            
        Returns:
            Full GitHub PR URL
            
        Requirements: 10.6
        """
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"

    def format_issue_link(self, owner: str, repo: str, issue_number: int) -> str:
        """
        Generate GitHub issue URL.
        
        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            issue_number: Issue number
            
        Returns:
            Full GitHub issue URL
            
        Requirements: 10.6
        """
        return f"https://github.com/{owner}/{repo}/issues/{issue_number}"
