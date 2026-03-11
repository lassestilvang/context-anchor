"""ContextAnchor: Developer workflow state management system."""

__version__ = "0.1.0"

from .github_integration import GitHubIntegration
from .git_observer import GitObserver
from .context_store import ContextStore
from .models import (
    ContextSnapshot,
    FileChange,
    CommitInfo,
    CaptureSignals,
    GitHubRepo,
    Repository,
    Config,
    QueuedOperation,
)

__all__ = [
    "GitHubIntegration",
    "GitObserver",
    "ContextStore",
    "ContextSnapshot",
    "FileChange",
    "CommitInfo",
    "CaptureSignals",
    "GitHubRepo",
    "Repository",
    "Config",
    "QueuedOperation",
]
