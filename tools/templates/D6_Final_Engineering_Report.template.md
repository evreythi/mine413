---
title: "Long-Term Stockpile Reconstruction and Block Modelling - Pit I HG Stockpile"
subtitle: "D6 Final Engineering Report to Mine Management | MIN E 413 Surface Mining Methods and Operations Management, Fall 2026"
author: "Long-Term Mine Planning Team: [Member 1], [Member 2], [Member 3], [Member 4], [Member 5]"
date: "November 2026 - platform version 2.0, model run {{RUN_ID}}"
---

# Executive Summary

**Request.** The Mine Manager asked for a defensible platform that reconstructs how truck-dumped material moved through the growing Pit I high-grade (HG) stockpile, estimates where it now resides, and produces an updatable block model of tonnage, Cu, Au, contained metal and uncertainty.

**Data.** We received 275 FMS dump records (44,650 t, 2026-03-15 to 03-31) and ten Vulcan survey files. Each survey file is a **closed change solid**: its top is the new surface and its bottom the previous one, over the area that changed. The surveys therefore give measured fill per interval, 35,096 m³ in total. The data also have important gaps:

* payloads are bucket-pass estimates (every value is a multiple of 38 t);
* grades are 21 source-block signatures, not load assays;
* 14 records carry a default (stuck) FMS position;
* two survey files carry the wrong year, and every DXF header declares inches although the data are metres;
* the survey acquisition time is not recorded;
* the FMS is missing records for 03-23 to 03-27 and after 08:17 on 03-29, while the surveys show material being placed.

**Method.** We developed **CPST (Constrained Push-and-Settle Transport)**. In each survey interval, the observed fill defines where material went. The FMS loads, material carried over on the platform, and dozer cuts are the sources. A slope-aware dozer push cost and entropy-regularised optimal transport (mixing length ε = 6 m) decide which source filled which part of the fill. Fill without an FMS source becomes **unattributed** material with an imputed grade. All operations act on tonnes and metal, so **mass and metal are conserved exactly**. Two inputs are calibrated on the data and tested on data held out from the calibration:

* **Survey cut-off.** A survey labelled day D closes its interval at **D+1 07:00**. This was found by scanning 0-36 h, and it coincides with the shift-change lull in dumping.
* **Volume factor.** Measured fill is **f_v = {{F_V}}** times the recorded tonnes ÷ FMS density on every day with a complete FMS record. Calibrated on the first half of the record, it predicts the second half to {{HO_MAE}}.

> **Grade units are unconfirmed.** The FMS grades average 8.4% Cu and 8.0 g/t Au, roughly an order of magnitude above typical Cu-Au mill feed (QA rule GRADE_UNITS_UNCONFIRMED). All grades and contained-metal figures are **as supplied** and must be confirmed with Geology before any economic use. Tonnages, the spatial distribution and relative grade patterns are not affected.

**Headline result: material placed during the record (15-31 March), tied to surveyed fill.**

| Record-period inventory | Tonnes | Cu % | Au g/t | Cu (t) | Au (koz) | Basis |
|---|---|---|---|---|---|---|
| FMS-tracked (survey-reconciled + 228 t provisional) | {{T_F}} | {{CU_F}} | {{AU_F}} | {{CUT_F}} | {{AUK_F}} | Measured tonnes and grades; location model-generated |
| Unattributed (surveyed fill with no FMS record) | {{T_U}} | {{CU_U}} | {{AU_U}} | {{CUT_U}} | {{AUK_U}} | Measured volume; **imputed** grade and density |
| **Record-period total** | **{{T_RP}}** | {{CU_RP}} | {{AU_RP}} | {{CUT_RP}} | {{AUK_RP}} | |

* Monte Carlo (60 realisations) P10 / P50 / P90: record-period tonnes **{{MC_RP}} kt**; contained Cu {{MC_RP_CU}} kt (as-supplied units). The FMS-tracked Cu grade ranges over {{MC_FCU}} % (P10-P90).
* **What these ranges include and exclude.** The ranges cover:
  * GPS, payload and assay errors;
  * survey cut-off 29-32 h;
  * the volume factor's calibration uncertainty;
  * the movement parameters;
  * the volume excess read as **bulking, plus up to 19% payload under-recording** (f_pay 1.00-1.19, most likely 1.00).

  They **do not** cover the interpretation that the excess volume is **whole loads missing from the FMS** (scenario X2). The data cannot exclude it. Under X2, record-period tonnes would be **{{X2_RP}} t (+{{X2_UPLIFT}})**. *Not included in those ranges.* Confirming whether the FMS density is a bank or a loose density, and running a pile density test, would settle this (R-02).

**Second: the pre-record core.** Below the earliest surveyed surfaces lies material placed before the record. Its geometry is inferred (floor plane, platform behind the crest) and its grade is assumed equal to the FMS mean. In the base case it holds {{T_L}} t. With it, the whole modelled pile is {{T_T}} t (Monte Carlo P10/P50/P90 {{MC_T}} kt). **{{S_L}} of the whole-pile tonnes have no measured grade basis**, so the whole-pile number must not be quoted without that qualification.

**Validation.**

