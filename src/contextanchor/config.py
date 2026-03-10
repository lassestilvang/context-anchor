"""
Configuration management for ContextAnchor.

This module handles loading, validating, and managing configuration from YAML files.
Configuration can be loaded from ~/.contextanchor/config.yaml with validation and defaults.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml

from contextanchor.models import Config


# Default configuration values
DEFAULT_CONFIG = {
    "api_endpoint": "https://api.contextanchor.example.com",
    "api_timeout_seconds": 30,
    "retry_attempts": 3,
    "capture_prompt": "What were you trying to solve right now?",
    "retention_days": 90,
    "offline_queue_max": 200,
    "enabled_signals": ["commits", "branches", "diffs", "pr_references"],
    "redact_patterns": [],
}

# Configuration schema for validation
CONFIG_SCHEMA = {
    "api_endpoint": str,
    "api_timeout_seconds": int,
    "retry_attempts": int,
    "capture_prompt": str,
    "retention_days": int,
    "offline_queue_max": int,
    "enabled_signals": list,
    "redact_patterns": list,
}


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed: {'; '.join(errors)}")


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return Path.home() / ".contextanchor" / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file with validation and defaults.

    Args:
        config_path: Optional path to config file. Defaults to ~/.contextanchor/config.yaml

    Returns:
        Config object with validated settings

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    if config_path is None:
        config_path = get_config_path()

    # Start with default configuration
    config_dict = DEFAULT_CONFIG.copy()

    # If config file exists, load and merge with defaults
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}

            # Merge user config with defaults
            if isinstance(user_config, dict):
                config_dict.update(user_config)
        except yaml.YAMLError as e:
            raise ConfigValidationError([f"Invalid YAML syntax: {str(e)}"])
        except Exception as e:
            raise ConfigValidationError([f"Failed to read config file: {str(e)}"])

    # Validate configuration
    validation_errors = validate_config(config_dict)
    if validation_errors:
        raise ConfigValidationError(validation_errors)

    # Create Config object (types are guaranteed by validation)
    return Config(
        api_endpoint=str(config_dict["api_endpoint"]),
        api_timeout_seconds=int(config_dict["api_timeout_seconds"]),
        retry_attempts=int(config_dict["retry_attempts"]),
        capture_prompt=str(config_dict["capture_prompt"]),
        retention_days=int(config_dict["retention_days"]),
        offline_queue_max=int(config_dict["offline_queue_max"]),
        enabled_signals=list(config_dict["enabled_signals"]),
        redact_patterns=list(config_dict["redact_patterns"]),
    )


def validate_config(config_dict: Dict[str, Any]) -> List[str]:
    """
    Validate configuration against schema.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check for required fields and types
    for field, expected_type in CONFIG_SCHEMA.items():
        if field not in config_dict:
            errors.append(f"Missing required field: {field}")
            continue

        value = config_dict[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"Invalid type for field '{field}': "
                f"expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    # Validate specific field constraints
    if "api_timeout_seconds" in config_dict:
        timeout = config_dict["api_timeout_seconds"]
        if isinstance(timeout, int) and timeout <= 0:
            errors.append("api_timeout_seconds must be positive")

    if "retry_attempts" in config_dict:
        retries = config_dict["retry_attempts"]
        if isinstance(retries, int) and retries < 0:
            errors.append("retry_attempts must be non-negative")

    if "retention_days" in config_dict:
        retention = config_dict["retention_days"]
        if isinstance(retention, int) and retention <= 0:
            errors.append("retention_days must be positive")

    if "offline_queue_max" in config_dict:
        queue_max = config_dict["offline_queue_max"]
        if isinstance(queue_max, int) and queue_max <= 0:
            errors.append("offline_queue_max must be positive")

    if "enabled_signals" in config_dict:
        signals = config_dict["enabled_signals"]
        if isinstance(signals, list):
            valid_signals = {"commits", "branches", "diffs", "pr_references"}
            for signal in signals:
                if not isinstance(signal, str):
                    errors.append(
                        f"enabled_signals must contain strings, "
                        f"got {type(signal).__name__}"
                    )
                elif signal not in valid_signals:
                    errors.append(
                        f"Invalid signal '{signal}'. "
                        f"Valid signals: {', '.join(sorted(valid_signals))}"
                    )

    if "redact_patterns" in config_dict:
        patterns = config_dict["redact_patterns"]
        if isinstance(patterns, list):
            for pattern in patterns:
                if not isinstance(pattern, str):
                    errors.append(
                        f"redact_patterns must contain strings, "
                        f"got {type(pattern).__name__}"
                    )

    return errors


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Config object to save
        config_path: Optional path to config file. Defaults to ~/.contextanchor/config.yaml
    """
    if config_path is None:
        config_path = get_config_path()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert Config to dictionary
    config_dict = {
        "api_endpoint": config.api_endpoint,
        "api_timeout_seconds": config.api_timeout_seconds,
        "retry_attempts": config.retry_attempts,
        "capture_prompt": config.capture_prompt,
        "retention_days": config.retention_days,
        "offline_queue_max": config.offline_queue_max,
        "enabled_signals": config.enabled_signals,
        "redact_patterns": config.redact_patterns,
    }

    # Write to file
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
