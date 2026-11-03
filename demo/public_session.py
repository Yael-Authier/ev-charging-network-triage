"""In-memory, per-Streamlit-session state for the public portfolio demo.

No filesystem writes. Each browser session gets its own intervention state
and change history. Session state is intentionally ephemeral.
"""
from datetime import datetime, timezone

from demo.audit_history import describe_closure_change, describe_intervention_change
from demo.interventions import initial_interventions


def new_demo_state(recommendations):
    return {"interventions": initial_interventions(recommendations), "history": []}


def append_session_event(history, station, action, details, *, timestamp=None):
    if not station or not action or not details:
        raise ValueError("History event must have a station, action and details")
    moment = timestamp or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("History timestamp requires a timezone")
    return [*history, {
        "timestamp_utc": moment.astimezone(timezone.utc).isoformat(),
        "station": station,
        "action": action,
        "details": details,
    }]


def record_visit_change(history, station, before, after):
    detail = describe_intervention_change(before, after)
    if before.get("resolved_incident_ids", []) != after.get("resolved_incident_ids", []):
        closures = describe_closure_change(before, after)
        detail = f"{detail}; {closures}" if detail else closures
    return append_session_event(history, station, "visit_updated", detail) if detail else history


def record_closure_change(history, station, before, after):
    if before.get("resolved_incident_ids", []) == after.get("resolved_incident_ids", []):
        return history
    return append_session_event(
        history, station, "incidents_confirmed",
        describe_closure_change(before, after),
    )
