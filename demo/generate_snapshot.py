"""Create a reproducible, explicitly fictional incident snapshot.

Run: python -m demo.generate_snapshot
Uses the existing observed station roster only. No latent world data.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo" / "incidents.csv"
AS_OF = date(2026, 11, 3)
FAULT_CODES = ("FC-CONN-DOWN", "FC-CHG-ABORT", "FC-LOW-POWER", "FC-NO-COMMS")
SEVERITIES = ("low", "medium", "high", "critical")


def generate_rows(seed: int = 20261103) -> list[dict[str, str | int]]:
    rng = random.Random(seed)
    network = yaml.safe_load((ROOT / "generator" / "network.yml").read_text(encoding="utf-8"))
    stations = network["stations"]
    rows: list[dict[str, str | int]] = []
    incident_number = 1
    for station in stations:
        # Some stations have no incidents; some have repeated open incidents.
        count = rng.choices((0, 1, 2), weights=(2, 5, 2), k=1)[0]
        for _ in range(count):
            rows.append({
                "incident_id": f"INC-{incident_number:04d}",
                "station_id": station["station_id"],
                "region": station["region"],
                "fault_code": rng.choice(FAULT_CODES),
                "severity": rng.choices(SEVERITIES, weights=(2, 4, 3, 1), k=1)[0],
                "opened_on": (AS_OF - timedelta(days=rng.randint(0, 20))).isoformat(),
                "estimated_affected_connectors": rng.randint(1, station["connectors"]),
                "status": rng.choices(("open", "assigned", "resolved"), weights=(7, 2, 1), k=1)[0],
            })
            incident_number += 1
    return rows


def main() -> None:
    rows = generate_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "incident_id", "station_id", "region", "fault_code", "severity",
            "opened_on", "estimated_affected_connectors", "status",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic incidents to {OUTPUT}")


if __name__ == "__main__":
    main()
