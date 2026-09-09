"""Contract tests for the frozen world configuration.

These run before any data exists. They assert that config.yml and network.yml
are internally consistent, that every scenario points at a real station and a
real condition, and that the pre-registered falsification block is complete.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter

STATION_ID_PATTERN = re.compile(r"^ST-\d{3}$")


def _as_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def _scenario_station_ids(scenario: dict) -> list[str]:
    """Normalise a scenario's station reference to a list of ids."""
    raw = scenario.get("station_id")
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


# --- meta --------------------------------------------------------------------

def test_seed_is_an_integer(config):
    assert isinstance(config["meta"]["seed"], int)


def test_window_is_ordered_and_two_years_long(config):
    start = _as_date(config["meta"]["start_date"])
    end = _as_date(config["meta"]["end_date"])
    assert start < end
    assert 720 <= (end - start).days <= 740, "expected a ~24 month window"


# --- roster ------------------------------------------------------------------

def test_station_count_matches_expectation(config, stations):
    assert len(stations) == config["network"]["expected_station_count"]


def test_station_ids_are_unique_and_well_formed(stations):
    ids = [s["station_id"] for s in stations]
    assert len(set(ids)) == len(ids), "duplicate station_id"
    for station_id in ids:
        assert STATION_ID_PATTERN.match(station_id), f"bad id: {station_id}"


def test_station_attributes_are_in_the_allowed_sets(config, stations):
    net = config["network"]
    for station in stations:
        assert station["region"] in net["regions"]
        assert station["site_type"] in net["site_types"]
        assert station["traffic_tier"] in net["traffic_tiers"]


def test_peer_groups_are_balanced(config, stations):
    expected_size = config["network"]["expected_peer_group_size"]
    groups = Counter((s["site_type"], s["traffic_tier"]) for s in stations)
    n_site_types = len(config["network"]["site_types"])
    n_tiers = len(config["network"]["traffic_tiers"])

    assert len(groups) == n_site_types * n_tiers, "a peer group is empty"
    for group, size in groups.items():
        assert size == expected_size, f"peer group {group} has {size} stations"


def test_connector_counts_are_within_site_type_bounds(config, stations):
    bounds = config["network"]["connector_bounds"]
    for station in stations:
        limits = bounds[station["site_type"]]
        count = station["connectors"]
        assert limits["min"] <= count <= limits["max"], (
            f"{station['station_id']} has {count} connectors, "
            f"outside {limits} for {station['site_type']}"
        )


def test_exactly_four_stations_are_commissioned_inside_the_window(config, stations):
    start = _as_date(config["meta"]["start_date"])
    end = _as_date(config["meta"]["end_date"])
    inside = [
        s["station_id"] for s in stations
        if start <= _as_date(s["commissioned_at"]) <= end
    ]
    assert len(inside) == 4, f"expected 4 late commissions, found {inside}"


def test_hardware_batch_membership_matches_expectation(config, stations):
    batch = config["hardware_batch"]
    lower, upper = (_as_date(d) for d in batch["commissioned_between"])
    members = [
        s for s in stations
        if lower <= _as_date(s["commissioned_at"]) <= upper
    ]
    assert len(members) == batch["expected_member_count"]

    # The batch must cross-cut site types, otherwise peer groups would absorb it
    # and scenario S11 would lose its purpose.
    site_types = {s["site_type"] for s in members}
    assert len(site_types) >= 3, f"batch is not cross-cutting: {site_types}"


# --- crews -------------------------------------------------------------------

def test_crew_capacity_matches_the_backtest_constraint(config):
    total = sum(c["weekly_visit_capacity"] for c in config["crews"])
    assert total == config["backtest"]["weekly_visit_capacity"]


def test_every_region_is_covered_by_at_least_one_crew(config):
    covered = {r for crew in config["crews"] for r in crew["regions"]}
    assert covered == set(config["network"]["regions"])


# --- conditions --------------------------------------------------------------

def test_field_fixability_is_declared_as_designed(config):
    conditions = config["conditions"]
    fixable = {
        "L1_connector_hard_fault",
        "L2_connector_intermittent_fault",
        "L3_power_derate",
        "L4_comms_module_failure",
        "L5_cable_damage",
    }
    not_fixable = {"L6_upstream_grid_limit", "L7_congestion"}

    assert set(conditions) == fixable | not_fixable

    for name in fixable:
        assert conditions[name]["field_fixable"] is True, name
    for name in not_fixable:
        assert conditions[name]["field_fixable"] is False, name


def test_every_condition_declares_a_scope_and_visit_success(config):
    for name, spec in config["conditions"].items():
        assert spec["scope"] in {"station", "connector"}, name
        assert 0.0 <= spec["visit_success_probability"] <= 1.0, name


# --- demand profiles ---------------------------------------------------------

def test_demand_profiles_exist_for_every_site_type(config):
    demand = config["demand"]
    for site_type in config["network"]["site_types"]:
        assert len(demand["dow_factors"][site_type]) == 7, site_type
        assert len(demand["season_factors"][site_type]) == 12, site_type
        assert site_type in demand["arrival_hour_profile"]
        assert site_type in demand["base_daily_sessions"]