* FMS tonnes, Cu, Au and Ag balance to floating-point precision.
* The reconstructed surface matches the latest surveys: RMSE {{GEO_RMSE}} m, with {{GEO_TAU}}% of cells within the 0.14 m detection limit.
* The volume factor predicts held-out intervals to {{HO_MAE}}. Reading the FMS density as the in-pile density misses them by {{HO_DENS}}.
* On held-out intervals, the forward physics model's earth-mover error is {{FWD_P}} m. This compares with {{FWD_B}} m without dozer push and {{FWD_U}} m for uniform spreading.
* In a synthetic twin with known truth, CPST recovers block Cu with RMSE {{TW_CPST}}% (r = {{TW_R}}). A period-average model gives {{TW_PA}}% and a single mean grade {{TW_GM}}%.
* In a stress test whose truth uses a placement rule CPST does *not* assume (random crest), CPST still gives {{TWA_RC_CPST}}% against {{TWA_RC_PA}}%.
* An independent second implementation of the project (B) reached the same volume factor (1.476), the same consistent intervals and a 47.6 kt record-period inventory (Section 9.8).

**Key conclusions.**

1. The material dumped during the record can be inventoried with stated ranges: {{T_RP}} t, of which {{RP_FMS_SHARE}} is FMS-tracked with measured grades. It forms the outer skin of the pile on the advancing south face and upper benches, and it can support near-term reclaim planning.
2. The largest single uncertainty in tonnes is no longer the algorithm or the survey timing. It is what the 47% volume excess means: bulking, or tonnes that the FMS did not record.
3. The pre-record core dominates the whole-pile tonnage but carries no grade information in the supplied data.

**Recommendations.**

1. Confirm the FMS density basis and test the pile density.
2. Audit the FMS for 03-23 to 03-27 and after 03-29 08:17.
3. Obtain a full-pile survey and any pre-stockpile ground survey.
4. Sample the pre-record core.
5. Record survey acquisition times.
6. Adopt the platform with the governance controls in Section 13. Run `python -m spbm update` after every survey.

# Introduction and Project Objectives

Pit I will be exhausted by the end of 2026. Its long-term HG stockpile then becomes a principal plant feed source. Reclaim sequencing, blending, metal forecasting and economic evaluation all require knowing *what material is where* in the pile. Unlike an in-situ deposit, a stockpile cannot be reconstructed from dump coordinates alone: dozers push loads to and over the crest, and gravity carries material down the face.

The ten objectives of the brief map onto this report as follows. QA/QC (Section 4); growth reconstruction (Section 5); movement algorithm with mass and metal balance (Section 6); 3-D distribution and block model (Section 8); validation (Section 9); sensitivity (Section 10); platform (Section 11); professional practice (Section 13). Assumptions are maintained in the register (Section 7 and D2).

This is version 2.0 of the platform and report. Version 1 was reviewed against an independent implementation of the same brief (B). The review found three things in version 1 that we have corrected:

* its survey-time search ended at its own optimum;
* it never tested the bulking explanation of the volume gap;
* it led with a whole-pile number that was mostly inferred material.

It also identified governance and testing practices worth adopting. What changed, and why, is recorded in the decision log (D1, DEC-11 to DEC-16) and in Appendix A.

# Description of Available Data

| Dataset | Content | Coverage |
|---|---|---|
| FMS (`Dump Data.csv`) | 275 records: cycle ID, payload, Cu %, Au g/t, Ag g/t, density, dump X/Y/Z, timestamp | 2026-03-15 17:43 to 03-31 20:52; 44,650 t |
| Surveys (10 DXF) | Vulcan 3DFACE closed change solids, layer `*_HGHS*` | Nominal dates 03-15, 16, 18, 19, 20, 21, 22, 27, 28, 29 (after re-dating) |
| Not supplied | Full-pile surface, original ground, truck ID, source bench, moisture, density tests, density basis, dozer records, survey acquisition times | - |

Coordinates are a projected mine grid in metres (E ≈ 511,300, N ≈ 7,122,300, Z ≈ 4,480 m). Every DXF header declares `$INSUNITS = 1` (inches) and `$MEASUREMENT = 0` (imperial). This is a template default: in inches the pile would be 2.5 m wide at 114 m elevation. The header is ignored, and the data are read as metres in the same grid as the FMS (A-01). All DXF headers also share one last-saved date (2025-11-14), and the layer names carry the year 2025, so header dates are not used for timing.

# Data Analysis and QA/QC

The full QA/QC is in D2 Section 2 and `outputs/qaqc/`. Every check is a named rule with a level (record, survey file, dataset), a severity and a treatment. {{QA_N_RULES}} rules are checked and {{QA_N_TRIG}} are triggered. No record was deleted or edited, and no FMS record met an error rule. Table 4.1 lists the rules that were triggered.

{{TABLE_QA_TRIG}}

**Principal findings and their influence on the model.**

