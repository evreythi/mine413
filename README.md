# SPBM: stockpile model

SPBM works out where the ore in the Pit I copper-gold stockpile came from and what grade it is, block by block.

**The problem.** Trucks dump ore on top of the stockpile and dozers push it over the edge. Nobody records where each truckload finally ends up, so the grade inside the pile is unknown.

**What we have.** Two records:

* the truck system (FMS) says *what* each truck dumped (tonnes, grade), *where* and *when*;
* the surveys show *where* the pile grew between survey dates.

**What SPBM does.** For each period between surveys it matches the truckloads to the new volume the survey shows, choosing the arrangement that needs the least dozer pushing. Every tonne of ore and metal the trucks recorded is kept. Nothing is lost or invented. The result is a 3-D block model (5 × 5 × 2 m blocks) with tonnes, Cu, Au and Ag, a confidence rating for each block, and a range (low / likely / high) for every total.

The maths, the steps and every assumption (A-01 to A-32) are explained in **[METHOD.md](METHOD.md)**.

## Starting it (no typing needed)

Double-click the launcher for your computer:

| Computer | Double-click |
|---|---|
| Windows | `Start SPBM (Windows).bat` |
| Mac | `Start SPBM (Mac).command` (the first time, right-click it and choose **Open**) |
| Linux | `start_spbm.sh` |

The first start takes a few minutes to set everything up. It needs [Python](https://www.python.org/downloads/) 3.10 or later. After that, SPBM starts in a few seconds and opens in your web browser. It runs quietly in the background and stops by itself about 15 minutes after you close the page (never in the middle of a run).

You can also open **`SPBM.html`**: it jumps straight to SPBM if it is running, and otherwise tells you how to start it. A web page cannot start a program by itself, because browsers do not allow that, so the launcher is needed once per session.

### What the page does

* **Overview** and **How it works**: what the model is and how it gets its answer, in plain language.
* **Parameters**: change any value or assumption (angle of repose, swell/volume factor, density, survey timing, dozer push, block size, uncertainty ranges…), on a form or as raw text. Your changes are saved separately (`config/project_custom.yaml`) and their results go to `outputs_custom/`. The official settings and results are never changed. The model has no prices or economic values; it reports tonnes, grades and contained metal.
* **Upload & run**: drag in new truck data (`.csv`) or surveys (`.dxf`), tick which steps to run, and watch the progress bar. The core always runs, takes about 20 s, and produces the full block model. The slow extras can each be turned off:

  | Step | Time |
  |---|---|
  | Monte Carlo (60 runs) | ~13 min |
  | Sensitivity | ~9 min |
  | Forward-model test | ~6 min |
  | Robustness | ~4.5 min |
  | Synthetic test | ~1.5 min |
  | Scenarios | ~40 s |
  | Figures | ~5 s |

* **Results**: key numbers, checks, scenarios, every figure and table, and downloads (block model as CSV and VTK). You can switch between the official results and your custom ones.

## Running from a terminal (optional)

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m spbm serve --open        # the web page (same as the launcher)
python -m spbm run --fast          # core + scenarios, about 1 min
python -m spbm run                 # everything, about 35 min
python -m spbm run --skip mc,sensitivity   # leave out chosen steps
python -m pytest -q                # 71 automated checks, about 2-3 min
```

Steps that `--skip` accepts:

| Name | Step |
|---|---|
| `align` | survey-timing check |
| `mc` | Monte Carlo |
| `temporal` | forward-model test |
| `twin` | synthetic test |
| `robust` | robustness |
| `scenarios` | scenarios |
| `sensitivity` | sensitivity |
| `figures` | figures |

Other commands:

* `python -m spbm update` picks up new files dropped into `data/inbox/` and re-runs.
* `python -m spbm qaqc` runs the data checks only.
* `python -m spbm status` lists the files the program knows about and the past runs.
* `examples/demo_update.sh` builds the model with data up to 22 March, then updates it with the rest.

Every run is repeatable: the same data and settings give exactly the same numbers.

## Inputs

* **`Data_Topo 2026.zip`**: the supplied truck records and surveys. It is never modified. On the first run each file is fingerprinted and copied into `data/raw_store/`, and the program only reads from there.
* **Truck records (FMS)**: CSV with `Cycle ID, Truck PayLoad, Au, Ag, Cu, Dens, X (Dump Event), Y (Dump Event), Z (Dump Event), Dump_tstamp`.
* **Surveys**: DXF change solids; the file name contains the date as `YYMMDD`.
* **`config/project.yaml`**: every setting, each tagged with its assumption number.
* **`config/manual_interventions.csv`**: the only way to correct the data. Every correction needs a reason, an author and a date. The two supplied rows fix the year in two survey file names.

## What it produces

All results go to `outputs/`; the results of the full run `20261118T182336` are included.

| Folder | Content |
|---|---|
| `blockmodel/` | Block model (CSV for mine-planning software, VTK for ParaView), summaries, figures |
| `movement/` | Where each truckload went; surfaces as grids |
| `qaqc/` | Data checks |
| `growth/` | How the pile grew; survey timing; tonnes-to-volume factor |
| `validation/` | Mass and metal balance, surface check, model tests |
| `uncertainty/` | Monte Carlo ranges, sensitivity, scenarios |
| `audit/` | Fingerprints of the inputs, settings and code version used; change report |
| `history/` | A copy of the key results of every run |

## Main results

| Material placed 15-31 March | Tonnes | Cu % | Au g/t | |
|---|---|---|---|---|
| Recorded by the trucks | 44,650 | 8.42 | 8.00 | measured |
| Surveyed but not in the truck records | 3,901 | 10.22 | 8.82 | grade estimated |
| **Total** | **48,551** | 8.57 | 8.06 | |

* **Likely range:** 48.5 to 55.4 kt (P10 to P90, middle 51.9 kt). The base case is at the low end because the only alternative tested for truck payloads (under-recording) can only add tonnes.
* **Volume gap:** the surveys show about 47% more volume than the truck tonnes would fill at their recorded density. The base case treats this as loose material taking up more room (swell). If it were truckloads missing from the records instead, the total would be 71,338 t. The data cannot rule that out, so it is reported separately.
* **Checks:** truck tonnes and metal are kept exactly, and the model surface matches the latest survey to 0.03 m.
* **Whole pile:** about 138,346 t. Of that, 89,795 t was already there before the records start; its shape is estimated and its grade assumed.

Grade units are as supplied and unconfirmed: 8.4% Cu and 8 g/t Au is about ten times typical copper-gold ore. Check with Geology before using any contained-metal number.

## Folder layout

```
Start SPBM (…)         double-click launchers (Windows, Mac); start_spbm.sh for Linux
SPBM.html              opens SPBM if it is running, otherwise explains how to start it
Data_Topo 2026.zip     supplied data
config/                settings and data corrections
spbm/                  program code (spbm/web.py and spbm/webui/ are the web page)
tests/                 automated checks
outputs/               results of the full run
current docs/          report, presentation and other course documents
METHOD.md              maths, steps and assumptions
```
