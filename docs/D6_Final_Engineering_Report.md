---
title: "Long-Term Stockpile Reconstruction and Block Modelling - Pit I HG Stockpile"
subtitle: "D6 Final Engineering Report to Mine Management | MIN E 413 Surface Mining Methods and Operations Management, Fall 2026"
author: "Long-Term Mine Planning Team: [Member 1], [Member 2], [Member 3], [Member 4], [Member 5]"
date: "November 2026 - model run 20261007T081228"
---

# Executive Summary

**Request.** The Mine Manager asked for a defensible platform that reconstructs how truck-dumped material moved through the growing Pit I high-grade (HG) stockpile, estimates where it now resides, and produces an updatable block model of tonnage, Cu, Au, contained metal and uncertainty.

**Data.** We received 275 FMS dump records (44,650 t, 2026-03-15 to 03-31) and ten Vulcan survey files. Our QA/QC showed that each survey file is a **closed change solid**: its top is the new surface and its bottom is the previous surface, over the area that changed. This gives measured daily fill (35,096 m³ in total). The data also have important gaps:

* Payloads are bucket-pass estimates; every value is a multiple of 38 t.
* Grades are 21 source-block signatures, not load assays.
* Dump elevations are unreliable, and 14 records carry a default (stuck) position.
* Two survey files carry the wrong year.
* No survey exists for 03-17 or 03-23 to 03-26.
* The FMS is silent for long periods (03-16 12:27 to 03-18 20:47, and 03-22 18:28 to 03-28 03:54, apart from one load on 03-25) while the surveys show material being placed.

**Method.** We developed **CPST (Constrained Push-and-Settle Transport)**. For each survey period, the observed fill defines where material went. The FMS loads (plus material carried over on the platform, and dozer cuts) are the sources. A slope-aware dozer push cost and entropy-regularised optimal transport decide which source filled which part of the observed fill. The mixing length is ε = 6 m. Two dummy nodes make data mismatches explicit: fill without an FMS source becomes **unattributed** material with an imputed grade, and FMS volume not seen on the face is **retained** and carried to the next period. All operations act on extensive quantities (tonnes, metal), so **mass and metal are conserved exactly**. A separate forward physics model (dozer push to the crest + avalanche at the 37° angle of repose measured from the surveys) is used for prediction, nowcasting and known-truth testing.

**Results (base case, 5 × 5 × 2 m blocks).**

| Material class | Tonnes | Share | Cu % | Au g/t | Basis of grade |
|---|---|---|---|---|---|
| FMS-tracked (survey-reconciled + 228 t provisional) | 44,650 | 22.1% | 8.42 | 8.00 | Measured inputs |
| Unattributed (surveyed, no FMS record) | 41,758 | 20.7% | 8.62 | 8.00 | **Imputed** |
| Legacy (pre-record pile) | 115,699 | 57.2% | 8.42 | 8.00 | **Assumed** |
| **Total modelled** | **202,107** | 100% | 8.46 | 8.00 | |

* Monte Carlo (60 realisations) P10/P50/P90: total tonnes 185 / 201 / 218 kt; contained Cu 15.4 / 17.0 / 19.0 kt; contained Au 46.9 / 51.7 / 56.9 koz. The FMS-tracked class: Cu grade P10-P90 8.05 - 8.88 %.
* Validation:
  * FMS tonnes, Cu, Au and Ag balance to floating-point precision.
  * The reconstructed surface matches the latest surveys (RMSE 0.03 m; 100.0% of cells within the 0.14 m detection limit).
  * On held-out periods the forward model's earth-mover error is 18.6 m, vs 20.4 m without dozer push.
  * In a synthetic twin with known truth, CPST recovers block Cu with RMSE 0.80% (r = 0.90), vs 1.18% for a period-average model and 1.83% for a single mean grade.

**Key conclusions.**

1. Only about one fifth of the modelled stockpile has a measured grade basis. A "definitive" Cu-Au inventory of the whole pile cannot be supported by the supplied data.
2. The FMS-tracked material forms the outer skin of the pile on the advancing south face and upper benches. It can support near-term reclaim planning with the stated P10-P90 ranges.
3. The largest uncertainties are the grade of the legacy core and the density/swell basis, not the reconstruction algorithm.

**Recommendations.**

1. Obtain a full-pile survey and, if one exists, a pre-stockpile ground survey.
2. Audit FMS completeness for the gap periods.
3. Sample the legacy core for grade, density and moisture.
4. Run tracer and mill-reconciliation trials to calibrate mixing.
5. Adopt the platform with the governance controls in Section 13. Run `python -m spbm update` after every survey.

# Introduction and Project Objectives

Pit I will be exhausted by the end of 2026. Its long-term HG stockpile then becomes a principal plant feed source. Reclaim sequencing, blending, metal forecasting and economic evaluation all require knowing *what material is where* in the pile. Unlike an in-situ deposit, a stockpile cannot be reconstructed from dump coordinates alone: dozers push loads to and over the crest, and gravity carries material down the face.

