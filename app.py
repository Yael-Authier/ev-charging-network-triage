"""Voltora | fictional EV charging operations triage portfolio demo.

Launch from the repository root:
    python -m streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

from demo.dashboard_data import dashboard_snapshot
from demo.incident_closure import incident_statuses, select_incident_closures
from demo.public_session import new_demo_state, record_visit_change, record_closure_change
from demo.interventions import (
    ALLOWED_STATUSES, CREWS, intervention_metrics,
    update_intervention,
)


def render_static_records(frame: pd.DataFrame, *, columns: list[str], empty_message: str = "No records to display.") -> None:
    """Render compact, escaped HTML cards without Streamlit's dynamic DataFrame bundle."""
    if frame.empty:
        st.info(empty_message)
        return
    for record in frame[columns].to_dict(orient="records"):
        parts = []
        for label, value in record.items():
            shown = "" if pd.isna(value) else str(value)
            parts.append(
                '<div class="voltora-record-field"><span class="voltora-record-label">'
                + escape(str(label)) + '</span><span class="voltora-record-value">'
                + escape(shown) + '</span></div>'
            )
        st.markdown(
            '<div class="voltora-record">' + "".join(parts) + '</div>',
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Voltora | Operations Triage", page_icon="⚡", layout="wide")

st.markdown("<style>" + (Path(__file__).parent / "demo" / "voltora.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
st.markdown('<div class="voltora-kicker">VOLTORA / NETWORK OPERATIONS</div>', unsafe_allow_html=True)
st.title("⚡ VOLTORA")
st.markdown('<div class="voltora-subtitle">EV charging · Field operations command center</div>', unsafe_allow_html=True)
st.info(
    "SYNTHETIC DEMO — All stations and incidents are fictional. "
    "Priority scores use a provisional, explainable heuristic; they are not validated ERV predictions.",
    icon="ℹ️",
)
snapshot = dashboard_snapshot()
if "interventions" not in st.session_state or "history" not in st.session_state:
    demo_state = new_demo_state(snapshot["recommendations"])
    st.session_state.interventions = demo_state["interventions"]
    st.session_state.history = demo_state["history"]

effective = pd.DataFrame(incident_statuses(snapshot["incidents"], st.session_state.interventions))
active = effective[effective["Status"].isin(["Open", "Assigned", "In Progress"])]
metrics = intervention_metrics(st.session_state.interventions, as_of=snapshot["as_of"])
st.caption(f"Snapshot {snapshot['as_of'].isoformat()} · 40 stations · 5 weekly field visits · Independent browser-session demo")
a, b, c, d = st.columns(4)
a.metric("ACTIVE INCIDENTS", len(active), delta=len(active) - snapshot["open_incident_count"], delta_color="inverse")
b.metric("AFFECTED SITES", active["Station"].nunique())
c.metric("VISITS ASSIGNED", metrics["assigned"])
d.metric("VISITS RESOLVED", metrics["resolved"])
st.caption(
    f"Baseline: {snapshot['open_incident_count']} active incidents / "
    f"{snapshot['affected_station_count']} affected stations. "
    "Confirmed closures are reflected above; the weekly plan stays fixed."
)
tab_queue, tab_work, tab_incidents, tab_history = st.tabs(
    ["⚡ Priority queue", "🛠️ Interventions", "📋 Incidents", "🕒 Change history"]
)

with tab_queue:
    st.subheader("This week's recommended visits")
    st.write(
        "Five distinct stations selected by fault severity, incident age, affected connectors "
        "and repeated open incidents. Scores are comparative heuristic points, not predicted impact."
    )
    recommendations = pd.DataFrame(snapshot["recommendations"])
    recommendations.insert(
        3,
        "Visit status",
        recommendations["Station"].map(
            lambda station: st.session_state.interventions[station]["status"]
        ),
    )
    render_static_records(recommendations, columns=list(recommendations.columns))

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


    st.caption("Frozen weekly plan · Priority scores are provisional, not recovered-energy estimates.")

with tab_work:
    st.subheader("Intervention management")
    st.caption(
        "Public demo. Changes stay in this browser session only, "
        "and do not dispatch technicians or update incident source data."
    )
    metrics = intervention_metrics(st.session_state.interventions, as_of=snapshot["as_of"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Visits planned", metrics["planned"])
    m2.metric("Crews assigned", metrics["assigned"])
    m3.metric("Visits resolved", metrics["resolved"])
    m4.metric("Overdue visits", metrics["overdue"])

    station_options = [item["Station"] for item in snapshot["recommendations"]]
    selected_station = st.radio("Select recommended station", station_options, horizontal=True, key="station_choice")
    current = st.session_state.interventions[selected_station]
    with st.form("intervention_form"):
        crew = st.radio("Assigned crew", CREWS, index=CREWS.index(current["crew"]), horizontal=True, key=f"crew_{selected_station}")
        status_value = st.radio(
            "Intervention status", ALLOWED_STATUSES,
            index=ALLOWED_STATUSES.index(current["status"]),
            horizontal=True, key=f"status_{selected_station}",
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
            previous = dict(st.session_state.interventions[selected_station])
            updated = update_intervention(
                st.session_state.interventions,
                selected_station,
                crew=crew,
                status=status_value,
                scheduled_for=planned_date if status_value != "Pending" else None,
                resolution_note=resolution_note,
            )
            st.session_state.history = record_visit_change(
                st.session_state.history, selected_station, previous, updated[selected_station]
            )
            st.session_state.interventions = updated
            st.success(f"Intervention for {selected_station} updated for this session.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.markdown("#### Incident closure")
    st.caption("Select only faults actually fixed during a resolved visit.")
    linked_ids = next((item["Incident IDs"].split(", ") for item in snapshot["recommendations"] if item["Station"] == selected_station), [])
    current_closures = st.session_state.interventions[selected_station].get("resolved_incident_ids", [])
    with st.form("incident_closure_form"):
        st.caption("Mark each incident confirmed resolved:")
        closed_ids = [
            incident_id for incident_id in linked_ids
            if st.checkbox(
                incident_id, value=incident_id in current_closures,
                key=f"closure_{selected_station}_{incident_id}",
            )
        ]
        close_submitted = st.form_submit_button("Save incident closure")
    if close_submitted:
        try:
            previous = dict(st.session_state.interventions[selected_station])
            updated = select_incident_closures(st.session_state.interventions, selected_station, closed_ids, linked_ids)
            st.session_state.history = record_closure_change(
                st.session_state.history, selected_station, previous, updated[selected_station]
            )
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
    render_static_records(pd.DataFrame(intervention_rows), columns=list(intervention_rows[0]))
    if st.button("Reset demo interventions"):
        demo_state = new_demo_state(snapshot["recommendations"])
        st.session_state.interventions = demo_state["interventions"]
        st.session_state.history = demo_state["history"]
        st.rerun()



with tab_incidents:
    st.subheader("Incident explorer")
    incidents = pd.DataFrame(incident_statuses(snapshot["incidents"], st.session_state.interventions))
    left, right = st.columns(2)
    with left:
        region = st.radio("Region", ["All", *sorted(incidents["Region"].unique())], horizontal=True)
    with right:
        status = st.radio("Status", ["All", *sorted(incidents["Status"].unique())], horizontal=True)
    filtered = incidents.copy()
    if region != "All":
        filtered = filtered[filtered["Region"] == region]
    if status != "All":
        filtered = filtered[filtered["Status"] == status]
    st.caption(f"{len(filtered)} incidents match the selected filters.")
    page_size = 8
    page_count = max(1, (len(filtered) + page_size - 1) // page_size)
    if page_count > 1:
        page = st.radio(
            "Page", list(range(1, page_count + 1)),
            horizontal=True, key=f"incident_page_{region}_{status}",
        )
    else:
        page = 1
    start = (page - 1) * page_size
    st.caption(f"Showing {start + 1 if len(filtered) else 0}–{min(start + page_size, len(filtered))} of {len(filtered)}")
    render_static_records(filtered.iloc[start:start + page_size], columns=list(filtered.columns))
    st.caption("Synthetic data · Isolated, temporary session changes · No real dispatch or shared database.")


with tab_history:
    st.subheader("Change history")
    st.caption("Changes in this browser session only · Times in UTC · Reset clears this history.")
    events = st.session_state.history
    if events:
        history_rows = pd.DataFrame(reversed(events)).rename(columns={
            "timestamp_utc": "Timestamp (UTC)",
            "station": "Station",
            "action": "Action",
            "details": "Changes",
        })
        render_static_records(history_rows, columns=list(history_rows.columns))
    else:
        st.info("No changes have been recorded yet.")



st.markdown(
    '<div class="voltora-footer">VOLTORA · Synthetic portfolio project · '
    'Ephemeral per-session demo · No live dispatch or production data</div>',
    unsafe_allow_html=True,
)
