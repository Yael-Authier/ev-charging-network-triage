"""Local, single-user persistence for synthetic intervention records.

The JSON file is intentionally local and excluded from Git. This is not
multi-user storage, authentication, or a production database.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from demo.interventions import ALLOWED_STATUSES, CREWS, initial_interventions

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "demo" / "interventions.local.json"


def save_interventions(state: dict[str, dict], path: Path = DEFAULT_PATH) -> None:
    """Atomically save the current demo state to a local JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "interventions": {
            station: {
                **record,
                "scheduled_for": (
                    record["scheduled_for"].isoformat()
                    if record["scheduled_for"] is not None else None
                ),
            }
            for station, record in state.items()
        },
    }
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".interventions-", suffix=".tmp", delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def load_interventions(
    recommendations: list[dict],
    path: Path = DEFAULT_PATH,
) -> dict[str, dict]:
    """Restore saved visits, validating against the current recommendation set.

    Invalid or corrupted local files raise ValueError rather than silently
    losing the user's changes.
    """
    initial = initial_interventions(recommendations)
    path = Path(path)
    if not path.exists():
        return initial
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["schema_version"] != 1:
            raise ValueError("Unsupported local storage version")
        saved = data["interventions"]
        if not isinstance(saved, dict):
            raise ValueError("Invalid intervention storage")
        for station, record in saved.items():
            if station not in initial:
                continue
            if not isinstance(record, dict):
                raise ValueError("Invalid intervention record")
            crew, status = record["crew"], record["status"]
            if crew not in CREWS or status not in ALLOWED_STATUSES:
                raise ValueError("Invalid saved crew or status")
            scheduled = record.get("scheduled_for")
            scheduled_date = date.fromisoformat(scheduled) if scheduled else None
            note = record.get("resolution_note", "")
            if not isinstance(note, str):
                raise ValueError("Invalid resolution note")
            if status in {"Scheduled", "In progress", "Resolved"} and crew == "Unassigned":
                raise ValueError("Invalid saved assignment")
            if status in {"Scheduled", "In progress"} and scheduled_date is None:
                raise ValueError("Missing saved visit date")
            if status == "Resolved" and not note.strip():
                raise ValueError("Missing saved resolution note")
            closures = record.get("resolved_incident_ids", [])
            if not isinstance(closures, list) or any(not isinstance(item, str) for item in closures):
                raise ValueError("Invalid saved incident closures")
            if len(closures) != len(set(closures)):
                raise ValueError("Duplicate saved incident closures")
            if closures and status != "Resolved":
                raise ValueError("Incident closures require a resolved visit")
            initial[station].update(
                crew=crew, status=status,
                scheduled_for=scheduled_date,
                resolution_note=note,
                resolved_incident_ids=closures,
            )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read local interventions: {exc}") from exc
    return initial
