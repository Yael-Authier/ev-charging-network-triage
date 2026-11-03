# Voltora — Portfolio MVP scope (draft)

This is a **planning document**, not a completed demo or a change to the frozen analytical model.

## Problem and goal
Voltora is a fictional operator of 40 EV charging stations. It can dispatch five technician visits per week. The MVP must show an operations manager how to identify incidents, decide what to visit, assign responsibility, and track outcomes. The career goal is to demonstrate an end-to-end operational implementation suitable for complementary consulting/contract work.

## User journey
1. Inspect a reproducible synthetic snapshot of 40 stations and observed incidents.
2. See a transparent **provisional** top-five visit queue with reasons and a clear five-visit capacity limit.
3. Assign visits to crews, update statuses (pending, scheduled, in progress, resolved, blocked), and record resolution notes.
4. View open incidents, assigned visits, overdue visits, and completed interventions.
5. Reproduce the demo locally and open an independently hosted version.

## Scope and integrity
- Preserve existing generator/config.yml, generator/network.yml, preregistered falsification thresholds F1–F6, and the analytical decision log.
- Never use latent ground truth to rank operational visits.
- A simple early rule-based ranking must be labeled **provisional** and must not be presented as the final ERV policy.
- Do not claim recovered kWh, causality, or policy superiority without a validated backtest.
- Use only fictional/synthetic information, no employer systems or infrastructure.
- n8n/Make/Zapier are optional additions only if a real workflow benefits.
- Keep the analytical research intact; do not rebuild the whole Control de Locales ecosystem.

## Excluded from the first demo
Complete 24-month simulation/backtest; predictive maintenance; AI agent; full CRM/ticketing suite; multi-tenant permissions; multiple dashboards.

## Build order
1. Define a small observed-only synthetic incident snapshot, reusing existing station roster without changing frozen parameters.
2. Implement and test explainable provisional ranking, reason codes, and the capacity limit.
3. Add assignment/status tracking and operational metrics.
4. Build a simple UI, reproducibility instructions, and independent deployment.
5. Publish a case study distinguishing built, simulated, tested, and future capabilities.

## Portfolio acceptance criteria
A user can open the demo, understand why five stations were selected, assign work, mark outcomes, and see updated metrics. The repo has reproducible tests and a short English case study. No unverified impact claims.
