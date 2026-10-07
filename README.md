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

## Key results (base case; see D6)

See `outputs/summary.json` and `outputs/report_tables.md`. Every number in the report is traced to the run manifest `outputs/audit/run_manifest.json`.
