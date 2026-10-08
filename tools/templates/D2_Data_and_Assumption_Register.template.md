---
title: "D2 - Data and Assumption Register"
subtitle: "MIN E 413 Term Project - Pit I HG stockpile reconstruction (platform version 2.0, run {{RUN_ID}})"
---

This register is the controlled record of:

1. the data received;
2. the quality findings, as a catalogue of QA rules with counts;
3. every preprocessing and cleaning decision;
4. every engineering assumption, with its need, justification, consequence and treatment.

Parameter values live in `config/project.yaml`, and each value there is tagged with the ID used here (`A-xx`). The QA results are in `outputs/qaqc/`, in machine-readable form.

**No raw record was deleted or edited.** Every input file is copied once into the managed raw store (`data/raw_store/`, named by SHA-256, logged in `ingest_log.csv`). The analysis reads only from the store. Corrections are made only through `config/manual_interventions.csv`, and every row there needs an id, type, target, reason, author and date.

Information type key, used throughout the project (course outline, Task 7): **M** = measured, **I** = inferred from data, **A** = assumed, **G** = model-generated.

# 1. Dataset inventory

| ID | File(s) | Content | Coverage | Type | Notes |
|---|---|---|---|---|---|
| DS-1 | `Dump Data.csv` | 275 FMS truck-dump records: Cycle ID, payload (t), Au (g/t), Ag (g/t), Cu (%), density `Dens` (t/m³), dump X/Y/Z, timestamp (minute resolution) | 2026-03-15 17:43 to 2026-03-31 20:52; 44,650 t | M | No truck ID or source (pit/bench) field. Grades are per **source signature** (21 distinct Cu/Au/Ag/Dens combinations), not per-load assays. The basis of `Dens` (bank or loose) is not documented |
| DS-2 | `Topo_260315.dxf` … `Topo_260327.dxf` (8 files) | Vulcan DXF, 3DFACE triangles, one layer per file | Nominal dates 03-15 to 03-27 (none for 03-17 or 03-23 to 03-26) | M | Each file is a **closed change solid**: top = this survey, bottom = the previous surface, over the area that changed (QA-S01) |
| DS-3 | `Topo_250328.dxf`, `Topo_250329.dxf` | As DS-2 | Re-dated to 2026-03-28 and 2026-03-29 (MI-001, MI-002) | M | File-name year inconsistent with the record (rule SURVEY_NAME_YEAR) |
| DS-4 | (not supplied) | Full stockpile surface, pre-stockpile ground, density tests, dozer logs, truck IDs, moisture, survey acquisition times | None | n/a | Absence drives assumptions A-05, A-06, A-12, A-13, A-14, A-22 |

**Units and coordinate reference.** Coordinates are in metres. Easting is about 511,300 and Northing about 7,122,300, consistent with a UTM-type grid in the southern hemisphere. Elevation is about 4,480 m. The DXF headers say otherwise: all ten files declare `$INSUNITS = 1` (inches) and `$MEASUREMENT = 0` (imperial). This is a default template value, not the unit of the data, for three reasons:

* the coordinates coincide with the FMS mine grid (dumps sit on and behind the surveyed crests);
* in inches, the pile would be 2.5 m wide and stand 114 m above sea level;
* the face slopes (36°) and the volume budget (Section 2.5) are physically consistent only in metres.

The header is therefore ignored (rule DXF_UNITS_HEADER). FMS and surveys overlay without offset, so **no transformation** was applied (A-01).

**File dates.** All ten DXF headers carry the same last-saved date, `$TDUPDATE` = 2025-11-14 00:52 local (07:52 UTC), which is earlier than the nominal survey dates. The layer names all carry the year token `25` (e.g. `250315_STOCK_HGHS`), and two file names do too. Together these suggest that the absolute dates were shifted by one year when the data set was prepared. Only relative timing matters to the model, and the FMS and survey sequences agree once MI-001/MI-002 are applied, so header dates are not used (rules DXF_SAVED_BEFORE_SURVEY, LAYER_DATE_MISMATCH).

# 2. QA/QC findings

