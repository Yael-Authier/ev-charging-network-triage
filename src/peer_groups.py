"""Peer group assignment: grouping stations that are actually comparable.

This is a DERIVED analytical feature, computed exclusively from observed station
attributes. It lives here and not in `generator/` because the generator does not
use peer groups: the synthetic world's seasonality is defined per `site_type`,
and the peer group is the analytical approximation to it.

`src/` must never import from `generator/`.

Fallback hierarchy, frozen in the Data Generating Constitution:

    site_type x traffic_tier   (if the group has at least `min_size` stations)
        -> site_type           (if that has at least `min_size`)
        -> network             (always available)

Assignment is fully deterministic and uses no randomness.
"""

from __future__ import annotations

import pandas as pd

LEVEL_SITE_TYPE_TIER = "site_type_x_traffic_tier"
LEVEL_SITE_TYPE = "site_type"
LEVEL_NETWORK = "network"

NETWORK_GROUP_KEY = "ALL"

PEER_GROUP_COLUMNS = ["station_id", "peer_group", "peer_group_level"]


def assign_peer_groups(stations: pd.DataFrame, min_size: int) -> pd.DataFrame:
    """Assign each station to the finest peer group that meets `min_size`.

    Parameters
    ----------
    stations:
        Observed station attributes. Requires `station_id`, `site_type` and
        `traffic_tier`.
    min_size:
        Minimum stations for a group to be usable. Comes from
        `config.yml -> network.min_peer_group_size` (frozen at 4).

    Returns
    -------
    One row per station with its group key and the level that produced it.
    """
    required = {"station_id", "site_type", "traffic_tier"}
    missing = required - set(stations.columns)
    if missing:
        raise ValueError(f"stations is missing required columns: {sorted(missing)}")

    if min_size < 1:
        raise ValueError(f"min_size must be at least 1, got {min_size}")

    fine_sizes = stations.groupby(["site_type", "traffic_tier"]).size()
    coarse_sizes = stations.groupby("site_type").size()

    rows: list[dict] = []
    for station in stations.itertuples(index=False):
        fine_key = (station.site_type, station.traffic_tier)

        if fine_sizes.get(fine_key, 0) >= min_size:
            peer_group = f"{station.site_type}|{station.traffic_tier}"
            level = LEVEL_SITE_TYPE_TIER
        elif coarse_sizes.get(station.site_type, 0) >= min_size:
            peer_group = station.site_type
            level = LEVEL_SITE_TYPE
        else:
            peer_group = NETWORK_GROUP_KEY
            level = LEVEL_NETWORK

        rows.append(
            {
                "station_id": station.station_id,
                "peer_group": peer_group,
                "peer_group_level": level,
            }
        )

    frame = pd.DataFrame(rows).sort_values("station_id").reset_index(drop=True)
    return frame[PEER_GROUP_COLUMNS]


def summarise_peer_groups(assignment: pd.DataFrame) -> pd.DataFrame:
    """Group sizes and the level each group was resolved at.

    Used by notebook 03 to report how many stations ended up compared against a
    coarser reference than intended.
    """
    summary = (
        assignment.groupby(["peer_group", "peer_group_level"])
        .size()
        .reset_index(name="station_count")
    )
    return summary.sort_values(["peer_group_level", "peer_group"]).reset_index(drop=True)