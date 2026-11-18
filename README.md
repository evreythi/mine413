# SPBM: stockpile reconstruction and block model

`spbm` reconstructs how truck-dumped material moved through the Pit I copper-gold HG stockpile and builds a 3-D block model of tonnage, Cu, Au, Ag, contained metal and uncertainty.

**Method in one sentence:** the survey change solids say *where* volume appeared, the FMS says *what* was dumped and where, and an entropy-regularised optimal-transport allocation over a slope-aware dozer push cost decides *which* load filled *which* part of the observed fill. Mass and metal are conserved exactly. Anything the data cannot explain is kept in its own class (unattributed or pre-record), never mixed with measured material.

The mathematics, algorithm, validation design and every assumption (A-01 to A-32) are in **[METHOD.md](METHOD.md)**.

## Requirements

Python 3.10 or later on Windows, macOS or Linux. All dependencies are open source.

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python -m pytest -q                # 67 tests (unit, real data, platform), about 3 min
python -m pytest -q -m "not slow"  # skip the end-to-end pipeline test
python -m spbm run --fast          # base reconstruction, block model, QA/QC, balances, scenarios (about 1 min)
python -m spbm run                 # full analysis incl. Monte Carlo, validation, sensitivity (about 40 min)
python -m spbm run --mc 200        # more Monte Carlo realisations
```

The run is deterministic: the base case has no randomness and the Monte Carlo uses the fixed seed in the configuration, so re-running gives identical numbers.

Other commands:

```bash
python -m spbm ingest PATH ...     # add files, folders or zips to the managed raw store
python -m spbm update              # import new data from data/inbox/ and re-run
python -m spbm qaqc                # data checks only
python -m spbm status              # registered input files and run log
python -m spbm run --fast --until "2026-03-23 07:00" --out outputs_demo   # model with data up to a date
```

`examples/demo_update.sh` builds a model with the data available on 22 March, updates it with the rest, and prints the change report.

## Inputs

| Input | Format |
|---|---|
| `Data_Topo 2026.zip` | The supplied data: FMS dump records (CSV) and the survey change solids (DXF). Never modified |
| FMS | CSV with columns `Cycle ID, Truck PayLoad, Au, Ag, Cu, Dens, X (Dump Event), Y (Dump Event), Z (Dump Event), Dump_tstamp` |
| Surveys | DXF with 3DFACE entities forming a closed change solid; the file name contains the nominal date as `YYMMDD` |
| `config/project.yaml` | Every parameter, tagged with its assumption ID |
| `config/manual_interventions.csv` | The only way to correct data (`id, type, target, value, reason, author, date, approved_by`); a row without reason, author or date stops the run |

On the first run every source file is hashed (SHA-256) and copied once into `data/raw_store/`; the analysis reads only from there. New data go into `data/inbox/` (or `python -m spbm ingest <path>`), followed by `python -m spbm update`.

Intervention types: `survey_date`, `survey_cutoff_hours`, `fms_exclude`, `fms_location_unknown`, `supersede`. The two supplied rows (MI-001, MI-002) re-date `Topo_250328.dxf` and `Topo_250329.dxf` to 2026.

## Steps the platform runs

1. **Ingest and QA/QC** (`io.py`, `dataset.py`, `rules.py`, `qaqc.py`): hash and register inputs, apply interventions, check every FMS record and survey file against the rule catalogue. Records are flagged, never deleted.
2. **Growth and timing** (`growth.py`, `volume.py`): scan the survey cut-off (result: D+1 07:00), calibrate the volume factor f_v and test it on held-out intervals.
3. **Surfaces** (`grid.py`, `surfaces.py`): rasterise the change solids on a 1 m grid, fit the floor plane, infer the pre-record surface.
4. **Reconstruction** (`movement.py`): for each survey interval, compute cuts, fill and the push cost, solve the transport problem (log-domain Sinkhorn), deposit layers; carry retained material forward; place loads after the last survey with the forward model (`forward.py`).
5. **Block model** (`blockmodel.py`, `bmviz.py`): integrate layers into 5 × 5 × 2 m blocks, with provenance, information and confidence classes.
6. **Validation** (`validation.py`): mass and metal balance, geometry check, forward-model temporal test, synthetic twin, numerical robustness.
7. **Uncertainty** (`uncertainty.py`): Monte Carlo, one-at-a-time sensitivity, volume-gap scenarios.
8. **Audit** (`audit.py`): run manifest (input hashes, configuration, code identity, library versions), model-version history and change report.

## Outputs

Everything is written to `outputs/` (not committed; regenerate with `python -m spbm run`).

| Folder / file | Content |
|---|---|
| `blockmodel/` | Block model (CSV, VTK), block definition, summaries by class, confidence, bench; grade-tonnage; figures |
| `movement/` | Destination of each load, transport plans of every interval, surfaces as ESRI ASCII grids |
| `qaqc/` | Rule catalogue, records with one column per rule, daily coverage, grade signatures, survey QA, figures |
| `growth/` | Interval reconciliation, cut-off scan, volume-factor calibration and hold-out, figures |
| `validation/` | Mass/metal balance, inventory by class, geometry, temporal test, twin, robustness |
| `uncertainty/` | Monte Carlo realisations and summary, sensitivity table, scenarios, figures |
| `audit/` | Data registry, ingest log, survey register, interventions applied, run manifest, configuration used, run log, change report |
| `history/<run_id>/` | Manifest and key tables of every model version |
| `summary.json`, `summary_tables.md` | Key numbers and tables of the run |

## Base-case results

| Class | Tonnes | Cu % | Au g/t | Basis |
|---|---|---|---|---|
| FMS-tracked (survey-reconciled + provisional) | 44,650 | 8.42 | 8.00 | measured tonnes and grades |
| Unattributed (surveyed fill, no FMS record) | 3,901 | 10.22 | 8.82 | imputed grade |
| **Record period (15-31 March)** | **48,551** | 8.57 | 8.06 | |

* Monte Carlo P10/P50/P90 of record-period tonnes: 48.5 / 51.9 / 55.4 kt. The base case sits near P10 because the only sampled alternative for payloads (under-recording) adds tonnes.
* If the 47% volume excess is loads missing from the FMS rather than bulking, record-period tonnes are 71,338 t (scenario X2, outside the ranges).
* Survey cut-off D+1 07:00; volume factor f_v = 1.472 (hold-out error 3.5%).
* FMS mass and metal are conserved exactly (relative error < 1e-9); model surface vs survey RMSE 0.03 m.
* Pre-record core 89,795 t (inferred geometry, assumed grade); whole modelled pile 138,346 t.

Grade units are as supplied and unconfirmed (8.4% Cu / 8.0 g/t Au is about ten times typical Cu-Au feed). Confirm with Geology before using any contained-metal figure.

## Layout

```
Data_Topo 2026.zip     supplied data (read into data/raw_store/ on first run)
config/                parameters and manual interventions
spbm/                  platform source code
tests/                 unit, real-data and platform tests
examples/              update demonstration
METHOD.md              mathematics, algorithm, validation and assumptions
```
