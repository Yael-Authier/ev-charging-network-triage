# ⚡ Voltora | EV Charging Operations Triage

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Interactive%20App-FF4B4B?logo=streamlit&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Automated%20Tests-0A9EDC?logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI-2088FF?logo=githubactions&logoColor=white)
![Status](https://img.shields.io/badge/Status-Portfolio%20MVP-55E0C4)
![Data](https://img.shields.io/badge/Data-100%25%20Synthetic-64748B)

**From operational incidents to a traceable weekly field-service plan.**

Voltora is a fictional EV charging operator with **40 stations** and capacity for just **5 technician visits per week**. The operational challenge is not simply monitoring faults: it is deciding **which stations to visit first, explaining why, assigning work, and confirming what was actually resolved**.

This repository contains a working, bounded **operations triage portfolio MVP**. It demonstrates a decision-to-execution workflow rather than a production dispatch platform.

---

## 🎯 Business problem

When field capacity is constrained, incident lists alone do not answer the most important operational questions:

- Which five stations should receive a visit this week?
- What observable evidence supports each recommendation?
- Who is assigned, and what is the status of the visit?
- Which specific incidents were resolved, and which remain open?
- Can the decision and subsequent changes be traced?

**Decision output:** one ranked weekly plan with five distinct stations, explanation codes and a lightweight intervention workflow.

## 🖥️ Product walkthrough

The Streamlit interface uses a dark **Network Operations Command Center** design with four sections:

| Section | What it supports |
| --- | --- |
| **Priority queue** | A frozen five-station weekly plan, priority scores, explanations and live visit status |
| **Interventions** | Crew assignment, scheduling, visit status, resolution notes and selective incident closure |
| **Incidents** | Searchable/filterable synthetic incident records with confirmed closures reflected in the display |
| **Change history** | Session-only timestamps, stations, actions and change details |

**Key operational distinction:** a resolved technician visit does **not** automatically close every incident at that station. Incident closures must be explicitly confirmed; other faults remain active.

The top-level KPIs reflect confirmed closures, while the original weekly recommendation list remains fixed. This preserves the difference between **the approved plan** and **its execution progress**.

> **Demo notice:** Voltora, its stations, incidents, crews and business rules are entirely fictional. No real operational data is included.

---

## ⚙️ How prioritization works

The portfolio MVP ranks stations using an **explainable, provisional heuristic** based on:

1. Reported fault severity.
2. Days an incident has remained open.
3. Estimated number of affected connectors.
4. Multiple active incidents at one station.

The five highest-priority **distinct stations** form the weekly plan. Each recommendation includes a score and human-readable reasons.

**Important:** heuristic points are **not** predicted recovered energy, causal impact, or a validated optimization result. The formal Expected Recovered Value (ERV) research and preregistered evaluation described in the methodology documents are separate, unfinished work. The MVP does not claim to implement or validate ERV.

## 🔄 Operational workflow

```text
Synthetic incident snapshot
           |
           v
Explainable station ranking
           |
           v
Frozen weekly plan (5 visits)
           |
           v
Crew assignment + visit scheduling
           |
           v
Intervention status + resolution note
           |
           v
Explicit incident-by-incident closure
           |
           v
Updated active-incident KPIs + local change history
```

The demo includes validation rules: a crew is required before a visit progresses, a resolution note is required to resolve a visit, and only incidents associated with a resolved visit may be marked closed.

---

## 🧰 Technology and architecture

| Layer | Implementation |
| --- | --- |
| Interface | Python, Streamlit, custom CSS and native dark theme |
| Synthetic snapshot | Deterministic Python demo generator |
| Decision logic | Explainable station-level ranking |
| Workflow rules | Validated Python functions |
| Local storage | Streamlit session state for public demo; JSON local-storage modules retained for the separate local prototype |
| Quality | Pytest and GitHub Actions CI |

```text
app.py                         Streamlit entry point
.streamlit/config.toml          Native dark theme
demo/
  generate_snapshot.py         Reproducible synthetic incident snapshot
  dashboard_data.py            Observed-only dashboard data model
  interventions.py             Intervention workflow and validations
  incident_closure.py          Explicit closure overlay
  intervention_store.py        Local intervention persistence (not used by the public app)
  audit_history.py             Local history implementation (not used by the public app)
  voltora.css                  Command-center visual identity
src/
  demo_triage.py               Provisional ranking and reason codes
tests/                          Automated unit and contract tests
generator/                      Broader synthetic-world research scaffolding
docs/                           Methodology and decision log
```

The demo presentation and prioritization use **observed synthetic data**, not hidden ground-truth variables. The broader research project keeps latent truth separate from the analysis layer.

## 🚀 Run locally

Requires Python 3.11 or 3.12 (the versions covered by CI).

```bash
git clone https://github.com/Yael-Authier/ev-charging-network-triage.git
cd ev-charging-network-triage
git switch public-session-demo
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install and launch:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Open the local address printed by Streamlit (usually `http://localhost:8501`).

**Public demo state:** the deployed app uses Streamlit `st.session_state` for interventions and change history. Each independent browser session starts with the same fictional baseline, but changes are **temporary and not shared** with other sessions. Refreshing the same active session may preserve changes; reconnecting or restarting can reset them. **Reset demo interventions** clears both the intervention state and its session history. The local JSON storage modules remain in the repository for the original local prototype, but are not used by the public app.

### ☁️ Deploy to Streamlit Community Cloud

1. Push this branch to GitHub and verify the automated tests pass.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
3. Choose **Create app**, select repository `Yael-Authier/ev-charging-network-triage`, branch `public-session-demo`, and entrypoint `app.py`.
4. Deploy. Copy the generated public URL into your portfolio and README after checking it works in a private browser window.

No database credentials or API keys are required. Community Cloud may restart sleeping apps, which resets temporary sessions.

## 🧪 Testing

The project uses automated tests for the ranking workflow, deterministic synthetic inputs, intervention validation, selective closure, local persistence, isolated public sessions, change history, and basic application contracts.

Run:

```bash
python -m pytest -q
```

CI runs tests on Python 3.11 and 3.12. A passing test suite validates covered behaviors; it is **not** evidence of production readiness or of a validated economic prioritization model.

## 🔒 Scope and limitations

This is a **public, per-browser-session prototype**. It does **not** provide:

- Authentication, permissions or multi-user concurrency.
- Real technician dispatch, notifications or live external integrations.
- Production-grade database storage or a transactional audit log.
- Dynamic re-optimization of an already-approved weekly plan.
- Validated ERV, financial impact estimates or a real-world pilot.

The synthetic snapshot is fixed for reproducibility. Per-session intervention changes are overlays on that snapshot rather than edits to a real source system.

## 🧭 Research track and next steps

The repository also contains a broader, separately scoped research design. Its frozen configuration, methodological decisions and preregistered falsification criteria are documented in:

- [Decision log](docs/04-decisions-log.md)
- [Synthetic-world configuration](generator/config.yml)
- [Repository development principles](CLAUDE.md)

Potential future work includes multi-user persistence, operational ownership, dispatch integration and formal ERV evaluation. **These are not implemented features of the current MVP.**

---

## 👩‍💻 Author

**Yael Authier**  
Business Operations · Systems Implementation · Data Analytics

[LinkedIn](https://www.linkedin.com/in/yael-authier/) · [GitHub](https://github.com/Yael-Authier) · [Portfolio](https://yael-authier.github.io/)

*Portfolio case study: translating an operational capacity constraint into a transparent, testable and traceable decision workflow.*