## 2.1 QA rule catalogue

Every check is a named rule at one of three levels: record (FMS), survey file, or dataset. Each rule has a severity and a treatment:

* **error**: the record or file cannot be used as recorded. It is excluded from modelling and kept in the register, or it is corrected by a logged intervention.
* **warning**: modelled, with the treatment stated.
* **info**: recorded for traceability only.

Record-level rules are defined once (`spbm/rules.py`) and used by both the QA report and the engine. The table is generated from `outputs/qaqc/qa_rule_catalogue.csv`.

{{TABLE_QA_CAT}}

{{QA_N_RULES}} rules are checked and {{QA_N_TRIG}} are triggered by the supplied data. No FMS record meets an error rule, so all 275 records are modelled. The 14 LOC_DEFAULT records (2,356 t) are modelled with an unknown location.

## 2.2 FMS records (DS-1): findings and treatment

| ID | Finding | Evidence (rule) | Action / treatment | Influence on model |
|---|---|---|---|---|
| QA-F01 | No missing, invalid or duplicated fields; no repeated Cycle IDs | Error rules = 0 | None | - |
| QA-F02 | **Payload is not weighed.** All 275 payloads are exact multiples of 38 t (38-304 t; 152 t = 155 loads), so payload = passes × nominal bucket | PAYLOAD_QUANTISED, PAYLOAD_OFF_QUANTUM = 0 | Per-load CV 8% (A-10); a *systematic* payload factor f_pay 1.00-1.19 (A-06). The largest load (304 t) sets the upper bound | Tonnage and metal uncertainty |
| QA-F03 | **Grades are source-block values**, not load assays: 21 signatures. Cu 5.6-13.7%, Au 5.6-10.1 g/t, Ag 147-256 g/t, Dens 1.92-2.22 t/m³ | `grade_signatures.csv` | Best available grade per load. Grade error per signature (correlated across loads of a source), CV 10% (A-11) | Within-load homogeneity assumed |
| QA-F04 | Grade magnitudes are very high for a Cu-Au mine (mean 8.4% Cu, 8.0 g/t Au) | GRADE_UNITS_UNCONFIRMED | Units used **as supplied**, labelled in every output, stated in the executive summary | Absolute metal values depend on unit confirmation; relative patterns do not |
| QA-F05 | 33 Cycle IDs out of chronological order; 2 records share a timestamp (03-19 21:40, different positions) | ID_OUT_OF_ORDER, TIME_DUPLICATE | Information only. The timestamp defines order | None |
| QA-F06 | **Dump Z is unreliable.** Where the cell had been surveyed before the dump, Z minus that surface has median −0.3 m and P10/P90 −2.5/+3.6 m (n = 197). Two dumps lie outside the [interval start, interval end] surface envelope by more than 5 m | LOC_Z_INCONSISTENT = 2 | Z not used by the algorithm; only X/Y is used (A-29) | Removes a noisy input |
| QA-F07 | **FMS coverage by production day** (D 07:00 to D+1 07:00, `daily_coverage.csv`). 03-17 has neither FMS records nor a survey. Its fill appears in the 03-18 solid, and that interval's volume ratio (1.40) is consistent, so **03-17 was a non-dumping day, not an FMS outage**. Genuine FMS gaps (dataset rules FMS_SILENCE, VOLUME_RATIO_OUTLIER): <br>• interval 0, where the record starts at 17:43 on 03-15; <br>• interval 7 (03-23 07:00 to 03-28 07:00), with 21 loads, silences of 65 h and 64 h, and a ratio of 2.32; <br>• interval 9, where the record stops at 08:17 on 03-29 (ratio 2.17) | `volume_factor_calibration.csv` | These three intervals are excluded from the volume calibration. Their fill not explained by FMS becomes **unattributed** (A-21) | {{UNATT_VOL}} m³ unattributed |
| QA-F08 | 1 load (228 t, 03-31 20:52) is after the last survey cut-off (03-30 07:00) | TIME_AFTER_LAST_SURVEY | Placed **provisionally** with the forward model; re-reconciled when the next survey arrives | 0.5% of tonnes |
| QA-F09 | 56 dumps (9,120 t) lie outside the union of all change solids (median 8 m, max 26 m): dumping on the unsurveyed platform behind the crest | LOC_OUTSIDE_SURVEYS | Modelled; pushed from the dump point. None is more than 100 m away (LOC_OUTSIDE_DOMAIN = 0) | Push distances |
| QA-F10 | **Default / stuck FMS position.** 14 records (2,356 t, 5.3% of FMS tonnes, 03-16 to 03-28) share the identical position E 511,334.7, N 7,122,320.4, Z 4,473.0. That point is below the floor and, until 03-27, in front of the toe | LOC_DEFAULT | Location **unknown**: the load keeps its tonnes, grade and interval, but no position. Its push cost is uniform over the interval's fill (A-32). Version 1 imputed the period centroid instead, which is still an invented position | Allocation of 2.4 kt within its intervals |

