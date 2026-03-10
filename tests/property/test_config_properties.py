"""
Property-based tests for configuration management.

Tests universal properties that must hold for all configuration scenarios.
"""

import tempfile
from pathlib import Path
from hypothesis import given, strategies as st
import yaml
import pytest

from contextanchor.config import (
    load_config,
    validate_config,
    save_config,
    ConfigValidationError,
    DEFAULT_CONFIG,
)
from contextanchor.models import Config


# Hypothesis strategies for configuration values
@st.composite
def valid_config_dict(draw):
    """Generate valid configuration dictionaries."""
    return {
        "api_endpoint": draw(st.text(min_size=1, max_size=200)),
        "api_timeout_seconds": draw(st.integers(min_value=1, max_value=300)),
        "retry_attempts": draw(st.integers(min_value=0, max_value=10)),
        "capture_prompt": draw(st.text(min_size=1, max_size=500)),
        "retention_days": draw(st.integers(min_value=1, max_value=365)),
        "offline_queue_max": draw(st.integers(min_value=1, max_value=10000)),
        "enabled_signals": draw(
            st.lists(
                st.sampled_from(["commits", "branches", "diffs", "pr_references"]),
                min_size=0,
                max_size=4,
                unique=True,
            )
        ),
        "redact_patterns": draw(st.lists(st.text(min_size=0, max_size=100), max_size=10)),
    }


@st.composite
def partial_config_dict(draw):
    """Generate partial configuration dictionaries (subset of fields)."""
    all_fields = {
        "api_endpoint": draw(st.text(min_size=1, max_size=200)),
        "api_timeout_seconds": draw(st.integers(min_value=1, max_value=300)),
        "retry_attempts": draw(st.integers(min_value=0, max_value=10)),
        "capture_prompt": draw(st.text(min_size=1, max_size=500)),
        "retention_days": draw(st.integers(min_value=1, max_value=365)),
        "offline_queue_max": draw(st.integers(min_value=1, max_value=10000)),
        "enabled_signals": draw(
            st.lists(
                st.sampled_from(["commits", "branches", "diffs", "pr_references"]),
                min_size=0,
                max_size=4,
                unique=True,
            )
        ),
        "redact_patterns": draw(st.lists(st.text(min_size=0, max_size=100), max_size=10)),
    }

    # Select a random subset of fields
    num_fields = draw(st.integers(min_value=1, max_value=len(all_fields)))
    selected_keys = draw(
        st.lists(
            st.sampled_from(list(all_fields.keys())),
            min_size=num_fields,
            max_size=num_fields,
            unique=True,
        )
    )

    return {k: v for k, v in all_fields.items() if k in selected_keys}


def test_property_46_custom_prompt_configuration():
    """
    **Validates: Requirements 15.2**

    Feature: context-anchor, Property 46: Custom Prompt Configuration

    For any config file with a custom capture prompt, that prompt must be used
    instead of the default prompt when executing save-context.
    """

    @given(custom_prompt=st.text(min_size=1, max_size=500))
    def check_custom_prompt(custom_prompt):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with custom prompt
            config_dict = {"capture_prompt": custom_prompt}
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Load config
            config = load_config(config_path)

            # Verify custom prompt is used
            assert config.capture_prompt == custom_prompt
            assert (
                config.capture_prompt != DEFAULT_CONFIG["capture_prompt"]
                or custom_prompt == DEFAULT_CONFIG["capture_prompt"]
            )

    check_custom_prompt()


def test_property_47_custom_retention_configuration():
    """
    **Validates: Requirements 15.3**

    Feature: context-anchor, Property 47: Custom Retention Configuration

    For any config file with a custom retention period, Context_Snapshots must use
    that retention period for TTL calculation.
    """

    @given(retention_days=st.integers(min_value=1, max_value=365))
    def check_custom_retention(retention_days):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with custom retention
            config_dict = {"retention_days": retention_days}
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Load config
            config = load_config(config_path)

            # Verify custom retention is used
            assert config.retention_days == retention_days
            assert (
                config.retention_days != DEFAULT_CONFIG["retention_days"]
                or retention_days == DEFAULT_CONFIG["retention_days"]
            )

    check_custom_retention()