The ten objectives of the brief map onto this report as follows. QA/QC (Section 4); growth reconstruction (Section 5); movement algorithm with mass and metal balance (Section 6); 3-D distribution and block model (Section 8); validation (Section 9); sensitivity (Section 10); platform (Section 11); professional practice (Section 13). Assumptions are maintained in the register (Section 7 and D2).

# Description of Available Data

| Dataset | Content | Coverage |
|---|---|---|
| FMS (`Dump Data.csv`) | 275 records: cycle ID, payload, Cu %, Au g/t, Ag g/t, density, dump X/Y/Z, timestamp | 2026-03-15 17:43 to 03-31 20:52; 44,650 t |
| Surveys (10 DXF) | Vulcan 3DFACE closed change solids of layer `*_HGHS*` | 03-15, 16, 18, 19, 20, 21, 22, 27, 28, 29 (after re-dating) |
| Not supplied | Full-pile surface, original ground, truck ID, source bench, moisture, density tests, dozer records | - |

Coordinates are a projected mine grid in metres (E ≈ 511,300, N ≈ 7,122,300, Z ≈ 4,480 m). The FMS and surveys overlay consistently, so no transformation was applied (A-01). Units are as supplied. The grade magnitudes (mean 8.4% Cu, 8.0 g/t Au) are unusually high for a Cu-Au operation, and the units should be confirmed with geology (QA-F04). All conclusions about *relative* distribution are unaffected.

# Data Analysis and QA/QC

The full QA/QC is in D2 Section 2 and `outputs/qaqc/`. No record was deleted. Fourteen flags were applied, each with a documented treatment (Table 4.1).

*Table 4.1 - FMS flags (records retained; treatment as stated)*

| flag | description | records | treatment |
|---|---|---|---|
| F01_duplicate_id | Duplicate Cycle ID | 0 | Second occurrence excluded from modelling, kept in register |
| F02_missing_field | Missing mandatory field | 0 | Excluded from modelling (cannot be placed/graded), kept in register |
| F03_bad_timestamp | Unparseable timestamp | 0 | Excluded from modelling, kept in register |
| F04_id_out_of_order | Cycle ID not in chronological order | 33 | Information only - timestamp governs ordering |
| F05_low_payload | Payload < 50% of median (part load) | 2 | Retained; higher payload uncertainty in Monte Carlo |
| F06_high_payload | Payload > 150% of median | 3 | Retained; checked against truck class; higher uncertainty |
| F07_grade_outlier | Grade outside Q1-3IQR..Q3+3IQR or <=0 | 1 | Retained (source-block grade); flagged |
| F08_density_range | Density outside 1.5-3.0 t/m3 | 0 | Retained; flagged |
| F09_far_from_face | Dump > 60 m from any surveyed change | 0 | Retained; push distance check |
| F10_below_floor | Dump Z below fitted stockpile floor - 0.5 m | 14 | Retained; XY used, Z not used by algorithm |
| F11_z_residual | |Dump Z - surface| > 3 m where surface known | 29 | Retained; Z not used by algorithm (XY only) |
| F12_after_last_survey | Dump after the last survey | 1 | Placed provisionally (unreconciled) - updated when next survey arrives |
| F13_survey_gap_period | Dump inside a period with a missing survey | 18 | Retained; period flagged in reconciliation |
| F14_repeated_location | Identical X/Y/Z shared by >= 3 records (default / stuck FMS position) | 14 | Retained; X/Y imputed as tonnage-weighted centroid of the period's other dumps, GPS error x5 in Monte Carlo |


**Principal findings and their influence on the model.**

* **Surveys are change solids (QA-S01).** Every rasterised cell is crossed by exactly two faces. The divergence-theorem volume equals the gridded volume. The bottom of each solid equals the top of the previous one to 0.000 m (P5-P95) in overlaps. This turned a "partial surface" problem into a measured-fill problem.
* **Mis-dated files (QA-S02).** `Topo_250328/250329` were re-dated to 2026-03-28/29 by a logged override. All ten layer names carry the year token '25', so the year in names is unreliable, but the FMS dates and face progression are unambiguous.
* **Survey timing (QA-S03).** Assigning surveys to 23:59 gives r = 0.96 between period FMS volume and surveyed volume. Any time before 10:00 gives r ≤ 0.21 (alignment figure below).
* **Elevation decreases hidden in solids (QA-S05)** and **toe-clipped solids (QA-S06)**. These are handled as dozer cuts and as unobserved toe fill respectively.
* **Payload and grade (QA-F02, F03).** Payloads are estimated, not weighed, and grades are source-block values. Both enter the uncertainty analysis as correlated errors.
* **Dump Z (QA-F06).** Z minus the surveyed surface at dump time has P10/P90 of −2.8/+2.0 m, so only X/Y is used.
* **Default FMS position (QA-F11).** Fourteen records (2,356 t) share one identical position, below the floor and in front of the toe. This is a default or stuck position, not a dump location, so their X/Y is imputed from the other dumps of the same period (A-32). The originals are retained.
* **Completeness (QA-F07).** FMS and survey coverage are uneven in time (daily coverage figure below).

