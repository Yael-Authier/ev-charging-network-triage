# ⚡ Voltora | EV Charging Operations Triage

**A fictional operational decision-to-execution portfolio demo.**

Voltora models an EV charging network with **40 stations** and a weekly capacity of **5 field visits**. The challenge is to decide which stations need attention first, explain the prioritization, assign regional crews, track interventions, and confirm exactly which incidents were resolved.

**[Launch the live demo](https://ev-charging-network-triage-c5gfb2y7uupxmzzgul9aqg.streamlit.app/)**

**[View the implemented public-demo source and full documentation](https://github.com/Yael-Authier/ev-charging-network-triage/tree/public-session-demo)**

## Project status

The interactive Streamlit MVP is implemented and deployed from the **`public-session-demo` branch**, not from `main`. This default branch contains the original research scaffold and methodology. For the working application, current tests, operational rules and setup instructions, use the linked public-demo branch.

The public app provides a fixed, reproducible synthetic incident snapshot, an explainable five-station priority queue, intervention status and crew scheduling, selective incident closure, and per-session change history. The demo's state is temporary and isolated per browser session; it is **not** a live dispatch system or shared production database.

## What the demo demonstrates

- **Operational prioritization:** severity, age, affected connectors and repeated incidents produce an explainable *provisional* ranking, with a visible score breakdown.
- **Execution controls:** regional crew matching, one active visit per crew per date, reasons for blocked visits, and resolution notes.
- **Decision traceability:** the weekly plan stays frozen while confirmed incident closures update active-incident metrics and session history.
- **Scope discipline:** synthetic data, no real customer information, no claimed operational impact, no validated Expected Recovered Value (ERV) model.

## Research and methodology

The original research track and preregistered evaluation remain separate from the deployed MVP. The provisional priority score is **not** a validated optimization policy or an estimate of recovered energy.

See [the full public-demo README](https://github.com/Yael-Authier/ev-charging-network-triage/blob/public-session-demo/README.md) for architecture, local installation, test commands and limitations.

---

**Yael Authier** · Business Operations · Systems Implementation · Data Analytics

[LinkedIn](https://www.linkedin.com/in/yael-authier/) · [GitHub](https://github.com/Yael-Authier)