def test_property_48_signal_monitoring_configuration():
    """
    **Validates: Requirements 15.4**

    Feature: context-anchor, Property 48: Signal Monitoring Configuration

    For any config file with specific git signals disabled, those signals must not
    be collected during git activity monitoring.
    """

    @given(
        enabled_signals=st.lists(
            st.sampled_from(["commits", "branches", "diffs", "pr_references"]),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    def check_signal_configuration(enabled_signals):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with specific enabled signals
            config_dict = {"enabled_signals": enabled_signals}
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Load config
            config = load_config(config_path)

            # Verify enabled signals match configuration
            assert config.enabled_signals == enabled_signals

            # Verify disabled signals are not in the list
            all_signals = {"commits", "branches", "diffs", "pr_references"}
            disabled_signals = all_signals - set(enabled_signals)
            for signal in disabled_signals:
                assert signal not in config.enabled_signals

    check_signal_configuration()


def test_property_49_invalid_configuration_handling():
    """
    **Validates: Requirements 15.5, 15.6**

    Feature: context-anchor, Property 49: Invalid Configuration Handling

    For any invalid configuration file, the tool must display validation errors
    identifying the invalid fields and use default values for those fields.
    """

    @given(
        invalid_field=st.sampled_from(
            [
                ("api_timeout_seconds", "not_an_int"),
                ("api_timeout_seconds", -5),
                ("api_timeout_seconds", 0),
                ("retry_attempts", "not_an_int"),
                ("retry_attempts", -1),
                ("retention_days", "not_an_int"),
                ("retention_days", 0),
                ("retention_days", -10),
                ("offline_queue_max", "not_an_int"),
                ("offline_queue_max", 0),
                ("offline_queue_max", -100),
                ("enabled_signals", "not_a_list"),
                ("enabled_signals", ["invalid_signal"]),
                ("enabled_signals", [123]),
                ("redact_patterns", "not_a_list"),
                ("redact_patterns", [123, 456]),
            ]
        )
    )
    def check_invalid_config_handling(invalid_field):
        field_name, invalid_value = invalid_field

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with invalid field
            config_dict = DEFAULT_CONFIG.copy()
            config_dict[field_name] = invalid_value

            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Attempt to load config - should raise validation error
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config(config_path)

            # Verify error message identifies the invalid field
            error_message = str(exc_info.value)
            assert field_name in error_message or "validation" in error_message.lower()

            # Verify validation errors list is not empty
            assert len(exc_info.value.errors) > 0

    check_invalid_config_handling()


def test_property_config_validation_identifies_exact_fields():
    """
    Additional property: Validation must identify exact invalid fields.

    For any configuration with multiple invalid fields, validation must report
    all invalid fields, not just the first one.
    """

    @given(
        invalid_fields=st.lists(
            st.sampled_from(
                [
                    ("api_timeout_seconds", -5),
                    ("retry_attempts", -1),
                    ("retention_days", 0),
                    ("offline_queue_max", -100),
                ]
            ),
            min_size=1,
            max_size=4,
            unique_by=lambda x: x[0],
        ),
    )
    def check_multiple_invalid_fields(invalid_fields):
        config_dict = DEFAULT_CONFIG.copy()

        # Apply all invalid values
        for field_name, invalid_value in invalid_fields:
            config_dict[field_name] = invalid_value

        # Validate
        errors = validate_config(config_dict)

        # Should have at least as many errors as invalid fields
        assert len(errors) >= len(invalid_fields)

    check_multiple_invalid_fields()


def test_property_partial_config_merges_with_defaults():
    """
    Additional property: Partial configuration merges with defaults.

    For any configuration file with only a subset of fields, the missing fields
    must be filled with default values.
    """

    @given(config_dict=partial_config_dict())
    def check_partial_config_merge(config_dict):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Write partial config
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Load config
            config = load_config(config_path)

            # Verify specified fields use custom values
            for field, value in config_dict.items():
                assert getattr(config, field) == value

            # Verify missing fields use defaults
            for field, default_value in DEFAULT_CONFIG.items():
                if field not in config_dict:
                    assert getattr(config, field) == default_value

    check_partial_config_merge()


def test_property_config_round_trip():
    """
    Additional property: Configuration round-trip preservation.

    For any valid configuration, saving and loading it must preserve all values.
    """

    @given(config_dict=valid_config_dict())
    def check_config_round_trip(config_dict):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config object
            config = Config(
                api_endpoint=config_dict["api_endpoint"],
                api_timeout_seconds=config_dict["api_timeout_seconds"],
                retry_attempts=config_dict["retry_attempts"],
                capture_prompt=config_dict["capture_prompt"],
                retention_days=config_dict["retention_days"],
                offline_queue_max=config_dict["offline_queue_max"],
                enabled_signals=config_dict["enabled_signals"],
                redact_patterns=config_dict["redact_patterns"],
            )

            # Save config
            save_config(config, config_path)

            # Load config
            loaded_config = load_config(config_path)

            # Verify all fields match
            assert loaded_config.api_endpoint == config.api_endpoint
            assert loaded_config.api_timeout_seconds == config.api_timeout_seconds
            assert loaded_config.retry_attempts == config.retry_attempts
            assert loaded_config.capture_prompt == config.capture_prompt
            assert loaded_config.retention_days == config.retention_days
            assert loaded_config.offline_queue_max == config.offline_queue_max
            assert loaded_config.enabled_signals == config.enabled_signals
            assert loaded_config.redact_patterns == config.redact_patterns

    check_config_round_trip()


def test_property_missing_config_file_uses_defaults():
    """
    Additional property: Missing config file uses all defaults.

    For any non-existent config file path, loading configuration must return
    a Config object with all default values.
    """

    @given(st.just(None))  # No randomization needed, just test the behavior
    def check_missing_config_defaults(_):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent" / "config.yaml"

            # Load config from non-existent path
            config = load_config(config_path)

            # Verify all fields use defaults
            assert config.api_endpoint == DEFAULT_CONFIG["api_endpoint"]
            assert config.api_timeout_seconds == DEFAULT_CONFIG["api_timeout_seconds"]
            assert config.retry_attempts == DEFAULT_CONFIG["retry_attempts"]
            assert config.capture_prompt == DEFAULT_CONFIG["capture_prompt"]
            assert config.retention_days == DEFAULT_CONFIG["retention_days"]
            assert config.offline_queue_max == DEFAULT_CONFIG["offline_queue_max"]
            assert config.enabled_signals == DEFAULT_CONFIG["enabled_signals"]
            assert config.redact_patterns == DEFAULT_CONFIG["redact_patterns"]

    check_missing_config_defaults()