![Dump locations (orange, by day) and survey change-solid footprints (blue, light = early).](../outputs/qaqc/fig_qaqc_dump_map.png)

![Daily FMS tonnage and survey solid volume. Shaded: survey change without FMS records.](../outputs/qaqc/fig_qaqc_daily_tonnage_volume.png)

![Temporal alignment of FMS and surveys as a function of the assumed survey time of day.](../outputs/growth/fig_temporal_alignment.png)

![Change-solid thickness of each survey.](../outputs/qaqc/fig_qaqc_survey_solids.png)

![Payload values and grade signatures.](../outputs/qaqc/fig_qaqc_payload_grades.png)

![Surveyed face slopes; the angle of repose (A-03) is taken from this distribution.](../outputs/qaqc/fig_qaqc_repose.png)

# Stockpile Growth Analysis

The stockpile grew by end-dumping on a platform at about 4,488-4,490 m. Dozers pushed material over a crescent-shaped crest, and the south face advanced about 30 m in two weeks (face-advance map below). The face stands at a median 36.7° (P75 38.5°). The floor is a near-horizontal plane at 4,475.1 m (dip 0.29°, residual SD 0.26 m).

![Survey period in which each cell first received fill.](../outputs/growth/fig_growth_face_advance.png)

![Elevation increase per period with the truck dumps of that period.](../outputs/growth/fig_growth_period_maps.png)

**FMS vs survey reconciliation.** Table 5.1 compares, per survey period, the surveyed fill with the FMS volume (tonnes ÷ FMS density).

*Table 5.1 - Period reconciliation (FMS m³ includes volume carried over from the previous period)*

| period end | gap | loads | FMS t | FMS m³ | solid m³ | fill m³ | cut m³ | unattributed m³ | retained m³ | FMS explains | FMS Cu % | FMS Au g/t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 03-15 |  | 11 | 1,976 | 998 | 2,867 | 2,853 | 0 | 1,855 | 0 | 35% | 8.61 | 9.96 |
| 03-16 |  | 28 | 4,598 | 2,145 | 2,306 | 2,932 | 0 | 787 | 0 | 73% | 10.05 | 7.48 |
| 03-18 | yes | 17 | 2,698 | 1,265 | 4,843 | 5,683 | 319 | 4,099 | 0 | 28% | 7.06 | 7.39 |
| 03-19 |  | 75 | 12,616 | 5,920 | 8,708 | 11,286 | 0 | 5,367 | 0 | 52% | 6.37 | 7.31 |
| 03-20 |  | 36 | 6,004 | 2,819 | 2,151 | 2,474 | 0 | 0 | 345 | 100% | 5.81 | 7.30 |
| 03-21 |  | 11 | 1,710 | 1,149 | 1,426 | 1,564 | 4 | 411 | 0 | 74% | 12.17 | 5.85 |
| 03-22 |  | 27 | 4,522 | 2,261 | 2,888 | 3,280 | 57 | 962 | 0 | 71% | 9.33 | 9.25 |
| 03-27 | yes | 1 | 152 | 72 | 3,679 | 5,086 | 13 | 5,001 | 0 | 2% | 5.78 | 6.30 |
| 03-28 |  | 50 | 7,182 | 3,744 | 4,919 | 5,501 | 173 | 1,583 | 0 | 71% | 12.11 | 8.72 |
| 03-29 |  | 18 | 2,964 | 1,498 | 1,310 | 1,693 | 0 | 195 | 0 | 88% | 8.66 | 9.89 |


Interpretation:

* **Gap periods (03-18 and 03-27)** have little FMS (28% and 2% of fill explained). This is a *data* limitation: missing FMS records and missing surveys, not a physical effect.
* **First period (03-15).** The FMS starts at 17:43, so only 35% of that period's fill can be explained.
* **Complete days** have a pooled apparent density of 1.67 t/m³ against an FMS density of 2.06 t/m³ (κ ≈ 0.81). Two explanations remain open: swell or loose end-dumped placement (physical), or a few percent of unrecorded loads (data). The data cannot separate them, so κ is sampled over 0.80-1.05.
* **Dozer lag (physical).** On 03-20, FMS volume exceeds the fill by 345 m³. The surplus is pushed on 03-21, and CPST carries it forward explicitly.
* **Cuts.** 567 m³ of dozer cuts were re-handled. The sub-threshold change not modelled is 96 m³ (0.2%).

![Cumulative FMS tonnes vs surveyed volume × FMS density.](../outputs/growth/fig_growth_cumulative.png)

![Period reconciliation.](../outputs/growth/fig_growth_period_reconciliation.png)

# Material-Movement Methodology

The full derivation, pseudocode and flowcharts are in D3. In summary, each period's update answers the required questions:

