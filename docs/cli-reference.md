# CLI Reference

The ContextAnchor CLI (`contextanchor`) captures and restores developer context tied to your current Git repository.

## Command Index

```text
contextanchor [OPTIONS] COMMAND [ARGS]...
```

Commands:

- `init`
- `save-context`
- `show-context`
- `list-contexts`
- `history`
- `delete-context`
- `sync`
- `list-repositories`
- `export-metrics`

## Global Options

- `--help`: Show command help
- `--version`: Show installed version

## Command Details

### `contextanchor init`

Initialize ContextAnchor in the current Git repository.

What it does:

1. Creates `.contextanchor/config.yaml`.
2. Installs `.git/hooks/post-commit` and `.git/hooks/post-checkout`.
3. Registers repository metadata in local storage.

### `contextanchor save-context`

Capture and persist a snapshot of the current work context.

Options:

- `-m, --message TEXT`: Developer intent text (skips interactive prompt)
- `--hook`: Internal flag for non-interactive hook mode
- `--branch-switch`: Internal flag for branch-switch hook usage

Example:

```bash
contextanchor save-context -m "Investigating flaky integration test"
```

### `contextanchor show-context [SNAPSHOT_ID]`

Show one snapshot by ID, or list recent snapshots if ID is omitted.

Arguments:

- `SNAPSHOT_ID` (optional): Specific snapshot identifier

Options:

- `-f, --format [text|json|markdown]`: Output format (default `text`)
- `-l, --limit INTEGER`: Number of recent snapshots when no ID is provided (default `5`)

Examples:

```bash
contextanchor show-context
contextanchor show-context snap_123456 -f json
```

### `contextanchor list-contexts`

List context snapshots for the current repository.

Options:

- `-l, --limit INTEGER`: Number of results (default `20`)
- `-f, --format [text|json|markdown]`: Output format

Example:

```bash
contextanchor list-contexts -l 10
```

### `contextanchor history`

List context history for a branch.

Options:

- `-b, --branch TEXT`: Branch to query (defaults to current branch)
- `-l, --limit INTEGER`: Number of results (default `20`)
- `-f, --format [text|json|markdown]`: Output format

Example:

```bash
contextanchor history -b main -l 20
```

### `contextanchor delete-context SNAPSHOT_ID`

Soft-delete a specific snapshot.

Arguments:

- `SNAPSHOT_ID`: Snapshot identifier to delete

Example:

```bash
contextanchor delete-context snap_123456
```

### `contextanchor sync`

Replay queued offline operations for the current repository.

Example:

```bash
contextanchor sync
```

### `contextanchor list-repositories`

Show repositories registered in local storage.

Example:

```bash
contextanchor list-repositories
```

### `contextanchor export-metrics`

Export metrics and instrumentation events.

Options:

- `-f, --format [json|csv]`: Export format (default `json`)

Examples:

```bash
contextanchor export-metrics -f json
contextanchor export-metrics -f csv
```

## Configuration

Each initialized repository has `.contextanchor/config.yaml`.

Default shape:

```yaml
api_endpoint: "https://api.contextanchor.example.com"
api_timeout_seconds: 30
retry_attempts: 3
capture_prompt: "What were you trying to solve right now?"
retention_days: 90
offline_queue_max: 200
enabled_signals:
  - commits
  - branches
  - diffs
  - pr_references
redact_patterns: []
```

`api_endpoint` should be set to your deployed API Gateway base URL (typically ending with `/prod/v1`).

## Credentials

API key is read from:

```text
~/.contextanchor/credentials
```

Recommended permissions:

```bash
chmod 600 ~/.contextanchor/credentials
```

## Troubleshooting

### Network/Sync Problems

If cloud calls fail, ContextAnchor queues operations locally and retries with exponential backoff.

Use:

```bash
contextanchor sync
```

### Branch Switch Context Not Showing

Verify hooks are executable:

```bash
chmod +x .git/hooks/post-checkout .git/hooks/post-commit
```

### Inspect Local Logs

```bash
tail -n 200 ~/.contextanchor/logs/contextanchor.log
```
