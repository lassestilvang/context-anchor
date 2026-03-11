"""CLI entry point for ContextAnchor."""

import os
import stat
import click
import re
import dataclasses
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.theme import Theme
from rich.live import Live
from rich.status import Status
from pathlib import Path

# Initialize Rich console with custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "bold magenta",
    "muted": "grey50"
})
console = Console(theme=custom_theme)

from .config import Config, save_config


from typing import Optional


def _render_context(context_data: dict, output_format: str) -> None:
    if output_format == "json":
        import json
        console.print_json(data=context_data)
        return

    from rich.markdown import Markdown
    
    title = f"[bold success]Context Snapshot:[/bold success] [highlight]{context_data.get('snapshot_id', 'unknown')}[/highlight]"
    meta = f"[muted]Captured:[/muted] {context_data.get('captured_at', 'unknown')} | [muted]Branch:[/muted] {context_data.get('branch', 'unknown')}"
    
    content = f"# Goals\n{context_data.get('goals', 'None specified')}\n\n"
    content += f"# Rationale\n{context_data.get('rationale', 'None specified')}\n\n"
    content += "# Next Steps\n"
    for step in context_data.get('next_steps', []):
        content += f"- {step}\n"

    console.print(Panel(Markdown(content), title=title, subtitle=meta, border_style="success"))


def _render_context_list(contexts: list, output_format: str) -> None:
    if output_format == "json":
        console.print_json(data=contexts)
        return

    if not contexts:
        console.print("[warning]No historical contexts found.[/warning]")
        return

    table = Table(title=f"Recent Contexts ({len(contexts)})", border_style="highlight")
    table.add_column("ID", style="success", no_wrap=True)
    table.add_column("Captured", style="muted")
    table.add_column("Branch", style="info")
    table.add_column("Intent")

    for ctx in contexts:
        table.add_row(
            ctx.get("snapshot_id", "unknown")[:8],
            ctx.get("captured_at", "N/A"),
            ctx.get("branch", "N/A"),
            ctx.get("developer_intent", "N/A")
        )

    console.print(table)


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


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def main(ctx: click.Context) -> None:
    """ContextAnchor: Developer workflow state management system."""
    from .logging import setup_logging
    setup_logging()
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    # Fallback branch switch detection
    if ctx.invoked_subcommand not in ["init", "_hook-branch-switch"]:
        repo_root = _find_git_root()
        if repo_root:
            state_file = repo_root / ".contextanchor" / "state.json"
            from .git_observer import GitObserver
            import json

            git_obs = GitObserver(str(repo_root))
            branch = git_obs.get_current_branch()

            state = {}
            if state_file.exists():
                try:
                    with open(state_file, "r") as f:
                        state = json.load(f)
                except Exception:
                    pass

            last_branch = state.get("last_branch")
            if branch and branch != last_branch:
                state["last_branch"] = branch
                try:
                    with open(state_file, "w") as f:
                        json.dump(state, f)
                except Exception:
                    pass

                # Show context as fallback
                console.print(f"\\n[highlight]🔍 ContextAnchor: Detected switch to branch '{branch}' (fallback)[/highlight]")
                try:
                    from .metrics import MetricsCollector
                    repo_id = git_obs.generate_repository_id() or "unknown"
                    MetricsCollector().emit_event("resume_session_started", repo_id, branch)
                except Exception:
                    pass
                try:
                    from .config import load_config

                    config_path = repo_root / ".contextanchor" / "config.yaml"
                    if config_path.exists():
                        config = load_config(config_path)
                        from .api_client import APIClient
                        from .local_storage import LocalStorage

                        client = APIClient(
                            config.api_endpoint, config.retry_attempts, config.api_timeout_seconds
                        )
                        repo_id = git_obs.generate_repository_id() or "unknown"

                        try:
                            contexts = client.list_contexts(repo_id, branch, 1)
                            ctx_list = (
                                contexts.get("contexts", contexts)
                                if isinstance(contexts, dict)
                                else contexts
                            )
                            if ctx_list and len(ctx_list) > 0:
                                _render_context(ctx_list[0], "text")
                            else:
                                console.print("[warning]No saved context found for this branch.[/warning]")
                        except ConnectionError:
                            local = LocalStorage()
                            cached = local.get_cached_snapshot(repo_id, branch)
                            if cached:
                                import dataclasses

                                try:
                                    c_dict = dataclasses.asdict(cached)
                                except TypeError:
                                    c_dict = getattr(cached, "__dict__", {})
                                _render_context(c_dict, "text")
                            else:
                                console.print("[warning]No saved context found for this branch.[/warning]")
                except Exception:
                    pass  # Keep fallback quiet on errors

            # Check for first productive action
            try:
                from .metrics import MetricsCollector
                metrics = MetricsCollector()
                repo_id = git_obs.generate_repository_id() or "unknown"
                
                # Get events for this repo/branch
                events = metrics.get_events(repository_id=repo_id, event_types=["resume_session_started", "first_productive_action"])
                
                # Find if there is a pending session (started but not yet productive)
                pending_start = None
                for e in reversed(events):
                    if e["branch"] == branch:
                        if e["event_type"] == "first_productive_action":
                            # Already productive for this session
                            break 
                        if e["event_type"] == "resume_session_started":
                            pending_start = e
                            break
                
                if pending_start:
                    from datetime import datetime
                    start_ts = datetime.fromisoformat(pending_start["timestamp"])
                    if git_obs.has_productive_action_since(start_ts):
                        metrics.emit_event("first_productive_action", repo_id, branch)
            except Exception:
                pass