| Question | CPST answer |
|---|---|
| A. Initial placement | Each load is a parcel of volume m/(κρ) at its reported X/Y (GPS error σ = 3 m in the Monte Carlo) |
| B. Direction | Least-work route over the pre-period terrain: geodesic distance with uphill penalty α = 4 m per m of lift. The survey decides which face sector received fill |
| C. Distance / stopping | Material stops where observed accommodation space exists (capacity constraint). Max push 90 m. Unplaceable volume is retained on the platform (dozer lag) |
| D. Downslope behaviour | The layer top is the surveyed surface, with faces at the measured repose angle. Forward model: avalanche CA at 37° |
| E. Mixing | Entropic OT with mixing length ε = 6 m. Grades composited from metal ÷ tonnes |
| F. Surface reconciliation | Column marginals = observed fill, so the model surface = survey (residual ≤ 8×10⁻⁷) |
| G. Mass conservation | Row sums exact by construction; unattributed and legacy volumes kept in separate classes |
| H. Metal conservation | All operations linear in metal; verified to 10⁻¹² relative |
| I. Sequential updating | Column stacks plus carried parcels form the initial state of the next period. Cuts remove and re-handle the column top |
| J. Numerical stability | Log-domain Sinkhorn (tolerance 10⁻⁶); 1 m grid; robustness tested (Section 9.6) |

![CPST algorithm for one survey period.](figures/fig_algorithm.png)

**Why optimal transport?** Moving cut volume to fill volume with minimum work is the original optimal-transport problem (Monge, 1781). The entropic form adds exactly one physically interpretable parameter, the mixing length. It is solved robustly with Sinkhorn iterations, and it guarantees conservation. Rules that push each load to its nearest crest cell cannot honour the observed fill, while black-box regression has no training data. The forward-model test (Section 9.3) shows that physics alone predicts the fill location only moderately well, which confirms that survey constraint is necessary.

![Reconstructed (volume-weighted) push distances.](../outputs/growth/fig_growth_push_distance.png)

# Assumption Register

The complete register (31 assumptions with need, justification, consequence and treatment) is in D2 Section 4. The configuration file tags every parameter with its assumption ID. The assumptions with the greatest influence, from the sensitivity analysis, are:

| ID | Assumption | Effect if wrong | Treatment |
|---|---|---|---|
| A-06 | In-pile density = FMS density (κ = 1) | Total tonnes ±10% for κ ±0.1 (182-222 kt) | MC κ ~ U(0.80, 1.05); tornado |
| A-22 | Legacy grade = FMS mean | Legacy metal could differ by any amount | Separate class; "Uninformed"; prior range; sampling (R-03) |
| A-13/A-13b/A-14 | Geometry of never-surveyed parts; toe fill | 14.5 kt moves between unattributed and legacy; block Cu 0.25% | Switch tested; full survey (R-01) |
| A-05 | Survey at 23:59 | Loads shift one period; largest effect on block grades (0.28% Cu) | Alignment analysis; MC |
| A-18 | Mixing length 6 m | Block-scale grade smoothing | Twin experiment; MC; tornado |
| A-21 | Unattributed grade = neighbouring periods | Grade of 21% of tonnes | Bootstrap in MC; separate class |

# Block Model Construction

* **Block size 5 × 5 × 2 m** (27 × 26 × 10 grid; origin E 511,290 N 7,122,280 Z 4,474). Horizontal size is matched to the information resolution (GPS σ ≈ 3 m plus mixing length 6 m). Vertical size matches the daily layer thickness (median 0.9-3.0 m) and loader reclaim slices. Alternatives were tested in Section 10.
* **Partial blocks** keep their exact material volume (fill fraction). There is no sub-blocking, because layers are integrated exactly.
* **Density** per material class; block density is derived as tonnes ÷ volume.
* **Compositing** by metal ÷ tonnes. Within-block heterogeneity of mixed loads is reported.
* **Provenance**: each block lists its effective number of loads and its top three contributing cycle IDs, enabling reconciliation with plant data.
* **Uncertain or uninformed regions** are labelled by information class (FMS-reconciled, Unattributed-imputed, Legacy-assumed, Provisional) and by confidence class (High, Medium, Low, Uninformed).

*Table 8.1 - Inventory by confidence class*

| confidence | blocks | tonnes | cu_pct | au_gpt | cu_t | au_koz |
|---|---|---|---|---|---|---|
| High | 172 | 8,971 | 8.62 | 8.18 | 773 | 2.4 |
| Medium | 478 | 34,468 | 8.29 | 7.90 | 2,857 | 8.8 |
| Low | 412 | 33,534 | 8.40 | 7.95 | 2,818 | 8.6 |
| Uninformed | 1,633 | 125,134 | 8.51 | 8.03 | 10,654 | 32.3 |


![Block model Cu grade by 2 m bench.](../outputs/blockmodel/fig_bm_plans_cu_pct.png)

![Fraction of block tonnes that is FMS-tracked.](../outputs/blockmodel/fig_bm_plans_frac_fms.png)

![Sections through the centre of the FMS-tracked material. Dashed orange: pre-record surface (top of legacy).](../outputs/blockmodel/fig_bm_sections_cu_pct.png)

![3-D view of FMS-tracked blocks.](../outputs/blockmodel/fig_bm_3d_cu_pct.png)

