"""Observed-only presentation model for the Voltora portfolio dashboard."""
from __future__ import annotations

from datetime import date

from demo.generate_snapshot import AS_OF, generate_rows
from src.demo_triage import Incident, rank_visits

REASON_LABELS = {
    "SEVERITY_LOW": "Low-severity fault",
    "SEVERITY_MEDIUM": "Medium-severity fault",
    "SEVERITY_HIGH": "High-severity fault",
    "SEVERITY_CRITICAL": "Critical fault",
    "OPEN_7_PLUS_DAYS": "Open for 7+ days",
    "MULTIPLE_CONNECTORS_AFFECTED": "Multiple connectors affected",
    "MULTIPLE_OPEN_INCIDENTS": "Multiple open incidents",
}


def dashboard_snapshot(*, as_of: date = AS_OF) -> dict:
    """Build a deterministic dashboard view from synthetic observations."""
    rows = generate_rows()
    incidents = [
        Incident(
            incident_id=str(row["incident_id"]),
            station_id=str(row["station_id"]),
            region=str(row["region"]),
            fault_code=str(row["fault_code"]),
            severity=str(row["severity"]),
            opened_on=date.fromisoformat(str(row["opened_on"])),
            estimated_affected_connectors=int(row["estimated_affected_connectors"]),
            status=str(row["status"]),
        )
        for row in rows
    ]
    queue = rank_visits(incidents, as_of=as_of, capacity=5)
    recommendations = [
        {
            "Rank": rec.rank,
            "Station": rec.station_id,
            "Region": rec.region.title(),
            "Priority score": rec.score,
            "Why this visit": " · ".join(REASON_LABELS.get(reason, reason) for reason in rec.reason_codes),
            "Incident IDs": ", ".join(rec.incident_ids),
        }
        for rec in queue
    ]
    incident_table = [
        {
            "Incident": inc.incident_id,
            "Station": inc.station_id,
            "Region": inc.region.title(),
            "Fault": inc.fault_code,
            "Severity": inc.severity.title(),
            "Opened": inc.opened_on.isoformat(),
            "Days open": (as_of - inc.opened_on).days,
            "Connectors affected": inc.estimated_affected_connectors,
            "Status": inc.status.replace("_", " ").title(),
        }
        for inc in incidents
    ]
    return {
        "as_of": as_of,
        "station_count": 40,
        "incident_count": len(incidents),
        "open_incident_count": sum(inc.status in {"open", "assigned", "in_progress"} for inc in incidents),
        "affected_station_count": len({inc.station_id for inc in incidents if inc.status in {"open", "assigned", "in_progress"}}),
        "recommendations": recommendations,
        "incidents": incident_table,
    }
