"""Static world construction for the Voltora synthetic EV charging network.

Writes nothing. All output is in-memory; file writing belongs to block 3.

Information boundary
--------------------
`ObservedWorld` holds what a real operator would have and what gets written to
`data/observed/`. `LatentWorld` holds the true state of the world, written to
`data/ground_truth/`.

The split makes the boundary EXPLICIT, but it does not by itself make leakage
impossible: `World.config` carries the full configuration, including latent
sections such as `ambient_temperature`, `hardware_batch` and `conditions`. The
guarantee is layered, not absolute:

  1. separation of objects (`ObservedWorld` vs `LatentWorld`);
  2. `src/` is forbidden from importing `generator/`, enforced by a test;
  3. the file-level leakage guards added in block 4.

`World` is a generator-side object. The analytical layer never receives one: it
reads `data/observed/` and nothing else.

Random streams
--------------
Every stochastic component draws from its own named stream, derived from the
frozen seed via an explicit `spawn_key`, so a stream's values depend only on
(seed, index) and never on call order. Adding a stream later does NOT change
existing ones. `STREAM_REGISTRY` is APPEND-ONLY: never reorder or reassign.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG_PATH = REPO_ROOT / "generator" / "config.yml"
DEFAULT_NETWORK_PATH = REPO_ROOT / "generator" / "network.yml"

# Named random streams. APPEND ONLY - see module docstring.
STREAM_REGISTRY: dict[str, int] = {
    "world": 0,
    "temperature": 1,
    "conditions": 2,
    "sessions": 3,
    "heartbeats": 4,
    "tickets": 5,
    "data_quality": 6,
}

# Columns written to data/observed/stations. `operation_type` was deliberately
# dropped: nothing in the MVP uses it (see docs/04-decisions-log.md).
STATION_COLUMNS = [
    "station_id",
    "region",
    "site_type",
    "traffic_tier",
    "connector_count",
    "commissioned_at",
]

CONNECTOR_COLUMNS = [
    "connector_id",
    "station_id",
    "connector_standard",
    "rated_kw",
    "installed_at",
]

CREW_COLUMNS = ["crew_id", "region", "weekly_visit_capacity"]

# `produced_by` is GROUND TRUTH and is excluded from the observed frame.
# `typical_resolution_days` was deliberately removed: it would let a downstream
# `days_at_risk` read a resolution time off the catalogue instead of estimating
# it from observed episode history. See docs/04-decisions-log.md.
FAULT_CATALOG_COLUMNS = [
    "fault_code",
    "description",
    "field_fixable",
]

# Column names that must never appear in any observed frame.
GROUND_TRUTH_COLUMN_BLOCKLIST = {
    "produced_by",
    "batch_id",
    "hardware_batch",
    "ambient_temperature_c",
    "condition_code",
    "severity",
    "potential_sessions",
    "potential_kwh",
    "lost_sessions",
    "lost_kwh",
    "balked_sessions",
    "scenario_id",
}


# =============================================================================
# Loading
# =============================================================================

def load_yaml(path: Path) -> dict:
    """Read a YAML file into a dictionary."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_config(path: Path | None = None) -> dict:
    """Load the frozen world configuration."""
    return load_yaml(path or DEFAULT_CONFIG_PATH)


def load_network(path: Path | None = None) -> dict:
    """Load the frozen station roster."""
    return load_yaml(path or DEFAULT_NETWORK_PATH)


# =============================================================================
# Random streams
# =============================================================================

def build_streams(seed: int) -> dict[str, np.random.Generator]:
    """Build one independent generator per named stream.

    Each stream is derived with an explicit `spawn_key`, so its values depend
    only on (seed, index) and never on the order in which streams are created.
    """
    return {
        name: np.random.default_rng(
            np.random.SeedSequence(entropy=seed, spawn_key=(index,))
        )
        for name, index in STREAM_REGISTRY.items()
    }


# =============================================================================
# Observed entities
# =============================================================================

def build_stations(network: dict) -> pd.DataFrame:
    """Build the station dimension from the frozen roster.

    The roster calls the column `connectors`; the observed contract calls it
    `connector_count`. The rename happens here so the roster stays readable.
    """
    frame = pd.DataFrame(network["stations"])
    frame["commissioned_at"] = pd.to_datetime(frame["commissioned_at"])
    frame = frame.rename(columns={"connectors": "connector_count"})
    frame = frame.sort_values("station_id").reset_index(drop=True)
    return frame[STATION_COLUMNS]