*Table 8.2 - Inventory by 4 m reclaim bench (all classes; see D4 for class split)*

| bench | blocks | tonnes | cu_pct | au_gpt | cu_t | au_koz |
|---|---|---|---|---|---|---|
| 4490-4494 | 18 | 51 | 9.22 | 9.59 | 5 | 0.0 |
| 4486-4490 | 459 | 20,958 | 8.76 | 8.10 | 1,836 | 5.5 |
| 4482-4486 | 671 | 59,209 | 8.46 | 8.00 | 5,011 | 15.2 |
| 4478-4482 | 755 | 68,506 | 8.46 | 7.99 | 5,794 | 17.6 |
| 4474-4478 | 792 | 53,383 | 8.35 | 7.97 | 4,455 | 13.7 |


# Validation and Reconciliation

## Mass and metal balance

*Table 9.1 - FMS mass and metal balance*

| quantity | unit | FMS input | block model | difference |
|---|---|---|---|---|
| FMS tonnes | t | 44,650.000 | 44,650.000 | -2.9e-11 |
| FMS Cu | t Cu | 3,760.423 | 3,760.423 | -2.7e-12 |
| FMS Au | kg Au | 357.124 | 357.124 | -1.5e-12 |
| FMS Ag | kg Ag | 8,824.138 | 8,824.138 | -5.5e-12 |


FMS tonnes, Cu, Au and Ag entering the stockpile equal the block model inventory to floating-point precision. Volume reconciliation for the whole record:

*Table 9.2 - Volume reconciliation over the record*

| item | value |
|---|---|
| survey change-solid volume (m3) | 35,095.6 |
| observed fill used by model (m3) | 42,352.8 |
|   of which unobserved fill on first-surveyed cells (m3) | 7,231.56 |
| cut / re-handled volume (m3) | 566.95 |
| sub-threshold change not modelled (m3) | 96.2073 |
| FMS volume (tonnes / density) (m3) | 21,640.5 |
| FMS volume placed into observed fill (m3) | 22,092.2 |
| unattributed fill volume (m3) | 20,261 |
| FMS volume never reconciled (provisional) (m3) | 115.268 |
| max Sinkhorn column residual (relative) | 7.06308e-07 |


## Geometry

The survey-reconciled model surface differs from the latest surveyed surface by RMSE 0.03 m (bias -0.007 m). 100.0% of cells are within the 0.14 m detection limit. The residuals are sub-threshold changes that are intentionally not moved. Geometry is constrained by design, so this test verifies the numerics; the independent tests follow.

![Geometry check.](../outputs/validation/fig_val_geometry.png)

## Temporal behaviour (held-out periods)

The forward physics model was calibrated (repose angle, deposit radius, release offset: 27 combinations) on periods 03-16 to 03-21. It was then tested on periods 03-22 to 03-29, which it never saw, predicting each period's fill from the previous state and that period's dumps only.

*Table 9.3 - Forward model: calibration and unseen test periods (means)*

| set | mode | W1 (m) | capture | centroid error (m) |
|---|---|---|---|---|
| calibration | no-push baseline | 21.8 | 0.29 | 20.3 |
| calibration | push (calibrated) | 19.0 | 0.34 | 17.8 |
| calibration | push (default) | 20.0 | 0.37 | 18.8 |
| test (unseen) | no-push baseline | 20.4 | 0.34 | 16.1 |
| test (unseen) | push (calibrated) | 18.6 | 0.39 | 14.4 |
| test (unseen) | push (default) | 18.6 | 0.43 | 14.3 |


The dozer-push model improves on the no-push baseline in the unseen periods: lower earth-mover (W1) distance and centroid error, and higher capture. The absolute errors (about 14-18 m) are large compared with the block size. **Physics alone cannot say where on a 100 m face a day's fill will land; the surveys must constrain it.** This justifies the survey-constrained design of CPST, and the forward model is used only where no survey exists (nowcast of the 03-31 load).

![Unseen test periods: observed fill vs prediction.](../outputs/validation/fig_val_forward_test.png)

## Inversion skill: synthetic twin with known truth

A known-truth stockpile was generated from the real dump sequence with the forward model, with random dozer deviations (6 m). It was then observed as the real one is: change solids with survey noise, GPS error σ = 3 m, payload noise, and **15% of FMS records deleted**. It was reconstructed blind.

*Table 9.4 - Synthetic twin: block-level accuracy vs known truth (blocks with > 25 t of true FMS material)*

| method | blocks | cu_rmse | cu_mae | cu_corr | au_rmse | au_corr | tonnes_corr |
|---|---|---|---|---|---|---|---|
| CPST eps=2 m | 589 | 0.83 | 0.55 | 0.89 | 0.40 | 0.91 | 0.83 |
| CPST eps=6 m (base) | 589 | 0.80 | 0.56 | 0.90 | 0.39 | 0.93 | 0.83 |
| CPST eps=15 m | 589 | 0.83 | 0.60 | 0.89 | 0.42 | 0.91 | 0.83 |
| CPST eps=6, no uphill penalty | 589 | 0.80 | 0.56 | 0.90 | 0.39 | 0.93 | 0.83 |
| Baseline: period-average (eps=1e4) | 589 | 1.18 | 0.89 | 0.78 | 0.63 | 0.82 | 0.81 |
| Reference: global mean grade | 589 | 1.83 | 1.51 |  |  |  |  |


