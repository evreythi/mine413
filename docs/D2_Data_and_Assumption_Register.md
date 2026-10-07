---
title: "D2 - Data and Assumption Register"
subtitle: "MIN E 413 Term Project - Pit I HG stockpile reconstruction"
---

This register is the controlled record of (1) the data received, (2) the quality findings, (3) every preprocessing and cleaning decision, and (4) every engineering assumption, with its need, justification, consequence and treatment. Parameter values live in `config/project.yaml`, and each value there is tagged with the ID used here (`A-xx`). Machine-readable versions of the QA/QC results are in `outputs/qaqc/`. **No raw record was deleted or edited.** Raw files are read in place from `Data_Topo 2026.zip` and identified by SHA-256 (`outputs/audit/data_registry.csv`).

Information type key, used throughout the project (course outline, Task 7): **M** = measured, **I** = inferred from data, **A** = assumed, **G** = model-generated.

# 1. Dataset inventory

| ID | File(s) | Content | Coverage | Type | Notes |
|---|---|---|---|---|---|
| DS-1 | `Dump Data.csv` | 275 FMS truck-dump records: Cycle ID, payload (t), Au (g/t), Ag (g/t), Cu (%), density (t/m³), dump X/Y/Z, timestamp (minute resolution) | 2026-03-15 17:43 to 2026-03-31 20:52; 44,650 t | M | No truck ID or source (pit/bench) field supplied. Grades are per **source signature** (21 distinct Cu/Au/Ag/density combinations), not per-load assays |
| DS-2 | `Topo_260315.dxf` … `Topo_260327.dxf` (8 files) | Vulcan DXF, 3DFACE triangles, one layer per file | 2026-03-15 to 03-27 (no 03-17, 03-23 to 03-26) | M | Each file is a **closed change solid**: a top surface (this survey) and a bottom surface (previous surface) over the area that changed (QA-S01) |
| DS-3 | `Topo_250328.dxf`, `Topo_250329.dxf` | As DS-2 | Re-dated to 2026-03-28 and 2026-03-29 (QA-S02) | M | File-name year inconsistent with the record |
| DS-4 | (not supplied) | Full stockpile surface, pre-stockpile ground, density tests, dozer logs, truck IDs, moisture | None | n/a | Absence drives assumptions A-12, A-13, A-14, A-22. Requested as recommendations (D6) |

Units and coordinate reference: metres. Easting is about 511,300 and Northing about 7,122,300, consistent with a UTM-type grid in the southern hemisphere. Elevation is about 4,480 m. DXF `$INSUNITS` is 6 (metres). FMS and surveys overlay without offset (dumps sit on and behind the surveyed crest), so **no transformation** was applied (A-01).

# 2. QA/QC findings

## 2.1 FMS records (DS-1)

