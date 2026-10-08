# MIN E 413 Term Project - Long-Term Stockpile Reconstruction and Block Modelling

This project reconstructs how truck-dumped material moved through the Pit I copper-gold HG stockpile. It also builds a 3-D block model of tonnage, Cu, Au, Ag, contained metal and uncertainty. Everything is delivered as a reproducible in-house platform (`spbm`, version 2.0).

**Method in one sentence:** the survey change solids say *where* volume appeared, the FMS says *what* was dumped and where, and an entropy-regularised optimal-transport allocation over a slope-aware dozer push cost decides *which* load filled *which* part of the observed fill. Mass and metal are conserved exactly. Anything the data cannot explain is labelled as unattributed or assumed, never hidden.

**Version 2.0** combines this platform (A) with the stronger ideas of an independent implementation of the same brief (B, `MINE413_TERM_PROJECT-B.zip`), following a reviewer's comparison:

* the survey cut-off scanned over 0-36 h (it is D+1 07:00, not 23:59);
* a calibrated and hold-out-tested volume factor;
* the record-period inventory reported first, with scenarios that say what the ranges exclude;
* the DXF unit-header finding and a 40-rule QA catalogue;
* unknown-location treatment of default-position loads;
* a hashed raw store, and manual interventions that require a reason, author and date;
* 66 tests (previously 10).

See Appendix A and D1 (DEC-11 to DEC-16).

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
python -m pytest -q          # 66 tests (unit, real data, platform), about 2 min
python -m spbm run --fast    # base reconstruction and block model (~1.5 min)
python -m spbm run           # full analysis incl. Monte Carlo, validation, sensitivity, scenarios (~40 min)
python tools/fill_report.py  # refresh numbers in D2/D4/D6/README from the latest run
python tools/build_docs.py   # rebuild DOCX/PDF/XLSX/PPTX documents
```

Rebuilding the documents also needs `pandoc`, Node.js (`cd tools && npm install` for pptxgenjs) and Playwright/Chromium for PDF rendering. The analysis itself needs only Python.

New data: drop files into `data/inbox/` (or `python -m spbm ingest <path>`) and run `python -m spbm update` (see D5). Corrections go in `config/manual_interventions.csv`, never into the raw files.

## Repository layout

```
Data_Topo 2026.zip                  raw data as supplied (ingested into data/raw_store/, never modified)
MINE413_TERM_PROJECT-B.zip          independent implementation B (reference only; not executed)
Surface_Mining_..._Project.pdf      project brief
config/project.yaml                 every parameter, tagged with its assumption ID (A-xx)
config/manual_interventions.csv     the only way to correct data (id, type, target, value, reason, author, date)
spbm/                               platform source code (see D3 Section 9 for the module map)
tests/                              automated tests (unit, real data, platform)
tools/                              report filler and templates, diagrams, document and presentation build
examples/demo_update.sh             demonstration of the update workflow
outputs/                            results of the submitted run (all reproducible)
docs/                               deliverables (Markdown sources) and docs/build/ (DOCX, PDF, XLSX, PPTX)
```

`data/raw_store/` and `data/cache/` are generated on the first run and are not committed.

## Key results (base case, run `{{RUN_ID}}`)

**Material placed during the record (15-31 March), tied to surveyed fill:**

| Class | Tonnes | Cu % | Au g/t | Basis |
|---|---|---|---|---|
| FMS-tracked (survey-reconciled + provisional) | {{T_F}} | {{CU_F}} | {{AU_F}} | measured tonnes and grades |
| Unattributed (surveyed fill, no FMS record) | {{T_U}} | {{CU_U}} | {{AU_U}} | imputed grade |
| **Record-period total** | **{{T_RP}}** | {{CU_RP}} | {{AU_RP}} | |

* Monte Carlo P10/P50/P90: record-period tonnes {{MC_RP}} kt; contained Cu {{MC_RP_CU}} kt.
* **Not included in those ranges:** the reading that the 47% volume excess is loads missing from the FMS rather than bulking. Under that reading, record-period tonnes are {{X2_RP}} t (+{{X2_UPLIFT}}). See D6 Section 10.2.
* Survey cut-off D+1 07:00. Volume factor f_v = {{F_V}}, predicting held-out intervals to {{HO_MAE}}. The independent implementation B found 1.476.
* FMS mass and metal balance: exact (relative error < 1e-9). Geometry RMSE vs survey: {{GEO_RMSE}} m.
* Synthetic known-truth test: block Cu RMSE {{TW_CPST}}% (r = {{TW_R}}), vs {{TW_PA}}% for a period-average model.

**Pre-record core and whole pile.** The core below the earliest surveyed surfaces holds {{T_L}} t. Its geometry is inferred and its grade assumed. The whole modelled pile is {{T_T}} t (P10/P50/P90 {{MC_T}} kt). {{S_L}} of that is the pre-record core, with an assumed grade.

> **Grade units are as supplied and unconfirmed.** 8.4% Cu / 8.0 g/t Au is roughly an order of magnitude above typical Cu-Au feed. Confirm with Geology before using any contained-metal figure. Pre-record and unattributed grades equal or derive from the FMS mean by assumption (A-22, A-21).

> Version 1 of this repository reported 202 kt for the whole pile. That number rested on a survey-time artefact and an untested density assumption, and it is superseded.

Every number is traced to `outputs/audit/run_manifest.json`; the full tables are in `outputs/report_tables.md`.

## What the team still has to do before submission

1. Enter names in `config/team.yaml`. This fills every `[Member n]` in the built documents, the deck and the zip name. Sign D1. Keep the meeting log and contribution record (D1 §8) from what actually happens, including the proposer and approver of each decision (DEC-01 to DEC-16).
2. Each member writes their own **D8** (reflection + confidential peer assessment) and **D9** (ethics/equity response) from the templates.
3. Complete the verification log in **Appendix A** (AI/software disclosure, including the A + B integration) and confirm the course AI policy.
4. Rehearse D7 (speaker notes assign each member's part).
5. Re-run `python tools/fill_report.py` and `python tools/build_docs.py` after any edit, then `python tools/make_submission.py` to create the Canvas zip.
