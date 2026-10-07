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
| Temporal alignment | Hand calculation for 2 survey times from `daily_coverage.csv` | | |
| Block model totals | Hand sum of `summary_by_info_class.csv` vs `inventory_by_class.csv` | | |
| Spot check of 3 loads in `load_destinations.csv` against period maps | Visual / distance calculation | | |
| Every number quoted in D6 | Traced to `outputs/report_tables.md` / `summary.json` of the cited run ID | | |
| References | Each reference located and checked for existence and relevance | | |
| Literature-based parameter claims (repose, push distance, GPS accuracy) | Compared against course notes / handbook | | |

# A.4 Technical decisions that remain the team's responsibility

* Acceptance of the change-solid interpretation and of the survey re-dating (A-02, A-04).
* The survey-time assumption (A-05) and the density basis (A-06, κ = 1).
* The choice of CPST and its parameters (ε, α, L_max), and of the forward-model calibration.
* Treatment of unobserved fill (A-13b), unattributed material (A-21) and legacy material (A-22).
* Block size, confidence-class rules and how uncertainty is communicated to management.
* All conclusions and recommendations in D6, and the professional/ethical position in Section 13.
