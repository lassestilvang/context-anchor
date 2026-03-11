# Getting Started with ContextAnchor

ContextAnchor helps you capture the context of your work inside a Git repository so that you can pick it up exactly where you left off later.

## Installation

Before you begin, ensure you have deployed the ContextAnchor AWS backend and installed the Python CLI locally. See [INSTALL.md](../INSTALL.md) for full details.

## Step 1: Initialize ContextAnchor

Navigate to the root of a Git repository where you want to use ContextAnchor:

```bash
cd /path/to/your/project
contextanchor init
```

*What happens?*
- The tool creates a `.contextanchor/config.yaml` file to store settings.
- It sets up `post-commit` and `post-checkout` Git hooks.

**Action Required:** Open `.contextanchor/config.yaml` and enter your backend `api_endpoint` URL.

## Step 2: Working & Capturing Context

ContextAnchor works automatically for the most part, but you can also manually capture a snapshot whenever you finish a task or switch contexts.

**Method A: Automatic Capture (Recommended)**
Whenever you make a Git commit, ContextAnchor automatically captures the changed files, commit message, and branch. It operates silently in the background.

**Method B: Manual Capture**
If you want to explicitly capture your current working state without committing:

```bash
contextanchor save-context -m "I was just implementing the new auth flow. Still need to add tests for the JWT validation."
```

## Step 3: Restoring Context

When you switch back to a branch you were previously working on, ContextAnchor automatically retrieves the last captured snapshot.

```bash
$ git checkout feature/auth-flow
Switched to branch 'feature/auth-flow'

🔍 ContextAnchor: Switched to branch 'feature/auth-flow'
╭──────────────────────── Context Snapshot: snap-xyz123 ─────────────────────────╮
│                                    Goals                                     │
│ Implement the new auth flow with JWT                                         │
│                                                                              │
│                                  Next Steps                                  │
│ - Add tests for JWT validation                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

If you ever need to manually review the last snapshot:

```bash
contextanchor show-context
```

## Next Steps

- Check out the [CLI Reference](cli-reference.md) for a complete list of commands.
- Read about the [Architecture](architecture.md) to understand how ContextAnchor keeps your data private.