## 2.3 Surveys (DS-2, DS-3)

| ID | Finding | Evidence | Action / treatment | Influence |
|---|---|---|---|---|
| QA-S01 | **Each DXF is a closed change solid, not a surface.** 100% of cells are crossed by exactly two faces. The divergence-theorem volume equals the gridded volume (e.g. 2,868 vs 2,867 m³). The bottom of solid *s* equals the top of solid *s−1* wherever they overlap (P5-P95 = 0.000 m) | `survey_qaqc.csv` (SOLID_NOT_CLOSED = 0) | Top = surface at survey *s*; bottom = surface before it; only changed areas are present | Gives measured fill per interval (M) |
| QA-S02 | File names `Topo_250328`/`Topo_250329` carry year 2025. The FMS shows dumping on 2026-03-28/29, the faces advance beyond the 2026-03-27 solid, and their bottoms match its top | SURVEY_NAME_YEAR | Re-dated by **MI-001, MI-002** (reason, author, date recorded; files not renamed) | Chronology |
| QA-S03 | DXF header: `$INSUNITS = 1` (inches), `$MEASUREMENT = 0` (imperial), `$TDUPDATE` 2025-11-14 in all files | DXF_UNITS_HEADER, DXF_SAVED_BEFORE_SURVEY | Header ignored; data are metres (Section 1) | None, once recognised |
| QA-S04 | **Survey acquisition time not supplied** | `temporal_alignment.csv`, `dump_time_of_day.csv` | Cut-off D+1 07:00 (A-05, Section 2.4) | Assignment of loads to intervals |
| QA-S05 | Missing surveys: no file for 03-17 or 03-23 to 03-26. The bottom of the 03-18 solid differs from the previous top on 23% of overlapping cells | SURVEY_GAP, SOLID_BASE_MISMATCH | Intervals flagged; the solid bottom is trusted (A-13b off) | Coarser time resolution in intervals 2 and 7 |
| QA-S06 | **Elevation decreases are not stored as solids.** In the 03-18 solid, 22% of overlap cells have bottoms up to 1-2 m *below* the earlier surveyed surface (dozer cuts, slumping); 6% in the 03-28 solid | `period_reconciliation.csv` (`cut_volume`) | Treated as cuts: the column top is removed and re-handled as a transport source (A-20). {{CUT_VOL}} m³ in total | Mixing of earlier material into later fill |
| QA-S07 | 4 surveys (03-16, 03-21, 03-22, 03-29) do not reach the floor (minimum Z 4,476.4-4,478.8 m vs floor about 4,475 m): the change polygon was clipped above the toe | `reaches_floor` | Recorded; the volume budget shows no missing fill on complete days (A-13b off) | Sensitivity S2 |
| QA-S08 | `Topo_250328.dxf` has inverted face winding (signed volume −4,924 m³). All files contain vertical faces with zero plan area (214-639 per file). Most contain a few degenerate (≤ 25) and duplicate (≤ 6) faces | NORMALS_INVERTED, ZERO_PLAN_AREA_FACES, DEGENERATE_FACES, DUPLICATE_FACES | The rasteriser is winding-independent (top = max, bottom = min); faces without plan area are skipped | None |
| QA-S09 | Triangle edge median 0.93-1.15 m, so the native resolution is about 1 m | `edge_median_m` | Simulation grid 1 m (A-24) | Resolution |
| QA-S10 | Face slopes (cells > 25°): median 36.7°, mode 37.0°, P75 38.5° | `fig_qaqc_repose.png` | Angle of repose 37° (A-03) | Forward model, inference |
| QA-S11 | Toe elevations define a near-horizontal floor: plane 4,475.08 m, dip 0.29°, residual sd 0.26 m | `fig_qaqc_floor_plane.png` | Floor plane (A-12) | Pre-record core thickness |
| QA-S12 | Survey precision cannot be estimated from repeat surveys (bottoms are copies of previous tops). 8-16% of solid area is thinner than 0.1 m | `sliver_frac_lt_0.1m` | σz = 0.05 m assumed; detection limit τ = 0.14 m; changes below τ are not moved | Negligible volume |