CPST recovers block Cu grade with RMSE 0.80% Cu (r = 0.90). This is a 32% lower error than allocating each period's loads uniformly over its fill, and far better than a single mean grade. The intermediate mixing length (ε = 6 m) performs best among those tested. The uphill penalty has little effect in this geometry.

![Twin experiment: true vs reconstructed block Cu.](../outputs/validation/fig_val_twin_scatter.png)

## Robustness to numerical settings

*Table 9.5 - Robustness to numerical settings*

| variant | total_tonnes | fms_tonnes | unattributed_tonnes | legacy_tonnes | tracked_blocks_cu_pct | top_bench_cu_pct | mean_abs_block_cu_change |
|---|---|---|---|---|---|---|---|
| base (1 m cell, tol 1e-6) | 202,107 | 44,650 | 41,758 | 115,699 | 8.36 | 8.59 | 0.00 |
| cell 0.5 m | 199,538 | 44,650 | 38,430 | 116,459 | 8.33 | 8.59 | 0.07 |
| cell 2.5 m | 201,035 | 44,650 | 47,009 | 109,376 | 8.36 | 8.60 | 0.12 |
| Sinkhorn tol 1e-4 | 202,107 | 44,650 | 41,758 | 115,699 | 8.36 | 8.59 | 0.00 |
| Sinkhorn tol 1e-8 | 202,107 | 44,650 | 41,758 | 115,699 | 8.36 | 8.59 | 0.00 |
| LoD k=1 (tau 0.07 m) | 202,181 | 44,650 | 41,764 | 115,767 | 8.36 | 8.59 | 0.01 |
| LoD k=4 (tau 0.28 m) | 201,883 | 44,650 | 41,423 | 115,810 | 8.35 | 8.59 | 0.02 |


Key results (class tonnages, tracked-block grade, top-bench grade) are stable under changes of grid resolution, solver tolerance and detection limit. They are not artefacts of a single numerical setting.

## Performance measures (summary)

| Measure | Value |
|---|---|
| FMS mass / metal balance error | < 10⁻⁹ relative |
| Geometry RMSE vs survey | 0.03 m |
| Sinkhorn max column residual | ≤ 8×10⁻⁷ |
| Forward model W1 (test periods) | 18.6 m (no-push 20.4 m) |
| Twin block Cu RMSE / r | 0.80% / 0.90 |

# Uncertainty and Sensitivity Analysis

Sixty Monte Carlo realisations jointly sampled the following (D3, Section 7):

* truck GPS error (σ 3 m);
* tonnage error (8% per load, 3% systematic);
* assay error (10% per grade signature);
* density/compaction (κ 0.80-1.05);
* survey bias (5 cm);
* survey timing (21:00-23:59);
* mixing length (2-15 m), uphill penalty (1-10) and maximum push (50-130 m);
* the unattributed grade (bootstrap).

*Table 10.1 - Monte Carlo summary (60 realisations); class_* rows by information class*

| quantity | P10 | P50 | P90 | cv |
|---|---|---|---|---|
| total_tonnes | 184,798.60 | 201,201.16 | 218,064.47 | 0.062 |
| cu_t | 15,390.04 | 16,983.56 | 19,021.86 | 0.083 |
| au_kg | 1,459.52 | 1,607.90 | 1,768.71 | 0.076 |
| cu_pct | 8.09 | 8.52 | 8.94 | 0.042 |
| au_gpt | 7.56 | 7.96 | 8.55 | 0.047 |
| fms_tonnes | 43,147.57 | 44,784.94 | 46,217.64 | 0.029 |
| class_fms_cu_pct | 8.05 | 8.49 | 8.88 | 0.042 |
| class_fms_au_gpt | 7.58 | 7.99 | 8.56 | 0.047 |
| class_t_u | 34,123.54 | 41,710.66 | 47,830.82 | 0.130 |
| class_t_l | 105,774.89 | 115,492.81 | 124,970.66 | 0.063 |


![Monte Carlo distributions of total tonnes and contained metal.](../outputs/uncertainty/fig_unc_global_histograms.png)

![One-at-a-time sensitivity (tornado).](../outputs/uncertainty/fig_sens_tornado.png)

![Block-level Cu uncertainty (FMS-tracked columns).](../outputs/uncertainty/fig_unc_block_maps.png)

**Interpretation.**

