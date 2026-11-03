"""Local persistence checks: restart, reset, and corrupt storage."""
from datetime import date

import pytest

from demo.interventions import initial_interventions, update_intervention
from demo.intervention_store import load_interventions, save_interventions

QUEUE = [{"Station": "ST-001", "Rank": 1}, {"Station": "ST-002", "Rank": 2}]


def test_roundtrip_persists_assignment_and_resolution(tmp_path):
    path = tmp_path / "interventions.json"
    state = initial_interventions(QUEUE)
    state = update_intervention(
        state, "ST-001", crew="North crew", status="Resolved",
        scheduled_for=date(2026, 11, 3), resolution_note="Replaced connector",
    )
    save_interventions(state, path)
    assert load_interventions(QUEUE, path) == state


def test_no_file_returns_initial_state(tmp_path):
    assert load_interventions(QUEUE, tmp_path / "missing.json") == initial_interventions(QUEUE)


def test_corrupt_file_is_not_silently_overwritten(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read"):
        load_interventions(QUEUE, path)


def test_older_station_records_are_ignored(tmp_path):
    path = tmp_path / "interventions.json"
    save_interventions(initial_interventions(QUEUE), path)
    assert set(load_interventions([QUEUE[0]], path)) == {"ST-001"}
