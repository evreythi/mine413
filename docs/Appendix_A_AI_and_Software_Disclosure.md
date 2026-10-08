---
title: "Appendix A - Use of Software, Code and Artificial Intelligence"
subtitle: "MIN E 413 Term Project - disclosure required by Section 6.1 of the project outline"
---

> **Team action required before submission.** This appendix records how AI was used to produce the material in this repository. The team must (1) complete the verification log in Section A.3 with the names of the members who performed each check, (2) add any further AI use by individual members, and (3) confirm that the course's AI policy permits this level of assistance. The team remains professionally responsible for every number, statement and line of code submitted.

# A.1 AI system used

| Item | Disclosure |
|---|---|
| AI system / tool | Anthropic Claude (Claude Code agent, run in a cloud development environment), October 2026 |
| Purpose | Data exploration; design and implementation of the analysis platform (`spbm`); generation of figures; first drafts of deliverables D1-D7 and the D8/D9 templates |
| Nature of assistance | Substantial. The AI wrote the Python package, tests, configuration, document sources and presentation generator. It proposed the interpretation of the DXF files as change solids, the survey re-dating and timing analysis, and the CPST optimal-transport formulation, and it drafted the report text |
| What was not delegated | D8 (individual reflection and confidential peer assessment) and D9 (individual ethics assessment) are provided **only as templates**; each student must write their own. Team-charter names, roles, signatures, meeting log and contribution record must be completed by the team from its actual activity |
| Version 2.0 (combined A + B) | A second, independent implementation of the same project ("B", supplied to the team as `MINE413_TERM_PROJECT-B.zip`, also AI-assisted) was compared with this one ("A") by a reviewer. Version 2.0 is a combined platform built from that review by the same AI system. **No code from B was copied or executed.** B's report, outputs and test names were read as a description of its methods, and the ideas were re-implemented in `spbm` (Section A.5) |

# A.2 Other software, libraries and external methods

| Resource | Use | Licence |
|---|---|---|
| Python 3, NumPy, SciPy (`csgraph.dijkstra`, `ndimage`, `special.logsumexp`, `spatial`) | Numerics, geodesic distances, image operations | BSD |
| pandas | Tables | BSD |
| matplotlib | Figures | PSF-based |
| ezdxf | Reading DXF 3DFACE entities | MIT |
| PyYAML, openpyxl, python-docx | Configuration, Excel and Word output | MIT |
| pandoc | Markdown → DOCX/HTML | GPL (tool only) |
| Chromium via Playwright | HTML → PDF | BSD / Apache-2.0 (tool only) |
| pptxgenjs | Presentation | MIT |
| Optimal transport / Sinkhorn algorithm | Allocation method (Cuturi 2013; Peyré and Cuturi 2019); implemented from the published equations, not copied code | - |
| Sandpile / avalanche cellular automaton | Forward gravity model (Bak et al. 1987); implemented from first principles | - |

Data: `Data_Topo 2026.zip` (FMS records and survey solids) supplied by the course instructor. No other datasets were used.

# A.3 How the output was checked (verification log)

| What was checked | Method | Result | Checked by (team member) |
|---|---|---|---|
| DXF interpretation as closed change solids | Independent check: divergence-theorem volume vs gridded volume; count of faces per cell; bottom(s) vs top(s−1) | Volumes agree to < 0.2%; 100% two-face cells; P5-P95 difference 0.000 m | |
| Rasterisation | Unit test with an analytical box (`test_rasterize_closed_box`) | Pass | |
| Sinkhorn solver | Unit tests: marginals and small-ε limit | Pass | |
| Mass and metal conservation | End-to-end test (FMS in = block model out, Cu/Au/Ag) | Relative error < 10⁻⁹ | |
| Avalanche model | Unit test: volume conserved, slope ≤ repose | Pass | |
| Survey re-dating | Unit test + manual review of face progression figure | Pass | |
| Survey cut-off scan | Hand calculation of the interval FMS volumes for cut-offs of 24 h and 31 h from `fms_records_with_flags.csv`; check of the dump-time lull in `dump_time_of_day.csv` | | |
| Volume factor | Recompute f_v and the first-half hold-out by hand from `volume_factor_calibration.csv` | | |
| Cross-implementation check | Compare A's calibrated f_v, consistent intervals, hold-out error, net fill and QA counts with B's published values (D6 Section 9.8) | f_v 1.472 vs 1.476; same intervals; hold-out 3.5% vs 3.2% | |
| Block model totals | Hand sum of `summary_by_dominant_info_class.csv` vs `inventory_by_class.csv` | | |
| Spot check of 3 loads in `load_destinations.csv` against period maps | Visual / distance calculation | | |
| Every number quoted in D6 | Traced to `outputs/report_tables.md` / `summary.json` of the cited run ID | | |
| References | Each reference located and checked for existence and relevance | | |
| Literature-based parameter claims (repose, push distance, GPS accuracy) | Compared against course notes / handbook | | |

# A.4 Technical decisions that remain the team's responsibility

* Acceptance of the change-solid interpretation and of the survey re-dating (A-02, A-04).
* The survey cut-off (A-05, D+1 07:00) and the volume conversion (A-06: calibrated f_v, the base-case split f_pay = 1, and the decision to report the missing-load interpretation as a scenario outside the ranges).
* The choice of CPST and its parameters (ε, α, L_max), and of the forward-model calibration.
* Treatment of unobserved fill (A-13b), unattributed material (A-21) and legacy material (A-22).
* Block size, confidence-class rules and how uncertainty is communicated to management.
* All conclusions and recommendations in D6, and the professional/ethical position in Section 13.

# A.5 What version 2.0 took from implementation B

The reviewer's comparison identified where B was stronger. Each point was re-implemented in A's code base and verified with A's own data and tests:

| Idea (from B) | Re-implemented in | How it was verified here |
|---|---|---|
| Survey cut-off scanned 0-36 h after 00:00 of the nominal date, corroborated by shift-change gaps in dump times | `growth.temporal_alignment` | Scan plateau 30-31.5 h; test `test_cutoff_scan_supports_31h`, `test_shift_change_lull_in_dump_times` |
| Volume factor calibrated on internally consistent intervals, with a hold-out test | `volume.calibrate` | f_v 1.472 (B 1.476), same consistent intervals; hold-out 3.5% (B 3.2%); tests in `test_real_data.py` |
| Report the scope tied to surveyed fill first | D6 executive summary, `scenarios.csv` | Scenario table with explicit "not included in those ranges" |
| `$INSUNITS = 1` (inches) DXF header finding, and a rule catalogue with IDs | `rules.py`, `qaqc.py` | Counts reconciled with B (D6 Section 9.8) |
| Default-position records as location-unknown | `movement.prepare_loads`, `reconstruct` | `test_unknown_location_loads*` |
| Hashed raw store; manual interventions that require reason/author/date | `io.ingest`, `io.load_interventions` | `test_ingest_is_idempotent_and_refuses_conflicts`, `test_intervention_without_reason_*` |
| Testing philosophy: pin real-data facts, test the platform end to end | `tests/` (67 tests, previously 10) | `python -m pytest` |

What A kept from version 1: the CPST engine (survey-constrained entropic optimal transport with exact conservation), the forward physics model, the synthetic twin and its stress twins, 5 × 5 × 2 m blocks, and the built deliverables (report, presentation, register workbook, submission package).

B's numbers quoted in D6 Section 9.8 come from B's own report as supplied. They were not re-run.