| ID | Finding | Evidence | Action / treatment | Influence on model | Traceability |
|---|---|---|---|---|---|
| QA-F01 | No duplicate IDs, missing fields or unparseable timestamps | Flags F01-F03 = 0 | None | - | `fms_flag_summary.csv` |
| QA-F02 | **Payload is not weighed.** All 275 payloads are exact multiples of 38 t (38-304 t; 152 t = 155 loads), so payload is a pass-count estimate (bucket factor × passes) | `payload_distribution.csv` | Retained. Per-load payload error CV 8% plus a ±3% systematic bias per Monte Carlo realisation (A-10). 2 part loads (38, 76 t) and 3 heavy loads (266, 304 t) flagged F05/F06 | Tonnage, and therefore metal, uncertainty | Flags kept in `fms_records_with_flags.csv` |
| QA-F03 | **Grades are source-block values**, not load assays: 21 signatures, each repeated across many loads. Cu 5.6-13.7%, Au 5.6-10.1 g/t, Ag 147-256 g/t, density 1.92-2.22 t/m³ | `grade_signatures.csv` | Treated as the best available grade per load. Grade error modelled per signature (correlated across loads of the same source), CV 10% (A-11) | Within-load homogeneity assumed (A-11) | Signature ID `grade_group` added |
| QA-F04 | Grade magnitudes are very high for a Cu-Au mine (mean 8.4% Cu, 8.0 g/t Au). Possible unit scaling or anonymisation | Summary statistics | Units used **as supplied** (% Cu, g/t Au/Ag), labelled in every output. Flagged for confirmation with the mine geology team | Absolute metal values depend on unit confirmation; relative patterns do not | Recommendation R-07 |
| QA-F05 | 33 Cycle IDs out of chronological order | F04 | Information only. The timestamp defines order | None | Flag |
| QA-F06 | **Dump Z is unreliable**: Z minus surveyed surface at dump time has median −0.7 m and P10/P90 −2.8/+2.0 m (n = 200). 14 dumps lie below the fitted floor and 29 have \|ΔZ\| > 3 m | `fig_qaqc_dumpz_timeofday.png` | Z not used by the algorithm. Only X/Y is used (A-29) | Removes a noisy input | F10/F11 flags |
| QA-F07 | **FMS completeness is uneven in time.** No records for 2026-03-17, 03-23, 03-24, 03-26, 03-27 or 03-30. Single records on 03-25 and 03-31. Records stop at 12:27 on 03-16 and restart at 20:47 on 03-18 (56 h silence) while the surveys show 4,843 m³ placed | `daily_coverage.csv`, `fig_qaqc_daily_tonnage_volume.png` | Not imputed as loads. The observed volume not explained by FMS becomes **unattributed** material with an imputed grade and a separate class (A-21) | Large unattributed share in periods 03-18 and 03-27 | Period table; class fields in the block model |
| QA-F08 | FMS starts at 17:43 on 03-15, part-way through the first survey period | `daily_coverage.csv` | Period 0 treated as partially covered: 65% of its fill is unattributed | As above | |
| QA-F09 | 1 load (228 t, 03-31 20:52) is after the last survey | F12 | Placed **provisionally** with the forward physics model and flagged; re-reconciled automatically when the next survey arrives | 0.1% of tonnes | Class "Provisional" |
| QA-F10 | All dumps lie within 60 m of surveyed change (F09 = 0); 18 dumps fall in survey-gap periods (F13) | Flags | Retained | - | Flags |

## 2.2 Surveys (DS-2, DS-3)

| ID | Finding | Evidence | Action / treatment | Influence |
|---|---|---|---|---|
| QA-S01 | **Each DXF is a closed change solid, not a surface.** 100% of cells are crossed by exactly two faces. The divergence-theorem volume equals the gridded volume (e.g. 2,868 vs 2,867 m³). The bottom of solid *s* equals the top of solid *s−1* wherever they overlap (P5-P95 = 0.000 m) | `survey_qaqc.csv` | Top = surface at survey *s*; bottom = surface at the previous survey; only changed areas are present | Defines fill per period directly (M). The pre-record surface is observed only where change occurred |
| QA-S02 | File names `Topo_250328`/`Topo_250329` carry year 2025. All ten layer names use year '25' (e.g. layer `250315_STOCK_HGHS` in `Topo_260315.dxf`). FMS shows dumping on 2026-03-28/29. The faces advance beyond the 2026-03-27 solid, and their bottoms match its top | `survey_qaqc.csv`, `fig_growth_face_advance.png` | Re-dated to 2026-03-28 and 2026-03-29 via `config/survey_overrides.csv` (manual intervention, reason recorded, applied in code not by renaming files) | Chronology |
| QA-S03 | **Survey timing not supplied.** Correlation of period FMS volume with surveyed volume is r = 0.96 if surveys represent end of day (23:59), and r ≤ 0.21 for any time before 10:00 | `temporal_alignment.csv`, `fig_temporal_alignment.png` | Survey time = 23:59 of the file date (A-05); 21:00-23:59 sampled in Monte Carlo | Assignment of loads to periods |
| QA-S04 | Missing surveys: 03-17 and 03-23 to 03-26. Bottoms of the 03-18 and 03-27 solids differ from the previous tops on 23% and 14% of overlapping cells | `survey_qaqc.csv` | Periods flagged as gap periods; unobserved fill on first-surveyed cells inferred (A-13b) | Larger uncertainty in those periods |
| QA-S05 | **Elevation decreases are not stored as solids.** 22% of overlap cells in the 03-18 solid and 6% in the 03-28 solid have bottoms up to 1-2 m *below* the earlier surveyed surface (dozer cuts or slumping) | `period_reconciliation.csv` (`frac_lowered`, `cut_volume`) | Treated as cuts: the top of the column is removed and re-handled as a transport source (A-20). Total 567 m³ | Mixing of earlier material into later fill |
| QA-S06 | 4 surveys (03-16, 03-21, 03-22, 03-29) do not reach the floor (minimum Z 4,476.4-4,478.8 m vs floor about 4,475 m): the change polygon was clipped above the toe | `reaches_floor` | Toe fill captured later is attributed by A-13b | Part of the 7,232 m³ of "unobserved fill" |
| QA-S07 | `Topo_250328.dxf` has inverted face winding (signed volume −4,924 m³). There are a few degenerate (≤ 25) and duplicate (≤ 6) triangles per file | `survey_qaqc.csv` | Rasterisation is winding-independent (top = max, bottom = min); degenerate faces are skipped | None |
| QA-S08 | Triangle edge median 0.93-1.15 m, so the native resolution is about 1 m | `edge_median_m` | Simulation grid 1 m (A-24) | Resolution |
| QA-S09 | Face slopes (cells > 25°, n = 13,084): median 36.7°, mode 37.0°, P75 38.5°, P90 40.1° | `fig_qaqc_repose.png` | Angle of repose 37° (A-03) | Forward model, inference |
| QA-S10 | Toe elevations define a near-horizontal floor: plane 4,475.08 m, dip 0.29°, residual sd 0.26 m (n = 197) | `fig_qaqc_floor_plane.png` | Floor plane (A-12) | Legacy thickness |
| QA-S11 | Survey precision cannot be estimated from repeat surveys (bottoms are copies of previous tops). 8-16% of solid area is thinner than 0.1 m | `sliver_frac_lt_0.1m` | σz = 0.05 m assumed; detection limit τ = 0.14 m; changes below τ are not moved (96 m³ in total) | Negligible volume |