def allocate_connector_specs(profile: dict, count: int) -> list[dict]:
    """Split `count` connectors across a power profile's declared shares.

    NEW DECISION 9, pre-registered before data generation: discretisation uses
    LARGEST-REMAINDER allocation. The declared shares (0.6 / 0.4) are continuous
    and connectors are not, so a rule is required; this one is deterministic and
    involves no RNG, so connector layout never depends on a random stream.

    This choice determines physical capacity, which feeds the congestion
    mechanism (L7) and therefore scenario S13. It is frozen: see
    docs/04-decisions-log.md.

    Example: a 2-connector `mixed_dc50_ac22` station gets exactly one 50 kW and
    one 22 kW connector.
    """
    specs = profile["connectors"]
    exact = [count * spec["share"] for spec in specs]
    allocation = [int(math.floor(value)) for value in exact]

    shortfall = count - sum(allocation)
    if shortfall > 0:
        # Highest fractional remainder first; ties broken by declaration order.
        order = sorted(
            range(len(specs)),
            key=lambda i: (-(exact[i] - allocation[i]), i),
        )
        for i in order[:shortfall]:
            allocation[i] += 1

    resolved: list[dict] = []
    for spec, units in zip(specs, allocation):
        for _ in range(units):
            resolved.append(
                {"connector_standard": spec["standard"], "rated_kw": spec["rated_kw"]}
            )

    # Highest-rated connectors get the lowest index, for a stable id order.
    resolved.sort(key=lambda item: (-item["rated_kw"], item["connector_standard"]))
    return resolved


def build_connectors(config: dict, stations: pd.DataFrame) -> pd.DataFrame:
    """Build the connector dimension.

    `installed_at` equals the station's `commissioned_at`: no connector
    replacement history is modelled. Consequence, documented as a limitation:
    connector age is perfectly collinear with station age.
    """
    profile_by_site_type = config["network"]["power_profile_by_site_type"]
    profiles = config["network"]["power_profiles"]

    rows: list[dict] = []
    for station in stations.itertuples(index=False):
        profile_name = profile_by_site_type[station.site_type]
        specs = allocate_connector_specs(profiles[profile_name], station.connector_count)

        for position, spec in enumerate(specs, start=1):
            rows.append(
                {
                    "connector_id": f"{station.station_id}-C{position}",
                    "station_id": station.station_id,
                    "connector_standard": spec["connector_standard"],
                    "rated_kw": spec["rated_kw"],
                    "installed_at": station.commissioned_at,
                }
            )

    frame = pd.DataFrame(rows).sort_values("connector_id").reset_index(drop=True)
    return frame[CONNECTOR_COLUMNS]


def build_crews(config: dict) -> pd.DataFrame:
    """Build the crew dimension, one row per crew and covered region."""
    rows = [
        {
            "crew_id": crew["crew_id"],
            "region": region,
            "weekly_visit_capacity": crew["weekly_visit_capacity"],
        }
        for crew in config["crews"]
        for region in crew["regions"]
    ]
    frame = pd.DataFrame(rows).sort_values(["crew_id", "region"]).reset_index(drop=True)
    return frame[CREW_COLUMNS]


def build_fault_catalog(config: dict) -> pd.DataFrame:
    """Build the OBSERVED fault catalogue.

    The `produced_by` column is ground truth and is dropped here: a ticket must
    never reveal which latent condition caused it.
    """
    frame = pd.DataFrame(config["fault_catalog"])
    frame = frame.sort_values("fault_code").reset_index(drop=True)
    return frame[FAULT_CATALOG_COLUMNS]


def latent_fault_code_map(config: dict) -> dict[str, str]:
    """GROUND TRUTH: latent condition -> operational fault code.

    Used by the generator to emit tickets. Never exposed to the analytical
    layer. `L7_congestion` is absent on purpose: it produces no ticket.
    """
    mapping: dict[str, str] = {}
    for entry in config["fault_catalog"]:
        for condition in entry["produced_by"]:
            mapping[condition] = entry["fault_code"]
    return mapping


# =============================================================================
# Latent entities
# =============================================================================

def build_hardware_batch(config: dict, stations: pd.DataFrame) -> pd.DataFrame:
    """GROUND TRUTH: which stations carry the elevated-L4 comms module batch.

    Derived from the commissioning window. `commissioned_at` IS observed, so a
    cohort analysis can discover the elevated failure rate - but the batch label
    itself is not handed to the analyst.
    """
    batch = config["hardware_batch"]
    lower, upper = (pd.Timestamp(value) for value in batch["commissioned_between"])

    members = stations.loc[
        stations["commissioned_at"].between(lower, upper), ["station_id"]
    ].copy()
    members["batch_id"] = batch["batch_id"]
    return members.sort_values("station_id").reset_index(drop=True)