* **Total tonnage.** In the Monte Carlo the range is dominated by the density/swell basis (κ). In the tornado, κ = 0.9/1.1 moves the total by about ±20 kt (182-222 kt). The A-13b switch (toe fill treated as unattributed or as legacy) moves about 14.5 kt between those two classes, with little change in total. Grid resolution changes the total by about 1%. The movement parameters (ε, α, L_max), survey precision and survey time change it by less than 0.7%.
* **Spatial grade field.** The grade field of the FMS-tracked material (mean absolute block Cu change) is most sensitive to the survey-time assumption (0.28% Cu when surveys are assumed at 21:00) and the A-13b switch (0.25% Cu). Next come the mixing length (ε = 2 m: 0.12%), the maximum push (50 m: 0.12%) and grid resolution (≤ 0.12%). Raising the maximum push to 130 m changes nothing, because no reconstructed push reaches 90 m. Monte Carlo block Cu CV for FMS-tracked blocks is typically 7-9% (maximum about 22%).
* **What the Monte Carlo cannot quantify.** The legacy grade is an assumption, not a measurement. For blocks with less than 50% FMS-tracked material we therefore report a *prior* range: the load-scale P10-P90 of all FMS loads, 5.8-12.1 % Cu. We do not report Monte Carlo precision for these blocks, because it would be false.

Information types in the results: measured (survey solids, FMS inputs), inferred (survey timing, floor, pre-record surface, toe fill), assumed (legacy grade and density, κ, unattributed grade) and model-generated (load destinations, block grades, ranges). These are distinguished field by field in the block model (D4, Section 1.1).

# Automated Platform

The platform (`spbm`, D5) performs the eleven required steps with one command:

* import of new FMS and survey files (SHA-256 registry);
* QA/QC and period identification;
* CPST;
* block model and inventories;
* uncertainty, QA/QC and reconciliation outputs;
* exports (CSV, VTK, ESRI grids, figures);
* an audit trail: run manifest with code commit, library versions, configuration hash, input hashes and manual interventions, model history, and an automatic change report between versions.

Eight automated tests (including end-to-end conservation) guard every change. The update workflow is demonstrated in `examples/demo_update.sh` (model to 22 March, then updated with later data).

![Platform workflow.](figures/fig_workflow.png)

# Results and Discussion

1. **Where the dumped material is.** FMS-tracked material forms a skin on the south and west faces and the upper benches. Its column thickness is typically 1.6-5.4 m (interquartile range; up to 8 m where the face advanced most), laid in daily layers that dip with the face (see the block model sections). The median reconstructed push is about 22 m per load (P90 about 54 m), and a typical load is spread over a 10-15 m patch of face (median spread 13 m). This reflects dozer spreading and rolling on the face.
2. **Grade pattern.** Daily mean grade varies strongly (5.8-12.2% Cu and 5.8-10.1 g/t Au by day), so the tracked material is banded parallel to the face:
   * 03-16 material (about 10.1% Cu) lies furthest inside, under the north-central crest;
   * low-Cu material from 03-19 and 03-20 (5.8-6.4%) forms the middle band;
   * high-Cu material from 03-28 (about 12.1%) forms the south face, overlain at the toe by 03-29 material (about 8.7%).

   A reclaim cut advancing from the south face would therefore see the feed grade change by more than a factor of two over about 20 m, so it must be blended.
3. **The legacy core dominates the tonnage** but carries no grade information in the supplied data. Its geometry (base plane plus inferred platform) is also the least certain part of the model.
4. **The FMS record is incomplete.** About 20,261 m³ of surveyed fill has no FMS source. This is a data-system issue that should be fixed before the pile is reclaimed.

# Professional Accountability, Ethics and Equity

**Scenario.** Management requests a definitive Cu-Au inventory and reclaim sequence. Some regions are highly uncertain, and data completeness is uneven across periods (and, at an operating mine, possibly across crews, contractors or systems).

**Our position.**

* *We will provide an inventory, but not a single "definitive" number.* We report P10/P50/P90 and the split into measured-basis, imputed and assumed material. A target that relies on legacy material should be labelled "unsupported by data until sampled".
* *Limitations that must not be hidden.* We must not hide that 57% of tonnes have an assumed grade and 21% an imputed grade. Nor should we hide the density/swell ambiguity, the unconfirmed grade units, or the uncalibrated mixing parameters.
* *When to qualify or decline.* We decline to certify a whole-pile metal inventory or a 12-month reclaim schedule that depends on legacy grades. We qualify the near-term schedule on FMS-tracked benches with ranges.
* *Responsibility and evidence.* The model should be independently reviewed by a second engineer and by geology/survey before operational use. It should be validated against reclaim reconciliation (mill/stacker grades vs block predictions) for at least the first months.
* *Documentation.* Every assumption, correction and manual intervention is in the register and the run manifests. The model history keeps prior versions.
* *AI and external code.* AI assistance was substantial and is disclosed in Appendix A, together with how it was verified. Code is protected by automated tests. Engineering decisions remain the team's.

**Equity and inclusive decision-making.**

