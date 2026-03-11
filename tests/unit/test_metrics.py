import unittest
import os
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta, timezone
from src.contextanchor.metrics import MetricsCollector

class TestMetricsCollector(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.db_path = Path("tests/tmp_metrics.db")
        if self.db_path.exists():
            os.remove(self.db_path)
        self.collector = MetricsCollector(db_path=self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            os.remove(self.db_path)

    def test_emit_and_get_events(self):
        self.collector.emit_event("test_event", "repo1", "main", {"key": "value"})
        events = self.collector.get_events("repo1")
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "test_event")
        self.assertEqual(events[0]["repository_id"], "repo1")
        self.assertEqual(events[0]["branch"], "main")
        self.assertEqual(events[0]["payload"], {"key": "value"})

    def test_calculate_time_to_productivity(self):
        # Create a session start
        start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.collector.emit_event("resume_session_started", "repo1", "main")
        
        # Override the timestamp for the first event manually for precise testing
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE events SET timestamp = ? WHERE event_type = ?", (start_time.isoformat(), "resume_session_started"))
        conn.commit()
        conn.close()
        
        # Emit productive action
        self.collector.emit_event("first_productive_action", "repo1", "main")
        
        ttp = self.collector.calculate_time_to_productivity("repo1")
        self.assertEqual(len(ttp), 1)
        self.assertGreaterEqual(ttp[0]["time_to_productivity_seconds"], 600)
        self.assertLess(ttp[0]["time_to_productivity_seconds"], 610)

    def test_export_json(self):
        self.collector.emit_event("test_event", "repo1", "main")
        export_data = json.loads(self.collector.export_metrics(format="json"))
        
        self.assertIn("events", export_data)
        self.assertIn("time_to_productivity", export_data)
        self.assertEqual(len(export_data["events"]), 1)

    def test_export_csv(self):
        self.collector.emit_event("test_event", "repo1", "main", {"info": "extra"})
        csv_data = self.collector.export_metrics(format="csv")
        
        output = io.StringIO(csv_data)
        reader = csv.DictReader(output)
        rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "test_event")
        self.assertEqual(json.loads(rows[0]["payload"]), {"info": "extra"})

if __name__ == "__main__":
    unittest.main()
