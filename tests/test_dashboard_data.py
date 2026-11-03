"""Contract checks for the read-only portfolio dashboard."""
from datetime import date

from demo.dashboard_data import dashboard_snapshot


def test_dashboard_uses_five_distinct_stations():
    snapshot = dashboard_snapshot()
    visits = snapshot["recommendations"]
    assert snapshot["station_count"] == 40
    assert len(visits) == 5
    assert len({visit["Station"] for visit in visits}) == 5
    assert [visit["Rank"] for visit in visits] == [1, 2, 3, 4, 5]


def test_dashboard_reasons_and_incidents_are_traceable():
    snapshot = dashboard_snapshot()
    incident_ids = {row["Incident"] for row in snapshot["incidents"]}
    for visit in snapshot["recommendations"]:
        assert visit["Why this visit"]
        assert set(visit["Incident IDs"].split(", ")).issubset(incident_ids)


def test_dashboard_is_deterministic():
    assert dashboard_snapshot() == dashboard_snapshot()


def test_dashboard_open_count_excludes_resolved():
    snapshot = dashboard_snapshot()
    expected = sum(row["Status"] in {"Open", "Assigned", "In Progress"} for row in snapshot["incidents"])
    assert snapshot["open_incident_count"] == expected


def test_snapshot_date_matches_generated_data():
    assert dashboard_snapshot()["as_of"] == date(2026, 11, 3)
