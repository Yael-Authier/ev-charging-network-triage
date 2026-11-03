"""Demo-only intervention workflow; no persistent backend or real dispatch."""
from __future__ import annotations

from datetime import date

ALLOWED_STATUSES = ("Pending", "Scheduled", "In progress", "Resolved", "Blocked")
CREWS = ("Unassigned", "North crew", "Central crew", "Coast crew")


def initial_interventions(recommendations: list[dict]) -> dict[str, dict]:
    """One intervention per recommended station, keyed by station ID."""
    return {
        item["Station"]: {
            "station_id": item["Station"],
            "rank": item["Rank"],
            "crew": "Unassigned",
            "status": "Pending",
            "scheduled_for": None,
            "resolution_note": "",
        }
        for item in recommendations
    }


def update_intervention(
    interventions: dict[str, dict],
    station_id: str,
    *,
    crew: str,
    status: str,
    scheduled_for: date | None,
    resolution_note: str,
) -> dict[str, dict]:
    """Validate and return a new workflow state without mutating the original."""
    if station_id not in interventions:
        raise ValueError("Unknown recommended station")
    if crew not in CREWS:
        raise ValueError("Unknown crew")
    if status not in ALLOWED_STATUSES:
        raise ValueError("Unknown status")
    if status in {"Scheduled", "In progress", "Resolved"} and crew == "Unassigned":
        raise ValueError("Assign a crew before scheduling or progressing a visit")
    if status in {"Scheduled", "In progress"} and scheduled_for is None:
        raise ValueError("A scheduled date is required")
    if status == "Resolved" and not resolution_note.strip():
        raise ValueError("A resolution note is required")
    updated = {key: dict(value) for key, value in interventions.items()}
    updated[station_id].update(
        crew=crew,
        status=status,
        scheduled_for=scheduled_for,
        resolution_note=resolution_note.strip(),
        resolved_incident_ids=(
            list(updated[station_id].get("resolved_incident_ids", []))
            if status == "Resolved" else []
        ),
    )
    return updated


def intervention_metrics(interventions: dict[str, dict], *, as_of: date) -> dict[str, int]:
    values = list(interventions.values())
    return {
        "planned": len(values),
        "assigned": sum(item["crew"] != "Unassigned" for item in values),
        "resolved": sum(item["status"] == "Resolved" for item in values),
        "blocked": sum(item["status"] == "Blocked" for item in values),
        "overdue": sum(
            item["status"] not in {"Resolved", "Blocked"}
            and item["scheduled_for"] is not None
            and item["scheduled_for"] < as_of
            for item in values
        ),
    }
