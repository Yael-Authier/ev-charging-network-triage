"""Explicit closure contract tests."""
from datetime import date

import pytest

from demo.incident_closure import incident_statuses, select_incident_closures
from demo.interventions import initial_interventions, update_intervention
from demo.intervention_store import load_interventions, save_interventions


QUEUE = [{"Station": "ST-023", "Rank": 1}]


def resolved_visit():
    state = initial_interventions(QUEUE)
    return update_intervention(
        state, "ST-023", crew="Central crew", status="Resolved",
        scheduled_for=date(2026, 11, 3), resolution_note="Inspected station",
    )


def test_partial_closure_leaves_other_incidents_active():
    state = select_incident_closures(
        resolved_visit(), "ST-023", ["INC-0020"], ["INC-0020", "INC-0021"]
    )
    rows = [
        {"Incident": "INC-0020", "Status": "Open"},
        {"Incident": "INC-0021", "Status": "Open"},
    ]
    statuses = incident_statuses(rows, state)
    assert [row["Status"] for row in statuses] == ["Resolved", "Open"]
    assert rows[0]["Status"] == "Open"


def test_pending_visit_cannot_close_incidents():
    with pytest.raises(ValueError, match="Resolve"):
        select_incident_closures(
            initial_interventions(QUEUE), "ST-023", ["INC-0020"], ["INC-0020"]
        )


def test_cannot_close_unrelated_incident():
    with pytest.raises(ValueError, match="Invalid"):
        select_incident_closures(
            resolved_visit(), "ST-023", ["INC-9999"], ["INC-0020"]
        )


def test_closures_survive_restart(tmp_path):
    state = select_incident_closures(
        resolved_visit(), "ST-023", ["INC-0020"], ["INC-0020", "INC-0021"]
    )
    path = tmp_path / "state.json"
    save_interventions(state, path)
    restored = load_interventions(QUEUE, path)
    assert restored["ST-023"]["resolved_incident_ids"] == ["INC-0020"]
