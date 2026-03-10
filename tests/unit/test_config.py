"""
Unit tests for configuration management edge cases.

Tests specific scenarios and edge cases for configuration loading and validation.
"""

import tempfile
from pathlib import Path
import yaml
import pytest

from contextanchor.config import (
    load_config,
    validate_config,
    save_config,
    ConfigValidationError,
    DEFAULT_CONFIG,
    get_config_path,
)
from contextanchor.models import Config


def test_missing_config_file_uses_defaults():
    """
    Test that missing config file returns default configuration.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "nonexistent" / "config.yaml"

        # Load config from non-existent path
        config = load_config(config_path)

        # Verify all defaults are used
        assert config.api_endpoint == DEFAULT_CONFIG["api_endpoint"]
        assert config.api_timeout_seconds == DEFAULT_CONFIG["api_timeout_seconds"]
        assert config.retry_attempts == DEFAULT_CONFIG["retry_attempts"]
        assert config.capture_prompt == DEFAULT_CONFIG["capture_prompt"]
        assert config.retention_days == DEFAULT_CONFIG["retention_days"]
        assert config.offline_queue_max == DEFAULT_CONFIG["offline_queue_max"]
        assert config.enabled_signals == DEFAULT_CONFIG["enabled_signals"]
        assert config.redact_patterns == DEFAULT_CONFIG["redact_patterns"]


def test_invalid_yaml_syntax():
    """
    Test that invalid YAML syntax raises ConfigValidationError.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Write invalid YAML
        with open(config_path, "w") as f:
            f.write("invalid: yaml: syntax: [unclosed")

        # Should raise validation error
        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        assert "YAML" in str(exc_info.value) or "syntax" in str(exc_info.value).lower()


def test_invalid_field_types():
    """
    Test that invalid field types are caught by validation.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Test invalid type for api_timeout_seconds
        config_dict = DEFAULT_CONFIG.copy()
        config_dict["api_timeout_seconds"] = "not_an_integer"

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_path)

        assert "api_timeout_seconds" in str(exc_info.value)
        assert "type" in str(exc_info.value).lower()


def test_invalid_field_values():
    """
    Test that invalid field values are caught by validation.

    Requirements: 15.5, 15.6
    """
    # Test negative timeout
    errors = validate_config({**DEFAULT_CONFIG, "api_timeout_seconds": -5})
    assert any("api_timeout_seconds" in err for err in errors)

    # Test zero retention days
    errors = validate_config({**DEFAULT_CONFIG, "retention_days": 0})
    assert any("retention_days" in err for err in errors)

    # Test negative retry attempts
    errors = validate_config({**DEFAULT_CONFIG, "retry_attempts": -1})
    assert any("retry_attempts" in err for err in errors)

    # Test invalid signal name
    errors = validate_config({**DEFAULT_CONFIG, "enabled_signals": ["invalid_signal"]})
    assert any("signal" in err.lower() for err in errors)


def test_partial_configuration_merges_with_defaults():
    """
    Test that partial configuration merges with defaults.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Write partial config with only capture_prompt
        partial_config = {"capture_prompt": "Custom prompt here"}
        with open(config_path, "w") as f:
            yaml.dump(partial_config, f)

        # Load config
        config = load_config(config_path)

        # Custom field should be used
        assert config.capture_prompt == "Custom prompt here"

        # Other fields should use defaults
        assert config.api_endpoint == DEFAULT_CONFIG["api_endpoint"]
        assert config.api_timeout_seconds == DEFAULT_CONFIG["api_timeout_seconds"]
        assert config.retry_attempts == DEFAULT_CONFIG["retry_attempts"]
        assert config.retention_days == DEFAULT_CONFIG["retention_days"]
        assert config.offline_queue_max == DEFAULT_CONFIG["offline_queue_max"]
        assert config.enabled_signals == DEFAULT_CONFIG["enabled_signals"]
        assert config.redact_patterns == DEFAULT_CONFIG["redact_patterns"]


