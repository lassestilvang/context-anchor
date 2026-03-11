"""
Categorized error classes for ContextAnchor.
"""


class ContextAnchorError(Exception):
    """Base class for all ContextAnchor errors."""

    pass


class NetworkError(ContextAnchorError):
    """Errors related to API connectivity or timeouts."""

    pass


class GitError(ContextAnchorError):
    """Errors related to git command execution or repository state."""

    pass


class ConfigurationError(ContextAnchorError):
    """Errors related to invalid configuration or credentials."""

    pass


class DataError(ContextAnchorError):
    """Errors related to malformed data or schema violations."""

    pass


class UserError(ContextAnchorError):
    """Errors caused by invalid user input or CLI arguments."""

    pass