## 2.4 Survey timing (A-05)

The survey cut-off was scanned from 0 to 36 h after 00:00 of the nominal survey date, in 0.5 h steps. For each cut-off, the loads were re-assigned and the interval FMS volume Σ T/Dens was compared with the surveyed solid volume. The comparison uses intervals between consecutive-day surveys, a set that does not depend on the cut-off.

{{TABLE_CUTOFF}}

The scan has a plateau from 30 to 31.5 h (r = {{R_31}}, robust CV {{RCV_31}}). Midnight (24 h) gives r = {{R_24}} and robust CV {{RCV_24}}. The dump times corroborate the result. Only 2 of 275 dumps fall between 06:00 and 07:30, and none falls between 18:30 and 20:00 or between 00:00 and 01:30. These are shift changes and meal breaks. Any cut-off between 06:00 and 07:30 therefore gives the same assignment. **The cut-off is D+1 07:00 (31 h)**, the production-day convention. Version 1 searched only 21:00-23:59 of day D, and its "optimum" of 23:59 was the end point of that range.

## 2.5 FMS vs survey volume reconciliation and the volume factor (A-06)

The surveyed change solids total **35,096 m³**: fill {{FILL_VOL}} m³, less {{CUT_VOL}} m³ of revealed cuts, gives a net fill of {{NET_VOL}} m³. Recorded FMS tonnage converts to {{VDENS}} m³ at the FMS densities (Σ T/Dens). Interval by interval:

{{TABLE_VF}}

On the seven intervals with complete FMS records (consistent: within median ± 3 robust SD), measured net fill is a stable 1.19-1.58 times Σ T/Dens. The pooled value is the **volume factor f_v = {{F_V}}** (bootstrap P10-P90 {{F_V_P10}}-{{F_V_P90}}). The three excluded intervals are the FMS gaps of QA-F07, at ratios 2.2-2.4.

f_v is predictive, not merely fitted:

| Hold-out test (`volume_factor_summary.csv`) | Mean absolute volume error on held-out consistent intervals |
|---|---|
| f_v calibrated on the first half (intervals 0-4), predicting intervals 5, 6 and 8 | **{{HO_MAE}}** |
| Constant density (tonnes ÷ volume) calibrated on the first half | {{HO_CONST}} |
| Dens used as the in-pile density (f_v = 1) | {{HO_DENS}} |
| Leave one consistent interval out | {{LOO}} |

What f_v means is **not identifiable** from these data. The in-pile volume of a load is T × f_v / Dens. Two explanations, and any mix of them, fit the same volume:

* **bulking**: the in-pile density is below Dens. If Dens is a bank density, f_v = 1.47 is an ordinary swell factor for blasted rock;
* **under-recorded or unrecorded tonnes**: either payloads understated (pass-count × nominal bucket) or whole loads missing.

The platform carries the split as the payload factor f_pay (true tonnes = T × f_pay, in-pile density = Dens × f_pay / f_v). The base case is f_pay = 1 (recorded tonnes; in-pile density {{RHO_PILE}} t/m³). The Monte Carlo samples f_pay from 1.00 to 1.19 (triangular, most likely 1.00), where the upper bound takes the largest load of 304 t to 362 t, about the largest haul-truck rating. Two interpretations fall outside that range:

