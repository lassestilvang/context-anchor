"""
Unit tests for GitHub Integration component.

Tests the parsing of GitHub remote URLs, PR references, and issue references.
"""

from src.contextanchor.github_integration import GitHubIntegration
from src.contextanchor.models import GitHubRepo


class TestParseRemoteUrl:
    """Tests for parse_remote_url method."""

    def test_parse_https_url(self):
        """Test parsing standard HTTPS GitHub URL."""
        integration = GitHubIntegration()
        url = "https://github.com/contextanchor/cli.git"

        result = integration.parse_remote_url(url)

        assert result is not None
        assert isinstance(result, GitHubRepo)
        assert result.owner == "contextanchor"
        assert result.name == "cli"
        assert result.remote_url == url

    def test_parse_https_url_without_git_extension(self):
        """Test parsing HTTPS URL without .git extension."""
        integration = GitHubIntegration()
        url = "https://github.com/user/repo"

        result = integration.parse_remote_url(url)

        assert result is not None
        assert result.owner == "user"
        assert result.name == "repo"

    def test_parse_ssh_url(self):
        """Test parsing SSH GitHub URL."""
        integration = GitHubIntegration()
        url = "git@github.com:contextanchor/cli.git"

        result = integration.parse_remote_url(url)

        assert result is not None
        assert result.owner == "contextanchor"
        assert result.name == "cli"
        assert result.remote_url == url

    def test_parse_git_protocol_url(self):
        """Test parsing git:// protocol URL."""
        integration = GitHubIntegration()
        url = "git://github.com/user/repo.git"

        result = integration.parse_remote_url(url)

        assert result is not None
        assert result.owner == "user"
        assert result.name == "repo"

    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        integration = GitHubIntegration()
        url = "https://github.com/user/repo.git/"

        result = integration.parse_remote_url(url)

        assert result is not None
        assert result.owner == "user"
        assert result.name == "repo"

    def test_parse_non_github_url(self):
        """Test parsing non-GitHub URL returns None."""
        integration = GitHubIntegration()
        url = "https://gitlab.com/user/repo.git"

        result = integration.parse_remote_url(url)

        assert result is None

    def test_parse_invalid_url(self):
        """Test parsing invalid URL returns None."""
        integration = GitHubIntegration()
        url = "not-a-valid-url"

        result = integration.parse_remote_url(url)

        assert result is None

    def test_parse_empty_url(self):
        """Test parsing empty URL returns None."""
        integration = GitHubIntegration()

        result = integration.parse_remote_url("")

        assert result is None

    def test_parse_none_url(self):
        """Test parsing None URL returns None."""
        integration = GitHubIntegration()

        result = integration.parse_remote_url(None)

        assert result is None

    def test_parse_url_with_invalid_path(self):
        """Test parsing URL with invalid path structure."""
        integration = GitHubIntegration()
        url = "https://github.com/onlyowner"

        result = integration.parse_remote_url(url)

        assert result is None

    def test_parse_url_with_too_many_path_parts(self):
        """Test parsing URL with too many path parts."""
        integration = GitHubIntegration()
        url = "https://github.com/owner/repo/extra"

        result = integration.parse_remote_url(url)

        assert result is None


class TestParsePrReferences:
    """Tests for parse_pr_references method."""

    def test_parse_simple_pr_reference(self):
        """Test parsing simple #123 format."""
        integration = GitHubIntegration()
        text = "Fixed bug in #123"

        result = integration.parse_pr_references(text)

        assert result == [123]

    def test_parse_pr_with_prefix(self):
        """Test parsing PR #123 format."""
        integration = GitHubIntegration()
        text = "Merged PR #456"

        result = integration.parse_pr_references(text)

        assert result == [456]

    def test_parse_pull_request_format(self):
        """Test parsing 'pull request #123' format."""
        integration = GitHubIntegration()
        text = "Reviewed pull request #789"

        result = integration.parse_pr_references(text)

        assert result == [789]

    def test_parse_multiple_pr_references(self):
        """Test parsing multiple PR references."""
        integration = GitHubIntegration()
        text = "Fixed #123 and PR #456, also pull request #789"

        result = integration.parse_pr_references(text)

        assert result == [123, 456, 789]

    def test_parse_duplicate_pr_references(self):
        """Test parsing duplicate PR references returns unique list."""
        integration = GitHubIntegration()
        text = "Fixed #123 and also #123"

        result = integration.parse_pr_references(text)

        assert result == [123]

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        integration = GitHubIntegration()
        text = "Merged pr #123 and PR #456"

        result = integration.parse_pr_references(text)

        assert result == [123, 456]

    def test_parse_empty_text(self):
        """Test parsing empty text returns empty list."""
        integration = GitHubIntegration()

        result = integration.parse_pr_references("")

        assert result == []

    def test_parse_none_text(self):
        """Test parsing None text returns empty list."""
        integration = GitHubIntegration()

        result = integration.parse_pr_references(None)

        assert result == []

    def test_parse_text_without_references(self):
        """Test parsing text without PR references."""
        integration = GitHubIntegration()
        text = "Fixed a bug in the code"

        result = integration.parse_pr_references(text)

        assert result == []