## 2.3 FMS vs survey reconciliation (Task 2 summary)

The surveyed change solids total **35,096 m³**. With the inferred unobserved toe fill (A-13b), the observed fill used by the model is **42,353 m³**. FMS tonnage converts to **21,640 m³** at the FMS densities. In periods with complete FMS and survey coverage, the apparent density (FMS t ÷ solid m³) is 1.2-2.8 t/m³ day by day, with a pooled value of 1.67 t/m³ (39,596 t / 23,708 m³), against a mean FMS density of 2.06 t/m³. The day-to-day scatter is dominated by dozer timing (material dumped late in one survey day and pushed the next). For example, 03-20 shows 345 m³ more FMS volume than fill; that volume is carried to 03-21. The pooled deficit (FMS volume = 81% of surveyed solid volume on the "complete" days; 56-131% day by day) has two non-exclusive explanations that the supplied data cannot separate: (a) swell, so the in-pile density is lower than the FMS density (κ < 1); (b) unrecorded loads. Both are carried as uncertainty (A-06, A-21).

# 3. Preprocessing decisions

| ID | Decision | Why necessary | Action | Possible influence | How original is retained |
|---|---|---|---|---|---|
| PP-01 | Survey re-dating | Chronology | Override table with reason and approver | Wrong order would corrupt sequencing | Original names unchanged; `date_from_name` and `assigned_date` both stored |
| PP-02 | Survey time 23:59 | Assign loads to periods | Config value, data-driven choice | ±1 period for loads near midnight | Alignment table |
| PP-03 | Rasterise solids to 1 m grid (top/bottom at cell centres) | Common computational grid | Cached by file hash | ≤ 1 m edge effects | Raw DXF untouched |
| PP-04 | Dump Z ignored | Unreliable | Only X/Y used | None | Z kept in loads table |
| PP-05 | Unattributed fill volume | FMS gaps | Separate material class, imputed grade | Grade of 21% of tonnes is imputed | Class tonnage per block |
| PP-06 | Cuts detected from bottoms below earlier tops | Solids omit decreases | Removal + re-handling | Mixing | `cut_volume` per period |
| PP-07 | Load after last survey | Not yet surveyed | Forward-model nowcast, flagged | 228 t | Class "Provisional" |
| PP-08 | No record excluded | Brief: do not simply delete | Flags only | - | All 275 records used |

# 4. Assumption register

