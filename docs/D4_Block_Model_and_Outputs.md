---
title: "D4 - Stockpile Block Model and Model Outputs"
subtitle: "Pit I HG stockpile - current state after the 2026-03-29 survey (provisional through 2026-03-31)"
---

# 1. Model files

| File | Format | Use |
|---|---|---|
| `outputs/blockmodel/stockpile_block_model.csv` | CSV, one row per block containing material (2,699 blocks) | Excel, Vulcan, Datamine, Leapfrog, Deswik (import with centroid + size) |
| `outputs/blockmodel/stockpile_block_model.vtk` | VTK structured points, cell data | ParaView 3-D viewing (*Threshold* `tonnes > 0`) |
| `outputs/blockmodel/block_model_definition.json` | JSON | Origin, block size, dimensions, units, CRS note |
| `outputs/movement/*.asc` | ESRI ASCII grids (1 m) | Floor plane, pre-record surface, final model surface, latest surveyed surface (GIS / CAD) |
| `outputs/movement/load_destinations.csv` | CSV | Where each truck load was placed (destination centroid, push distance, spread) |
| `outputs/blockmodel/summary_*.csv` | CSV | Inventory by material source (**exact** class split), by dominant information class (whole blocks), confidence class, 4 m bench; grade-tonnage |

**Block definition.** Origin (lower-left-bottom corner) E 511,290, N 7,122,280, Z 4,474.0. Blocks 5 × 5 × 2 m; 27 × 26 × 10 blocks. Partial blocks are exported with `fill_frac` and their true material volume. Coordinates are in the mine grid (see D2, A-01).

**Units.** Tonnes are as reported by the FMS (moisture basis not stated, A-26). Block volumes use the in-pile volume T × f_v / Dens with the calibrated volume factor f_v = 1.472. In the base case the in-pile density is 1.40 t/m³ (A-06; D2 Section 2.5). Cu is in %, Au and Ag in g/t (as supplied, see QA-F04). Contained Cu is in tonnes, Au and Ag in kg (1 koz = 31.1035 kg).

## 1.1 Block fields

| Field | Meaning | Info type |
|---|---|---|
| `ix, iy, iz, xc, yc, zc, dx, dy, dz` | Block index, centroid, size | - |
| `volume_m3`, `fill_frac` | Material volume in block; fraction of block filled | Measured geometry + inferred where unsurveyed |
| `tonnes`, `density` | Total tonnes; derived in-pile density (tonnes ÷ volume) | Measured tonnes, calibrated volume (FMS); assumed by class otherwise |
| `cu_pct, au_gpt, ag_gpt` | Best-estimate grade (all classes) | Mixed: see class fractions |
| `cu_t, au_kg, ag_kg` | Contained metal | Mixed |
| `t_fms, t_unattributed, t_legacy, t_provisional` | Tonnes by information class (`t_legacy` = pre-record core) | - |
| `frac_fms, frac_unattributed, frac_legacy` | Class fractions | - |
| `cu_pct_fms, au_gpt_fms` | Grade of the FMS-tracked part only | Measured inputs, model-generated placement |
| `cu_sd_within, au_sd_within` | Grade heterogeneity among the loads mixed into the block | Model-generated |
| `n_eff_loads, n_loads_ge1pct, top_loads` | Effective number of loads; loads ≥ 1% of block; top three cycle IDs with share | Model-generated provenance |
| `mean_place_date` | Tonnage-weighted placement time of FMS material | Measured + model |
| `top_surveyed_frac` | Fraction of block footprint whose top surface was surveyed | Measured |
| `cu_p10/p50/p90, au_p10/p50/p90, tonnes_p10/p90, cu_cv, au_cv, tonnes_cv` | Uncertainty (Monte Carlo, 60 realisations; prior load-scale range for blocks < 50% FMS-tracked, see `grade_range_basis`) | Model-generated |
| `info_class` | Dominant class: FMS-reconciled / Unattributed-imputed / Legacy-assumed / Provisional | - |
| `confidence` | High / Medium / Low / Uninformed (rules in D3, Section 5.1) | - |

# 2. Inventory

## 2.1 By information class (base case)

*Inventory by information class (FMS grades/metal shown for the whole FMS class)*

| class | tonnes | share | Cu % | Au g/t | Cu (t) | Au (koz) | basis of grade |
|---|---|---|---|---|---|---|---|
| FMS-tracked, survey-reconciled | 44,422 | 32.1% | 8.42 | 8.00 | 3,760 | 11.5 | measured inputs; location model-generated |
| FMS-tracked, provisional (after last survey) | 228 | 0.2% |  |  |  |  | measured inputs; location from forward model |
| Unattributed (surveyed volume, no FMS record) | 3,901 | 2.8% | 10.22 | 8.82 | 399 | 1.1 | imputed (same/adjacent intervals) |
| **Record-period total** | 48,551 | 35.1% | 8.57 | 8.06 | 4,159 | 12.6 |  |
| Pre-record core (legacy) | 89,795 | 64.9% | 8.42 | 8.00 | 7,562 | 23.1 | assumed (FMS mean); geometry inferred |
| Whole pile modelled | 138,346 | 100.0% | 8.47 | 8.02 | 11,722 | 35.7 |  |