* **Surveys are change solids (QA-S01).** Every rasterised cell is crossed by exactly two faces. The divergence-theorem volume equals the gridded volume, and the bottom of each solid equals the top of the previous one to 0.000 m (P5-P95) in overlaps. This turned a "partial surface" problem into a measured-fill problem.
* **Survey timing (QA-S04).** The acquisition time is not recorded. A scan of the cut-off (below and Section 5) gives D+1 07:00.
* **Mis-dated files and header dates (QA-S02, S03).** `Topo_250328/250329` were re-dated to 2026-03-28/29 by the logged interventions MI-001/MI-002. The DXF header units and dates are template values.
* **Elevation decreases hidden in solids (QA-S06).** These are handled as dozer cuts, re-handled as transport sources.
* **Payload and grade (QA-F02, F03).** Payloads are pass-count estimates and grades are source-block values. Both enter the uncertainty analysis as correlated errors. Payload under-recording also enters the systematic payload factor (Section 5).
* **Dump Z (QA-F06).** Z minus the previously surveyed surface has P10/P90 of −2.5/+3.6 m, so only X/Y is used.
* **Default FMS position (QA-F10).** Fourteen records (2,356 t) share one identical position, below the floor and in front of the toe. Their location is treated as **unknown**: they fill whatever part of their interval's fill the located loads do not claim (A-32).
* **FMS completeness (QA-F07).** Grouping by production day (D 07:00 to D+1 07:00) shows three genuine FMS gaps: interval 0 (the record starts at 17:43 on 03-15), 03-23 to 03-27, and after 08:17 on 03-29. 03-17, which version 1 reported as an FMS outage, has neither dumps nor a survey. Its fill appears in the 03-18 solid at a normal volume ratio, so it was a non-dumping day.

![Dump locations (by day) and survey change-solid footprints; LOC_DEFAULT and LOC_OUTSIDE_SURVEYS marked.](../outputs/qaqc/fig_qaqc_dump_map.png)

![FMS tonnage per production day and survey solid volume.](../outputs/qaqc/fig_qaqc_daily_tonnage_volume.png)

![Survey cut-off scan (left) and dump times (right): the correlation plateaus at 30-31.5 h, i.e. D+1 06:00-07:30, exactly the shift-change lull in dumping.](../outputs/growth/fig_temporal_alignment.png)

![Change-solid thickness of each survey.](../outputs/qaqc/fig_qaqc_survey_solids.png)

![Payload values and grade signatures.](../outputs/qaqc/fig_qaqc_payload_grades.png)

![Surveyed face slopes; the angle of repose (A-03) is taken from this distribution.](../outputs/qaqc/fig_qaqc_repose.png)

# Stockpile Growth Analysis

The stockpile grew by end-dumping on a platform at about 4,488-4,490 m. Dozers pushed material over a crescent-shaped crest, and the south face advanced about 30 m in two weeks (face-advance map below). The face stands at a median 36.7° (P75 38.5°). The floor is a near-horizontal plane at 4,475.1 m (dip 0.29°, residual SD 0.26 m).

![Survey interval in which each cell first received fill.](../outputs/growth/fig_growth_face_advance.png)

![Elevation increase per interval with the truck dumps of that interval.](../outputs/growth/fig_growth_period_maps.png)

## When does a survey close its interval?

The surveys carry a date, not a time. The cut-off was scanned from 0 to 36 h after 00:00 of the nominal date (D2, Section 2.4):

{{TABLE_CUTOFF}}

Midnight is clearly not the cut-off. The correlation keeps rising after 24 h and plateaus between 30 and 31.5 h (D+1 06:00-07:30). The robust spread of the volume ratio falls by a factor of three (from {{RCV_24}} to {{RCV_31}}). The FMS dump times show the reason. Dumping stops between 06:00 and 07:30 (2 dumps in two weeks), and again between 18:30 and 20:00. These are shift changes. A production day runs from one morning shift change to the next, and the survey labelled D was evidently taken at its end. We adopt **D+1 07:00** and sample 29-32 h in the Monte Carlo.

## FMS vs survey: the volume factor

The table below compares, per interval, the measured net fill (fill − revealed cuts) with the FMS volume at the recorded density, Σ T/Dens.

{{TABLE_VF}}

* **Complete intervals.** On the seven intervals whose FMS record is complete (blue in the figure), measured fill is a stable 1.19-1.58 times Σ T/Dens. The pooled value is **f_v = {{F_V}}** (bootstrap P10-P90 {{F_V_P10}}-{{F_V_P90}}). The lowest ratio (03-16, 1.19) is dozer lag: 541 m³ of that day's FMS volume reaches the face on 03-18 and is carried forward explicitly.
* **FMS-gap intervals** (03-15, 03-27, 03-29) have ratios of 2.2-2.4. Their fill is only partly explained by FMS, and the rest becomes **unattributed** volume ({{UNATT_VOL}} m³ in total).
* **Prediction.** f_v calibrated on the first half of the record predicts the held-out complete intervals to {{HO_MAE}}. A constant density gives {{HO_CONST}}, and using Dens as the in-pile density (f_v = 1) gives {{HO_DENS}}.

![Volume ratio per interval (left) and hold-out prediction error (right).](../outputs/growth/fig_volume_factor.png)

**What f_v means.** f_v fixes the in-pile **volume** of each load (T × f_v / Dens). How many **tonnes** that volume holds depends on why it is 47% larger than T/Dens, and the data cannot tell:

