"""Explicit incident closure overlay for the local portfolio demo."""


def incident_statuses(incidents, interventions):
    """Return display records with explicitly closed incident IDs only."""
    closed = set()
    for intervention in interventions.values():
        if intervention["status"] == "Resolved":
            closed.update(intervention.get("resolved_incident_ids", []))
    result = []
    for incident in incidents:
        record = dict(incident)
        if record["Incident"] in closed:
            record["Status"] = "Resolved"
        result.append(record)
    return result


def select_incident_closures(interventions, station_id, selected_ids, allowed_ids):
    """Close only selected incidents for a resolved station visit."""
    if station_id not in interventions:
        raise ValueError("Unknown station")
    if interventions[station_id]["status"] != "Resolved":
        raise ValueError("Resolve the intervention before closing incidents")
    if len(selected_ids) != len(set(selected_ids)) or not set(selected_ids).issubset(set(allowed_ids)):
        raise ValueError("Invalid incident selection")
    updated = {key: dict(value) for key, value in interventions.items()}
    updated[station_id]["resolved_incident_ids"] = list(selected_ids)
    return updated
