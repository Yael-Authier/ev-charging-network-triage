"""Tests for the static world.

These cover three things: that the world matches the frozen configuration, that
the information boundary holds, and that the build is reproducible. Several are
drift detectors: they fail if a later change silently contradicts the Data
Generating Constitution.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from generator import world as world_module


# =============================================================================
# Scope: this block writes nothing and implements no metrics
# =============================================================================

def test_world_builds_without_writing_any_data_files(repo_root, world):
    """Block 2 is a pure library: no file may appear under data/."""
    for folder in ("observed", "ground_truth"):
        contents = sorted(
            path.name
            for path in (repo_root / "data" / folder).iterdir()
            if path.name != ".gitkeep"
        )
        assert contents == [], f"data/{folder} is not empty: {contents}"


def test_world_module_implements_no_metric_or_policy_logic(repo_root):
    """Scope guard.

    Availability, failure rates, power-per-minute, coverage and the ERV belong
    to blocks 5 and 7. If any of those words show up here, this block has grown
    beyond its remit and the freeze order has been broken.
    """
    source = (repo_root / "generator" / "world.py").read_text(encoding="utf-8")
    lowered = source.lower()

    # Whole-word matching only: a plain substring check would flag "erv" inside
    # "observed", which appears legitimately all over this module.
    forbidden = [
        "uptime",
        "failure_rate",
        "kwh_per_minute",
        "coverage_pct",
        "erv",
        "erv_kwh",
        "intervention_queue",
        "reason_code",
    ]
    found = [
        token
        for token in forbidden
        if re.search(rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])", lowered)
    ]
    assert found == [], f"world.py implements out-of-scope logic: {found}"


# =============================================================================
# Stations
# =============================================================================

def test_stations_frame_matches_the_observed_contract(world):
    assert list(world.observed.stations.columns) == world_module.STATION_COLUMNS


def test_operation_type_is_absent_from_the_contract(world):
    """Dropped deliberately: nothing in the MVP uses it."""
    assert "operation_type" not in world.observed.stations.columns


def test_station_count_and_ids_match_the_roster(world, stations):
    frame = world.observed.stations
    assert len(frame) == len(stations)
    assert set(frame["station_id"]) == {s["station_id"] for s in stations}
    assert frame["station_id"].is_unique


def test_station_attributes_match_the_roster(world, stations):
    expected = {s["station_id"]: s for s in stations}
    for row in world.observed.stations.itertuples(index=False):
        source = expected[row.station_id]
        assert row.region == source["region"]
        assert row.site_type == source["site_type"]
        assert row.traffic_tier == source["traffic_tier"]
        assert row.connector_count == source["connectors"]


def test_st015_still_matches_the_s13_congestion_premise(world):
    """Drift detector for scenario S13.

    S13 places sustained congestion on ST-015 precisely because it is an
    `urban / high` station with only TWO connectors. A highway/high station
    cannot congest at the configured parameters. If the roster changes and
    ST-015 gains connectors or changes site type, S13 becomes inert and this
    test is the warning.
    """
    row = world.observed.stations.set_index("station_id").loc["ST-015"]
    assert row["site_type"] == "urban"
    assert row["traffic_tier"] == "high"
    assert row["connector_count"] == 2


# =============================================================================
# Connectors
# =============================================================================

def test_connector_total_matches_the_roster(world, stations):
    expected_total = sum(s["connectors"] for s in stations)
    assert len(world.observed.connectors) == expected_total


def test_connector_frame_matches_the_observed_contract(world):
    assert list(world.observed.connectors.columns) == world_module.CONNECTOR_COLUMNS


def test_connector_count_per_station_matches_the_roster(world):
    counts = world.observed.connectors.groupby("station_id").size()
    declared = world.observed.stations.set_index("station_id")["connector_count"]
    pd.testing.assert_series_equal(
        counts.sort_index().rename("connector_count"),
        declared.sort_index(),
        check_dtype=False,
    )


def test_connector_ids_are_unique_and_derived_from_the_station_id(world):
    frame = world.observed.connectors
    assert frame["connector_id"].is_unique
    for row in frame.itertuples(index=False):
        assert row.connector_id.startswith(f"{row.station_id}-C")


def test_connector_ratings_only_use_declared_values(world):
    declared = {
        spec["rated_kw"]
        for profile in world.config["network"]["power_profiles"].values()
        for spec in profile["connectors"]
    }
    assert set(world.observed.connectors["rated_kw"]) <= declared


def test_connector_power_mix_follows_the_declared_profile(world):
    """A 2-connector mixed station must get exactly one 50 kW and one 22 kW."""
    stations = world.observed.stations.set_index("station_id")
    two_connector_urban = stations[
        (stations["site_type"] == "urban") & (stations["connector_count"] == 2)
    ].index

    assert len(two_connector_urban) > 0, "expected at least one 2-connector urban site"

    for station_id in two_connector_urban:
        ratings = sorted(
            world.observed.connectors.loc[
                world.observed.connectors["station_id"] == station_id, "rated_kw"
            ]
        )
        assert ratings == [22, 50], f"{station_id} has ratings {ratings}"


def test_dc150_sites_are_single_standard(world):
    stations = world.observed.stations.set_index("station_id")
    dc_sites = stations[stations["site_type"].isin(["highway", "fleet_depot"])].index
    subset = world.observed.connectors[
        world.observed.connectors["station_id"].isin(dc_sites)
    ]
    assert set(subset["rated_kw"]) == {150}


def test_connector_installed_at_equals_station_commissioning(world):
    """No connector replacement history is modelled.

    Documented limitation: connector age is perfectly collinear with station
    age, and no MVP analysis tries to separate the two.
    """
    merged = world.observed.connectors.merge(
        world.observed.stations[["station_id", "commissioned_at"]],
        on="station_id",
        how="left",
    )
    assert (merged["installed_at"] == merged["commissioned_at"]).all()


# =============================================================================
# Crews
# =============================================================================

def test_crews_frame_matches_config(world):
    frame = world.observed.crews
    assert list(frame.columns) == world_module.CREW_COLUMNS

    declared_pairs = {
        (crew["crew_id"], region)
        for crew in world.config["crews"]
        for region in crew["regions"]
    }
    assert set(zip(frame["crew_id"], frame["region"])) == declared_pairs


def test_crew_capacity_is_not_double_counted_across_regions(world):
    """Capacity is per crew, not per crew-region row."""
    per_crew = world.observed.crews.groupby("crew_id")["weekly_visit_capacity"].max()
    assert per_crew.sum() == world.config["backtest"]["weekly_visit_capacity"]


# =============================================================================
# Fault catalogue and the information boundary
# =============================================================================

def test_fault_catalog_is_exposed_without_the_latent_mapping(world):
    frame = world.observed.fault_catalog
    assert list(frame.columns) == world_module.FAULT_CATALOG_COLUMNS
    assert "produced_by" not in frame.columns


def test_fault_catalog_declares_no_resolution_time(world):
    """`typical_resolution_days` was removed on purpose.

    Nothing in the MVP needs it, and publishing it would let the ERV's
    `days_at_risk` read a resolution time straight off the catalogue instead of
    estimating it from observed episode history. That would shortcut the
    analytical work and anchor the estimate on a generator parameter.
    """
    assert "typical_resolution_days" not in world.observed.fault_catalog.columns
    for entry in world.config["fault_catalog"]:
        assert "typical_resolution_days" not in entry


def test_fault_catalog_covers_every_condition_except_congestion(world):
    mapped = set(world.latent.fault_code_map)
    declared = set(world.config["conditions"])

    assert "L7_congestion" not in mapped, "congestion must not produce a ticket"
    assert mapped == declared - {"L7_congestion"}


def test_low_power_code_hides_both_a_fixable_and_a_non_fixable_cause(world):
    """The central trap of the catalogue must be present.

    FC-LOW-POWER covers L3 (field fixable) and L6 (not field fixable) and still
    declares field_fixable: true. That is what forces the analyst to find the
    time-of-day discriminator instead of trusting the catalogue.
    """
    mapping = world.latent.fault_code_map
    assert mapping["L3_power_derate"] == "FC-LOW-POWER"
    assert mapping["L6_upstream_grid_limit"] == "FC-LOW-POWER"

    entry = world.observed.fault_catalog.set_index("fault_code").loc["FC-LOW-POWER"]
    assert bool(entry["field_fixable"]) is True

    conditions = world.config["conditions"]
    assert conditions["L3_power_derate"]["field_fixable"] is True
    assert conditions["L6_upstream_grid_limit"]["field_fixable"] is False


def test_no_observed_frame_carries_a_ground_truth_column(world):
    for name, frame in world.observed.frames().items():
        leaked = set(frame.columns) & world_module.GROUND_TRUTH_COLUMN_BLOCKLIST
        assert leaked == set(), f"observed frame `{name}` leaks {sorted(leaked)}"


# =============================================================================
# Latent world
# =============================================================================

def test_hardware_batch_is_latent_and_has_nine_cross_cutting_members(world):
    members = world.latent.hardware_batch

    assert len(members) == world.config["hardware_batch"]["expected_member_count"] == 9
    assert set(members["batch_id"]) == {world.config["hardware_batch"]["batch_id"]}

    site_types = set(
        world.observed.stations.set_index("station_id")
        .loc[members["station_id"], "site_type"]
    )
    assert len(site_types) >= 3, f"batch is not cross-cutting: {site_types}"

    # And it must not be reachable from the observed side.
    assert "batch_id" not in world.observed.stations.columns


def test_ambient_temperature_is_latent_and_region_daily(world):
    frame = world.latent.ambient_temperature
    regions = world.config["network"]["regions"]

    dates = pd.date_range(
        start=world.config["meta"]["start_date"],
        end=world.config["meta"]["end_date"],
        freq="D",
    )

    assert list(frame.columns) == ["region", "date", "ambient_temperature_c"]
    assert len(frame) == len(regions) * len(dates)
    assert set(frame["region"]) == set(regions)

    per_region = frame.groupby("region").size()
    assert (per_region == len(dates)).all()


def test_ambient_temperature_values_are_physically_plausible(world):
    values = world.latent.ambient_temperature["ambient_temperature_c"]
    assert values.between(-25.0, 55.0).all()
    assert values.std() > 1.0, "temperature has no variation at all"


def test_ambient_temperature_is_seasonal(world):
    """Summer must be warmer than winter, or it is not a seasonal driver."""
    frame = world.latent.ambient_temperature.copy()
    frame["month"] = frame["date"].dt.month

    summer = frame.loc[frame["month"].isin([7, 8]), "ambient_temperature_c"].mean()
    winter = frame.loc[frame["month"].isin([1, 2]), "ambient_temperature_c"].mean()
    assert summer > winter + 5.0


# =============================================================================
# Reproducibility
# =============================================================================

def test_world_is_reproducible_for_the_frozen_seed():
    first = world_module.build_world()
    second = world_module.build_world()

    for name, frame in first.observed.frames().items():
        pd.testing.assert_frame_equal(frame, second.observed.frames()[name])
    for name, frame in first.latent.frames().items():
        pd.testing.assert_frame_equal(frame, second.latent.frames()[name])


def test_structure_is_seed_independent_but_temperature_is_not():
    """Station and connector layout come from the roster, not from an RNG."""
    frozen = world_module.build_world()
    alternate = world_module.build_world(seed=999)

    pd.testing.assert_frame_equal(
        frozen.observed.stations, alternate.observed.stations
    )
    pd.testing.assert_frame_equal(
        frozen.observed.connectors, alternate.observed.connectors
    )

    assert not np.allclose(
        frozen.latent.ambient_temperature["ambient_temperature_c"],
        alternate.latent.ambient_temperature["ambient_temperature_c"],
    )


def test_streams_are_independent_of_creation_order():
    """Adding a stream later must not disturb the existing ones.

    Each stream is derived from an explicit spawn_key, so its values depend only
    on (seed, index). This is what keeps already-committed results reproducible
    when block 3 adds its own streams.
    """
    seed = 20260909
    streams = world_module.build_streams(seed)
    baseline = streams["temperature"].normal(size=5)

    rebuilt = np.random.default_rng(
        np.random.SeedSequence(
            entropy=seed, spawn_key=(world_module.STREAM_REGISTRY["temperature"],)
        )
    ).normal(size=5)

    assert np.allclose(baseline, rebuilt)


def test_stream_registry_indices_are_unique_and_contiguous():
    indices = sorted(world_module.STREAM_REGISTRY.values())
    assert indices == list(range(len(indices)))


def test_effective_seed_is_recorded_on_the_world(world):
    assert world.seed == world.config["meta"]["seed"]
    assert world_module.build_world(seed=999).seed == 999


# =============================================================================
# Connector allocation, in isolation
# =============================================================================

@pytest.mark.parametrize(
    "count, expected",
    [
        (2, [50, 22]),
        (3, [50, 50, 22]),
        (4, [50, 50, 22, 22]),
    ],
)
def test_largest_remainder_allocation_is_deterministic(world, count, expected):
    profile = world.config["network"]["power_profiles"]["mixed_dc50_ac22"]
    specs = world_module.allocate_connector_specs(profile, count)
    assert [spec["rated_kw"] for spec in specs] == expected