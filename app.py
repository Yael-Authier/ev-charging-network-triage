"""Voltora | fictional EV charging operations triage portfolio demo.

Launch from the repository root:
    python -m streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from demo.dashboard_data import dashboard_snapshot
from demo.incident_closure import incident_statuses, select_incident_closures
from demo.intervention_store import load_interventions, save_interventions
from demo.interventions import (
    ALLOWED_STATUSES, CREWS, initial_interventions, intervention_metrics,
    update_intervention,
)

st.set_page_config(page_title="Voltora | Operations Triage", page_icon="⚡", layout="wide")

st.title("⚡ Voltora")
st.caption("EV charging network · Operations triage · Synthetic portfolio demonstration")
st.info(
    "DEMO MODE — All stations and incidents are fictional. Priority scores use a "
    "transparent provisional rule, not the validated expected-recovery (ERV) model.",
    icon="ℹ️",
)

snapshot = dashboard_snapshot()
st.subheader("Network overview")
st.caption(f"Snapshot date: {snapshot['as_of'].isoformat()} · Weekly field capacity: 5 visits")

a, b, c, d = st.columns(4)
a.metric("Stations", snapshot["station_count"])
b.metric("Total incidents", snapshot["incident_count"])
c.metric("Baseline active incidents", snapshot["open_incident_count"])
d.metric("Baseline affected stations", snapshot["affected_station_count"])

st.divider()
st.subheader("This week's recommended visits")
st.write(
    "Five distinct stations selected by fault severity, incident age, affected connectors "
    "and repeated open incidents. Scores are comparative heuristic points, not predicted impact."
)
recommendations = pd.DataFrame(snapshot["recommendations"])
st.dataframe(recommendations, hide_index=True, width="stretch")

with st.expander("How the provisional priority score works"):
    st.markdown(
        """
        - **Severity:** low 10 · medium 30 · high 55 · critical 80 points.
        - **Age:** 1 point per day open, capped at 14.
        - **Affected connectors:** 5 points each, capped at 4 connectors.
        - **Repeated incidents:** 5 points per additional active incident, capped at 3.
        - Each station appears once. Ties are resolved by station ID.
        - This is a demonstration rule, **not** an estimated recovered-energy model.
        """
    )

st.divider()
st.subheader("Intervention management")
st.caption(
    "Single-user local demo. Changes are saved on this computer, "
    "but do not dispatch technicians or update incident source data."
)
if "interventions" not in st.session_state:
    try:
        st.session_state.interventions = load_interventions(snapshot["recommendations"])
    except ValueError as exc:
        st.error(f"Local intervention file needs attention: {exc}")
        st.stop()

metrics = intervention_metrics(st.session_state.interventions, as_of=snapshot["as_of"])
m1, m2, m3, m4 = st.columns(4)
m1.metric("Visits planned", metrics["planned"])
m2.metric("Crews assigned", metrics["assigned"])
m3.metric("Visits resolved", metrics["resolved"])
m4.metric("Overdue visits", metrics["overdue"])

station_options = [item["Station"] for item in snapshot["recommendations"]]
selected_station = st.selectbox("Select recommended station", station_options)
current = st.session_state.interventions[selected_station]
with st.form("intervention_form"):
    crew = st.selectbox("Assigned crew", CREWS, index=CREWS.index(current["crew"]))
    status_value = st.selectbox(
        "Intervention status", ALLOWED_STATUSES,
        index=ALLOWED_STATUSES.index(current["status"]),
    )
    planned_date = st.date_input(
        "Visit date (used for scheduled / in-progress visits)",
        value=current["scheduled_for"] or snapshot["as_of"],
    )
    resolution_note = st.text_area(
        "Resolution note (required when resolved)", value=current["resolution_note"]
    )
    submitted = st.form_submit_button("Save intervention", type="primary")
if submitted:
    try:
        st.session_state.interventions = update_intervention(
            st.session_state.interventions,
            selected_station,
            crew=crew,
            status=status_value,
            scheduled_for=planned_date if status_value != "Pending" else None,
            resolution_note=resolution_note,
        )
        save_interventions(st.session_state.interventions)
        st.success(f"Intervention for {selected_station} saved locally.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

st.markdown("#### Incident closure")
st.caption("Select only faults actually fixed during a resolved visit.")
linked_ids = next((item["Incident IDs"].split(", ") for item in snapshot["recommendations"] if item["Station"] == selected_station), [])
current_closures = st.session_state.interventions[selected_station].get("resolved_incident_ids", [])
with st.form("incident_closure_form"):
    closed_ids = st.multiselect("Incidents confirmed resolved", linked_ids, default=[item for item in current_closures if item in linked_ids])
    close_submitted = st.form_submit_button("Save incident closure")
if close_submitted:
    try:
        updated = select_incident_closures(st.session_state.interventions, selected_station, closed_ids, linked_ids)
        save_interventions(updated)
        st.session_state.interventions = updated
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

intervention_rows = [
    {
        "Station": item["station_id"],
        "Rank": item["rank"],
        "Crew": item["crew"],
        "Status": item["status"],
        "Visit date": item["scheduled_for"].isoformat() if item["scheduled_for"] else "",
        "Resolution note": item["resolution_note"],
    }
    for item in st.session_state.interventions.values()
]
st.dataframe(pd.DataFrame(intervention_rows), hide_index=True, width="stretch")
if st.button("Reset demo interventions"):
    st.session_state.interventions = initial_interventions(snapshot["recommendations"])
    save_interventions(st.session_state.interventions)
    st.rerun()

st.divider()
st.subheader("Incident explorer")
incidents = pd.DataFrame(incident_statuses(snapshot["incidents"], st.session_state.interventions))
left, right = st.columns(2)
with left:
    region = st.selectbox("Region", ["All", *sorted(incidents["Region"].unique())])
with right:
    status = st.selectbox("Status", ["All", *sorted(incidents["Status"].unique())])
filtered = incidents.copy()
if region != "All":
    filtered = filtered[filtered["Region"] == region]
if status != "All":
    filtered = filtered[filtered["Status"] == status]
st.dataframe(filtered, hide_index=True, width="stretch")
active_rows = incidents[incidents["Status"].isin(["Open", "Assigned", "In Progress"])]
st.metric("Active incidents after confirmed closures", len(active_rows))
st.caption(f"Active stations after confirmed closures: {active_rows[\u0027Station\u0027].nunique()}")
st.caption("Synthetic data · Locally saved intervention records · No real dispatch or shared database.")