@main.command()
def init() -> None:
    """Initialize ContextAnchor in the current repository."""
    repo_root = _find_git_root()
    if not repo_root:
        console.print("[error]❌ Error: Not inside a git repository.[/error]")
        raise click.Abort()

    config_dir = repo_root / ".contextanchor"
    config_path = config_dir / "config.yaml"

    if config_path.exists():
        console.print("[warning]⚠ ContextAnchor is already initialized in this repository.[/warning]")
        raise click.Abort()

    config_dir.mkdir(exist_ok=True)

    config = Config(api_endpoint="https://api.contextanchor.example.com")
    save_config(config, config_path)

    post_commit_script = "#!/bin/sh\ncontextanchor save-context --hook\n"
    post_checkout_script = "#!/bin/sh\ncontextanchor save-context --hook --branch-switch\n"

    status_commit = _install_git_hook(repo_root, "post-commit", post_commit_script)
    status_checkout = _install_git_hook(repo_root, "post-checkout", post_checkout_script)

    style_map = {"active": "success", "degraded": "warning", "unavailable": "error"}
    hook_style = style_map.get(overall_status, "muted")

    console.print(f"[success]✅ Initialized ContextAnchor in[/success] [highlight]{repo_root}[/highlight]")
    console.print(f"Hook status: [{hook_style}]{overall_status}[/{hook_style}]")