* **Bulking.** If the FMS density is a bank (in-situ) density, f_v = 1.47 is an ordinary swell factor for blasted rock. Recorded tonnes are then correct, and the in-pile density is {{RHO_PILE}} t/m³. This is our base case.
* **Under-recorded payloads.** Payload is passes × a nominal 38 t bucket. A larger real bucket factor would add tonnes. We allow up to 19% (f_pay = 1.19), at which the largest load (304 t) reaches 362 t, about the largest haul-truck rating. All of the excess (f_pay = 1.47) would need 448 t loads, which is excluded (X1).
* **Missing loads.** About {{X2_SHARE}} of the volume on otherwise complete days would have to come from trucks or loads absent from the FMS (X2). This cannot be excluded.

Version 1 of this report sampled the in-pile density only over κ = 0.80-1.05 times Dens. Its lowest value corresponds to f_v = 1.25, so the full bulking explanation (f_v ≈ 1.47, κ ≈ 0.68) was never tested, and most of the excess volume was booked as unattributed material. Section 10.2 reports all three interpretations.

**Other reconciliation features.**

* **Dozer lag (physical).** When an interval's FMS volume exceeds its fill, the surplus is retained on the platform and pushed in the next interval.
* **Cuts.** {{CUT_VOL}} m³ of dozer cuts were re-handled.

{{TABLE_PERIODS}}

![Cumulative FMS tonnes vs surveyed volume.](../outputs/growth/fig_growth_cumulative.png)

![Interval reconciliation.](../outputs/growth/fig_growth_period_reconciliation.png)

# Material-Movement Methodology

The full derivation, pseudocode and flowcharts are in D3. In summary, each interval's update answers the required questions:

| Question | CPST answer |
|---|---|
| A. Initial placement | Each load is a parcel of in-pile volume T·f_v/Dens at its reported X/Y (GPS error σ = 3 m in the Monte Carlo). Loads with a default FMS position have an unknown location (uniform cost) |
| B. Direction | Least-work route over the pre-interval terrain: geodesic distance with uphill penalty α = 4 m per m of lift. The survey decides which face sector received fill |
| C. Distance / stopping | Material stops where observed accommodation space exists (capacity constraint). Max push 90 m. Unplaceable volume is retained on the platform (dozer lag) |
| D. Downslope behaviour | The layer top is the surveyed surface, with faces at the measured repose angle. Forward model: avalanche CA at 37° |
| E. Mixing | Entropic OT with mixing length ε = 6 m. Grades composited from metal ÷ tonnes |
| F. Surface reconciliation | Column marginals = observed fill, so the model surface = survey (residual ≤ 8×10⁻⁷) |
| G. Mass conservation | Row sums exact by construction; unattributed and pre-record volumes kept in separate classes |
| H. Metal conservation | All operations linear in metal; verified to 10⁻¹² relative |
| I. Sequential updating | Column stacks plus carried parcels form the initial state of the next interval. Cuts remove and re-handle the column top |
| J. Numerical stability | Log-domain Sinkhorn (tolerance 10⁻⁶); 1 m grid; robustness tested (Section 9.5) |

![CPST algorithm for one survey interval.](figures/fig_algorithm.png)

**Why optimal transport?** Moving cut volume to fill volume with minimum work is the original optimal-transport problem (Monge, 1781). The entropic form adds exactly one physically interpretable parameter, the mixing length. Sinkhorn iterations solve it robustly, and conservation is guaranteed. A rule that pushes each load to its nearest crest cell cannot honour the observed fill, and black-box regression has no training data. The forward-model test (Section 9.3) shows that physics alone predicts the fill location only moderately well, which confirms that the survey constraint is necessary.

![Reconstructed (volume-weighted) push distances.](../outputs/growth/fig_growth_push_distance.png)

# Assumption Register

The complete register (32 assumptions with need, justification, consequence and treatment) is in D2 Section 4. The configuration file tags every parameter with its assumption ID. The assumptions with the greatest influence are:

| ID | Assumption | Effect if wrong | Treatment |
|---|---|---|---|
| A-06 | In-pile volume = T·f_v/Dens (f_v calibrated, {{F_V}}); recorded tonnes correct (f_pay = 1) | Record-period tonnes +{{S1_UPLIFT}} at f_pay = 1.19; +{{X2_UPLIFT}} if the excess is missing loads | MC (f_v bootstrap, f_pay 1.00-1.19 triangular); tornado; scenarios X1 (excluded), X2 (not included) |
| A-22 | Pre-record core grade = FMS mean | Core metal could differ by any amount | Separate class; "Uninformed"; prior range; sampling (R-04) |
| A-13/A-14 | Geometry of never-surveyed parts | Core volume and extent | Full survey (R-03) |
| A-05 | Survey closes its interval at D+1 07:00 | Loads shift one interval | Cut-off scan; MC 29-32 h; tornado |
| A-18 | Mixing length 6 m | Block-scale grade smoothing | Twin experiments; MC; tornado |
| A-21 | Unattributed grade = neighbouring intervals | Grade of {{S_U}} of tonnes | Bootstrap in MC; separate class |
| A-32 | Default-position loads have unknown location | Allocation of 2.4 kt within their intervals | Uniform cost; tests |

# Block Model Construction

