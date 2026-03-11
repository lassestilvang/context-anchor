import os
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta, timezone
from hypothesis import given, settings, strategies as st
from src.contextanchor.metrics import MetricsCollector

# Strategies
@st.composite
def event_data(draw):
    return {
        "event_type": draw(st.sampled_from([
            "context_capture_started", "context_capture_completed", "context_capture_failed",
            "context_restored", "context_restore_failed", "resume_session_started", "first_productive_action"
        ])),
        "repository_id": draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "branch": draw(st.text(min_size=1, max_size=10)),
        "payload": draw(st.one_of(st.none(), st.dictionaries(st.text(min_size=1), st.text())))
    }

class TestMetricsProperties:
    def setup_method(self):
        self.db_path = Path("tests/prop_metrics.db")
        if self.db_path.exists():
            os.remove(self.db_path)
        self.collector = MetricsCollector(db_path=self.db_path)

    def teardown_method(self):
        if self.db_path.exists():
            os.remove(self.db_path)

    @given(events=st.lists(event_data(), min_size=1, max_size=20))
    @settings(max_examples=10)
    def test_property_50_event_emission_and_retrieval(self, events):
        """Property 50: Event Emission for Operations"""
        if self.db_path.exists():
            os.remove(self.db_path)
        collector = MetricsCollector(db_path=self.db_path)
        
        for e in events:
            collector.emit_event(e["event_type"], e["repository_id"], e["branch"], e["payload"])
        
        # All events should be retrievable
        all_events = collector.get_events()
        assert len(all_events) == len(events)

        
        # Verify first event
        assert all_events[0]["event_type"] == events[0]["event_type"]
        assert all_events[0]["repository_id"] == events[0]["repository_id"]

    @given(repo_id=st.text(min_size=5), branch=st.text(min_size=1))
    @settings(max_examples=10)
    def test_property_51_resume_session_event(self, repo_id, branch):
        """Property 51: Resume Session Event"""
        self.collector.emit_event("resume_session_started", repo_id, branch)
        events = self.collector.get_events(repository_id=repo_id, event_types=["resume_session_started"])
        assert len(events) >= 1
        assert events[-1]["branch"] == branch

    @given(repo_id=st.text(min_size=5), branch=st.text(min_size=1))
    @settings(max_examples=10)
    def test_property_53_time_to_productivity_calculation(self, repo_id, branch):
        """Property 53: Time to Productivity Calculation"""
        # Event 1: Start
        self.collector.emit_event("resume_session_started", repo_id, branch)
        
        # Event 2: Productive action after 5 seconds (simulated)
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        # Shift the first event back by 5 seconds
        past_ts = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        conn.execute("UPDATE events SET timestamp = ? WHERE event_type = ?", (past_ts, "resume_session_started"))
        conn.commit()
        conn.close()
        
        self.collector.emit_event("first_productive_action", repo_id, branch)
        
        ttp = self.collector.calculate_time_to_productivity(repo_id)
        assert len(ttp) >= 1
        assert ttp[-1]["time_to_productivity_seconds"] >= 4.9 # Close to 5

    @given(format=st.sampled_from(["json", "csv"]))
    @settings(max_examples=5)
    def test_property_87_metrics_export_formats(self, format):
        """Property 87: Metrics Export Formats"""
        self.collector.emit_event("test", "repo", "branch")
        export = self.collector.export_metrics(format=format)
        assert len(export) > 0
        if format == "json":
            data = json.loads(export)
            assert "events" in data
        else:
            assert "timestamp,event_type" in export