def build_ambient_temperature(
    config: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """GROUND TRUTH: daily ambient temperature, one value per region per day.

    Granularity is region-day, not station-day: stations in the same region
    share the day's temperature. That is physically sensible and it keeps
    temperature a genuine common driver. Per-station i.i.d. noise would dilute
    the unobserved confounding and make the exercise easier than it should be.

    Temperature drives the L2 and L3 hazards only. It is not a cause of
    availability.
    """
    ambient = config["ambient_temperature"]
    regions = sorted(config["network"]["regions"])

    dates = pd.date_range(
        start=config["meta"]["start_date"],
        end=config["meta"]["end_date"],
        freq="D",
    )
    day_of_year = dates.dayofyear.to_numpy()

    seasonal = ambient["annual_amplitude_c"] * np.cos(
        2.0 * np.pi * (day_of_year - ambient["peak_day_of_year"]) / 365.25
    )

    # One draw for the whole grid, so values never depend on iteration order.
    noise = rng.normal(0.0, ambient["daily_noise_sd_c"], size=(len(regions), len(dates)))

    rows: list[pd.DataFrame] = []
    for position, region in enumerate(regions):
        rows.append(
            pd.DataFrame(
                {
                    "region": region,
                    "date": dates,
                    "ambient_temperature_c": (
                        ambient["annual_mean_c"]
                        + seasonal
                        + ambient["region_offset_c"][region]
                        + noise[position]
                    ),
                }
            )
        )

    frame = pd.concat(rows, ignore_index=True)
    return frame.sort_values(["region", "date"]).reset_index(drop=True)


# =============================================================================
# Assembly
# =============================================================================

@dataclass(frozen=True)
class ObservedWorld:
    """Entities a real operator would have. Written to data/observed/."""

    stations: pd.DataFrame
    connectors: pd.DataFrame
    crews: pd.DataFrame
    fault_catalog: pd.DataFrame

    def frames(self) -> dict[str, pd.DataFrame]:
        """Every observed frame, keyed by its table name."""
        return {
            "stations": self.stations,
            "connectors": self.connectors,
            "crews": self.crews,
            "fault_catalog": self.fault_catalog,
        }


@dataclass(frozen=True)
class LatentWorld:
    """True state of the world. Written to data/ground_truth/.

    OFF LIMITS to sql/, notebooks/01-03, src/policy.py and app/.
    """

    hardware_batch: pd.DataFrame
    ambient_temperature: pd.DataFrame
    fault_code_map: dict[str, str]

    def frames(self) -> dict[str, pd.DataFrame]:
        """Every latent frame, keyed by its table name."""
        return {
            "hardware_batch": self.hardware_batch,
            "ambient_temperature": self.ambient_temperature,
        }


@dataclass(frozen=True)
class World:
    """The static world: observed entities, latent entities, and its streams."""

    observed: ObservedWorld
    latent: LatentWorld
    config: dict
    streams: dict[str, np.random.Generator]

    @property
    def seed(self) -> int:
        """The frozen seed this world was built from."""
        return self.config["meta"]["seed"]


def build_world(
    config_path: Path | None = None,
    network_path: Path | None = None,
    seed: int | None = None,
) -> World:
    """Build the complete static world.

    Writes nothing. `seed` overrides the frozen seed for reproducibility tests
    only; production generation always uses the value in `config.yml`.
    """
    config = load_config(config_path)
    network = load_network(network_path)

    effective_seed = config["meta"]["seed"] if seed is None else seed
    streams = build_streams(effective_seed)

    stations = build_stations(network)
    connectors = build_connectors(config, stations)

    observed = ObservedWorld(
        stations=stations,
        connectors=connectors,
        crews=build_crews(config),
        fault_catalog=build_fault_catalog(config),
    )

    latent = LatentWorld(
        hardware_batch=build_hardware_batch(config, stations),
        ambient_temperature=build_ambient_temperature(config, streams["temperature"]),
        fault_code_map=latent_fault_code_map(config),
    )

    # The seed actually used is recorded, so an overridden seed cannot silently
    # masquerade as the frozen one.
    effective_config = {**config, "meta": {**config["meta"], "seed": effective_seed}}

    return World(
        observed=observed,
        latent=latent,
        config=effective_config,
        streams=streams,
    )