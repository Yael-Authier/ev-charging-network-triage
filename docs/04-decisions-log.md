\# Decisions log



Append-only. Newest entries at the bottom. Every entry states what was decided,

why, and whether it was decided before or after seeing data.



\---



\## 2026-09-09 — Generator neutrality rule



\*\*Decided before any data was generated.\*\*



The synthetic world is not designed to make the proposed policy win. It is built

to be plausible and internally consistent; which policy performs better is

discovered afterwards.



It is valid and accepted that a hypothesis fails to hold, that peer groups add

little, that a simple policy turns out competitive, that a metric we believed

important does not change the decision, or that the ERV does not win in every

scenario. \*\*If that happens, the generator will not be retrospectively modified

to obtain a more attractive result.\*\* The goal is to demonstrate analytical

judgement, not to manufacture a win.



\---



\## 2026-09-09 — Information boundary



\*\*Decided before any data was generated.\*\*



Three levels of information, and the commitment that follows from them:



| Level | Definition |

|---|---|

| Observed data | Directly available in the synthetic sources under `data/observed/` |

| Derived features / estimates | Computed exclusively from observed data |

| Latent ground truth | The true state of the world, under `data/ground\_truth/`, inaccessible to the policy |



> \*\*All ERV components must be estimable exclusively from information available

> to the analytical layer.\*\*



No ERV component may read latent ground truth. `days\_at\_risk` in particular is a

\*derived estimate\*, not an observation, and is documented as such.



`ambient\_temperature` is deliberately kept as ground truth even though a real

operator would have it. It is a latent driver of multiple performance mechanisms,

particularly L2 intermittent faults and L3 power derating; withholding it forces

the analysis to deal with unobserved confounding.



\---



\## 2026-09-09 — Pre-registered falsification thresholds F1-F6



\*\*Frozen before any data was generated.\*\* Machine-readable copy in

`generator/config.yml` under `falsification`. Modifying these after generation is

prohibited.



| ID | Hypothesis under test | Falsified when |

|---|---|---|

| \*\*F1\*\* | Peer groups improve comparability | P3 improves \*\*less than 3%\*\* over P4 in recovered kWh, \*\*OR\*\* the improvement is absent in at least 2 of 3 regions (OR logic) |

| \*\*F2\*\* | ERV beats simple policies | ERV does \*\*not\*\* improve on the best of P1/P2 by at least 10% in recovered kWh, \*\*AND\*\* does \*\*not\*\* reduce the wasted-trip rate by at least 5 percentage points (AND logic) |

| \*\*F3\*\* | Each ERV mechanism carries information | Leave-one-mechanism-out changes the weekly top-5 in \*\*less than 10%\*\* of weeks |

| \*\*F4\*\* | The ranking is stable enough to publish | In \*\*more than 25%\*\* of weeks, the ERV top-5 overlaps the bootstrap top-5 in \*\*fewer than 3 of 5\*\* stations |

| \*\*F5\*\* | The policy does not systematically underserve low-traffic stations | Share of true conditions addressed within 3 weeks of onset in the lowest-traffic quartile is \*\*below half\*\* that of the highest quartile — \*\*interpreted only if at least 10 evaluable true episodes exist in each quartile\*\*, otherwise reported as insufficient evidence |

| \*\*F6\*\* | Correcting the availability definition changes decisions | Naive and corrected definitions agree on the top-5 in \*\*more than 90%\*\* of weeks |



\*\*Rationale for the F1/F2 asymmetry.\*\* F1 uses OR (stricter) and F2 uses AND

(more permissive). Peer groups are one \*component inside\* the ERV and must earn

their place against a hard criterion. The ERV is the \*whole proposal\* and

deserves to survive if it contributes materially on either dimension.



\*\*Anticipated consequence of F1's OR logic, recorded in advance.\*\* The OR also

falsifies the case of a large improvement concentrated in a single region. If

that happens, the number is reported as-is and F1 is applied anyway: peer groups

leave `src/policy.py` and the regional finding is documented as a V2 line. The

rule is honoured even when the result is inconvenient — that is why it was frozen.



\---



\## 2026-09-09 — Network sizing driven by an analytical requirement



\*\*Decided before any data was generated.\*\*



40 stations and 24 months are not arbitrary. 4 site types x 2 traffic tiers gives

8 peer groups; 40 stations puts \~5 in each, the minimum for group statistics to

mean anything. 24 months allows self-resolution rates to be estimated on the

first 18 while leaving 26 weeks for the backtest.



The analytical requirement drove the data design, not the other way around.



\---



\## 2026-09-09 — Task runner instead of Makefile



\*\*Implementation decision, no analytical impact.\*\*



`tasks.py` replaces a `Makefile` so the project runs on Windows, macOS and Linux

with no tooling beyond Python. Lowers the barrier for anyone cloning the repo.



\---



\## 2026-09-09 — Reconciliation: constitution vs. block 1 files



\*\*Decided before any data was generated.\*\* A consistency review of the block 1

files against the approved Data Generating Constitution V1 found three

discrepancies. None of them touches a falsification threshold, a prevalence, a

severity path or the information boundary. F1-F6 remain untouched.



| # | Discrepancy | Resolution | Nature |

|---|---|---|---|

| 1 | `hardware\_batch`: constitution says 9 stations, `config.yml` said 10 and the roster produced 10 | \*\*Constitution wins: 9.\*\* `ST-007` moved from 2021-11-16 to 2022-05-16, out of the batch window; `expected\_member\_count` set to 9 | Unintended drift in the block files, not a design improvement |

| 2 | `S13`: constitution said `highway / high`, `config.yml` points at `ST-015` (`urban / high`) | \*\*Block wins: `ST-015`.\*\* Constitution corrected | Deliberate correction with quantitative grounds |

| 3 | `ambient\_temperature` described as the common cause of availability vs. session failure rate | Wording corrected in both documents. The world is unchanged | Documentation error, no DGP impact |



\*\*Grounds for the S13 correction.\*\* A `highway / high` station cannot congest at

the configured parameters, which would have left the scenario inert. 42 sessions

per day over 5 connectors at \~22 minutes each is \~13% mean utilisation, and \~28%

even inside a 6-hour peak window. `ST-015` is `urban / high` with \*\*2\*\*

connectors and a \~43-minute mean session: \~51% mean utilisation, and in the

evening peak roughly 860 minutes of demand against \~540 minutes of connector

capacity. Balking occurs there. Congestion requires high demand with \*\*few\*\*

connectors, not high demand in absolute terms.



After removing `ST-007`, the batch keeps 9 members spanning all four site types

(2 highway, 3 urban, 2 mall, 2 fleet\_depot), so it remains cross-cutting and

scenario S11 keeps its purpose.