class TestParseIssueReferences:
    """Tests for parse_issue_references method."""

    def test_parse_fixes_keyword(self):
        """Test parsing 'fixes #123' format."""
        integration = GitHubIntegration()
        text = "fixes #123"

        result = integration.parse_issue_references(text)

        assert result == [123]

    def test_parse_closes_keyword(self):
        """Test parsing 'closes #456' format."""
        integration = GitHubIntegration()
        text = "closes #456"

        result = integration.parse_issue_references(text)

        assert result == [456]

    def test_parse_resolves_keyword(self):
        """Test parsing 'resolves #789' format."""
        integration = GitHubIntegration()
        text = "resolves #789"

        result = integration.parse_issue_references(text)

        assert result == [789]

    def test_parse_refs_keyword(self):
        """Test parsing 'refs #012' format."""
        integration = GitHubIntegration()
        text = "refs #012"

        result = integration.parse_issue_references(text)

        assert result == [12]  # Leading zeros are stripped

    def test_parse_singular_keywords(self):
        """Test parsing singular forms (fix, close, resolve, ref)."""
        integration = GitHubIntegration()
        text = "fix #1 close #2 resolve #3 ref #4"

        result = integration.parse_issue_references(text)

        assert result == [1, 2, 3, 4]

    def test_parse_multiple_issue_references(self):
        """Test parsing multiple issue references."""
        integration = GitHubIntegration()
        text = "fixes #123 and closes #456"

        result = integration.parse_issue_references(text)

        assert result == [123, 456]

    def test_parse_duplicate_issue_references(self):
        """Test parsing duplicate issue references returns unique list."""
        integration = GitHubIntegration()
        text = "fixes #123 and resolves #123"

        result = integration.parse_issue_references(text)

        assert result == [123]

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        integration = GitHubIntegration()
        text = "Fixes #123 and CLOSES #456"

        result = integration.parse_issue_references(text)

        assert result == [123, 456]

    def test_parse_empty_text(self):
        """Test parsing empty text returns empty list."""
        integration = GitHubIntegration()

        result = integration.parse_issue_references("")

        assert result == []

    def test_parse_none_text(self):
        """Test parsing None text returns empty list."""
        integration = GitHubIntegration()

        result = integration.parse_issue_references(None)

        assert result == []

    def test_parse_text_without_keywords(self):
        """Test parsing text without issue keywords."""
        integration = GitHubIntegration()
        text = "Fixed bug #123"  # No keyword, just #123

        result = integration.parse_issue_references(text)

        assert result == []  # Should not match without keyword

    def test_parse_does_not_match_pr_only_references(self):
        """Test that issue parsing doesn't match PR-only references."""
        integration = GitHubIntegration()
        text = "PR #123"  # PR reference without issue keyword

        result = integration.parse_issue_references(text)

        assert result == []


class TestFormatPrLink:
    """Tests for format_pr_link method."""

    def test_format_pr_link(self):
        """Test formatting PR link."""
        integration = GitHubIntegration()

        link = integration.format_pr_link("contextanchor", "cli", 123)

        assert link == "https://github.com/contextanchor/cli/pull/123"

    def test_format_pr_link_with_different_values(self):
        """Test formatting PR link with different values."""
        integration = GitHubIntegration()

        link = integration.format_pr_link("user", "repo", 456)

        assert link == "https://github.com/user/repo/pull/456"


class TestFormatIssueLink:
    """Tests for format_issue_link method."""

    def test_format_issue_link(self):
        """Test formatting issue link."""
        integration = GitHubIntegration()

        link = integration.format_issue_link("contextanchor", "cli", 123)

        assert link == "https://github.com/contextanchor/cli/issues/123"

    def test_format_issue_link_with_different_values(self):
        """Test formatting issue link with different values."""
        integration = GitHubIntegration()

        link = integration.format_issue_link("user", "repo", 789)

        assert link == "https://github.com/user/repo/issues/789"
