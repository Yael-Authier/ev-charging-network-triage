"""Tests for the provisional portfolio triage, separate from formal ERV."""
from datetime import date, timedelta

import pytest

from src.demo_triage import Incident, rank_visits
from demo.generate_snapshot import AS_OF, generate_rows


def incident(number, station, severity="medium", days=2, affected=1, status="open"):
    return Incident(
        incident_id=f"INC-{number}", station_id=station, region="north",
        fault_code="FC-CONN-DOWN", severity=severity,
        opened_on=AS_OF - timedelta(days=days),
        estimated_affected_connectors=affected, status=status,
    )


def test_capacity_and_unique_stations():
    rows = [incident(i, f"ST-{i:03d}") for i in range(1, 10)]
    rows.append(incident(20, "ST-001", "critical"))
    result = rank_visits(rows, as_of=AS_OF)
    assert len(result) == 5
    assert len({r.station_id for r in result}) == 5
    assert result[0].station_id == "ST-001"


def test_reasons_explain_ranking():
    rows = [incident(1, "ST-001", "critical", days=10, affected=3)]
    result = rank_visits(rows, as_of=AS_OF)
    assert result[0].reason_codes == (
        "SEVERITY_CRITICAL", "OPEN_7_PLUS_DAYS", "MULTIPLE_CONNECTORS_AFFECTED"
    )


def test_resolved_incidents_are_not_ranked():
    assert rank_visits([incident(1, "ST-001", status="resolved")], as_of=AS_OF) == []


def test_ties_are_deterministic():
    rows = [incident(1, "ST-009"), incident(2, "ST-001")]
    assert [r.station_id for r in rank_visits(rows, as_of=AS_OF)] == ["ST-001", "ST-009"]


def test_future_incident_is_rejected():
    with pytest.raises(ValueError):
        rank_visits([incident(1, "ST-001", days=-1)], as_of=AS_OF)


def test_negative_capacity_is_rejected():
    with pytest.raises(ValueError):
        rank_visits([], as_of=AS_OF, capacity=-1)


def test_snapshot_reproducible_and_observed_only():
    first, second = generate_rows(), generate_rows()
    assert first == second
    assert len(first) > 0
    assert len({r["station_id"] for r in first}) <= 40
    assert all(r["opened_on"] <= AS_OF.isoformat() for r in first)
    forbidden = {"condition_code", "lost_kwh", "scenario_id", "ambient_temperature_c"}
    assert not (forbidden & set(first[0]))