* **Block size 5 × 5 × 2 m** (27 × 26 × 10 grid; origin E 511,290 N 7,122,280 Z 4,474). Horizontal size is matched to the information resolution (GPS σ ≈ 3 m plus mixing length 6 m). Vertical size matches the daily layer thickness (median 0.9-3.0 m) and loader reclaim slices. Alternatives (2 × 2 × 1 m, 10 × 10 × 4 m) are tested in Section 10. Implementation B used 2 × 2 × 1 m blocks. We keep 5 × 5 × 2 m because the data cannot resolve grade below about 5 m, and smaller blocks would only add false precision.
* **Partial blocks** keep their exact material volume (fill fraction). There is no sub-blocking, because layers are integrated exactly.
* **Density** per material class: in-pile density Dens·f_pay/f_v for FMS loads; block density is derived as tonnes ÷ volume.
* **Compositing** is by metal ÷ tonnes. The within-block heterogeneity of mixed loads is reported.
* **Provenance**: each block lists its effective number of loads and its top three contributing cycle IDs, enabling reconciliation with plant data.
* **Uncertain or uninformed regions** are labelled by information class (FMS-reconciled, Unattributed-imputed, Legacy-assumed = pre-record core, Provisional) and by confidence class (High, Medium, Low, Uninformed).
* **Two class breakdowns exist, and both are correct.** The *exact* tonnage split (each block's tonnes divided among the classes) is `summary_by_material_source.csv` and `validation/inventory_by_class.csv`; it is the split quoted throughout this report. `summary_by_dominant_info_class.csv` instead assigns each *whole* block to its dominant class, for mapping and reclaim planning. Both sum to the same total.

{{TABLE_CONF}}

![Block model Cu grade by 2 m bench.](../outputs/blockmodel/fig_bm_plans_cu_pct.png)

![Fraction of block tonnes that is FMS-tracked.](../outputs/blockmodel/fig_bm_plans_frac_fms.png)

![Sections through the centre of the FMS-tracked material. Dashed orange: pre-record surface (top of the pre-record core).](../outputs/blockmodel/fig_bm_sections_cu_pct.png)

![3-D view of FMS-tracked blocks.](../outputs/blockmodel/fig_bm_3d_cu_pct.png)

{{TABLE_BENCH}}

# Validation and Reconciliation

## Mass and metal balance

{{TABLE_BALANCE}}

FMS tonnes, Cu, Au and Ag entering the stockpile equal the block model inventory to floating-point precision. Volume reconciliation for the whole record:

{{TABLE_VOLUME}}

## Geometry

The survey-reconciled model surface differs from the latest surveyed surface by RMSE {{GEO_RMSE}} m (bias {{GEO_BIAS}} m). {{GEO_TAU}}% of cells are within the 0.14 m detection limit. The residuals are sub-threshold changes that are intentionally not moved. Geometry is constrained by design, so this test verifies the numerics; the independent tests follow.

![Geometry check.](../outputs/validation/fig_val_geometry.png)

## Temporal behaviour (held-out intervals)

The forward physics model was calibrated on intervals 1-5: repose angle, deposit radius and release offset, 27 combinations. It was then tested on intervals 6-9, which it never saw. For each test interval it predicted the fill from the previous state and that interval's dumps only.

{{TABLE_FORWARD}}

On the unseen intervals the dozer-push model ({{FWD_P}} m) is far better than the no-information baseline ({{FWD_U}} m, volume spread evenly over the pile). It is only marginally better than leaving material at the dump point ({{FWD_B}} m), although it captures more of the observed fill. The absolute errors are large compared with the block size. **Physics alone cannot say where on a 100 m face a day's fill will land; the surveys must constrain it.** This justifies the survey-constrained design of CPST. The forward model is used only where no survey exists (nowcast of the 03-31 load).

![Unseen test intervals: observed fill vs prediction.](../outputs/validation/fig_val_forward_test.png)

## Inversion skill: synthetic twin with known truth

A known-truth stockpile was generated from the real dump sequence with the forward model, with random dozer deviations of 6 m. It was then observed the way the real one is: change solids with survey noise, GPS error σ = 3 m, payload noise, and **15% of FMS records deleted**. Finally it was reconstructed blind.

{{TABLE_TWIN}}

CPST recovers block Cu grade with RMSE {{TW_CPST}}% Cu (r = {{TW_R}}). That is a {{TW_IMPROVE}}% lower error than allocating each interval's loads uniformly over its fill, and far better than a single mean grade. In this twin a larger mixing length (ε = 15 m, {{TW_E15}}%) does slightly better than the base 6 m, which suggests the base case may under-mix somewhat. ε is therefore sampled over 2-15 m in the Monte Carlo, and calibrating it with tracers is recommended (R-06).

![Twin experiment: true vs reconstructed block Cu.](../outputs/validation/fig_val_twin_scatter.png)

**Is the twin circular?** The main twin's truth comes from our own forward physics (push to the nearest crest, avalanche at 37°). CPST does not use the forward model, but its push cost encodes a similar idea: material goes to the nearby face. Two further twins therefore use truths generated by rules CPST does **not** assume:

* **Random crest.** Each load is pushed to a uniformly random point of the active crest, so the dump position carries no information about the destination.
* **Period-uniform mixing.** Each interval's fill is perfectly homogeneous.

{{TABLE_TWIN_ALT}}

When the dump position is uninformative, CPST's error rises from {{TW_CPST}}% to {{TWA_RC_CPST}}% Cu. It still beats the period-average model ({{TWA_RC_PA}}%) and the global mean ({{TWA_RC_GM}}%). Most of CPST's skill therefore comes from the survey constraint, which says which interval's material is where and in which layer. Under period-uniform mixing, CPST does not impose spurious structure ({{TWA_PU_CPST}}% vs {{TWA_PU_PA}}%).

## Robustness to numerical settings

{{TABLE_ROBUST}}

Class tonnages, tracked-block grade and top-bench grade are stable under changes of grid resolution, solver tolerance and detection limit. They are not artefacts of a single numerical setting.

## Volume conversion (hold-out)

See Section 5 and D2 Section 2.5. f_v is calibrated on the first half of the record and tested on the second. The mean absolute error on held-out complete intervals is {{HO_MAE}}, against {{HO_CONST}} for a constant density and {{HO_DENS}} for f_v = 1. The leave-one-out error is {{LOO}}.

## Performance measures (summary)

| Measure | Value |
|---|---|
| FMS mass / metal balance error | < 10⁻⁹ relative |
| Geometry RMSE vs survey | {{GEO_RMSE}} m |
| Sinkhorn max column residual | ≤ 8×10⁻⁷ |
| Volume factor hold-out error | {{HO_MAE}} (f_v = 1: {{HO_DENS}}) |
| Forward model W1 (test intervals) | {{FWD_P}} m (no-push {{FWD_B}} m; uniform {{FWD_U}} m) |
| Twin block Cu RMSE / r | {{TW_CPST}}% / {{TW_R}} |
| Automated tests | 66 (unit, real-data, platform) |

## Cross-implementation check

A second team (implementation B) built an independent platform from the same brief and data. Its methods differ from ours in three ways:

* a FIFO pad-buffer stock-flow decides how much of each load enters each interval's fill, before a Sinkhorn allocation with ε = 3 m and sparsification (CPST does both in one transport problem, with dummy nodes);
* 2 × 2 × 1 m blocks;
* its own rasteriser and QA code.

Where the two answer the same question, they agree:

{{TABLE_XIMPL}}

The agreement on f_v and on the consistent intervals matters most. Two different codes, with different rasterisation and cut detection, measure the same physical ratio from the same data. Both find the unattributed volume in the same four intervals (0, 7, 8, 9). The record-period inventories differ by about 2%, mainly because the unattributed volumes differ: B books fill within a survey tolerance band to its pad buffer. B's numbers are quoted from B's report and were not re-run.

# Uncertainty and Sensitivity Analysis

## Monte Carlo and tornado

Sixty Monte Carlo realisations jointly sampled the following (D3, Section 7):

* truck GPS error (σ 3 m);
* per-load tonnage error (8%) and the systematic payload factor (f_pay 1.00-1.19, triangular with mode 1.00);
* the volume factor (bootstrap of its calibration at the sampled cut-off);
* assay error (10% per grade signature);
* survey bias (5 cm);
* survey cut-off (29-32 h);
* mixing length (2-15 m), uphill penalty (1-10) and maximum push (50-130 m);
* the unattributed grade (bootstrap).

{{TABLE_MC}}

![Monte Carlo distributions: record-period tonnes and Cu, and the whole pile.](../outputs/uncertainty/fig_unc_global_histograms.png)

![Monte Carlo: record-period tonnes against the sampled volume factor, payload factor and mixing length.](../outputs/uncertainty/fig_unc_param_scatter.png)

![One-at-a-time sensitivity (tornado).](../outputs/uncertainty/fig_sens_tornado.png)

![Block-level Cu uncertainty (FMS-tracked columns).](../outputs/uncertainty/fig_unc_block_maps.png)

**Interpretation.**

* **Record-period tonnage** is driven by the payload factor and the volume factor (scatter plot above). Moving the survey cut-off to 29 or 32 h changes record-period tonnes by {{CUT_SENS_T}}, mostly through the recalibrated f_v. It still moves block grades by up to {{CUT_SENS_CU}}% Cu on average, because loads dumped within an hour or two of the cut-off change interval.
* **Whole-pile tonnage** is driven by the in-pile density applied to the pre-record core, which follows the volume factor. The A-13b switch moves about {{S2_SHIFT}} kt from the core to the unattributed class.
* **Spatial grade field.** The survey cut-off, the movement parameters, the grid and the A-13b switch drive the grade field of the FMS-tracked material (mean absolute block Cu change in the tornado). The Monte Carlo block Cu CV for FMS-tracked blocks has a median of {{BLK_CV_P50}} (P90 {{BLK_CV_P90}}).
* **What the Monte Carlo cannot quantify.** The pre-record core grade is an assumption, not a measurement. For blocks with less than 50% FMS-tracked material we therefore report a *prior* range: the load-scale P10-P90 of all FMS loads, {{PRIOR_CU}} % Cu. We do not report Monte Carlo precision for these blocks, because it would be false.

## Interpretations of the volume gap (scenarios)

The calibrated f_v fixes the in-pile volume of the FMS material. The scenarios below differ only in how many tonnes the **same surveyed volume** holds.

{{TABLE_SCEN}}

![Tonnes held by the same surveyed volume under each interpretation.](../outputs/uncertainty/fig_scenarios.png)

* **S0 and S1** bound the Monte Carlo range.
* **S2** (A-13b on) changes the class split rather than the total.
* **X1** is excluded on physical grounds.
* **X2 is not included in the reported ranges** because the evidence weighs against it, not because it is impossible. If the FMS density is a loose (truck-box) density, X2 or payload under-recording becomes the likelier explanation, and record-period tonnes rise to about {{X2_RP}} t. The basis of the FMS density must be confirmed (R-02).

Information types in the results: measured (survey solids, FMS inputs), inferred (survey cut-off, f_v, floor, pre-record surface), assumed (pre-record grade, f_pay split, unattributed grade) and model-generated (load destinations, block grades, ranges). The block model distinguishes them field by field (D4, Section 1.1).

# Automated Platform

The platform (`spbm`, D5) performs the eleven required steps with one command:

* **Import** of new FMS and survey files into a managed raw store. Files are named by SHA-256 and logged in `ingest_log.csv`. A changed file with an existing name is refused unless a `supersede` intervention authorises it.
* **QA/QC** with a 40-rule catalogue, the survey cut-off scan, and the volume-factor calibration with hold-out.
* **CPST.**
* **Block model and inventories**, including record-period vs pre-record classes.
* **Uncertainty**: Monte Carlo, tornado and volume-gap scenarios.
* **Exports**: CSV, VTK, ESRI grids, figures.
* **Audit trail**:
  * run manifest with the code commit (or, without Git, the packaged commit from `BUILD_INFO.json`);
  * SHA-256 of the platform source;
  * library versions, configuration hash and input hashes;
  * the applied manual interventions, each with reason, author and date;
  * model history, and an automatic change report between versions.

Manual corrections are possible only through `config/manual_interventions.csv`. A row without a reason, author or date stops the run. Sixty-six automated tests guard every change. They cover synthetic unit cases, real-data facts (for example the calibrated f_v, the cut-off optimum and the rule counts) and the platform end to end. The update workflow is demonstrated in `examples/demo_update.sh`: a model built to the 03-22 survey, then updated with the later data.

![Platform workflow.](figures/fig_workflow.png)

# Results and Discussion

1. **Where the dumped material is.** FMS-tracked material forms a skin on the south and west faces and the upper benches, laid in daily layers that dip with the face (see the block model sections). The median reconstructed push is about {{PUSH_P50}} m per load (P90 about {{PUSH_P90}} m). A typical load is spread over a patch of face about {{SPREAD_P50}} m across, reflecting dozer spreading and rolling on the face.
2. **Grade pattern.** Grade varies strongly between production days, from 5.8% Cu (03-19, 03-20) to 13.2% (03-21) and 12.2% (03-27). The tracked material is therefore banded parallel to the face. A reclaim cut advancing from the south face would see the feed grade change by more than a factor of two over about 20 m, so it must be blended.
3. **The record-period inventory is now consistent between the surveys and the FMS.** Once the cut-off and the volume factor are calibrated, recorded loads explain the measured fill of every complete day. Only {{UNATT_VOL}} m³ of surveyed fill (about {{UNATT_SHARE}} of the fill) has no FMS source, and all of it falls in the three FMS-gap intervals. Version 1 booked roughly ten times as much unattributed material, because it did not calibrate the volume conversion.
4. **The pre-record core dominates the whole-pile tonnage** but carries no grade information in the supplied data. Its geometry (floor plane plus inferred platform) is also the least certain part of the model.
5. **The volume excess is the open question.** Bulking (our base case) and missing tonnes are indistinguishable from volumes alone. The answer moves the record-period tonnes by up to {{X2_UPLIFT}}.

# Professional Accountability, Ethics and Equity

**Scenario.** Management requests a definitive Cu-Au inventory and reclaim sequence. Some regions are highly uncertain, and data completeness is uneven across periods (and, at an operating mine, possibly across crews, contractors or systems).

**Our position.**

* *We will provide an inventory, but not a single "definitive" number.* We lead with the record-period inventory, which is tied to surveyed fill and measured grades, with its P10/P50/P90. We state what the ranges do *not* include (missing loads, X2). The pre-record core is reported separately, and a target that relies on it is labelled "unsupported by data until sampled".
* *Limitations that must not be hidden:*
  * {{S_L}} of the whole-pile tonnes have an assumed grade;
  * the volume excess has two unresolved explanations;
  * the grade units are unconfirmed;
  * the mixing parameters are not calibrated in the field.
* *Correcting our own work.* Version 1 of this analysis had a timing artefact and an untested density hypothesis. Both were found by comparing it with an independent implementation. The corrections, and their effect on the numbers, are documented (D1 decision log, Appendix A). The superseded headline (202 kt) must not be reused.
* *When to qualify or decline.* We decline to certify a whole-pile metal inventory, or a 12-month reclaim schedule that depends on the pre-record core. We qualify the near-term schedule on FMS-tracked benches with ranges.
* *Responsibility and evidence.* The model should be independently reviewed by a second engineer and by geology/survey before operational use. It should then be validated against reclaim reconciliation (mill or stacker grades vs block predictions) for at least the first months.
* *Documentation.* Every assumption, correction and manual intervention is in the register and the run manifests. The model history keeps prior versions.
* *AI and external code.* AI assistance was substantial and is disclosed in Appendix A, together with how it was verified. Code is protected by automated tests. Engineering decisions remain the team's.

**Equity and inclusive decision-making.**

* *Systematic bias from unequal data.* Average-grade imputation for gap intervals and pre-record material can systematically mis-state the least-documented regions. These blocks are flagged, never blended silently into "measured" totals.
* *Attribution risk.* The supplied data contain no crew or contractor identifiers. The observed gaps line up with *periods and systems*: FMS outages, missing or clipped surveys, template DXF headers. The volume excess could be read as "someone is not recording loads", but it is equally consistent with ordinary swell. Discrepancies must not be attributed to people without evidence. Any operational investigation should start from system logs and involve the crews concerned.
* *Explainability.* Maps, classes and block provenance (which loads are in a block) let planners, operators and plant staff question the model. Plain-language summaries accompany every release.
* *Inclusion of perspectives.* Geology (grade units, pre-record history), survey (timing, clipping, units), operations (dozer practice, bucket calibration), processing (blend limits) and finance (risk ranges) should review each release.
* *Usability.* One-command operation, readable configuration with assumption IDs, and CSV outputs let engineers without programming expertise run and audit the platform.
* *Controls:*
  * a stage-gate sign-off;
  * mandatory display of confidence classes;
  * a "no single number" rule;
  * change reports between versions;
  * interventions that need a reason, author and date;
  * independent verification of code changes.

# Limitations

1. No full-pile or pre-stockpile ground survey. The geometry of the unsurveyed platform and the back of the pile is inferred (A-13, A-14), and the floor is a fitted plane.
2. Two weeks of FMS against a pile built over the life of Pit I. The pre-record core grade is assumed.
3. The split of the volume excess between bulking and unrecorded tonnes is not identifiable (A-06). The base case assumes bulking.
4. Grades are source-block values (no within-load variability); payloads are pass-count estimates; moisture basis unknown.
5. Missing surveys and toe-clipped solids. The survey cut-off is inferred, not recorded.
6. Within-interval vertical homogeneity (A-19); no particle-size segregation (A-27); no settlement (A-28).
7. Mixing length and push parameters are supported by the synthetic twins but not calibrated with field tracers.
8. Confidence classes are internal planning classes, not JORC/NI 43-101 categories.

# Recommendations for Mine Implementation

| # | Recommendation | Purpose | Priority |
|---|---|---|---|
| R-01 | FMS completeness audit for 03-23 to 03-27 and after 03-29 08:17; fix outage alarms | Convert unattributed to tracked | High |
| R-02 | Confirm whether the FMS `Dens` is a bank or loose density; bulk-density test on the pile (e.g. weighed reclaim against surveyed volume); calibrate loader bucket factors | Resolve the volume excess (A-06): bulking vs missing tonnes | High |
| R-03 | Full-pile drone/LiDAR survey now; locate any pre-stockpile ground survey | Remove A-13/A-14; pre-record core volume | High |
| R-04 | Sampling programme (trenching or sonic drilling) of the pre-record core: grade, density, moisture | Replace assumed grades; confirm units (QA-F04) | High |
| R-05 | Survey protocol: record the acquisition time; export full-pile surfaces daily; do not clip change solids at the toe; fix the DXF unit header | Remove A-05; units | Medium |
| R-06 | Reclaim reconciliation: compare stacker/mill grades with block `top_loads` predictions; RFID tracer trial | Calibrate ε and the push model | Medium |
| R-07 | Record truck ID and source bench in FMS dump events; per-load grade where available | Within-load variability; traceability | Medium |
| R-08 | Adopt SPBM with governance: owner, reviewer, stage-gate sign-off, monthly re-run, version log | Accountability | High |

# Conclusions

The supplied data support a defensible reconstruction of the material dumped during 15-31 March 2026. The change-solid surveys serve as measured fill. A survey cut-off and a volume factor are calibrated from the data and verified on held-out intervals. A conservative, survey-constrained optimal-transport allocation then places every FMS tonne and every unit of metal in a 3-D block model, with exact balances, quantified uncertainty and full provenance.

The record-period inventory is {{T_RP}} t (P10-P90 {{MC_RP_RANGE}} kt), with one explicitly stated exclusion: tonnes missing from the FMS. It agrees with an independent implementation to about 2%. Independent tests show that the method recovers block grades far better than simpler alternatives. Most of the whole pile pre-dates the record and has no grade information in the supplied data. The responsible deliverable is therefore:

* an inventory with ranges and explicit information classes;
* a near-term reclaim plan on the well-informed outer benches;
* a targeted data-collection programme for the rest, starting with the density basis.

The platform makes the analysis repeatable and auditable as new surveys and FMS records arrive.

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

* **Appendix A** - Use of software, code and AI, including the A + B integration (`docs/Appendix_A_AI_and_Software_Disclosure.md`).
* **Appendix B** - Data and Assumption Register (D2).
* **Appendix C** - Technical methodology, equations and pseudocode (D3).
* **Appendix D** - Block model file description (D4).
* **Appendix E** - Platform user and audit guide (D5).
* **Appendix F** - Key result tables generated by the run (`outputs/report_tables.md`) and run manifest (`outputs/audit/run_manifest.json`).