@main.command(name="_hook-branch-switch", hidden=True)
@click.argument("prev_head", required=False)
@click.argument("new_head", required=False)
def hook_branch_switch(prev_head: Optional[str], new_head: Optional[str]) -> None:
    """Internal hook for branch switches."""
    repo_root = _find_git_root()
    if not repo_root:
        return

    state_file = repo_root / ".contextanchor" / "state.json"

    from .git_observer import GitObserver

    git_obs = GitObserver(str(repo_root))
    branch = git_obs.get_current_branch()

    import json

    state = {}
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
        except Exception:
            pass

    old_branch = state.get("last_branch")

    if branch:
        state["last_branch"] = branch
        try:
            with open(state_file, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    if old_branch != branch and branch:
        click.echo(f"\\n--- ContextAnchor: Switched to branch '{branch}' ---")
        try:
            from .metrics import MetricsCollector
            repo_id = git_obs.generate_repository_id() or "unknown"
            MetricsCollector().emit_event("resume_session_started", repo_id, branch)
        except Exception:
            pass
        try:
            from .config import load_config

            config_path = repo_root / ".contextanchor" / "config.yaml"
            if not config_path.exists():
                return
            config = load_config(config_path)

            from .api_client import APIClient
            from .local_storage import LocalStorage

            client = APIClient(
                config.api_endpoint, config.retry_attempts, config.api_timeout_seconds
            )
            repo_id = git_obs.generate_repository_id() or "unknown"

            try:
                contexts = client.list_contexts(repo_id, branch, 1)
                ctx_list = (
                    contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts
                )
                if ctx_list and len(ctx_list) > 0:
                    _render_context(ctx_list[0], "text")
                else:
                    click.echo("No saved context found for this branch.")
            except ConnectionError:
                local = LocalStorage()
                cached = local.get_cached_snapshot(repo_id, branch)
                if cached:
                    import dataclasses

                    try:
                        c_dict = dataclasses.asdict(cached)
                    except TypeError:
                        c_dict = getattr(cached, "__dict__", {})
                    _render_context(c_dict, "text")
                else:
                    click.echo("No saved context found for this branch.")
        except Exception as e:
            click.echo(f"Error restoring context: {e}")


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
    from .errors import NetworkError, ContextAnchorError
    from .logging import get_logger

    logger = get_logger("cli.save_context")
    client = APIClient(config.api_endpoint, config.retry_attempts, config.api_timeout_seconds)
    from .metrics import MetricsCollector
    metrics = MetricsCollector()
    metrics.emit_event("context_capture_started", repo_id, branch)

    try:
        with console.status("[info]Saving context to cloud...[/info]", spinner="dots"):
            resp = client.create_context(repo_id, branch, intent_str, payload["signals"])
            snapshot_id = resp.get("snapshot_id", "unknown")
        
        console.print(f"[success]✅ Context snapshot saved successfully.[/success] [muted](ID: {snapshot_id})[/muted]")
        metrics.emit_event("context_capture_completed", repo_id, branch, {"snapshot_id": snapshot_id})
        logger.info(f"Context saved: {snapshot_id} for branch {branch}")
    except NetworkError as e:
        logger.warning(f"Network error during save: {e}. Queueing operation.")
        local = LocalStorage()
        op_id = local.queue_operation("save_context", repo_id, payload)
        console.print(f"[warning]⚠ Network unavailable. Queued operation for later.[/warning] [muted](Op ID: {op_id})[/muted]")
        metrics.emit_event("context_capture_failed", repo_id, branch, {"error": "NetworkError", "queued": True})
    except ContextAnchorError as e:
        logger.error(f"ContextAnchor error: {e}")
        console.print(f"[error]❌ Error:[/error] {e}")
        metrics.emit_event("context_capture_failed", repo_id, branch, {"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error during save_context")
        console.print(f"[error]❌ An unexpected error occurred:[/error] {e}")
        metrics.emit_event("context_capture_failed", repo_id, branch, {"error": "UnexpectedError"})


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
        status_msg = f"[info]Fetching snapshot {snapshot_id}...[/info]" if snapshot_id else f"[info]Listing recent {limit} snapshots for {repo_id}/{branch}...[/info]"
    else:
        status_msg = ""

    from .local_storage import LocalStorage
    from .errors import NetworkError, ContextAnchorError
    from .logging import get_logger

    logger = get_logger("cli.show_context")
    from .metrics import MetricsCollector
    metrics = MetricsCollector()
    try:
        if status_msg:
            with console.status(status_msg, spinner="dots"):
                if snapshot_id:
                    context_data = client.get_context_by_id(snapshot_id)
                else:
                    context_data = client.list_contexts(repo_id, branch, limit)
        else:
            if snapshot_id:
                context_data = client.get_context_by_id(snapshot_id)
            else:
                context_data = client.list_contexts(repo_id, branch, limit)

        if snapshot_id:
            _render_context(context_data, output_format)
            metrics.emit_event("context_restored", repo_id, branch, {"snapshot_id": snapshot_id})
            logger.info(f"Context restored: {snapshot_id}")
        else:
            _render_context_list(
                context_data.get("contexts", context_data) if isinstance(context_data, dict) else context_data,
                output_format,
            )
    except NetworkError as e:
        logger.warning(f"Network error during show_context: {e}")
        console.print("[warning]⚠ Network unavailable. Falling back to local cache.[/warning]")
        local = LocalStorage()
        if not snapshot_id:
            cached = local.get_cached_snapshot(repo_id, branch)
            if cached:
                import dataclasses
                try:
                    c_dict = dataclasses.asdict(cached)
                except TypeError:
                    c_dict = getattr(cached, "__dict__", {})
                _render_context(c_dict, output_format)
                metrics.emit_event("context_restored", repo_id, branch, {"snapshot_id": c_dict.get("snapshot_id"), "cache": True})
                logger.info("Restored latest context from local cache.")
            else:
                logger.info("No cached context found.")
                console.print("[warning]No cached context available.[/warning]")
                metrics.emit_event("context_restore_failed", repo_id, branch, {"error": "No cache"})
        else:
            logger.error(f"Cannot fetch historical snapshot {snapshot_id} while offline.")
            console.print(f"[error]❌ Cannot fetch specific historical snapshots while offline.[/error]")
            metrics.emit_event("context_restore_failed", repo_id, branch, {"error": "Network unavailable"})
    except ContextAnchorError as e:
        logger.error(f"ContextAnchor error: {e}")
        console.print(f"[error]❌ Error:[/error] {e}")
        metrics.emit_event("context_restore_failed", repo_id, branch, {"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error during show_context")
        console.print(f"[error]❌ An unexpected error occurred:[/error] {e}")
        metrics.emit_event("context_restore_failed", repo_id, branch, {"error": "UnexpectedError"})



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

    from .errors import ContextAnchorError, NetworkError
    from .logging import get_logger
    logger = get_logger("cli.list_contexts")

    try:
        with console.status("[info]Fetching contexts...[/info]", spinner="dots"):
            contexts = client.list_contexts(repo_id, None, limit)
        _render_context_list(
            contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts,
            output_format,
        )
    except NetworkError as e:
        logger.error(f"Network error in list_contexts: {e}")
        console.print(f"[error]❌ Network error:[/error] {e}")
    except ContextAnchorError as e:
        logger.error(f"ContextAnchor error in list_contexts: {e}")
        console.print(f"[error]❌ Error:[/error] {e}")
    except Exception as e:
        logger.exception("Unexpected error in list_contexts")
        console.print(f"[error]❌ An unexpected error occurred:[/error] {e}")


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

    from .errors import ContextAnchorError, NetworkError
    from .logging import get_logger
    logger = get_logger("cli.history")

    try:
        with console.status(f"[info]Fetching history for {target_branch}...[/info]", spinner="dots"):
            contexts = client.list_contexts(repo_id, target_branch, limit)
        _render_context_list(
            contexts.get("contexts", contexts) if isinstance(contexts, dict) else contexts,
            output_format,
        )
    except NetworkError as e:
        logger.error(f"Network error in history: {e}")
        console.print(f"[error]❌ Network error:[/error] {e}")
    except ContextAnchorError as e:
        logger.error(f"ContextAnchor error in history: {e}")
        console.print(f"[error]❌ Error:[/error] {e}")
    except Exception as e:
        logger.exception("Unexpected error in history")
        console.print(f"[error]❌ An unexpected error occurred:[/error] {e}")


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

    from .errors import ContextAnchorError, NetworkError
    from .logging import get_logger
    logger = get_logger("cli.delete_context")

    try:
        client.delete_context(snapshot_id)
        console.print(f"[success]✅ Context snapshot {snapshot_id} marked for deletion.[/success] [muted](purge 24h)[/muted]")
        logger.info(f"Context deleted: {snapshot_id}")
    except NetworkError as e:
        logger.error(f"Network error in delete_context: {e}")
        console.print(f"[error]❌ Network error:[/error] {e}")
    except ContextAnchorError as e:
        logger.error(f"ContextAnchor error in delete_context: {e}")
        console.print(f"[error]❌ Error:[/error] {e}")
    except Exception as e:
        logger.exception("Unexpected error in delete_context")
        console.print(f"[error]❌ An unexpected error occurred:[/error] {e}")


@main.command(name="export-metrics")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Export format.",
)
def export_metrics(format: str) -> None:
    """Export workflow metrics."""
    from .metrics import MetricsCollector

    metrics = MetricsCollector()
    data = metrics.export_metrics(format=format)
    if format == "json":
        console.print_json(data)
    else:
        console.print(data)

