# CLI Reference

The ContextAnchor CLI (`contextanchor`) provides commands to initialize your repository, capture context manually or automatically, and query your context history.

## Commands

### `contextanchor init`
Initializes ContextAnchor in the current Git repository.
- Creates `.contextanchor/config.yaml`
- Creates a local SQLite database for offline operations
- Installs `post-commit` and `post-checkout` hooks

### `contextanchor save-context`
Captures the current context (uncommitted changes, current branch) and sends it to the backend.

**Options:**
- `-m`, `--message`: Pass a message indicating your current intent or goals (skips the interactive prompt).
- `--hook`: Hidden flag used when called by a Git hook (runs silently).
- `--branch-switch`: Hidden flag used when called by the post-checkout hook.

### `contextanchor show-context`
Displays the latest context snapshot for the current branch or a specific snapshot.

**Arguments:**
- `snapshot_id` (Optional): Show a specific snapshot by its ID.

**Options:**
- `-f`, `--format`: Output format (`text` [default], `json`, `markdown`).
- `-b`, `--branch`: Specify the branch to retrieve the context for.
- `-t`, `--timestamp`: Retrieve a snapshot taken at or before this timestamp (ISO 8601).

### `contextanchor list-contexts`
Lists all context snapshots captured for the current repository.

**Options:**
- `--limit`: Maximum number of snapshots to display.
- `-f`, `--format`: Output format.

### `contextanchor history`
Displays a chronological history of contexts for the current branch.

**Options:**
- `-b`, `--branch`: The branch to query history for.
- `--limit`: Maximum number of snapshots to display (default: 20).

### `contextanchor delete-context [snapshot_id]`
Soft-deletes a context snapshot.

## Configuration File

The initialization process creates a `config.yaml` file in `.contextanchor/config.yaml`.

```yaml
api_endpoint: "https://your-api-gateway-url/prod/v1"
api_timeout_seconds: 30
capture_prompt: "What are you working on right now?"
enabled_signals:
  - "diffs"
  - "commits"
redact_patterns:
  - '(?i)bearer\s+[a-z0-9\-\._~]+'
  - '(?i)api[_-]?key[_-]?[a-z0-9]+'
retry_attempts: 3
retention_days: 30
```

- **api_endpoint:** The AWS API Gateway URL.
- **capture_prompt:** The prompt text shown when running `save-context` interactively.
- **enabled_signals:** The types of Git signals to capture.
- **redact_patterns:** Regex patterns used to scrub secrets before sending data to the backend.
- **retention_days:** Number of days before the backend automatically purges old snapshots.

## Troubleshooting

### Context Not Syncing
If `save-context` takes a long time or fails, ensure `api_endpoint` is reachable. The CLI will queue failed operations locally and retry them automatically on the next command execution using exponential backoff.

### Hook Execution Issues
If ContextAnchor isn't responding to Git checkouts, verify that `.git/hooks/post-checkout` is executable (`chmod +x .git/hooks/post-checkout`).
