"""Explainable operational triage for the portfolio demo.

This module uses only observed-style synthetic incident fields. It does not
depend on synthetic-world internals, use latent truth, or implement formal ERV.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 55, "critical": 80}
STATUS_OPEN = {"open", "assigned", "in_progress"}


@dataclass(frozen=True)
class Incident:
    incident_id: str
    station_id: str
    region: str
    fault_code: str
    severity: str
    opened_on: date
    estimated_affected_connectors: int
    status: str = "open"

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_POINTS:
            raise ValueError(f"Unsupported severity: {self.severity}")
        if self.estimated_affected_connectors < 0:
            raise ValueError("Affected connectors cannot be negative")
        if self.status not in STATUS_OPEN | {"resolved", "blocked"}:
            raise ValueError(f"Unsupported status: {self.status}")


@dataclass(frozen=True)
class Recommendation:
    rank: int
    station_id: str
    region: str
    score: int
    reason_codes: tuple[str, ...]
    incident_ids: tuple[str, ...]


def rank_visits(
    incidents: Iterable[Incident],
    *,
    as_of: date,
    capacity: int = 5,
) -> list[Recommendation]:
    """Rank distinct stations; each station consumes at most one visit slot.

    This is a transparent *provisional* heuristic, not a validated estimate
    of recovered energy or the project's preregistered ERV policy.
    """
    if capacity < 0:
        raise ValueError("Capacity cannot be negative")
    by_station: dict[str, list[Incident]] = {}
    for incident in incidents:
        if incident.status not in STATUS_OPEN:
            continue
        if incident.opened_on > as_of:
            raise ValueError(f"Incident {incident.incident_id} opens after as_of")
        by_station.setdefault(incident.station_id, []).append(incident)

    candidates: list[tuple[int, str, str, tuple[str, ...], tuple[str, ...]]] = []
    for station_id, group in by_station.items():
        regions = {item.region for item in group}
        if len(regions) != 1:
            raise ValueError(f"Inconsistent region for {station_id}")
        worst = max(group, key=lambda item: SEVERITY_POINTS[item.severity])
        oldest_days = max((as_of - item.opened_on).days for item in group)
        affected = max(item.estimated_affected_connectors for item in group)
        age_points = min(oldest_days, 14)
        connector_points = min(affected, 4) * 5
        repeat_points = min(len(group) - 1, 3) * 5
        score = SEVERITY_POINTS[worst.severity] + age_points + connector_points + repeat_points
        reasons = [f"SEVERITY_{worst.severity.upper()}"]
        if oldest_days >= 7:
            reasons.append("OPEN_7_PLUS_DAYS")
        if affected >= 2:
            reasons.append("MULTIPLE_CONNECTORS_AFFECTED")
        if len(group) > 1:
            reasons.append("MULTIPLE_OPEN_INCIDENTS")
        candidates.append((
            score, station_id, worst.region, tuple(reasons),
            tuple(sorted(item.incident_id for item in group)),
        ))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [
        Recommendation(rank=i, station_id=station_id, region=region,
                       score=score, reason_codes=reasons, incident_ids=ids)
        for i, (score, station_id, region, reasons, ids)
        in enumerate(candidates[:capacity], start=1)
    ]

