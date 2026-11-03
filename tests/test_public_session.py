"""Public demo sessions never share state or write local JSON."""
from datetime import date

from demo.public_session import (
    append_session_event, new_demo_state, record_closure_change, record_visit_change,
)
from demo.interventions import update_intervention


QUEUE = [{"Station": "ST-023", "Rank": 1}]


def test_two_sessions_are_independent():
    first = new_demo_state(QUEUE)
    second = new_demo_state(QUEUE)
    first["interventions"] = update_intervention(
        first["interventions"], "ST-023", crew="North crew",
        status="Scheduled", scheduled_for=date(2026, 11, 3), resolution_note="",
    )
    assert second["interventions"]["ST-023"]["crew"] == "Unassigned"
    assert second["history"] == []


def test_session_history_records_changes_without_mutating_original():
    state = new_demo_state(QUEUE)
    before = dict(state["interventions"]["ST-023"])
    after = {**before, "crew": "North crew"}
    updated = record_visit_change(state["history"], "ST-023", before, after)
    assert state["history"] == []
    assert updated[0]["action"] == "visit_updated"
    assert "North crew" in updated[0]["details"]


def test_noop_change_does_not_create_event():
    state = new_demo_state(QUEUE)
    before = state["interventions"]["ST-023"]
    assert record_visit_change([], "ST-023", before, before) == []
    assert record_closure_change([], "ST-023", before, before) == []


def test_reset_can_start_fresh_state():
    state = new_demo_state(QUEUE)
    state["history"] = append_session_event([], "ST-023", "test", "change")
    assert len(state["history"]) == 1
    assert new_demo_state(QUEUE)["history"] == []
