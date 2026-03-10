"""
Property-based tests for Git signal capture completeness.

Tests universal properties that must hold for all git activity monitoring operations.
Uses Hypothesis for comprehensive input coverage.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st, settings, assume
import git

from src.contextanchor.git_observer import GitObserver


# Hypothesis strategies for generating valid test data

@st.composite
def valid_commit_data(draw):
    """Generate valid commit data for testing."""
    message = draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00'
    )))
    # Ensure message is not just whitespace (git strips whitespace)
    assume(message.strip() != "")
    num_files = draw(st.integers(min_value=1, max_value=5))
    files = [f"file_{i}.txt" for i in range(num_files)]
    return message, files


@st.composite
def valid_branch_names(draw):
    """Generate valid git branch names."""
    # Git branch names can contain letters, digits, -, _, /
    # but cannot start with -, end with ., or contain ..
    name = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/"
    ))
    # Clean up invalid patterns
    name = name.strip("/").strip("-")
    name = name.replace("..", ".")
    assume(len(name) > 0)
    assume(not name.startswith("-"))
    assume(not name.endswith("."))
    return name


@st.composite
def valid_file_modifications(draw):
    """Generate valid file modification data."""
    num_files = draw(st.integers(min_value=1, max_value=5))
    files = []
    for i in range(num_files):
        filename = f"test_file_{i}.txt"
        content = draw(st.text(min_size=10, max_size=200))
        files.append((filename, content))
    return files


# Helper functions for test repository setup

def create_test_repo(temp_dir: str) -> git.Repo:
    """Create a test git repository with initial commit."""
    repo = git.Repo.init(temp_dir)
    
    # Configure git user for commits
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    
    # Create initial commit
    initial_file = os.path.join(temp_dir, "README.md")
    with open(initial_file, "w") as f:
        f.write("# Test Repository\n")
    
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    return repo


def create_commit_in_repo(repo: git.Repo, message: str, files: List[str]) -> str:
    """Create a commit with specified files in the repository."""
    repo_dir = repo.working_dir
    
    # Create/modify files
    for filename in files:
        filepath = os.path.join(repo_dir, filename)
        with open(filepath, "w") as f:
            f.write(f"Content for {filename}\n")
    
    # Stage and commit
    repo.index.add(files)
    commit = repo.index.commit(message)
    
    return commit.hexsha


def create_branch_and_switch(repo: git.Repo, branch_name: str) -> tuple:
    """Create a new branch and switch to it, returning (from_branch, to_branch)."""
    from_branch = repo.active_branch.name
    
    # Create and checkout new branch
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    
    return from_branch, branch_name


def create_uncommitted_changes(repo: git.Repo, files: List[tuple]) -> None:
    """Create uncommitted changes in the repository."""
    repo_dir = repo.working_dir
    
    for filename, content in files:
        filepath = os.path.join(repo_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)


# Property-based tests

@settings(max_examples=100, deadline=5000)
@given(commit_data=valid_commit_data())
def test_property_1_complete_commit_signal_capture(commit_data):
    """
    Feature: context-anchor, Property 1: Complete Commit Signal Capture
    
    **Validates: Requirements 1.1, 1.5, 1.6**
    
    For any commit created in a monitored repository, the captured signal must contain:
    - commit hash
    - message
    - timestamp
    - changed files
    - repository identifier
    - capture source
    """
    message, files = commit_data
    
    # Create temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup test repository
        repo = create_test_repo(temp_dir)
        
        # Create a commit with the generated data
        commit_hash = create_commit_in_repo(repo, message, files)
        
        # Initialize GitObserver
        observer = GitObserver(temp_dir)
        
        # Capture commit signal
        commit_signal = observer.capture_commit_signal()
        
        # Verify signal is not None
        assert commit_signal is not None, "Commit signal must be captured"
        
        # Verify commit hash is present and matches
        assert hasattr(commit_signal, 'hash'), "Commit signal must contain hash"
        assert commit_signal.hash == commit_hash, \
            f"Commit hash must match: expected {commit_hash}, got {commit_signal.hash}"
        
        # Verify message is present and matches (git strips whitespace)
        assert hasattr(commit_signal, 'message'), "Commit signal must contain message"
        assert commit_signal.message == message.strip(), \
            f"Commit message must match: expected '{message.strip()}', got '{commit_signal.message}'"
        
        # Verify timestamp is present and valid
        assert hasattr(commit_signal, 'timestamp'), "Commit signal must contain timestamp"
        assert isinstance(commit_signal.timestamp, datetime), \
            "Commit timestamp must be a datetime object"
        
        # Verify changed files are present
        assert hasattr(commit_signal, 'files_changed'), \
            "Commit signal must contain files_changed"
        assert isinstance(commit_signal.files_changed, list), \
            "files_changed must be a list"
        
        # Verify all committed files are in the signal
        for filename in files:
            assert filename in commit_signal.files_changed, \
                f"File '{filename}' must be in files_changed list"
        
        # Verify repository identifier can be generated
        repository_id = observer.generate_repository_id()
        assert repository_id is not None, "Repository identifier must be generated"
        assert isinstance(repository_id, str), "Repository identifier must be a string"
        assert len(repository_id) == 64, \
            "Repository identifier must be 64 characters (SHA-256 hash)"
        
        # Note: capture_source is not part of CommitInfo model but would be added
        # when CommitInfo is wrapped in CaptureSignals. This validates the commit
        # signal contains all required data that will be used in CaptureSignals.


@settings(max_examples=100, deadline=5000)
@given(branch_name=valid_branch_names())
def test_property_2_complete_branch_switch_signal_capture(branch_name):
    """
    Feature: context-anchor, Property 2: Complete Branch Switch Signal Capture
    
    **Validates: Requirements 1.2, 1.5, 1.6**
    
    For any branch switch in a monitored repository, the captured signal must contain:
    - source branch
    - target branch
    - timestamp
    - repository identifier
    - capture source
    """
    # Create temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup test repository
        repo = create_test_repo(temp_dir)
        
        # Get initial branch name
        from_branch = repo.active_branch.name
        
        # Create and switch to new branch
        try:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
        except Exception:
            # If branch name is invalid for git, skip this example
            assume(False)
        
        # Initialize GitObserver
        observer = GitObserver(temp_dir)
        
        # Capture branch switch signal
        branch_signal = observer.capture_branch_switch(from_branch, branch_name)
        
        # Verify signal is not None
        assert branch_signal is not None, "Branch switch signal must be captured"
        
        # Verify source branch is present and matches
        assert 'from_branch' in branch_signal, \
            "Branch switch signal must contain from_branch"
        assert branch_signal['from_branch'] == from_branch, \
            f"Source branch must match: expected '{from_branch}', got '{branch_signal['from_branch']}'"
        
        # Verify target branch is present and matches
        assert 'to_branch' in branch_signal, \
            "Branch switch signal must contain to_branch"
        assert branch_signal['to_branch'] == branch_name, \
            f"Target branch must match: expected '{branch_name}', got '{branch_signal['to_branch']}'"
        
        # Verify timestamp is present and valid
        assert 'timestamp' in branch_signal, \
            "Branch switch signal must contain timestamp"
        assert isinstance(branch_signal['timestamp'], datetime), \
            "Branch switch timestamp must be a datetime object"
        
        # Verify repository identifier is present
        assert 'repository_id' in branch_signal, \
            "Branch switch signal must contain repository_id"
        assert isinstance(branch_signal['repository_id'], str), \
            "Repository identifier must be a string"
        assert len(branch_signal['repository_id']) == 64, \
            "Repository identifier must be 64 characters (SHA-256 hash)"
        
        # Note: capture_source would be added when this signal is wrapped in
        # CaptureSignals. This validates the branch switch signal contains all
        # required data that will be used in CaptureSignals.


@settings(max_examples=100, deadline=5000)
@given(file_modifications=valid_file_modifications())
def test_property_3_complete_diff_signal_capture(file_modifications):
    """
    Feature: context-anchor, Property 3: Complete Diff Signal Capture
    
    **Validates: Requirements 1.3, 1.5, 1.6**
    
    For any diff generated in a monitored repository, the captured signal must contain:
    - file paths
    - change summary
    - repository identifier
    - capture source
    """
    # Create temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup test repository
        repo = create_test_repo(temp_dir)
        
        # Create uncommitted changes
        create_uncommitted_changes(repo, file_modifications)
        
        # Initialize GitObserver
        observer = GitObserver(temp_dir)
        
        # Capture diff signal
        diff_signal = observer.capture_diff_signal(source="test")
        
        # Verify signal is not None
        assert diff_signal is not None, "Diff signal must be captured"
        
        # Verify file paths are present
        assert 'file_paths' in diff_signal, \
            "Diff signal must contain file_paths"
        assert isinstance(diff_signal['file_paths'], list), \
            "file_paths must be a list"
        
        # Verify all modified files are in the signal
        expected_files = [filename for filename, _ in file_modifications]
        for filename in expected_files:
            assert filename in diff_signal['file_paths'], \
                f"File '{filename}' must be in file_paths list"
        
        # Verify change summary is present
        assert 'files_changed' in diff_signal, \
            "Diff signal must contain files_changed count"
        assert isinstance(diff_signal['files_changed'], int), \
            "files_changed must be an integer"
        assert diff_signal['files_changed'] == len(expected_files), \
            f"files_changed count must match: expected {len(expected_files)}, got {diff_signal['files_changed']}"
        
        assert 'lines_added' in diff_signal, \
            "Diff signal must contain lines_added"
        assert isinstance(diff_signal['lines_added'], int), \
            "lines_added must be an integer"
        
        assert 'lines_deleted' in diff_signal, \
            "Diff signal must contain lines_deleted"
        assert isinstance(diff_signal['lines_deleted'], int), \
            "lines_deleted must be an integer"
        
        # Verify repository identifier is present
        assert 'repository_id' in diff_signal, \
            "Diff signal must contain repository_id"
        assert isinstance(diff_signal['repository_id'], str), \
            "Repository identifier must be a string"
        assert len(diff_signal['repository_id']) == 64, \
            "Repository identifier must be 64 characters (SHA-256 hash)"
        
        # Verify capture source is present and matches
        assert 'capture_source' in diff_signal, \
            "Diff signal must contain capture_source"
        assert diff_signal['capture_source'] == "test", \
            f"Capture source must match: expected 'test', got '{diff_signal['capture_source']}'"


# Hypothesis strategies for commit messages with references

@st.composite
def commit_message_with_pr_references(draw):
    """Generate commit messages with PR references."""
    # Choose number of PR references (0-5)
    num_prs = draw(st.integers(min_value=1, max_value=5))

    # Generate PR numbers
    pr_numbers = [draw(st.integers(min_value=1, max_value=99999)) for _ in range(num_prs)]

    # Choose PR reference patterns
    patterns = ['#{}', 'PR #{}', 'pull request #{}']

    # Build commit message with PR references
    message_parts = [draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
    )))]

    for pr_num in pr_numbers:
        pattern = draw(st.sampled_from(patterns))
        message_parts.append(pattern.format(pr_num))
        # Add some text between references
        if draw(st.booleans()):
            message_parts.append(draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
                blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
            ))))

    message = ' '.join(message_parts)
    assume(message.strip() != "")

    return message, pr_numbers


@st.composite
def commit_message_with_issue_references(draw):
    """Generate commit messages with issue references using keywords."""
    # Choose number of issue references (1-5)
    num_issues = draw(st.integers(min_value=1, max_value=5))

    # Generate issue numbers
    issue_numbers = [draw(st.integers(min_value=1, max_value=99999)) for _ in range(num_issues)]

    # Keywords that indicate issue references
    keywords = ['fixes', 'closes', 'resolves', 'refs', 'fix', 'close', 'resolve', 'ref']

    # Build commit message with issue references
    message_parts = [draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
    )))]

    for issue_num in issue_numbers:
        keyword = draw(st.sampled_from(keywords))
        message_parts.append(f"{keyword} #{issue_num}")
        # Add some text between references
        if draw(st.booleans()):
            message_parts.append(draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
                blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
            ))))

    message = ' '.join(message_parts)
    assume(message.strip() != "")

    return message, issue_numbers


@st.composite
def commit_message_with_mixed_references(draw):
    """Generate commit messages with both PR and issue references."""
    # Generate PR references
    num_prs = draw(st.integers(min_value=0, max_value=3))
    pr_numbers = [draw(st.integers(min_value=1, max_value=99999)) for _ in range(num_prs)]

    # Generate issue references
    num_issues = draw(st.integers(min_value=0, max_value=3))
    issue_numbers = [draw(st.integers(min_value=1, max_value=99999)) for _ in range(num_issues)]

    # Ensure at least one reference exists
    assume(num_prs > 0 or num_issues > 0)

    # Build commit message
    message_parts = [draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
    )))]

    # Add PR references
    pr_patterns = ['#{}', 'PR #{}', 'pull request #{}']
    for pr_num in pr_numbers:
        pattern = draw(st.sampled_from(pr_patterns))
        message_parts.append(pattern.format(pr_num))
        if draw(st.booleans()):
            message_parts.append(draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
                blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
            ))))

    # Add issue references
    issue_keywords = ['fixes', 'closes', 'resolves', 'refs', 'fix', 'close', 'resolve', 'ref']
    for issue_num in issue_numbers:
        keyword = draw(st.sampled_from(issue_keywords))
        message_parts.append(f"{keyword} #{issue_num}")
        if draw(st.booleans()):
            message_parts.append(draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
                blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
            ))))

    message = ' '.join(message_parts)
    assume(message.strip() != "")

    return message, pr_numbers, issue_numbers


# Property 4: Reference Extraction from Commit Messages

@settings(max_examples=100, deadline=5000)
@given(message_data=commit_message_with_pr_references())
def test_property_4_pr_reference_extraction(message_data):
    """
    Feature: context-anchor, Property 4: Reference Extraction from Commit Messages (PR)

    **Validates: Requirements 1.4, 10.2, 10.3, 10.6**

    For any commit message containing PR references (with patterns: #, PR #, pull request #),
    the GitHubIntegration component must correctly extract and store all reference numbers.
    """
    from src.contextanchor.github_integration import GitHubIntegration

    message, expected_pr_numbers = message_data

    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()

    # Extract PR references
    extracted_prs = github_integration.parse_pr_references(message)

    # Verify all expected PR numbers were extracted
    assert extracted_prs is not None, "PR references must be extracted"
    assert isinstance(extracted_prs, list), "Extracted PRs must be a list"

    # Convert to sets for comparison (order doesn't matter, duplicates removed)
    expected_set = set(expected_pr_numbers)
    extracted_set = set(extracted_prs)

    assert extracted_set == expected_set, \
        f"All PR numbers must be extracted. Expected {expected_set}, got {extracted_set}. Message: '{message}'"


@settings(max_examples=100, deadline=5000)
@given(message_data=commit_message_with_issue_references())
def test_property_4_issue_reference_extraction(message_data):
    """
    Feature: context-anchor, Property 4: Reference Extraction from Commit Messages (Issues)

    **Validates: Requirements 1.4, 10.2, 10.3, 10.6**

    For any commit message containing issue references with keywords (fixes, closes, resolves, refs),
    the GitHubIntegration component must correctly extract and store all reference numbers.
    """
    from src.contextanchor.github_integration import GitHubIntegration

    message, expected_issue_numbers = message_data

    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()

    # Extract issue references
    extracted_issues = github_integration.parse_issue_references(message)

    # Verify all expected issue numbers were extracted
    assert extracted_issues is not None, "Issue references must be extracted"
    assert isinstance(extracted_issues, list), "Extracted issues must be a list"

    # Convert to sets for comparison (order doesn't matter, duplicates removed)
    expected_set = set(expected_issue_numbers)
    extracted_set = set(extracted_issues)

    assert extracted_set == expected_set, \
        f"All issue numbers must be extracted. Expected {expected_set}, got {extracted_set}. Message: '{message}'"


@settings(max_examples=100, deadline=5000)
@given(message_data=commit_message_with_mixed_references())
def test_property_4_mixed_reference_extraction(message_data):
    """
    Feature: context-anchor, Property 4: Reference Extraction from Commit Messages (Mixed)

    **Validates: Requirements 1.4, 10.2, 10.3, 10.6**

    For any commit message containing both PR and issue references, the GitHubIntegration
    component must correctly extract and store all reference numbers separately.
    
    Note: Issue references with keywords (e.g., "fixes #123") will also be picked up as
    PR references because they contain the #number pattern. This is expected behavior.
    """
    from src.contextanchor.github_integration import GitHubIntegration

    message, expected_pr_numbers, expected_issue_numbers = message_data

    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()

    # Extract PR references
    extracted_prs = github_integration.parse_pr_references(message)

    # Extract issue references
    extracted_issues = github_integration.parse_issue_references(message)

    # Verify PR extraction
    assert extracted_prs is not None, "PR references must be extracted"
    assert isinstance(extracted_prs, list), "Extracted PRs must be a list"

    # PR references should include explicit PR numbers AND issue numbers (since "fixes #123" contains #123)
    expected_pr_set = set(expected_pr_numbers) | set(expected_issue_numbers)
    extracted_pr_set = set(extracted_prs)

    assert extracted_pr_set == expected_pr_set, \
        f"All PR numbers must be extracted. Expected {expected_pr_set}, got {extracted_pr_set}. Message: '{message}'"

    # Verify issue extraction (only those with keywords)
    assert extracted_issues is not None, "Issue references must be extracted"
    assert isinstance(extracted_issues, list), "Extracted issues must be a list"

    expected_issue_set = set(expected_issue_numbers)
    extracted_issue_set = set(extracted_issues)

    assert extracted_issue_set == expected_issue_set, \
        f"All issue numbers must be extracted. Expected {expected_issue_set}, got {extracted_issue_set}. Message: '{message}'"


@settings(max_examples=100, deadline=5000)
@given(
    message=st.text(min_size=10, max_size=200, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00#'
    ))
)
def test_property_4_no_false_positives(message):
    """
    Feature: context-anchor, Property 4: Reference Extraction from Commit Messages (No False Positives)

    **Validates: Requirements 1.4, 10.2, 10.3, 10.6**

    For any commit message without PR or issue reference patterns, the GitHubIntegration
    component must not extract any references (no false positives).
    """
    from src.contextanchor.github_integration import GitHubIntegration

    # Ensure message doesn't contain reference patterns
    assume('#' not in message)
    assume('PR' not in message.upper())
    assume('FIXES' not in message.upper())
    assume('CLOSES' not in message.upper())
    assume('RESOLVES' not in message.upper())
    assume('REFS' not in message.upper())

    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()

    # Extract references
    extracted_prs = github_integration.parse_pr_references(message)
    extracted_issues = github_integration.parse_issue_references(message)

    # Verify no false positives
    assert extracted_prs == [], \
        f"No PR references should be extracted from message without patterns. Got {extracted_prs}. Message: '{message}'"

    assert extracted_issues == [], \
        f"No issue references should be extracted from message without patterns. Got {extracted_issues}. Message: '{message}'"



# Hypothesis strategies for GitHub remote URLs

@st.composite
def valid_github_owner_repo(draw):
    """Generate valid GitHub owner and repo names."""
    # GitHub usernames/org names: alphanumeric and hyphens, cannot start/end with hyphen
    # Repo names: alphanumeric, hyphens, underscores, dots
    owner_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
    repo_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    
    # Generate owner (1-39 chars, cannot start/end with hyphen)
    owner = draw(st.text(min_size=1, max_size=39, alphabet=owner_chars))
    owner = owner.strip('-')
    assume(len(owner) > 0)
    assume(not owner.startswith('-'))
    assume(not owner.endswith('-'))
    
    # Generate repo name (1-100 chars)
    repo = draw(st.text(min_size=1, max_size=100, alphabet=repo_chars))
    repo = repo.strip('-._')
    assume(len(repo) > 0)
    
    return owner, repo


@st.composite
def github_remote_url(draw):
    """Generate valid GitHub remote URLs in various formats."""
    owner, repo = draw(valid_github_owner_repo())
    
    # Choose URL format: HTTPS, SSH, or git://
    format_choice = draw(st.sampled_from(['https', 'ssh', 'git']))
    
    # Optionally add .git extension
    add_git_ext = draw(st.booleans())
    git_ext = ".git" if add_git_ext else ""
    
    # Optionally add trailing slash (should be handled)
    add_trailing_slash = draw(st.booleans())
    trailing_slash = "/" if add_trailing_slash and not add_git_ext else ""
    
    if format_choice == 'https':
        url = f"https://github.com/{owner}/{repo}{git_ext}{trailing_slash}"
    elif format_choice == 'ssh':
        url = f"git@github.com:{owner}/{repo}{git_ext}"
    else:  # git://
        url = f"git://github.com/{owner}/{repo}{git_ext}"
    
    return url, owner, repo


# Property 35: GitHub Remote Parsing

@settings(max_examples=100, deadline=5000)
@given(url_data=github_remote_url())
def test_property_35_github_remote_parsing(url_data):
    """
    Feature: context-anchor, Property 35: GitHub Remote Parsing
    
    **Validates: Requirements 10.1**
    
    For any valid GitHub remote URL (HTTPS, SSH, or git:// protocol), the GitHubIntegration
    component must correctly extract the repository owner and name.
    """
    from src.contextanchor.github_integration import GitHubIntegration
    
    url, expected_owner, expected_repo = url_data
    
    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()
    
    # Parse the remote URL
    result = github_integration.parse_remote_url(url)
    
    # Verify result is not None
    assert result is not None, \
        f"GitHub remote URL must be parsed successfully. URL: '{url}'"
    
    # Verify owner is extracted correctly
    assert hasattr(result, 'owner'), \
        "Parsed result must contain 'owner' attribute"
    assert result.owner == expected_owner, \
        f"Owner must match. Expected '{expected_owner}', got '{result.owner}'. URL: '{url}'"
    
    # Verify repo name is extracted correctly
    assert hasattr(result, 'name'), \
        "Parsed result must contain 'name' attribute"
    assert result.name == expected_repo, \
        f"Repo name must match. Expected '{expected_repo}', got '{result.name}'. URL: '{url}'"
    
    # Verify remote_url is preserved
    assert hasattr(result, 'remote_url'), \
        "Parsed result must contain 'remote_url' attribute"
    assert result.remote_url == url, \
        f"Remote URL must be preserved. Expected '{url}', got '{result.remote_url}'"


@settings(max_examples=100, deadline=5000)
@given(
    url=st.text(min_size=1, max_size=200, alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters='\x00'
    ))
)
def test_property_35_non_github_urls_return_none(url):
    """
    Feature: context-anchor, Property 35: GitHub Remote Parsing (Negative Case)
    
    **Validates: Requirements 10.1**
    
    For any URL that is not a valid GitHub remote URL, the GitHubIntegration
    component must return None (no false positives).
    """
    from src.contextanchor.github_integration import GitHubIntegration
    
    # Ensure URL doesn't contain github.com
    assume('github.com' not in url.lower())
    
    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()
    
    # Parse the remote URL
    result = github_integration.parse_remote_url(url)
    
    # Verify result is None for non-GitHub URLs
    assert result is None, \
        f"Non-GitHub URL must return None. URL: '{url}', got: {result}"


@settings(max_examples=50, deadline=5000)
@given(owner_repo=valid_github_owner_repo())
def test_property_35_all_url_formats_equivalent(owner_repo):
    """
    Feature: context-anchor, Property 35: GitHub Remote Parsing (Format Equivalence)
    
    **Validates: Requirements 10.1**
    
    For any GitHub owner/repo pair, all valid URL formats (HTTPS, SSH, git://)
    must parse to the same owner and repo name.
    """
    from src.contextanchor.github_integration import GitHubIntegration
    
    owner, repo = owner_repo
    
    # Initialize GitHubIntegration
    github_integration = GitHubIntegration()
    
    # Test all URL formats
    urls = [
        f"https://github.com/{owner}/{repo}",
        f"https://github.com/{owner}/{repo}.git",
        f"git@github.com:{owner}/{repo}",
        f"git@github.com:{owner}/{repo}.git",
        f"git://github.com/{owner}/{repo}",
        f"git://github.com/{owner}/{repo}.git",
    ]
    
    results = []
    for url in urls:
        result = github_integration.parse_remote_url(url)
        assert result is not None, \
            f"URL format must be parsed successfully: '{url}'"
        results.append(result)
    
    # Verify all formats produce the same owner and repo
    for i, result in enumerate(results):
        assert result.owner == owner, \
            f"All formats must extract same owner. URL: '{urls[i]}', expected '{owner}', got '{result.owner}'"
        assert result.name == repo, \
            f"All formats must extract same repo. URL: '{urls[i]}', expected '{repo}', got '{result.name}'"
