"""Tests for peer group assignment, including the frozen fallback hierarchy."""

from __future__ import annotations

import pandas as pd

from src import peer_groups


def _roster(records: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Build a minimal stations frame from (station_id, site_type, tier)."""
    return pd.DataFrame(
        records, columns=["station_id", "site_type", "traffic_tier"]
    )


# =============================================================================
# The frozen threshold
# =============================================================================

def test_min_peer_group_size_is_four(config):
    """Drift detector for the value frozen in the constitution."""
    assert config["network"]["min_peer_group_size"] == 4


# =============================================================================
# The real roster
# =============================================================================

def test_real_roster_yields_eight_full_groups_at_the_finest_level(world, config):
    assignment = peer_groups.assign_peer_groups(
        world.observed.stations, config["network"]["min_peer_group_size"]
    )

    assert len(assignment) == len(world.observed.stations)
    assert set(assignment["peer_group_level"]) == {peer_groups.LEVEL_SITE_TYPE_TIER}

    sizes = assignment.groupby("peer_group").size()
    assert len(sizes) == 8
    assert (sizes == config["network"]["expected_peer_group_size"]).all()


def test_every_station_receives_exactly_one_group(world, config):
    assignment = peer_groups.assign_peer_groups(
        world.observed.stations, config["network"]["min_peer_group_size"]
    )
    assert assignment["station_id"].is_unique
    assert set(assignment["station_id"]) == set(world.observed.stations["station_id"])
    assert assignment["peer_group"].notna().all()


def test_summary_reports_group_sizes_and_levels(world, config):
    assignment = peer_groups.assign_peer_groups(
        world.observed.stations, config["network"]["min_peer_group_size"]
    )
    summary = peer_groups.summarise_peer_groups(assignment)

    assert list(summary.columns) == ["peer_group", "peer_group_level", "station_count"]
    assert summary["station_count"].sum() == len(world.observed.stations)


# =============================================================================
# The fallback hierarchy, exercised on synthetic rosters
# =============================================================================

def test_fallback_to_site_type_when_a_fine_group_is_too_small():
    """urban/high has 2 stations, but urban as a whole has 6."""
    roster = _roster(
        [
            ("ST-001", "urban", "high"),
            ("ST-002", "urban", "high"),
            ("ST-003", "urban", "standard"),
            ("ST-004", "urban", "standard"),
            ("ST-005", "urban", "standard"),
            ("ST-006", "urban", "standard"),
        ]
    )
    assignment = peer_groups.assign_peer_groups(roster, min_size=4).set_index(
        "station_id"
    )

    assert assignment.loc["ST-001", "peer_group_level"] == peer_groups.LEVEL_SITE_TYPE
    assert assignment.loc["ST-001", "peer_group"] == "urban"

    # The tier group that IS big enough stays at the finest level.
    assert (
        assignment.loc["ST-003", "peer_group_level"]
        == peer_groups.LEVEL_SITE_TYPE_TIER
    )
    assert assignment.loc["ST-003", "peer_group"] == "urban|standard"


def test_fallback_to_network_when_a_site_type_is_too_small():
    """mall has 2 stations in total, so neither level is usable."""
    roster = _roster(
        [
            ("ST-001", "mall", "high"),
            ("ST-002", "mall", "standard"),
            ("ST-003", "urban", "standard"),
            ("ST-004", "urban", "standard"),
            ("ST-005", "urban", "standard"),
            ("ST-006", "urban", "standard"),
        ]
    )
    assignment = peer_groups.assign_peer_groups(roster, min_size=4).set_index(
        "station_id"
    )

    for station_id in ("ST-001", "ST-002"):
        assert assignment.loc[station_id, "peer_group_level"] == peer_groups.LEVEL_NETWORK
        assert assignment.loc[station_id, "peer_group"] == peer_groups.NETWORK_GROUP_KEY

    assert (
        assignment.loc["ST-003", "peer_group_level"]
        == peer_groups.LEVEL_SITE_TYPE_TIER
    )


def test_group_sizes_at_the_finest_level_always_meet_the_minimum():
    roster = _roster(
        [
            ("ST-001", "urban", "high"),
            ("ST-002", "urban", "high"),
            ("ST-003", "urban", "standard"),
            ("ST-004", "urban", "standard"),
            ("ST-005", "urban", "standard"),
            ("ST-006", "urban", "standard"),
        ]
    )
    assignment = peer_groups.assign_peer_groups(roster, min_size=4)
    finest = assignment[
        assignment["peer_group_level"] == peer_groups.LEVEL_SITE_TYPE_TIER
    ]
    sizes = finest.groupby("peer_group").size()
    assert (sizes >= 4).all()


# =============================================================================
# Determinism
# =============================================================================

def test_assignment_is_row_order_independent(world, config):
    """Peer groups come from declared attributes, never from data order."""
    min_size = config["network"]["min_peer_group_size"]
    forward = peer_groups.assign_peer_groups(world.observed.stations, min_size)
    reversed_rows = peer_groups.assign_peer_groups(
        world.observed.stations.iloc[::-1].reset_index(drop=True), min_size
    )
    pd.testing.assert_frame_equal(forward, reversed_rows)


def test_assignment_is_repeatable(world, config):
    min_size = config["network"]["min_peer_group_size"]
    first = peer_groups.assign_peer_groups(world.observed.stations, min_size)
    second = peer_groups.assign_peer_groups(world.observed.stations, min_size)
    pd.testing.assert_frame_equal(first, second)


def test_missing_columns_raise_a_clear_error():
    roster = pd.DataFrame({"station_id": ["ST-001"], "site_type": ["urban"]})
    try:
        peer_groups.assign_peer_groups(roster, min_size=4)
    except ValueError as error:
        assert "traffic_tier" in str(error)
    else:
        raise AssertionError("expected a ValueError for the missing column")