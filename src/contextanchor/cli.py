"""CLI entry point for ContextAnchor."""

import os
import stat
import click
import re
import dataclasses
from pathlib import Path

from .config import Config, save_config


from typing import Optional


def _render_context(context_data: dict, output_format: str) -> None:
    if output_format == "json":
        import json

        click.echo(json.dumps(context_data, indent=2))
        return

    click.echo(f"\\nContext Snapshot: {context_data.get('snapshot_id', 'unknown')}")
    click.echo(f"Captured: {context_data.get('captured_at', 'unknown')}")
    click.echo(f"Developer: {context_data.get('developer_id', 'unknown')}")
    click.echo(f"Branch: {context_data.get('branch', 'unknown')}\\n")
    click.echo("Goals:")
    click.echo(context_data.get("goals", "None specified"))
    click.echo("\\nRationale:")
    click.echo(context_data.get("rationale", "None specified"))
    click.echo("\\nNext Steps:")
    for step in context_data.get("next_steps", []):
        click.echo(f"- {step}")


def _render_context_list(contexts: list, output_format: str) -> None:
    if output_format == "json":
        import json

        click.echo(json.dumps(contexts, indent=2))
        return

    if not contexts:
        click.echo("No historical contexts found.")
        return

    click.echo(f"\\nRecent Contexts ({len(contexts)}):")
    for ctx in contexts:
        intent = ctx.get("developer_intent", "N/A")
        # Handle snapshots that might use developer_id if intent isn't at root
        click.echo(
            f"[{ctx.get('snapshot_id', 'unknown')}] {ctx.get('captured_at', 'unknown')} | {intent}"
        )


def _redact_secrets(text: str, patterns: list) -> str:
    """Apply regex redaction patterns to user input."""
    for pattern in patterns:
        try:
            regex = re.compile(pattern)
            text = regex.sub("[REDACTED]", text)
        except re.error:
            pass
    return text


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


@main.command(name="save-context")
@click.option("--message", "-m", help="Developer intent (skips prompt)")
@click.option("--hook", is_flag=True, help="Run in non-interactive hook mode.")
@click.option("--branch-switch", is_flag=True, help="Triggered by branch switch hook.")
def save_context(message: Optional[str], hook: bool, branch_switch: bool) -> None:
    """Capture and save developer context snapshot."""
    repo_root = _find_git_root()
    if not repo_root:
        click.echo("Error: Not inside a git repository.")
        raise click.Abort()

    config_path = repo_root / ".contextanchor" / "config.yaml"
    if not config_path.exists():
        click.echo("Error: ContextAnchor is not initialized in this repository.")
        raise click.Abort()

    from .config import load_config

    config = load_config(config_path)

    from .git_observer import GitObserver

    from .models import CaptureSignals

    git_obs = GitObserver(str(repo_root))
    repo_id = git_obs.generate_repository_id() or "unknown"
    branch = git_obs.get_current_branch() or "HEAD"

    uncommitted = git_obs.capture_uncommitted_changes() if "diffs" in config.enabled_signals else []
    commit_sig = git_obs.capture_commit_signal() if "commits" in config.enabled_signals else None

    signals = CaptureSignals(
        repository_id=repo_id,
        branch=branch,
        uncommitted_files=uncommitted,
        recent_commits=[commit_sig] if commit_sig else [],
        pr_references=[],
        issue_references=[],
        github_metadata=None,
        capture_source="hook" if hook else "cli",
    )

    intent = message
    if not intent:
        if hook and not os.isatty(0):
            intent = "Automated save from hook"
        else:
            intent = click.prompt(
                config.capture_prompt, type=str, default="Working on codebase", show_default=False
            )

    intent_str = _redact_secrets(intent, config.redact_patterns)

    from typing import Dict, Any

    try:
        signals_dict = dataclasses.asdict(signals)
    except TypeError:
        signals_dict = getattr(signals, "__dict__", {})

    payload: Dict[str, Any] = {
        "repository_id": repo_id,
        "branch": branch,
        "developer_intent": intent_str,
        "signals": signals_dict,
    }

    from .api_client import APIClient
    from .local_storage import LocalStorage

    client = APIClient(config.api_endpoint, config.retry_attempts, config.api_timeout_seconds)
    try:
        resp = client.create_context(repo_id, branch, intent_str, payload["signals"])
        snapshot_id = resp.get("snapshot_id", "unknown")
        click.echo(f"Context snapshot saved successfully. (ID: {snapshot_id})")
    except ConnectionError:
        local = LocalStorage()
        op_id = local.queue_operation("save_context", repo_id, payload)
        click.echo(f"Network unavailable. Queued operation for later. (Op ID: {op_id})")
    except Exception as e:
        click.echo(f"Error saving context: {e}")


