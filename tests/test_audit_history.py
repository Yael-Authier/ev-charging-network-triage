"""Audit log is durable, explicit and does not invent user identities."""
from datetime import datetime, timezone

import pytest

from demo.audit_history import (
    describe_closure_change, describe_intervention_change, read_history, record_event,
)


def test_history_roundtrip_and_append(tmp_path):
    path = tmp_path / "history.json"
    assert read_history(path) == []
    stamp = datetime(2026, 11, 3, 19, 0, tzinfo=timezone.utc)
    record_event("ST-023", "visit_updated", "crew: Unassigned -> Central crew", path, timestamp=stamp)
    record_event("ST-023", "incidents_confirmed", "INC-0020", path, timestamp=stamp)
    events = read_history(path)
    assert len(events) == 2
    assert events[0]["timestamp_utc"] == stamp.isoformat()
    assert events[1]["action"] == "incidents_confirmed"


def test_intervention_diff_only_changed_fields():
    before = {"crew": "Unassigned", "status": "Pending", "scheduled_for": None, "resolution_note": ""}
    after = {**before, "crew": "North crew"}
    assert describe_intervention_change(before, after) == "crew: Unassigned -> North crew"
    assert describe_intervention_change(before, before) == ""


def test_closure_diff_tracks_additions_and_removals():
    before = {"resolved_incident_ids": ["INC-1"]}
    after = {"resolved_incident_ids": ["INC-2"]}
    assert describe_closure_change(before, after) == (
        "Confirmed closures added: INC-2; removed: INC-1"
    )


def test_corrupt_history_is_not_silently_discarded(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read"):
        record_event("ST-001", "visit_updated", "Test", path)
    assert path.read_text(encoding="utf-8") == "not json"


def test_naive_timestamp_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        record_event("ST-001", "visit_updated", "Test", tmp_path / "h.json",
                     timestamp=datetime(2026, 11, 3, 19, 0))