Columns follow the course outline, Task 4: Assumption | Need | Justification | Consequence if wrong | Treatment. **S** = tested in sensitivity (one-at-a-time) and/or **MC** = sampled in the Monte Carlo uncertainty analysis.

| ID | Assumption (value / rule) | Need | Justification | Consequence if wrong | Treatment |
|---|---|---|---|---|---|
| A-01 | Coordinates of FMS and surveys share one projected mine grid (m); no transformation | Overlay data | Dumps lie on and behind surveyed crests; consistent elevations | Systematic offset would bias push distances | Visual + statistical check (QA-F06, F09) |
| A-02 | `Topo_2503xx` files are 2026 surveys | Chronology | QA-S02 evidence (FMS dates, face progression, bottom = previous top) | Sequence error | Manual override logged |
| A-03 | Angle of repose 37° | Forward model; inference of unseen faces | Measured mode 37.0°, median 36.7° of surveyed faces; typical 35-40° for blasted rock | Shape of inferred faces and nowcast | S (forward calibration 35/37/39°) |
| A-04 | DXF solids record accretion only; bottom = previous surface | Derive fill per period | QA-S01, QA-S05 | Misread change | Verified on all 9 overlaps |
| A-05 | Surveys represent the stockpile at 23:59 of the file date | Assign loads to periods | Alignment r = 0.96 vs ≤ 0.21 for morning (QA-S03) | Loads placed one period early or late | S (21:00 vs 23:59), MC (21:00-23:59) |
| A-06 | In-pile bulk density = FMS density × κ, κ = 1.0 | Convert tonnes to volume | FMS density is the mine's own value (M); calibrating κ from volumes is confounded with missing loads (Section 2.3) | Tonnage of unattributed/legacy volume and FMS footprint size change proportionally | S (0.90/1.10), MC U(0.80, 1.05) |
| A-07 | Truck GPS horizontal error σ = 3 m | Uncertainty | Typical autonomous/HP GPS on haul trucks 1-5 m; dump-event latency | Destination of individual loads | MC |
| A-08 | Survey vertical precision σz = 0.05 m | Detection limit, uncertainty | Typical drone photogrammetry/LiDAR on rock piles 0.03-0.10 m | Noise counted as fill | S (0.025/0.15), MC (per-survey bias 0.05 m) |
| A-09 | Detection limit τ = 2·√2·σz = 0.14 m | Ignore noise | Standard LoD for DEM differencing (95%) | 96 m³ not moved | Robustness (k = 1 to 4) |
| A-10 | Payload error CV 8% per load, ±3% systematic | Tonnage uncertainty | Pass-count payload (QA-F02); industry payload-monitor accuracy ±5-10% | Tonnes and metal | MC |
| A-11 | Grade of a load = its source signature; homogeneous within a load; signature error CV 10% | Assign grade | Only data available (QA-F03) | Block grade variance under-represented | MC (correlated by signature) |
| A-12 | Floor = plane fitted to toe cells (4,475.08 m, 0.29° dip) | Bottom of model | Toe elevations consistent across surveys (sd 0.26 m) | Legacy volume ±0.26 m × area (about ±2.6 kt per 5,000 m²) | Reported; floor residual map |
| A-13 | Never-surveyed cells: behind the crest = flat platform at the nearest crest elevation; in front of the face = face continued at 37° to the floor | Geometry where no survey exists | Truck-operated platform is flat; dumps on platform; faces at repose | Legacy volume/extent | Geometry class "inferred" in block model; legacy reported separately |
| A-13b | First-surveyed cells in front of an earlier surveyed face were at the repose extrapolation of that face; a solid bottom above it is fill placed during the record but not captured by a solid (toe-clipped solids, missing surveys) | Avoid counting recent fill as legacy | QA-S04, QA-S06: toe-clipped solids; solid bottoms 2-4 m above the floor directly in front of earlier faces | 7,232 m³ moves between "legacy" and "unattributed" | S (switch on/off) |
| A-14 | Model domain = convex hull of surveyed change and dump locations | Lateral limit of the pile | No full-pile survey supplied | The back of the pile outside the hull is not modelled | Stated limitation; R-01 |
| A-15 | Dozer push direction/destination follows least total push work (optimal transport over a slope-aware geodesic cost) | Unknown dozer trajectories | Operators minimise push distance; OT is the classical earth-moving formulation (Monge, 1781) | Wrong allocation of grade inside a period's fill | MC/S on ε, α, Lmax; twin experiment |
| A-16 | Uphill push penalty α = 4 m per m of lift | Prevent physically implausible uphill pushes | Dozer production falls sharply when pushing uphill (grade correction factors, Caterpillar Performance Handbook) | Allocation across the crest | S (1/10), MC U(1, 10) |
| A-17 | Maximum effective push distance 90 m (geodesic) | Limit movement | Dozing is generally considered economical to about 100 m (Caterpillar Performance Handbook); see the reconstructed push-distance distribution | Loads may be forced to platform (retained) | S (50/130), MC U(50, 130) |
| A-18 | Mixing length ε = 6 m (entropy regularisation) | Degree of mixing | Combination of GPS error (3 m), blade spill, rolling on the face; twin experiment favours small-moderate ε | Over- or under-mixing of grades | S (2/15), MC U(2, 15), twin |
| A-19 | Within one period, the fill of a column is vertically homogeneous | Vertical placement | Daily fill is built by many interleaved loads | Vertical grade resolution limited to the period layer (0.5-3 m) | Inherent; documented |
| A-20 | Elevation decrease below an earlier surface = material removed by dozer/slumping and re-handled in the same period | Solids omit cuts (QA-S05) | Dozers trim crests while pushing | 567 m³ re-mixed | Reported per period |
| A-21 | Unattributed fill has the tonnage-weighted mean grade/density of FMS loads in the same and adjacent periods | FMS gaps (QA-F07) | Material placed in the same days most likely came from the same faces | Grade of 41.8 kt is imputed | MC bootstrap of grades; separate class |
| A-22 | Legacy (pre-record) material: density and grade = FMS mean (8.42% Cu, 8.00 g/t Au, 2.06 t/m³) | Populate blocks below the pre-record surface | No information supplied | 116 kt carry an **assumed** grade | Class "Legacy-assumed", confidence "Uninformed"; never reported as measured |
| A-23 | FMS volume not seen in that period's fill is retained on the platform and pushed in a later period (dozer lag) | Timing mismatch | Paddock dumping and pushing later is normal practice | Grade appears in the next period's fill | Carried volume reported |
| A-24 | Simulation grid 1 m, vertical integration step exact (layers) | Numerics | Matches survey triangle size (QA-S08) | Edge effects | Robustness 0.5/2.5 m |
| A-25 | Block size 5 × 5 × 2 m, partial blocks kept with fill fraction | Planning unit | Information resolution about 5 m (GPS + mixing). A 2 m vertical gives several layers per face height; small enough for loader reclaim slices | Smoothing of grade | S (2 × 2 × 1, 10 × 10 × 4) |
| A-26 | Tonnes as reported by the FMS; no moisture correction (wet/dry basis unknown) | Units | No moisture data | Systematic tonnage bias of a few % | Stated; R-05 |
| A-27 | No particle-size segregation of grade down the face | Not observable | No size-grade data | Toe vs crest grade bias | Stated limitation; R-06 sampling |
| A-28 | No time-dependent settlement after placement | Not observable | Short record (2 weeks) | Small volume bias | Absorbed in κ range |
| A-29 | Dump Z is not used | QA-F06 | Unreliable | None | - |
| A-30 | Boundary conditions: material cannot leave the domain; outside the domain is not modelled | Numerics | Domain covers all observed change | None inside the domain | - |
| A-31 | Missing data: FMS gaps → unattributed class; survey gaps → gap periods; no synthetic loads are invented | Missing-data treatment | Transparency over completeness | Unattributed share is large (21% of tonnes) | Reported; R-02 |

# 5. Data that would most reduce uncertainty (value of information)

1. A full-pile survey (current) and a pre-stockpile ground survey (removes A-13, A-14 and most of A-22).
2. FMS completeness audit for 03-16 to 03-18 and 03-22 to 03-28 (removes most unattributed volume).
3. Bulk density and moisture tests on the stockpile (A-06, A-26).
4. Truck ID, source bench and per-load grade (A-11).
5. Tracer trials (RFID or coloured tags in selected loads) to calibrate ε and the push model (A-15 to A-18).
