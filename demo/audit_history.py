"""Local append-only-style audit log for the single-user fictional demo.

Events are stored in a separate JSON file. The timestamp is generated when
the user saves a change, not inferred from the synthetic snapshot date.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[1] / "demo" / "history.local.json"


def read_history(path: Path = DEFAULT_HISTORY_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read local history: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("Invalid local history format")
    for event in data:
        if not isinstance(event, dict) or not all(
            isinstance(event.get(field), str)
            for field in ("timestamp_utc", "station", "action", "details")
        ):
            raise ValueError("Invalid local history event")
    return data


def record_event(
    station: str,
    action: str,
    details: str,
    path: Path = DEFAULT_HISTORY_PATH,
    *,
    timestamp: datetime | None = None,
) -> dict:
    """Write an event with an atomic file replacement, preserving older events."""
    if not station or not action or not details:
        raise ValueError("Audit event requires station, action and details")
    path = Path(path)
    events = read_history(path)
    moment = timestamp or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("Audit timestamp must include a timezone")
    event = {
        "timestamp_utc": moment.astimezone(timezone.utc).isoformat(),
        "station": station,
        "action": action,
        "details": details,
    }
    events.append(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".history-", suffix=".tmp", delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(events, handle, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return event


def describe_intervention_change(before: dict, after: dict) -> str:
    fields = ("crew", "status", "scheduled_for", "resolution_note")
    changes = []
    for field in fields:
        if before.get(field) != after.get(field):
            changes.append(f"{field}: {before.get(field)!s} -> {after.get(field)!s}")
    return "; ".join(changes)


def describe_closure_change(before: dict, after: dict) -> str:
    previous = set(before.get("resolved_incident_ids", []))
    current = set(after.get("resolved_incident_ids", []))
    added = ", ".join(sorted(current - previous)) or "none"
    removed = ", ".join(sorted(previous - current)) or "none"
    return f"Confirmed closures added: {added}; removed: {removed}"
