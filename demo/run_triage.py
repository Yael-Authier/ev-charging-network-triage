"""Run the provisional Voltora triage demo from the command line.

Usage:
    python -m demo.run_triage

All incidents are synthetic. Rankings are provisional, not ERV.
"""
from __future__ import annotations

from datetime import date

from demo.generate_snapshot import AS_OF, generate_rows
from src.demo_triage import Incident, rank_visits


def main() -> None:
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
    queue = rank_visits(incidents, as_of=AS_OF, capacity=5)
    print(f"Voltora | Synthetic snapshot {AS_OF} | {len(rows)} incidents")
    print("PROVISIONAL five-visit priority queue (not validated ERV)")
    for item in queue:
        print(
            f"{item.rank}. {item.station_id} [{item.region}] "
            f"score={item.score} | {', '.join(item.reason_codes)} "
            f"| incidents={', '.join(item.incident_ids)}"
        )


if __name__ == "__main__":
    main()
