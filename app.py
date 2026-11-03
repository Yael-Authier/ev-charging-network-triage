"""Voltora | fictional EV charging operations triage portfolio demo.

Launch from the repository root:
    python -m streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from demo.dashboard_data import dashboard_snapshot

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
c.metric("Active incidents", snapshot["open_incident_count"])
d.metric("Stations with active incidents", snapshot["affected_station_count"])

st.divider()
st.subheader("This week's recommended visits")
st.write(
    "Five distinct stations selected by fault severity, incident age, affected connectors "
    "and repeated open incidents. Scores are comparative heuristic points, not predicted impact."
)
recommendations = pd.DataFrame(snapshot["recommendations"])
st.dataframe(recommendations, hide_index=True, use_container_width=True)

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
st.subheader("Incident explorer")
incidents = pd.DataFrame(snapshot["incidents"])
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
st.dataframe(filtered, hide_index=True, use_container_width=True)
st.caption(
    "Read-only MVP · Next iteration: technician assignment, intervention statuses, "
    "resolution notes and an operational scorecard."
)