def test_arrival_hour_weights_sum_to_one(config):
    for site_type, profile in config["demand"]["arrival_hour_profile"].items():
        total = sum(peak["w"] for peak in profile["peaks"])
        assert abs(total - 1.0) < 1e-9, f"{site_type} weights sum to {total}"


# --- scenarios ---------------------------------------------------------------

def test_scenario_ids_are_unique(config):
    ids = [s["id"] for s in config["scenarios"]]
    assert len(set(ids)) == len(ids)


def test_every_scenario_station_exists_in_the_roster(config, stations):
    known = {s["station_id"] for s in stations}
    for scenario in config["scenarios"]:
        for station_id in _scenario_station_ids(scenario):
            assert station_id in known, f"{scenario['id']} -> unknown {station_id}"


def test_every_scenario_condition_exists(config):
    known = set(config["conditions"])
    for scenario in config["scenarios"]:
        condition = scenario.get("condition")
        if condition is not None:
            assert condition in known, f"{scenario['id']} -> unknown {condition}"


def test_every_scenario_states_its_purpose(config):
    for scenario in config["scenarios"]:
        assert scenario.get("purpose"), f"{scenario['id']} has no purpose"


def test_referenced_demand_shocks_and_firmware_changes_exist(config):
    shock_ids = {s["shock_id"] for s in config["demand_shocks"]}
    firmware_stations = {
        f["station_id"] for f in config["telemetry"]["firmware_changes"]
    }

    for scenario in config["scenarios"]:
        if "links_shock" in scenario:
            assert scenario["links_shock"] in shock_ids, scenario["id"]
        if scenario.get("links_firmware"):
            assert (
                set(_scenario_station_ids(scenario)) <= firmware_stations
            ), scenario["id"]


def test_demand_shock_stations_exist_and_windows_are_ordered(config, stations):
    known = {s["station_id"] for s in stations}
    for shock in config["demand_shocks"]:
        assert shock["station_id"] in known, shock["shock_id"]
        if shock["to"] is not None:
            assert _as_date(shock["from"]) < _as_date(shock["to"]), shock["shock_id"]


# --- pre-registration --------------------------------------------------------

def test_falsification_block_is_complete_and_frozen(config):
    falsification = config["falsification"]
    assert falsification["frozen_before_data_generation"] is True
    _as_date(falsification["frozen_on"])

    expected = {
        "F1_peer_groups_add_no_value",
        "F2_erv_does_not_justify_complexity",
        "F3_mechanism_adds_no_information",
        "F4_recommendation_too_unstable",
        "F5_low_traffic_coverage_bias",
        "F6_corrected_availability_changes_nothing",
    }
    present = {k for k in falsification if k.startswith("F")}
    assert present == expected, f"missing or extra: {expected ^ present}"


def test_frozen_falsification_values_match_the_decisions_log(config):
    """Guards against silent drift of the pre-registered thresholds."""
    f = config["falsification"]

    assert f["F1_peer_groups_add_no_value"]["logic"] == "OR"
    assert f["F1_peer_groups_add_no_value"]["min_kwh_improvement_pct"] == 3.0
    assert f["F1_peer_groups_add_no_value"]["min_regions_with_improvement"] == 2

    assert f["F2_erv_does_not_justify_complexity"]["logic"] == "AND"
    assert (
        f["F2_erv_does_not_justify_complexity"][
            "min_kwh_improvement_pct_vs_best_simple"
        ]
        == 10.0
    )
    assert (
        f["F2_erv_does_not_justify_complexity"][
            "min_wasted_trip_reduction_pp"
        ]
        == 5.0
    )

    assert (
        f["F3_mechanism_adds_no_information"]["min_weeks_changing_top5_pct"]
        == 10.0
    )

    assert (
        f["F4_recommendation_too_unstable"]["max_unstable_weeks_pct"]
        == 25.0
    )
    assert f["F4_recommendation_too_unstable"]["min_overlap_of_top5"] == 3

    assert (
        f["F5_low_traffic_coverage_bias"]["max_ratio_low_vs_high_quartile"]
        == 0.5
    )
    assert (
        f["F5_low_traffic_coverage_bias"][
            "min_evaluable_episodes_per_quartile"
        ]
        == 10
    )

    assert (
        f["F6_corrected_availability_changes_nothing"]["max_top5_agreement_pct"]
        == 90.0
    )


def test_backtest_holdout_fits_inside_the_window(config):
    backtest = config["backtest"]
    assert 0 < backtest["holdout_weeks"] < backtest["weeks"]
    assert backtest["weekly_visit_capacity"] in backtest["capacity_sensitivity"]


def test_congestion_and_temperature_stay_ground_truth_only(config):
    assert config["congestion"]["ground_truth_only"] is True
    assert config["congestion"]["enabled"] is True

    # ambient_temperature has no `observed` switch by design; assert it exists
    # and carries the parameters the generator needs.
    ambient = config["ambient_temperature"]
    for key in ("annual_mean_c", "annual_amplitude_c", "region_offset_c"):
        assert key in ambient