* **X1** (all of the excess is payload under-recording). This is excluded, because the largest load would be 448 t.
* **X2** (the excess is loads missing from the FMS, Dens being the in-pile density). This cannot be excluded from these data. It is reported as a separate scenario, "not included in the ranges" (D6, Section 10).

If Dens is a loose (truck-box) density, bulking by a further 47% is implausible, and X2 or under-recording becomes the more likely explanation. **Confirming the basis of Dens is the single most valuable data item for the tonnage estimate** (Section 5).

# 3. Preprocessing decisions

| ID | Decision | Why necessary | Action | Possible influence | How original is retained |
|---|---|---|---|---|---|
| PP-01 | Survey re-dating | Chronology | Interventions MI-001, MI-002 (reason, author, date) | Wrong order would corrupt sequencing | File names unchanged; `date_from_name` and `assigned_date` both stored; intervention id in the survey register |
| PP-02 | Survey cut-off D+1 07:00 | Assign loads to intervals | Config value (`time.survey_cutoff_hours: 31`), chosen by the cut-off scan | Loads near the cut-off shift one interval | `temporal_alignment.csv`, `dump_time_of_day.csv` |
| PP-03 | Rasterise solids to a 1 m grid (top/bottom at cell centres) | Common computational grid | Cached by file hash | ≤ 1 m edge effects | Raw DXF untouched |
| PP-04 | Dump Z ignored | Unreliable (QA-F06) | Only X/Y used | None | Z kept in the loads table |
| PP-05 | Unattributed fill volume | FMS gaps (QA-F07) | Separate material class, imputed grade | {{UNATT_VOL}} m³ with imputed grade | Class tonnage per block |
| PP-06 | Cuts detected from bottoms below earlier tops | Solids omit decreases | Removal + re-handling | Mixing | `cut_volume` per interval |
| PP-07 | Load after the last survey | Not yet surveyed | Forward-model nowcast, flagged | 228 t | Class "Provisional" |
| PP-08 | No record excluded | Brief: do not simply delete | Error rules exclude from modelling only; none triggered | - | All 275 records modelled and kept in `fms_records_with_flags.csv` |
| PP-09 | Default-position records modelled with unknown location | Position physically impossible (QA-F10) | Uniform push cost over the interval's fill | Their material is spread where located loads do not claim the fill | `x_raw`/`y_raw` retained; `loc_unknown` in `movement/loads_used.csv` |
| PP-10 | DXF header units ignored | Header says inches; data are metres (QA-S03) | Coordinates read as metres | None | Header values in `survey_qaqc.csv` |

# 4. Assumption register

Columns follow the course outline, Task 4: Assumption | Need | Justification | Consequence if wrong | Treatment. **S** = tested in sensitivity (one-at-a-time); **MC** = sampled in the Monte Carlo; **Sc** = reported as a scenario.

