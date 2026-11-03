"""Intervention workflow tests for the session-only portfolio MVP."""
from datetime import date, timedelta

import pytest

from demo.interventions import initial_interventions, intervention_metrics, update_intervention

TODAY = date(2026, 11, 3)
QUEUE = [{"Station": "ST-001", "Rank": 1}, {"Station": "ST-002", "Rank": 2}]


def test_initial_state():
    state = initial_interventions(QUEUE)
    assert set(state) == {"ST-001", "ST-002"}
    assert all(item["status"] == "Pending" for item in state.values())


def test_assignment_and_schedule_do_not_mutate_original():
    original = initial_interventions(QUEUE)
    updated = update_intervention(
        original, "ST-001", crew="North crew", status="Scheduled",
        scheduled_for=TODAY, resolution_note="",
    )
    assert updated["ST-001"]["status"] == "Scheduled"
    assert original["ST-001"]["status"] == "Pending"


def test_resolution_requires_note_and_crew():
    state = initial_interventions(QUEUE)
    with pytest.raises(ValueError, match="crew"):
        update_intervention(state, "ST-001", crew="Unassigned", status="Resolved",
                            scheduled_for=TODAY, resolution_note="Fixed")
    with pytest.raises(ValueError, match="resolution note"):
        update_intervention(state, "ST-001", crew="North crew", status="Resolved",
                            scheduled_for=TODAY, resolution_note=" ")


def test_metrics_overdue_and_resolved():
    state = initial_interventions(QUEUE)
    state = update_intervention(
        state, "ST-001", crew="North crew", status="Scheduled",
        scheduled_for=TODAY - timedelta(days=1), resolution_note="",
    )
    state = update_intervention(
        state, "ST-002", crew="Central crew", status="Resolved",
        scheduled_for=TODAY - timedelta(days=1), resolution_note="Replaced connector",
    )
    assert intervention_metrics(state, as_of=TODAY) == {
        "planned": 2, "assigned": 2, "resolved": 1, "blocked": 0, "overdue": 1
    }


def test_unknown_station_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        update_intervention(initial_interventions(QUEUE), "ST-999", crew="North crew",
                            status="Pending", scheduled_for=None, resolution_note="")


def test_region_restriction():
    queue = [{"Station": "ST-001", "Rank": 1, "Region": "Central"}]
    state = initial_interventions(queue)
    with pytest.raises(ValueError, match="regional crew"):
        update_intervention(state, "ST-001", crew="North crew", status="Scheduled",
                            scheduled_for=TODAY, resolution_note="")
    assert update_intervention(state, "ST-001", crew="Central crew", status="Scheduled",
                               scheduled_for=TODAY, resolution_note="")["ST-001"]["crew"] == "Central crew"


def test_crew_cannot_have_two_active_visits_same_day():
    queue = [{"Station": "ST-001", "Rank": 1, "Region": "North"},
             {"Station": "ST-002", "Rank": 2, "Region": "North"}]
    state = initial_interventions(queue)
    state = update_intervention(state, "ST-001", crew="North crew", status="Scheduled",
                                scheduled_for=TODAY, resolution_note="")
    with pytest.raises(ValueError, match="already booked"):
        update_intervention(state, "ST-002", crew="North crew", status="In progress",
                            scheduled_for=TODAY, resolution_note="")
    assert update_intervention(state, "ST-002", crew="North crew", status="Scheduled",
                               scheduled_for=TODAY + timedelta(days=1),
                               resolution_note="")["ST-002"]["status"] == "Scheduled"


def test_blocked_requires_reason():
    state = initial_interventions(QUEUE)
    with pytest.raises(ValueError, match="blocking reason"):
        update_intervention(state, "ST-001", crew="North crew", status="Blocked",
                            scheduled_for=TODAY, resolution_note="")
