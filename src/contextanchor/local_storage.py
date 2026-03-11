"""
Local storage implementation using SQLite for offline queue and cache.

This module provides persistent local storage for:
- Offline operation queue with retry logic
- Context snapshot cache for offline access
- Exponential backoff retry scheduling
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextanchor.models import QueuedOperation, ContextSnapshot, generate_operation_id


class LocalStorage:
    """
    Local storage manager using SQLite for offline operations and caching.

    Provides:
    - Offline operation queue with exponential backoff retry
    - Context snapshot cache for offline access
    - Operation expiration after 24 hours
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize local storage.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.contextanchor/local.db
        """
        if db_path is None:
            db_path = Path.home() / ".contextanchor" / "local.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    repository_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    remote_url TEXT,
                    last_accessed_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_queue (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    repository_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at TEXT,
                    completed INTEGER NOT NULL DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshot_cache (
                    snapshot_id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    developer_id TEXT NOT NULL,
                    goals TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    open_questions TEXT NOT NULL,
                    next_steps TEXT NOT NULL,
                    relevant_files TEXT NOT NULL,
                    related_prs TEXT NOT NULL,
                    related_issues TEXT NOT NULL,
                    deleted_at TEXT
                )
            """)

            # Create indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_repositories_accessed
                ON repositories(last_accessed_at DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_repository
                ON offline_queue(repository_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_next_retry
                ON offline_queue(next_retry_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_repo_branch
                ON snapshot_cache(repository_id, branch, captured_at DESC)
            """)

            conn.commit()
        finally:
            conn.close()

    def register_repository(
        self, repo_id: str, name: str, root_path: str, remote_url: Optional[str] = None
    ) -> None:
        """
        Register or update repository metadata.

        Args:
            repo_id: Unique repository identifier
            name: Human-readable name (usually folder name)
            root_path: Absolute path to repo root
            remote_url: Git remote URL
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO repositories (
                    repository_id, name, root_path, remote_url, last_accessed_at
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (repo_id, name, root_path, remote_url, now),
            )
            conn.commit()

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get repository metadata.

        Args:
            repo_id: Repository identifier

        Returns:
            Dictionary with repo metadata or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT repository_id, name, root_path, remote_url, last_accessed_at FROM repositories WHERE repository_id = ?",
                (repo_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "repository_id": row[0],
                "name": row[1],
                "root_path": row[2],
                "remote_url": row[3],
                "last_accessed_at": row[4],
            }

    def list_repositories(self) -> List[Dict[str, Any]]:
        """
        List all registered repositories.

        Returns:
            List of dictionaries with repo metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT repository_id, name, root_path, remote_url, last_accessed_at FROM repositories ORDER BY last_accessed_at DESC"
            )
            repos = []
            for row in cursor.fetchall():
                repos.append(
                    {
                        "repository_id": row[0],
                        "name": row[1],
                        "root_path": row[2],
                        "remote_url": row[3],
                        "last_accessed_at": row[4],
                    }
                )
            return repos

    def update_last_accessed(self, repo_id: str) -> None:
        """
        Update the last_accessed_at timestamp for a repository.

        Args:
            repo_id: Repository identifier
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE repositories SET last_accessed_at = ? WHERE repository_id = ?",
                (now, repo_id),
            )
            conn.commit()

    def queue_operation(
        self, operation_type: str, repository_id: str, payload: Dict[str, Any]
    ) -> str:
        """
        Queue an operation for later execution.

        Args:
            operation_type: Type of operation ("save_context", "delete_context")
            repository_id: Repository identifier
            payload: Operation-specific data

        Returns:
            operation_id: Unique identifier for the queued operation
        """
        operation_id = generate_operation_id()
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=24)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO offline_queue (
                    operation_id, operation_type, repository_id, payload,
                    created_at, expires_at, retry_count, next_retry_at, completed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    operation_id,
                    operation_type,
                    repository_id,
                    json.dumps(payload),
                    created_at.isoformat(),
                    expires_at.isoformat(),
                    0,
                    None,
                    0,
                ),
            )
            conn.commit()

        return operation_id

    def get_pending_operations(self) -> List[QueuedOperation]:
        """
        Retrieve all pending operations ready for retry.

        Returns operations that:
        - Are not completed
        - Have not expired
        - Are ready for retry (next_retry_at is None or in the past)

        Returns:
            List of QueuedOperation objects ready for execution
        """
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT operation_id, operation_type, repository_id, payload,
                       created_at, expires_at, retry_count, next_retry_at
                FROM offline_queue
                WHERE completed = 0
                  AND expires_at > ?
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY created_at ASC
            """,
                (now.isoformat(), now.isoformat()),
            )

            operations = []
            for row in cursor.fetchall():
                operations.append(
                    QueuedOperation(
                        operation_id=row[0],
                        operation_type=row[1],
                        repository_id=row[2],
                        payload=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        expires_at=datetime.fromisoformat(row[5]),
                        retry_count=row[6],
                        next_retry_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    )
                )

            return operations

    def mark_operation_complete(self, operation_id: str) -> bool:
        """
        Mark an operation as completed and remove it from the queue.

        Args:
            operation_id: Unique identifier of the operation

        Returns:
            True if operation was found and marked complete, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE offline_queue
                SET completed = 1
                WHERE operation_id = ?
            """,
                (operation_id,),
            )
            conn.commit()

            return cursor.rowcount > 0

    def retry_operation(self, operation: QueuedOperation) -> None:
        """
        Update operation with exponential backoff retry schedule.

        Calculates next retry time using exponential backoff:
        - Retry 0: immediate
        - Retry 1: 2 seconds
        - Retry 2: 4 seconds
        - Retry 3: 8 seconds
        - ...
        - Max: 3600 seconds (1 hour)

        Args:
            operation: Operation to schedule for retry
        """
        operation.retry_count += 1
        backoff_seconds = min(2**operation.retry_count, 3600)
        operation.next_retry_at = datetime.now() + timedelta(seconds=backoff_seconds)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE offline_queue
                SET retry_count = ?, next_retry_at = ?
                WHERE operation_id = ?
            """,
                (
                    operation.retry_count,
                    operation.next_retry_at.isoformat(),
                    operation.operation_id,
                ),
            )
            conn.commit()

    def get_expired_operations(self) -> List[QueuedOperation]:
        """
        Get all operations that have expired (older than 24 hours).

        Returns:
            List of expired QueuedOperation objects
        """
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT operation_id, operation_type, repository_id, payload,
                       created_at, expires_at, retry_count, next_retry_at
                FROM offline_queue
                WHERE completed = 0
                  AND expires_at <= ?
            """,
                (now.isoformat(),),
            )

            operations = []
            for row in cursor.fetchall():
                operations.append(
                    QueuedOperation(
                        operation_id=row[0],
                        operation_type=row[1],
                        repository_id=row[2],
                        payload=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        expires_at=datetime.fromisoformat(row[5]),
                        retry_count=row[6],
                        next_retry_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    )
                )

            return operations

    def cache_snapshot(self, snapshot: ContextSnapshot) -> None:
        """
        Cache a context snapshot for offline access.

        Args:
            snapshot: ContextSnapshot to cache
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshot_cache (
                    snapshot_id, repository_id, branch, captured_at, developer_id,
                    goals, rationale, open_questions, next_steps, relevant_files,
                    related_prs, related_issues, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.snapshot_id,
                    snapshot.repository_id,
                    snapshot.branch,
                    snapshot.captured_at.isoformat(),
                    snapshot.developer_id,
                    snapshot.goals,
                    snapshot.rationale,
                    json.dumps(snapshot.open_questions),
                    json.dumps(snapshot.next_steps),
                    json.dumps(snapshot.relevant_files),
                    json.dumps(snapshot.related_prs),
                    json.dumps(snapshot.related_issues),
                    snapshot.deleted_at.isoformat() if snapshot.deleted_at else None,
                ),
            )
            conn.commit()

    def get_cached_snapshot(self, repository_id: str, branch: str) -> Optional[ContextSnapshot]:
        """
        Retrieve the most recent cached snapshot for a repository and branch.

        Args:
            repository_id: Repository identifier
            branch: Branch name

        Returns:
            Most recent ContextSnapshot or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT snapshot_id, repository_id, branch, captured_at, developer_id,
                       goals, rationale, open_questions, next_steps, relevant_files,
                       related_prs, related_issues, deleted_at
                FROM snapshot_cache
                WHERE repository_id = ? AND branch = ?
                ORDER BY captured_at DESC
                LIMIT 1
            """,
                (repository_id, branch),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return ContextSnapshot(
                snapshot_id=row[0],
                repository_id=row[1],
                branch=row[2],
                captured_at=datetime.fromisoformat(row[3]),
                developer_id=row[4],
                goals=row[5],
                rationale=row[6],
                open_questions=json.loads(row[7]),
                next_steps=json.loads(row[8]),
                relevant_files=json.loads(row[9]),
                related_prs=json.loads(row[10]),
                related_issues=json.loads(row[11]),
                deleted_at=datetime.fromisoformat(row[12]) if row[12] else None,
            )

    def count_queued_operations(self, repository_id: str) -> int:
        """
        Count pending operations for a repository.

        Args:
            repository_id: Repository identifier

        Returns:
            Number of pending operations
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*)
                FROM offline_queue
                WHERE repository_id = ? AND completed = 0
                """,
                (repository_id,),
            )

            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def cleanup_expired_operations(self) -> int:
        """
        Remove expired operations from the queue.

        Returns:
            Number of operations removed
        """
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM offline_queue
                WHERE expires_at <= ?
            """,
                (now.isoformat(),),
            )
            conn.commit()

            return cursor.rowcount
