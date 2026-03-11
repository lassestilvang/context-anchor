"""CLI entry point for ContextAnchor."""

import os
import stat
import click
from pathlib import Path

from .config import Config, save_config


from typing import Optional


def _find_git_root() -> Optional[Path]:
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").is_dir():
            return current
        current = current.parent
    return None


def _install_git_hook(repo_root: Path, hook_name: str, script_content: str) -> str:
    hook_path = repo_root / ".git" / "hooks" / hook_name

    # Check if we can write to hooks directory
    hooks_dir = hook_path.parent
    if not hooks_dir.exists():
        try:
            hooks_dir.mkdir(parents=True)
        except OSError:
            return "unavailable"

    if not os.access(hooks_dir, os.W_OK):
        return "unavailable"

    try:
        with open(hook_path, "w") as f:
            f.write(script_content)

        # Make executable
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
        return "active"
    except OSError:
        return "degraded"


@click.group()
@click.version_option()
def main() -> None:
    """ContextAnchor: Developer workflow state management system."""


@main.command()
def init() -> None:
    """Initialize ContextAnchor in the current repository."""
    repo_root = _find_git_root()
    if not repo_root:
        click.echo("Error: Not inside a git repository.")
        raise click.Abort()

    config_dir = repo_root / ".contextanchor"
    config_path = config_dir / "config.yaml"

    if config_path.exists():
        click.echo("Error: ContextAnchor is already initialized in this repository.")
        raise click.Abort()

    config_dir.mkdir(exist_ok=True)

    config = Config(api_endpoint="https://api.contextanchor.example.com")
    save_config(config, config_path)

    post_commit_script = "#!/bin/sh\ncontextanchor save-context --hook\n"
    post_checkout_script = "#!/bin/sh\ncontextanchor save-context --hook --branch-switch\n"

    status_commit = _install_git_hook(repo_root, "post-commit", post_commit_script)
    status_checkout = _install_git_hook(repo_root, "post-checkout", post_checkout_script)

    overall_status = "active"
    if status_commit == "unavailable" or status_checkout == "unavailable":
        overall_status = "unavailable"
    elif status_commit == "degraded" or status_checkout == "degraded":
        overall_status = "degraded"

    click.echo(f"Initialized ContextAnchor in {repo_root}")
    click.echo(f"Hook status: {overall_status}")


if __name__ == "__main__":
    main()
