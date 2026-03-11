import os
from click.testing import CliRunner
from hypothesis import given, settings, strategies as st
from src.contextanchor.cli import init, _redact_secrets
from src.contextanchor.models import FileChange
from pathlib import Path


@settings(max_examples=50, deadline=None)
@given(has_git=st.booleans(), already_initialized=st.booleans(), hooks_writable=st.booleans())
def test_property_init_behavior(tmp_path_factory, has_git, already_initialized, hooks_writable):
    """
    Feature: context-anchor
    Property 20: Initialization Creates Configuration
    Property 21: Git Availability Check
    Property 67: Re-Initialization Detection
    Validates: Requirements 7.2, 7.4, 7.3
    """
    tmp_path = tmp_path_factory.mktemp(f"test_{has_git}_{already_initialized}_{hooks_writable}")
    runner = CliRunner()
    test_dir = Path(tmp_path)
    current_cwd = os.getcwd()

    try:
        os.chdir(test_dir)

        if has_git:
            git_dir = test_dir / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            if hooks_writable:
                hooks_dir.mkdir()
            else:
                hooks_dir.touch()

        if already_initialized:
            config_dir = test_dir / ".contextanchor"
            config_dir.mkdir()
            (config_dir / "config.yaml").touch()

        result = runner.invoke(init)

        if not has_git:
            assert result.exit_code != 0
            assert "Not inside a git repository" in result.output
            return

        if already_initialized:
            assert result.exit_code != 0
            assert "already initialized" in result.output
            return

        assert result.exit_code == 0
        assert (test_dir / ".contextanchor" / "config.yaml").exists()

        if hooks_writable:
            assert "ContextAnchor initialized successfully" in result.output
        else:
            assert "initialized with degraded hook support" in result.output
    finally:
        os.chdir(current_cwd)


@given(text=st.text(min_size=1, max_size=500))
@settings(max_examples=50)
def test_property_secret_redaction(text):
    """
    Property 34: Secret Redaction
    Validates: Requirements 9.6
    """
    patterns = [r"sk-[a-zA-Z0-9]{20}"]
    text_with_secret = text + " sk-abcdef1234567890ABCD"
    redacted = _redact_secrets(text_with_secret, patterns)
    assert "sk-abcdef1234567890ABCD" not in redacted
    assert "[REDACTED]" in redacted


@given(file_contents=st.text(min_size=1, max_size=1000))
@settings(max_examples=50)
def test_property_no_source_transmission(file_contents):
    """
    Property 33: No Source Code Transmission
    Validates: Requirements 9.5
    """
    fc = FileChange(path="test.py", status="modified", lines_added=10, lines_deleted=5)

    assert not hasattr(fc, "contents")
    assert not hasattr(fc, "source_code")
