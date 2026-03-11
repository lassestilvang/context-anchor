"""
Metrics and instrumentation for ContextAnchor.
Tracks developer productivity events and exports metrics.
"""

import sqlite3
import json
import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any


class MetricsCollector:
    """
    Handles capturing, storing, and analyzing workflow metrics.
    Uses a local SQLite database for persistence.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            db_path: Path to metrics SQLite database. Defaults to ~/.contextanchor/metrics.db
        """
        if db_path is None:
            db_path = Path.home() / ".contextanchor" / "metrics.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize metrics database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    repository_id TEXT NOT NULL,
                    branch TEXT,
                    timestamp TEXT NOT NULL,
                    payload TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_repo ON events(repository_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            conn.commit()
        finally:
            conn.close()

    def emit_event(self, event_type: str, repository_id: str, branch: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a workflow event.
        
        Args:
            event_type: Type of event (e.g., 'context_capture_started')
            repository_id: ID of the repository
            branch: Current branch name
            payload: Optional metadata for the event
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload) if payload else None
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO events (event_type, repository_id, branch, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
                (event_type, repository_id, branch, timestamp, payload_json)
            )
            conn.commit()
        finally:
            conn.close()

    def get_events(self, repository_id: Optional[str] = None, event_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retrieve recorded events."""
        query = "SELECT event_type, repository_id, branch, timestamp, payload FROM events"
        params = []
        
        conditions = []
        if repository_id:
            conditions.append("repository_id = ?")
            params.append(repository_id)
        if event_types:
            placeholders = ",".join(["?"] * len(event_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp ASC"
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(query, params)
            events = []
            for row in cursor:
                events.append({
                    "event_type": row[0],
                    "repository_id": row[1],
                    "branch": row[2],
                    "timestamp": row[3],
                    "payload": json.loads(row[4]) if row[4] else None
                })
            return events
        finally:
            conn.close()

    def calculate_time_to_productivity(self, repository_id: str) -> List[Dict[str, Any]]:
        """
        Calculate time between session start and first productive action.
        Analyzes events to find 'resume_session_started' and subsequent 'first_productive_action'.
        """
        events = self.get_events(repository_id=repository_id, event_types=["resume_session_started", "first_productive_action"])
        
        sessions = []
        current_session_start = None
        
        for event in events:
            if event["event_type"] == "resume_session_started":
                current_session_start = event
            elif event["event_type"] == "first_productive_action" and current_session_start:
                # Calculate duration
                start_ts = datetime.fromisoformat(current_session_start["timestamp"])
                end_ts = datetime.fromisoformat(event["timestamp"])
                duration = (end_ts - start_ts).total_seconds()
                
                sessions.append({
                    "branch": event["branch"],
                    "session_start": current_session_start["timestamp"],
                    "productive_at": event["timestamp"],
                    "time_to_productivity_seconds": duration
                })
                # Reset for next session
                current_session_start = None
                
        return sessions

    def export_metrics(self, format: str = "json") -> str:
        """Export all events in requested format."""
        events = self.get_events()
        
        if format == "json":
            # Add time-to-productivity summary
            repos = set(e["repository_id"] for e in events)
            ttp_summary = {}
            for repo in repos:
                ttp_summary[repo] = self.calculate_time_to_productivity(repo)
                
            return json.dumps({
                "events": events,
                "time_to_productivity": ttp_summary
            }, indent=2)
            
        elif format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["timestamp", "event_type", "repository_id", "branch", "payload"])
            writer.writeheader()
            for event in events:
                # Flatten payload for CSV
                row = event.copy()
                row["payload"] = json.dumps(row["payload"]) if row["payload"] else ""
                writer.writerow(row)
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