def test_empty_config_file():
    """
    Test that empty config file uses all defaults.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Write empty file
        with open(config_path, "w") as f:
            f.write("")

        # Load config
        config = load_config(config_path)

        # All fields should use defaults
        assert config.api_endpoint == DEFAULT_CONFIG["api_endpoint"]
        assert config.capture_prompt == DEFAULT_CONFIG["capture_prompt"]
        assert config.retention_days == DEFAULT_CONFIG["retention_days"]


def test_config_with_null_values():
    """
    Test that null values in config are handled properly.

    Requirements: 15.5, 15.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Write config with null value
        with open(config_path, "w") as f:
            f.write("api_endpoint: null\n")

        # Should raise validation error for invalid type
        with pytest.raises(ConfigValidationError):
            load_config(config_path)


def test_save_and_load_config():
    """
    Test that saving and loading config preserves values.

    Requirements: 15.1
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Create custom config
        original_config = Config(
            api_endpoint="https://custom.example.com",
            api_timeout_seconds=60,
            retry_attempts=5,
            capture_prompt="Custom prompt?",
            retention_days=180,
            offline_queue_max=500,
            enabled_signals=["commits", "branches"],
            redact_patterns=["secret.*", "token.*"],
        )

        # Save config
        save_config(original_config, config_path)

        # Load config
        loaded_config = load_config(config_path)

        # Verify all fields match
        assert loaded_config.api_endpoint == original_config.api_endpoint
        assert loaded_config.api_timeout_seconds == original_config.api_timeout_seconds
        assert loaded_config.retry_attempts == original_config.retry_attempts
        assert loaded_config.capture_prompt == original_config.capture_prompt
        assert loaded_config.retention_days == original_config.retention_days
        assert loaded_config.offline_queue_max == original_config.offline_queue_max
        assert loaded_config.enabled_signals == original_config.enabled_signals
        assert loaded_config.redact_patterns == original_config.redact_patterns


def test_get_config_path():
    """
    Test that get_config_path returns correct path.

    Requirements: 15.1
    """
    config_path = get_config_path()
    assert config_path == Path.home() / ".contextanchor" / "config.yaml"


def test_validation_reports_multiple_errors():
    """
    Test that validation reports all errors, not just the first one.

    Requirements: 15.6
    """
    invalid_config = {
        **DEFAULT_CONFIG,
        "api_timeout_seconds": -5,
        "retention_days": 0,
        "retry_attempts": -1,
        "enabled_signals": ["invalid_signal"],
    }

    errors = validate_config(invalid_config)

    # Should have multiple errors
    assert len(errors) >= 3

    # Should mention specific fields
    error_text = " ".join(errors)
    assert "api_timeout_seconds" in error_text
    assert "retention_days" in error_text


def test_enabled_signals_validation():
    """
    Test that enabled_signals validation works correctly.

    Requirements: 15.4
    """
    # Valid signals should pass
    valid_config = {**DEFAULT_CONFIG, "enabled_signals": ["commits", "branches", "diffs"]}
    errors = validate_config(valid_config)
    assert len(errors) == 0

    # Empty list should pass
    valid_config = {**DEFAULT_CONFIG, "enabled_signals": []}
    errors = validate_config(valid_config)
    assert len(errors) == 0

    # Invalid signal should fail
    invalid_config = {**DEFAULT_CONFIG, "enabled_signals": ["commits", "invalid"]}
    errors = validate_config(invalid_config)
    assert len(errors) > 0
    assert any("invalid" in err.lower() for err in errors)

    # Non-string items should fail
    invalid_config = {**DEFAULT_CONFIG, "enabled_signals": [123, 456]}
    errors = validate_config(invalid_config)
    assert len(errors) > 0


def test_redact_patterns_validation():
    """
    Test that redact_patterns validation works correctly.

    Requirements: 15.1
    """
    # Valid patterns should pass
    valid_config = {**DEFAULT_CONFIG, "redact_patterns": ["secret.*", "token.*"]}
    errors = validate_config(valid_config)
    assert len(errors) == 0

    # Empty list should pass
    valid_config = {**DEFAULT_CONFIG, "redact_patterns": []}
    errors = validate_config(valid_config)
    assert len(errors) == 0

    # Non-string items should fail
    invalid_config = {**DEFAULT_CONFIG, "redact_patterns": [123, 456]}
    errors = validate_config(invalid_config)
    assert len(errors) > 0