@main.command(name="show-context")
@click.argument("snapshot_id", required=False)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    help="Output format",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=5,
    help="Number of historical snapshots to list if no ID provided.",
)
def show_context(snapshot_id: Optional[str], output_format: str, limit: int) -> None:
    """Display specific context snapshot or history."""
    repo_root = _find_git_root()
    if not repo_root:
        click.echo("Error: Not inside a git repository.")
        raise click.Abort()

    config_path = repo_root / ".contextanchor" / "config.yaml"
    if not config_path.exists():
        click.echo("Error: ContextAnchor is not initialized in this repository.")
        raise click.Abort()

    from .config import load_config

    config = load_config(config_path)

    from .git_observer import GitObserver

    git_obs = GitObserver(str(repo_root))
    repo_id = git_obs.generate_repository_id() or "unknown"
    branch = git_obs.get_current_branch() or "HEAD"

    from .api_client import APIClient

    client = APIClient(config.api_endpoint, config.retry_attempts, config.api_timeout_seconds)

    if output_format != "json":
        if snapshot_id:
            click.echo(f"Fetching snapshot {snapshot_id}...")
        else:
            click.echo(f"Listing recent {limit} snapshots for {repo_id}/{branch}...")

    from .local_storage import LocalStorage

    try:
        if snapshot_id:
            context_data = client.get_context_by_id(snapshot_id)
            _render_context(context_data, output_format)
        else:
            contexts = client.list_contexts(repo_id, branch, limit)
            _render_context_list(
                contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts,
                output_format,
            )
    except ConnectionError:
        click.echo("Network unavailable. Falling back to local cache.")
        local = LocalStorage()
        if not snapshot_id:
            cached = local.get_cached_snapshot(repo_id, branch)
            if cached:
                import dataclasses

                # convert to dict
                try:
                    c_dict = dataclasses.asdict(cached)
                except TypeError:
                    c_dict = getattr(cached, "__dict__", {})
                _render_context(c_dict, output_format)
            else:
                click.echo("No cached context available.")
        else:
            click.echo("Cannot fetch specific historical snapshots while offline.")
    except Exception as e:
        click.echo(f"Error fetching context: {e}")


@main.command(name="list-contexts")
@click.option("--limit", "-l", type=int, default=20, help="Number of contexts to show.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
)
def list_contexts(limit: int, output_format: str) -> None:
    """List all contexts in the repository."""
    repo_root = _find_git_root()
    if not repo_root:
        raise click.Abort()
    from .config import load_config
    config = load_config(repo_root / ".contextanchor" / "config.yaml")

    from .git_observer import GitObserver
    from .api_client import APIClient

    git_obs = GitObserver(str(repo_root))
    repo_id = git_obs.generate_repository_id() or "unknown"
    client = APIClient(config.api_endpoint, config.retry_attempts)

    try:
        # Pass None for branch to get all for repo
        contexts = client.list_contexts(repo_id, None, limit)
        _render_context_list(
            contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts,
            output_format,
        )
    except Exception as e:
        click.echo(f"Error: {e}")


@main.command(name="history")
@click.option("--branch", "-b", type=str, help="Specific branch history.")
@click.option("--limit", "-l", type=int, default=20)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
)
def history(branch: Optional[str], limit: int, output_format: str) -> None:
    """Show context history for a branch."""
    repo_root = _find_git_root()
    if not repo_root:
        raise click.Abort()
    from .config import load_config
    config = load_config(repo_root / ".contextanchor" / "config.yaml")

    from .git_observer import GitObserver
    from .api_client import APIClient

    git_obs = GitObserver(str(repo_root))
    repo_id = git_obs.generate_repository_id() or "unknown"
    target_branch = branch or git_obs.get_current_branch() or "HEAD"
    client = APIClient(config.api_endpoint, config.retry_attempts)

    try:
        contexts = client.list_contexts(repo_id, target_branch, limit)
        _render_context_list(
            contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts,
            output_format,
        )
    except Exception as e:
        click.echo(f"Error: {e}")


@main.command(name="delete-context")
@click.argument("snapshot_id")
def delete_context(snapshot_id: str) -> None:
    """Delete a specific context snapshot."""
    repo_root = _find_git_root()
    if not repo_root:
        raise click.Abort()
    from .config import load_config
    config = load_config(repo_root / ".contextanchor" / "config.yaml")

    from .api_client import APIClient

    client = APIClient(config.api_endpoint, config.retry_attempts)

    try:
        client.delete_context(snapshot_id)
        click.echo(f"Context snapshot {snapshot_id} marked for deletion (purge 24h).")
    except Exception as e:
        click.echo(f"Error deleting context: {e}")