| ID | Assumption (value / rule) | Need | Justification | Consequence if wrong | Treatment |
|---|---|---|---|---|---|
| A-01 | Coordinates of FMS and surveys share one projected mine grid (m); no transformation; DXF header units ignored | Overlay data | Dumps lie on and behind surveyed crests; consistent elevations; header unit implausible (QA-S03) | Systematic offset would bias push distances | Visual + statistical check (QA-F06, F09) |
| A-02 | `Topo_2503xx` files are 2026 surveys | Chronology | QA-S02 evidence (FMS dates, face progression, bottom = previous top) | Sequence error | Interventions MI-001/002 |
| A-03 | Angle of repose 37° | Forward model; inference of unseen faces | Measured mode 37.0°, median 36.7° of surveyed faces; typical 35-40° for blasted rock | Shape of inferred faces and nowcast | S (forward calibration 35/37/39°) |
| A-04 | DXF solids record accretion only; bottom = previous surface | Derive fill per interval | QA-S01, QA-S06 | Misread change | Verified on all 9 overlaps |
| A-05 | A survey labelled D closes its interval at D+1 07:00 (31 h after 00:00 of D); the first interval is 24 h long | Assign loads to intervals | Cut-off scan plateau 30-31.5 h; shift-change lull 06:00-07:30 (Section 2.4) | Loads shift one interval | S (29/32 h), MC (29-32 h, each with its own f_v calibration) |
| A-06 | In-pile volume = T × f_v / Dens, f_v calibrated (auto, {{F_V}}); true tonnes = T × f_pay, base f_pay = 1.0 (excess volume = bulking; in-pile density {{RHO_PILE}} t/m³) | Convert tonnes to volume and back | f_v hold-out error {{HO_MAE}} vs {{HO_DENS}} for f_v = 1 (Section 2.5). The bulking/under-recording split is not identifiable | Record-period tonnes +{{X2_UPLIFT}} if the excess is missing loads (X2) | MC (f_v bootstrap; f_pay triangular 1.00-1.19, mode 1.00); S (f_v 1.35/1.60, f_pay 1.19); Sc (X1 excluded, X2 not included) |
| A-07 | Truck GPS horizontal error σ = 3 m | Uncertainty | Typical HP GPS on haul trucks 1-5 m; dump-event latency | Destination of individual loads | MC |
| A-08 | Survey vertical precision σz = 0.05 m | Detection limit, uncertainty | Typical drone photogrammetry/LiDAR on rock piles 0.03-0.10 m | Noise counted as fill | S (0.025/0.15), MC (per-survey bias 0.05 m) |
| A-09 | Detection limit τ = 2·√2·σz = 0.14 m | Ignore noise | Standard LoD for DEM differencing (95%) | Small volume not moved | Robustness (k = 1 to 4) |
| A-10 | Payload error CV 8% per load; payload = passes × 38 t | Tonnage uncertainty | Pass-count payload (QA-F02); industry payload-monitor accuracy ±5-10% | Tonnes and metal | MC (systematic part via f_pay, A-06) |
| A-11 | Grade of a load = its source signature; homogeneous within a load; signature error CV 10% | Assign grade | Only data available (QA-F03) | Block grade variance under-represented | MC (correlated by signature) |
| A-12 | Floor = plane fitted to toe cells (4,475.08 m, 0.29° dip) | Bottom of model | Toe elevations consistent across surveys (sd 0.26 m) | Pre-record core volume ±0.26 m × area | Reported; floor residual map |
| A-13 | Never-surveyed cells: behind the crest = flat platform at the nearest crest elevation; in front of the face = face continued at 37° to the floor | Geometry where no survey exists | Truck-operated platform is flat; faces at repose | Pre-record core volume and extent | Geometry class "inferred"; reported separately |
| A-13b | **Off in the base case.** (If on: first-surveyed cells in front of an earlier face were at its repose extrapolation; a solid bottom above it is fill not captured by any solid.) | Option for toe-clipped solids | With f_v calibrated, recorded loads explain measured fill of complete days to ~3%, leaving no room for ~7,200 m³ of unrecorded fill | About 7,200 m³ moves from the pre-record core to unattributed | S (switch); Sc (S2) |
| A-14 | Model domain = convex hull of surveyed change and dump locations | Lateral limit of the pile | No full-pile survey supplied | The back of the pile outside the hull is not modelled | Stated limitation; R-01 |
| A-15 | Dozer push follows least total push work (optimal transport over a slope-aware geodesic cost) | Unknown dozer trajectories | Operators minimise push distance; OT is the classical earth-moving formulation | Wrong allocation of grade inside an interval's fill | MC/S on ε, α, L_max; twin experiments |
| A-16 | Uphill push penalty α = 4 m per m of lift | Prevent implausible uphill pushes | Dozer production falls sharply uphill (grade correction factors, Caterpillar Performance Handbook) | Allocation across the crest | S (1/10), MC U(1, 10) |
| A-17 | Maximum effective push distance 90 m (geodesic) | Limit movement | Dozing is generally economical to about 100 m | Loads may be retained on the platform | S (50/130), MC U(50, 130) |
| A-18 | Mixing length ε = 6 m (entropy regularisation) | Degree of mixing | GPS error (3 m), blade spill, rolling on the face; twin favours small-moderate ε | Over- or under-mixing of grades | S (2/15), MC U(2, 15), twin |
| A-19 | Within one interval, the fill of a column is vertically homogeneous | Vertical placement | Daily fill is built by many interleaved loads | Vertical grade resolution limited to the interval layer (0.5-3 m) | Inherent; documented |
| A-20 | Elevation decrease below an earlier surface = material removed by dozer/slumping and re-handled in the same interval | Solids omit cuts (QA-S06) | Dozers trim crests while pushing | Cut volume re-mixed | Reported per interval |
| A-21 | Unattributed fill has the tonnage-weighted mean grade and in-pile density of FMS loads in the same and adjacent intervals | FMS gaps (QA-F07) | Material placed in the same days most likely came from the same faces | Grade of {{T_U}} t is imputed | MC bootstrap of grades; separate class |
| A-22 | Pre-record core (legacy): in-pile density and grade = FMS mean | Populate blocks below the pre-record surface | No information supplied | {{T_L}} t carry an **assumed** grade | Class "Legacy-assumed", confidence "Uninformed"; reported after the record-period inventory, never as measured |
| A-23 | FMS volume not seen in an interval's fill is retained on the platform and pushed later (dozer lag) | Timing mismatch | Paddock dumping and pushing later is normal practice | Grade appears in the next interval's fill | Carried volume reported |
| A-24 | Simulation grid 1 m, vertical integration exact (layers) | Numerics | Matches survey triangle size (QA-S09) | Edge effects | Robustness 0.5/2.5 m |
| A-25 | Block size 5 × 5 × 2 m, partial blocks kept with fill fraction | Planning unit | Information resolution about 5 m (GPS + mixing); 2 m gives several layers per face height and suits loader slices | Smoothing of grade | S (2 × 2 × 1, 10 × 10 × 4) |
| A-26 | Tonnes as reported by the FMS; no moisture correction (wet/dry basis unknown) | Units | No moisture data | Systematic tonnage bias of a few % | Stated; R-05 |
| A-27 | No particle-size segregation of grade down the face | Not observable | No size-grade data | Toe vs crest grade bias | Stated limitation |
| A-28 | No time-dependent settlement after placement | Not observable | Short record (2 weeks) | Small volume bias | Absorbed in the f_v calibration |
| A-29 | Dump Z is not used | QA-F06 | Unreliable | None | - |
| A-30 | Boundary conditions: material cannot leave the domain; outside the domain is not modelled | Numerics | Domain covers all observed change | None inside the domain | - |
| A-31 | Missing data: FMS gaps → unattributed class; survey gaps → gap intervals; no synthetic loads are invented | Missing-data treatment | Transparency over completeness | Unattributed share | Reported; R-02 |
| A-32 | Records sharing an identical X/Y/Z with ≥ 2 others (LOC_DEFAULT), or > 100 m from every solid (LOC_OUTSIDE_DOMAIN), have an **unknown** dump location: uniform push cost over their interval's fill | 14 records have an impossible location (QA-F10) | Identical coordinates to 0.01 m over 12 days, below the floor | Allocation of 2.4 kt within its intervals | Unit and real-data tests; `fms_location_unknown` intervention for further cases |

# 5. Data that would most reduce uncertainty (value of information)

1. **The basis of `Dens`** (bank or loose density) and a bulk-density test on the pile. This decides between bulking and missing tonnes (A-06), and with it record-period tonnes within a factor of {{F_V}}.
2. A full-pile survey (current) and a pre-stockpile ground survey. These remove A-13 and A-14 and most of A-22.
3. An FMS completeness audit for 03-23 to 03-27 and after 03-29 08:17 (removes most unattributed volume), and the payload calibration of the loader buckets (f_pay).
4. Survey acquisition times (A-05).
5. Truck ID, source bench and per-load grade (A-11).
6. Tracer trials (RFID or coloured tags in selected loads) to calibrate ε and the push model (A-15 to A-18).