* *Systematic bias from unequal data.* Average-grade imputation for gap periods and legacy material can systematically mis-state the least-documented regions. These blocks are flagged, never blended silently into "measured" totals.
* *Attribution risk.* The supplied data contain no crew or contractor identifiers, and the observed gaps line up with *periods and systems* (FMS outages, missing or clipped surveys). Discrepancies must not be attributed to people without evidence. Any operational investigation should start from system logs and involve the crews concerned.
* *Explainability.* Maps, classes and block provenance (which loads are in a block) let planners, operators and plant staff question the model. Plain-language summaries accompany every release.
* *Inclusion of perspectives.* Geology (grade units, legacy history), survey (timing, clipping), operations (dozer practice, push distances), processing (blend limits) and finance (risk ranges) should review each release.
* *Usability.* One-command operation, readable configuration with assumption IDs, and CSV outputs mean that engineers without programming expertise can run and audit it.
* *Controls.* A stage-gate sign-off, mandatory display of confidence classes, a "no single number" rule, change reports between versions, and independent verification of code changes.

# Limitations

1. No full-pile or pre-stockpile ground survey. The geometry of the unsurveyed platform and the back of the pile is inferred (A-13, A-14), and the floor is a fitted plane.
2. Two weeks of FMS against a pile built over the life of Pit I. The legacy grade is assumed.
3. Grades are source-block values (no within-load variability); payloads are pass-count estimates; moisture basis unknown.
4. Missing surveys and toe-clipped solids. Unobserved fill is attributed to the period in which it is first seen (timing error of up to one period).
5. Within-period vertical homogeneity (A-19); no particle-size segregation (A-27); no settlement (A-28).
6. Mixing length and push parameters are supported by the synthetic twin but not calibrated with field tracers.
7. Confidence classes are internal planning classes, not JORC/NI 43-101 categories.

# Recommendations for Mine Implementation

| # | Recommendation | Purpose | Priority |
|---|---|---|---|
| R-01 | Full-pile drone/LiDAR survey now; locate any pre-stockpile ground survey | Remove A-13/A-14; legacy volume | High |
| R-02 | FMS completeness audit for 03-16 to 03-18 and 03-22 to 03-28; fix outage alarms | Convert unattributed to tracked | High |
| R-03 | Sampling programme (trenching/sonic drilling) of the legacy core: grade, density, moisture | Replace assumed grades; confirm units (QA-F04) | High |
| R-04 | Reclaim reconciliation: compare stacker/mill grades with block `top_loads` predictions; RFID tracer trial | Calibrate ε and push model | Medium |
| R-05 | Survey protocol: daily full-pile export with recorded acquisition time; change solids not clipped at toe | Remove A-05, A-13b | Medium |
| R-06 | Record truck ID and source bench in FMS dump events; per-load grade where available | Within-load variability; traceability | Medium |
| R-07 | Adopt SPBM with governance: owner, reviewer, stage-gate sign-off, monthly re-run, version log | Accountability | High |

# Conclusions

The supplied data support a defensible reconstruction of the material dumped during 15-31 March 2026. Using change-solid surveys as measured fill and a conservative, survey-constrained optimal-transport allocation, we placed every FMS tonne and every unit of metal in a 3-D block model with exact balances, quantified uncertainty and full provenance. Independent tests show that the method recovers block grades far better than simpler alternatives. The same analysis also shows that most of the stockpile pre-dates the record and has no grade information in the supplied data. The responsible deliverable is therefore an inventory with ranges and explicit information classes, a near-term reclaim plan on the well-informed outer benches, and a targeted data-collection programme for the rest. The platform makes the analysis repeatable and auditable as new surveys and FMS records arrive.

# References

* Bak, P., Tang, C. and Wiesenfeld, K. (1987). Self-organized criticality: an explanation of 1/f noise. *Physical Review Letters* 59, 381-384.
* Caterpillar Inc. *Caterpillar Performance Handbook* (current edition).
* Chizat, L., Peyré, G., Schmitzer, B. and Vialard, F.-X. (2018). Scaling algorithms for unbalanced optimal transport problems. *Mathematics of Computation* 87, 2563-2609.
* Cuturi, M. (2013). Sinkhorn distances: lightspeed computation of optimal transport. *NeurIPS* 26.
* Dijkstra, E.W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik* 1, 269-271.
* Engineers Canada (2016, updated). *Code of Ethics* and *Public Guideline on the Code of Ethics*.
* Monge, G. (1781). *Mémoire sur la théorie des déblais et des remblais.*
* Peyré, G. and Cuturi, M. (2019). Computational optimal transport. *Foundations and Trends in Machine Learning* 11, 355-607.
* Wheaton, J.M. et al. (2010). Accounting for uncertainty in DEMs from repeat topographic surveys. *Earth Surface Processes and Landforms* 35, 136-156.

# Appendices

* **Appendix A** - Use of software, code and AI (`docs/Appendix_A_AI_and_Software_Disclosure.md`).
* **Appendix B** - Data and Assumption Register (D2).
* **Appendix C** - Technical methodology, equations and pseudocode (D3).
* **Appendix D** - Block model file description (D4).
* **Appendix E** - Platform user and audit guide (D5).
* **Appendix F** - Key result tables generated by the run (`outputs/report_tables.md`) and run manifest (`outputs/audit/run_manifest.json`).