> **Read the record-period total first.** It is the material placed during the FMS record (15-31 March) and is tied to surveyed fill. The pre-record core has inferred geometry and an assumed grade. The whole-pile total includes it.
>
> **Not included in any range in this table:** the interpretation that the 47% volume excess is loads missing from the FMS. In that case record-period tonnes would be 71,338 t (scenario X2, D6 Section 10.2).
>
> **Two class tables.** This table is the *exact* split: every block's tonnes are divided among the classes. `summary_by_dominant_info_class.csv` instead counts each whole block under its dominant class, for maps and reclaim planning, so its class totals differ even though the grand total is the same.
>
> **Identical grades across classes** follow from the assumptions: legacy grade = FMS mean (A-22), and unattributed grade is imputed from the same loads (A-21).
>
> **Grade units are as supplied and unconfirmed (QA-F04).**

> **Reading this table.** Only the first two rows rest on measured grade data. The unattributed row has a measured volume but an imputed grade. The pre-record core's grade is assumed, and its volume depends on assumptions A-13 and A-14.

## 2.2 By confidence class

*Table 8.1 - Inventory by confidence class*

| confidence | blocks | tonnes | cu_pct | au_gpt | cu_t | au_koz |
|---|---|---|---|---|---|---|
| High | 695 | 36,117 | 8.26 | 7.90 | 2,983 | 9.2 |
| Medium | 242 | 10,703 | 9.22 | 8.40 | 987 | 2.9 |
| Low | 122 | 6,574 | 8.97 | 8.30 | 590 | 1.8 |
| Uninformed | 1,640 | 84,951 | 8.43 | 8.01 | 7,161 | 21.9 |


## 2.3 By 4 m reclaim bench

*Table 8.2 - Inventory by 4 m reclaim bench (all classes; see D4 for class split)*

| bench | blocks | tonnes | cu_pct | au_gpt | cu_t | au_koz |
|---|---|---|---|---|---|---|
| 4490-4494 | 18 | 50 | 8.72 | 9.96 | 4 | 0.0 |
| 4486-4490 | 460 | 14,305 | 8.75 | 8.15 | 1,251 | 3.7 |
| 4482-4486 | 671 | 40,591 | 8.45 | 8.02 | 3,429 | 10.5 |
| 4478-4482 | 757 | 46,928 | 8.43 | 8.00 | 3,957 | 12.1 |
| 4474-4478 | 793 | 36,472 | 8.44 | 8.00 | 3,080 | 9.4 |


Source: `outputs/blockmodel/summary_by_bench_4m.csv` (model run 20261008T074247).

# 3. Visualisations

![Cu grade by 2 m bench](../outputs/blockmodel/fig_bm_plans_cu_pct.png)

![Au grade by 2 m bench](../outputs/blockmodel/fig_bm_plans_au_gpt.png)

![Fraction of block tonnes that is FMS-tracked](../outputs/blockmodel/fig_bm_plans_frac_fms.png)

![Sections through the tonnage-weighted centre of FMS material](../outputs/blockmodel/fig_bm_sections_cu_pct.png)

![3-D view: FMS-tracked blocks coloured by Cu](../outputs/blockmodel/fig_bm_3d_cu_pct.png)

![Share of column tonnes by information class](../outputs/blockmodel/fig_bm_information_class.png)

![Confidence classes](../outputs/blockmodel/fig_bm_confidence.png)

![Grade-tonnage curves](../outputs/blockmodel/fig_bm_grade_tonnage.png)

![Block uncertainty (Monte Carlo)](../outputs/uncertainty/fig_unc_block_maps.png)

# 4. How to use the model

* **Reclaim sequencing / blending.** Filter `confidence ∈ {High, Medium}` for material whose grade rests on FMS data. Use `cu_p10` and `cu_p90` to test blends against plant constraints. Treat `Legacy-assumed` blocks as unknown-grade material until sampled.
* **Plant-feed / metal forecasting.** Use the bench summaries with their P10-P90 ranges. Report the record-period inventory first and separately from the pre-record core (D6, Section 13). Quote the scenario X2 next to any tonnage range.
* **Reconciliation.** `top_loads` and `load_destinations.csv` let mill or stacker grade measurements be compared with the loads predicted to be in a reclaimed block. This is how ε and the push parameters should be calibrated in operation.
* **Updating.** After each new survey run `python -m spbm update`. Provisional blocks will be re-reconciled.
