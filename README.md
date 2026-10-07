# MIN E 413 Term Project - Long-Term Stockpile Reconstruction and Block Modelling

Reconstruction of truck-dumped material movement through the Pit I copper-gold HG stockpile, and a 3-D block model of tonnage, Cu, Au, Ag, contained metal and uncertainty. It is delivered as a reproducible in-house platform (`spbm`).

**Method in one sentence:** the survey change solids say *where* volume appeared, the FMS says *what* was dumped and where, and an entropy-regularised optimal-transport allocation over a slope-aware dozer push cost decides *which* load filled *which* part of the observed fill. Mass and metal are conserved exactly, and anything the data cannot explain is labelled as unattributed or assumed, never hidden.

## Deliverables

| # | Deliverable | File(s) |
|---|---|---|
| D1 | Team Charter and Work Plan | `docs/D1_Team_Charter_and_Work_Plan.md` (+ `docs/build/*.docx/.pdf`) |
| D2 | Data and Assumption Register | `docs/D2_Data_and_Assumption_Register.md`, `docs/build/D2_Data_and_Assumption_Register.xlsx` |
| D3 | Technical Methodology and Algorithm | `docs/D3_Technical_Methodology_and_Algorithm.md` |
| D4 | Stockpile Block Model and Outputs | `docs/D4_Block_Model_and_Outputs.md`, `outputs/blockmodel/` (CSV, VTK, summaries, figures) |
| D5 | Automated Analysis Platform | `spbm/` (source), `config/`, `tests/`, `docs/D5_Automated_Platform_User_Guide.md` |
| D6 | Final Engineering Report | `docs/D6_Final_Engineering_Report.md` → `docs/build/D6_Final_Engineering_Report.pdf/.docx` |
| D7 | Presentation | `docs/build/D7_Presentation.pptx` (speaker notes assign each member's part) |
| D8 | Individual teamwork reflection + peer assessment | `docs/D8_..._TEMPLATE.md` (**each student completes their own**) |
| D9 | Individual ethics and equity assessment | `docs/D9_..._TEMPLATE.md` (**each student completes their own**) |

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q          # 8 tests incl. end-to-end mass/metal conservation
python -m spbm run --fast    # base reconstruction and block model (~30 s)
python -m spbm run           # full analysis incl. Monte Carlo, validation, sensitivity (~35 min)
python tools/build_docs.py   # rebuild DOCX/PDF/XLSX/PPTX documents
```

Document rebuilding additionally needs `pandoc`, Node.js (`cd tools && npm install` for pptxgenjs) and Playwright/Chromium for PDF rendering. The analysis itself needs only Python.

New data: drop files into `data/inbox/` and run `python -m spbm update` (see D5).

## Repository layout

```
Data_Topo 2026.zip                  raw data as supplied (read in place, never modified)
Surface_Mining_..._Project.pdf      project brief
config/project.yaml                 every parameter, tagged with its assumption ID (A-xx)
config/survey_overrides.csv         documented manual corrections (survey re-dating)
spbm/                               platform source code (see D3 Section 9 for the module map)
tests/                              automated tests
tools/                              diagrams, document build, presentation build
examples/demo_update.sh             demonstration of the update workflow
outputs/                            results of the submitted run (all reproducible)
docs/                               deliverables (Markdown sources) and docs/build/ (DOCX, PDF, XLSX, PPTX)
```

## Key results (base case, run `20261007T081228`)

| Material class | Tonnes | Share | Cu % | Au g/t | Grade basis |
|---|---|---|---|---|---|
| FMS-tracked (survey-reconciled + provisional) | 44,650 | 22% | 8.42 | 8.00 | measured inputs |
| Unattributed (surveyed volume, no FMS record) | 41,758 | 21% | 8.62 | 8.00 | imputed |
| Legacy (pre-record pile) | 115,699 | 57% | 8.42 | 8.00 | assumed |
| **Total** | **202,107** | | 8.46 | 8.00 | |

* Monte Carlo P10/P50/P90: total 185 / 201 / 218 kt; contained Cu 15.4 / 17.0 / 19.0 kt.
* FMS mass and metal balance: exact (relative error < 1e-9). Geometry RMSE vs survey: 0.026 m.
* Synthetic known-truth test: block Cu RMSE 0.80% (r = 0.90) vs 1.18% for a period-average model.

> **Grade units are as supplied and unconfirmed.** 8.4% Cu / 8.0 g/t Au is roughly an order of magnitude above typical Cu-Au feed. Confirm with Geology before using any contained-metal figure. Legacy and unattributed grades equal or derive from the FMS mean by assumption (A-22, A-21), which is why the class grades are nearly identical.

The class split above is exact (each block's tonnes divided among classes). `outputs/blockmodel/summary_by_dominant_info_class.csv` labels whole blocks by their dominant class instead, so its class totals differ while the grand total is the same.

Every number is traced to `outputs/audit/run_manifest.json`; full tables in `outputs/report_tables.md`.

## What the team still has to do before submission

1. Enter names in `config/team.yaml` (fills every `[Member n]` in the built documents, the deck and the zip name). Sign D1, and keep the meeting log and contribution record (D1 §8) from what actually happens, including proposer and approver for each decision.
2. Each member writes their own **D8** (reflection + confidential peer assessment) and **D9** (ethics/equity response) from the templates.
3. Complete the verification log in **Appendix A** (AI/software disclosure) and confirm the course AI policy.
4. Rehearse D7 (speaker notes assign each member's part).
5. Re-run `python tools/build_docs.py` after any edit, then `python tools/make_submission.py` to create the Canvas zip.
