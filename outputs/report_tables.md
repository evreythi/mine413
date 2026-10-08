# Key result tables (auto-generated - do not edit)

## QA rule catalogue
| rule_id | level | severity | description | count | tonnes | items |
|---|---|---|---|---|---|---|
| MISSING_PAYLOAD | record | error | Truck payload missing | 0 | 0 |  |
| MISSING_TIME | record | error | Dump timestamp missing or unparseable | 0 | 0 |  |
| GRADE_MISSING | record | error | Cu, Au or Ag missing | 0 | 0 |  |
| DENS_MISSING | record | error | Density missing | 0 | 0 |  |
| LOC_MISSING | record | error | Dump X or Y missing | 0 | 0 |  |
| DUP_IDENTICAL | record | warning | Cycle ID repeated with identical content | 0 | 0 |  |
| DUP_CONFLICT | record | error | Cycle ID repeated with different content | 0 | 0 |  |
| PAYLOAD_NONPOSITIVE | record | error | Payload <= 0 t | 0 | 0 |  |
| PAYLOAD_PARTIAL | record | info | Payload <= 50% of the median (part load) | 3 | 152 | cycle 666887, 667076, 671660 |
| PAYLOAD_HIGH | record | info | Payload > 150% of the median | 3 | 874 | cycle 665064, 666376, 668024 |
| PAYLOAD_OFF_QUANTUM | record | warning | Payload not a multiple of the 38 t pass quantum (A-10) | 0 | 0 |  |
| GRADE_INVALID | record | error | Cu <= 0 or > 100 %, or Au/Ag < 0 | 0 | 0 |  |
| GRADE_OUTLIER | record | info | Grade outside Q1 - 3 IQR .. Q3 + 3 IQR | 1 | 114 |  |
| DENS_INVALID | record | error | Density outside 1.5-3.0 t/m3 | 0 | 0 |  |
| LOC_OUTSIDE_DOMAIN | record | error | Dump X/Y more than 100 m outside every survey solid | 0 | 0 |  |
| LOC_DEFAULT | record | warning | X/Y/Z shared by >= 3 records (default / stuck FMS position, A-32) | 14 | 2,356 | cycle 664887, 664959, 665073, 666320, 666394, 666376, 666430, 666471, 666564, 666692, 666909, 667087, 667091, 671466 |
| LOC_OUTSIDE_SURVEYS | record | info | Dump X/Y outside the union of all survey change solids | 56 | 9,120 |  |
| LOC_Z_INCONSISTENT | record | info | Dump Z outside the interval's [start surface, end surface] envelope +/- 5 m | 2 | 380 | cycle 667102, 671466 |
| TIME_BEFORE_FIRST_INTERVAL | record | error | Dump before the start of the first survey interval | 0 | 0 |  |
| TIME_AFTER_LAST_SURVEY | record | warning | Dump after the last survey cut-off | 1 | 228 | cycle 673291 |
| TIME_DUPLICATE | record | info | Timestamp identical to another record | 2 | 304 | cycle 666880, 666882 |
| ID_OUT_OF_ORDER | record | info | Cycle ID not in chronological order | 33 | 5,358 |  |
| IN_SURVEY_GAP_INTERVAL | record | info | Dump inside a survey interval longer than 36 h | 63 | 9,918 |  |
| DXF_UNITS_HEADER | survey | warning | $INSUNITS = 1 (inches) and $MEASUREMENT = 0 (imperial) in the DXF header | 10 |  | all files |
| DXF_SAVED_BEFORE_SURVEY | survey | info | $TDUPDATE (last saved) is earlier than the nominal survey date | 10 |  | all files (TDUPDATE 2025-11-14) |
| SURVEY_NAME_YEAR | survey | error | File-name year contradicts the survey sequence and the FMS record | 2 |  | Topo_250328.dxf, Topo_250329.dxf |
| LAYER_DATE_MISMATCH | survey | info | Layer-name date token differs from the file-name date (year 25 vs 26) | 8 |  | Topo_260315.dxf, Topo_260316.dxf, Topo_260318.dxf, Topo_260319.dxf, Topo_260320.dxf, Topo_260321.dxf, Topo_260322.dxf, Topo_260327.dxf |
| ZERO_PLAN_AREA_FACES | survey | info | Faces with zero plan area (vertical walls of the closed solid) | 10 |  | all files (214-639 per file) |
| DEGENERATE_FACES | survey | info | Faces with zero 3-D area | 8 |  | Topo_260315.dxf, Topo_260318.dxf, Topo_260319.dxf, Topo_260320.dxf, Topo_260322.dxf, Topo_260327.dxf, Topo_250328.dxf, Topo_250329.dxf |
| DUPLICATE_FACES | survey | info | Faces repeated in the same file | 6 |  | Topo_260315.dxf, Topo_260318.dxf, Topo_260319.dxf, Topo_260320.dxf, Topo_260322.dxf, Topo_250328.dxf |
| SOLID_NOT_CLOSED | survey | warning | Under 98% of solid cells have exactly one top and one bottom face | 0 |  |  |
| NORMALS_INVERTED | survey | info | Face orientation gives a negative signed volume | 1 |  | Topo_250328.dxf |
| SOLID_BASE_MISMATCH | survey | warning | Over 20% of cells where the solid's bottom differs from the previous survey top by more than the LOD | 1 |  | Topo_260318.dxf |
| SURVEY_GAP | dataset | warning | Survey interval longer than 36 h | 2 |  | interval 2 (03-17 07:00 to 03-19 07:00, 48 h); interval 7 (03-23 07:00 to 03-28 07:00, 120 h) |
| FMS_PARTIAL_FIRST_INTERVAL | dataset | warning | FMS record starts after the start of the first survey interval | 1 |  | first FMS record 2026-03-15 17:43, interval 0 starts 2026-03-15 07:00 |
| FMS_SILENCE | dataset | warning | No FMS record for more than 24 h inside an interval | 2 |  | interval 2 (38 h); interval 7 (64 h) |
| VOLUME_RATIO_OUTLIER | dataset | warning | Interval's surveyed fill / FMS volume outside median +/- 3 robust SD | 3 |  | interval 0 (ratio 2.35); interval 7 (ratio 2.32); interval 9 (ratio 2.17) |
| SURVEY_CHANGE_NO_FMS | dataset | warning | A day with a survey change solid but no FMS record | 0 |  |  |
| PAYLOAD_QUANTISED | dataset | info | Every payload is a multiple of 38 t (pass count x nominal bucket) | 1 |  | 275 records |
| GRADE_UNITS_UNCONFIRMED | dataset | warning | Mean Cu 8.4 % and Au 8 g/t are about 10x typical Cu-Au feed | 1 |  | mean Cu 8.42 %, Au 8.00 g/t |

## FMS record rules
| rule_id | severity | description | records | tonnes | treatment |
|---|---|---|---|---|---|
| MISSING_PAYLOAD | error | Truck payload missing | 0 | 0 | Excluded from modelling, kept in register |
| MISSING_TIME | error | Dump timestamp missing or unparseable | 0 | 0 | Excluded from modelling, kept in register |
| GRADE_MISSING | error | Cu, Au or Ag missing | 0 | 0 | Excluded from modelling, kept in register |
| DENS_MISSING | error | Density missing | 0 | 0 | Excluded from modelling, kept in register |
| LOC_MISSING | error | Dump X or Y missing | 0 | 0 | Excluded from modelling, kept in register |
| DUP_IDENTICAL | warning | Cycle ID repeated with identical content | 0 | 0 | First copy modelled, repeats excluded |
| DUP_CONFLICT | error | Cycle ID repeated with different content | 0 | 0 | First copy modelled, others excluded; resolve with an fms_exclude intervention |
| PAYLOAD_NONPOSITIVE | error | Payload <= 0 t | 0 | 0 | Excluded from modelling |
| PAYLOAD_PARTIAL | info | Payload <= 50% of the median (part load) | 3 | 152 | Modelled; payload error in Monte Carlo |
| PAYLOAD_HIGH | info | Payload > 150% of the median | 3 | 874 | Modelled; bounds the payload factor (A-06) |
| PAYLOAD_OFF_QUANTUM | warning | Payload not a multiple of the 38 t pass quantum (A-10) | 0 | 0 | Modelled; checked manually |
| GRADE_INVALID | error | Cu <= 0 or > 100 %, or Au/Ag < 0 | 0 | 0 | Excluded from modelling |
| GRADE_OUTLIER | info | Grade outside Q1 - 3 IQR .. Q3 + 3 IQR | 1 | 114 | Modelled (source-block grade); flagged |
| DENS_INVALID | error | Density outside 1.5-3.0 t/m3 | 0 | 0 | Excluded from modelling |
| LOC_OUTSIDE_DOMAIN | error | Dump X/Y more than 100 m outside every survey solid | 0 | 0 | Location treated as unknown (as LOC_DEFAULT) |
| LOC_DEFAULT | warning | X/Y/Z shared by >= 3 records (default / stuck FMS position, A-32) | 14 | 2,356 | Location treated as unknown: uniform push cost over the interval's fill |
| LOC_OUTSIDE_SURVEYS | info | Dump X/Y outside the union of all survey change solids | 56 | 9,120 | Modelled: pushed from the dump point (crest dumping) |
| LOC_Z_INCONSISTENT | info | Dump Z outside the interval's [start surface, end surface] envelope +/- 5 m | 2 | 380 | Modelled; dump Z is not used by the engine (X/Y only) |
| TIME_BEFORE_FIRST_INTERVAL | error | Dump before the start of the first survey interval | 0 | 0 | Excluded (belongs to the pre-record pile) |
| TIME_AFTER_LAST_SURVEY | warning | Dump after the last survey cut-off | 1 | 228 | Placed provisionally by the forward model; reconciled when the next survey arrives |
| TIME_DUPLICATE | info | Timestamp identical to another record | 2 | 304 | Modelled; both kept |
| ID_OUT_OF_ORDER | info | Cycle ID not in chronological order | 33 | 5,358 | None - the timestamp governs ordering |
| IN_SURVEY_GAP_INTERVAL | info | Dump inside a survey interval longer than 36 h | 63 | 9,918 | Modelled; the interval's spatial resolution in time is coarser |

## Survey QA
| file | assigned_datetime | footprint_m2 | volume_m3 | slope_p50 | reaches_floor | normals_inverted | frac_bottom_mismatch_gt_0.14 |
|---|---|---|---|---|---|---|---|
| Topo_260315.dxf | 2026-03-16 07:00:00 | 1,996.00 | 2,867.01 | 35.96 | True | False |  |
| Topo_260316.dxf | 2026-03-17 07:00:00 | 1,330.00 | 2,305.84 | 36.18 | False | False | 0.00 |
| Topo_260318.dxf | 2026-03-19 07:00:00 | 2,290.00 | 4,842.78 | 36.16 | True | False | 0.23 |
| Topo_260319.dxf | 2026-03-20 07:00:00 | 2,568.00 | 8,708.00 | 34.66 | True | False | 0.00 |
| Topo_260320.dxf | 2026-03-21 07:00:00 | 1,607.00 | 2,150.86 | 36.82 | True | False | 0.00 |
| Topo_260321.dxf | 2026-03-22 07:00:00 | 1,327.00 | 1,425.73 | 36.16 | False | False | 0.01 |
| Topo_260322.dxf | 2026-03-23 07:00:00 | 1,642.00 | 2,887.79 | 35.90 | False | False | 0.09 |
| Topo_260327.dxf | 2026-03-28 07:00:00 | 2,147.00 | 3,679.46 | 35.34 | True | False | 0.14 |
| Topo_250328.dxf | 2026-03-29 07:00:00 | 3,173.00 | 4,918.55 | 34.21 | True | True | 0.07 |
| Topo_250329.dxf | 2026-03-30 07:00:00 | 1,352.00 | 1,309.54 | 35.46 | False | False | 0.00 |

## Period reconciliation
| period | survey | end | gap_detected | n_loads | fms_tonnes | fms_volume | carried_in_volume | solid_volume | fill_volume | cut_volume | unobserved_fill_new_cells | placed_volume | unattributed_volume | retained_volume | apparent_density_t_m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Topo_260315.dxf | 2026-03-16 07:00:00 | False | 14 | 2,432.00 | 1,783.78 | 0.00 | 2,867.01 | 2,853.02 | 0.00 | 0.00 | 1,783.78 | 1,069.25 | 0.00 | 0.85 |
| 1 | Topo_260316.dxf | 2026-03-17 07:00:00 | False | 25 | 4,142.00 | 2,841.54 | 0.00 | 2,305.84 | 2,300.10 | 0.00 | 0.00 | 2,300.10 | 0.00 | 541.45 | 1.80 |
| 2 | Topo_260318.dxf | 2026-03-19 07:00:00 | True | 42 | 6,802.00 | 4,691.30 | 541.45 | 4,842.78 | 4,792.22 | 317.37 | 0.00 | 4,796.34 | 0.00 | 753.78 | 1.40 |
| 3 | Topo_260319.dxf | 2026-03-20 07:00:00 | False | 71 | 11,704.00 | 8,087.39 | 750.58 | 8,708.00 | 8,696.64 | 0.19 | 0.00 | 8,697.12 | 0.00 | 141.04 | 1.34 |
| 4 | Topo_260320.dxf | 2026-03-21 07:00:00 | False | 17 | 3,040.00 | 2,100.51 | 141.04 | 2,150.86 | 2,142.34 | 0.00 | 0.00 | 2,142.69 | 0.00 | 98.86 | 1.41 |
| 5 | Topo_260321.dxf | 2026-03-22 07:00:00 | False | 12 | 2,166.00 | 1,500.13 | 98.86 | 1,425.73 | 1,419.82 | 4.00 | 0.00 | 1,420.12 | 0.00 | 182.87 | 1.52 |
| 6 | Topo_260322.dxf | 2026-03-23 07:00:00 | False | 24 | 3,838.00 | 2,853.17 | 182.87 | 2,887.79 | 2,907.76 | 57.41 | 0.00 | 2,908.25 | 0.00 | 185.21 | 1.33 |
| 7 | Topo_260327.dxf | 2026-03-28 07:00:00 | True | 21 | 3,116.00 | 2,380.15 | 185.21 | 3,679.46 | 3,769.50 | 12.65 | 0.00 | 2,578.01 | 1,191.49 | 0.00 | 0.85 |
| 8 | Topo_250328.dxf | 2026-03-29 07:00:00 | False | 41 | 6,004.00 | 4,564.09 | 0.00 | 4,918.55 | 4,928.26 | 173.37 | 0.00 | 4,737.46 | 190.79 | 0.00 | 1.22 |
| 9 | Topo_250329.dxf | 2026-03-30 07:00:00 | False | 7 | 1,178.00 | 877.40 | 0.00 | 1,309.54 | 1,295.14 | 0.00 | 0.00 | 877.40 | 417.74 | 0.00 | 0.90 |

## Volume factor calibration (A-06)
| interval | survey | end | fill_m3 | inferred_toe_fill_m3 | cut_m3 | net_m3 | fms_t | vdens_m3 | longest_fms_silence_h | ratio | consistent | role | err_fv_first_half |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Topo_260315.dxf | 2026-03-16 07:00:00 | 2,853.02 | 0.00 | 0.00 | 2,853.02 | 2,432.00 | 1,212.02 | 11.02 | 2.35 | False | calibration | 0.38 |
| 1 | Topo_260316.dxf | 2026-03-17 07:00:00 | 2,300.10 | 0.00 | 0.00 | 2,300.10 | 4,142.00 | 1,930.74 | 18.55 | 1.19 | True | calibration | -0.23 |
| 2 | Topo_260318.dxf | 2026-03-19 07:00:00 | 4,792.22 | 0.00 | 317.37 | 4,474.85 | 6,802.00 | 3,187.59 | 37.78 | 1.40 | True | calibration | -0.04 |
| 3 | Topo_260319.dxf | 2026-03-20 07:00:00 | 8,699.13 | 0.00 | 0.19 | 8,698.94 | 11,704.00 | 5,495.13 | 5.77 | 1.58 | True | calibration | 0.08 |
| 4 | Topo_260320.dxf | 2026-03-21 07:00:00 | 2,142.56 | 0.00 | 0.00 | 2,142.56 | 3,040.00 | 1,427.23 | 11.48 | 1.50 | True | calibration | 0.03 |
| 5 | Topo_260321.dxf | 2026-03-22 07:00:00 | 1,420.23 | 0.00 | 4.00 | 1,416.23 | 2,166.00 | 1,019.29 | 13.23 | 1.39 | True | held-out | -0.05 |
| 6 | Topo_260322.dxf | 2026-03-23 07:00:00 | 2,907.91 | 0.00 | 57.39 | 2,850.51 | 3,838.00 | 1,938.64 | 12.53 | 1.47 | True | held-out | 0.00 |
| 7 | Topo_260327.dxf | 2026-03-28 07:00:00 | 3,769.82 | 0.00 | 12.64 | 3,757.18 | 3,116.00 | 1,617.24 | 64.00 | 2.32 | False | held-out | 0.37 |
| 8 | Topo_250328.dxf | 2026-03-29 07:00:00 | 4,928.27 | 0.00 | 173.32 | 4,754.95 | 6,004.00 | 3,101.15 | 10.58 | 1.53 | True | held-out | 0.05 |
| 9 | Topo_250329.dxf | 2026-03-30 07:00:00 | 1,295.13 | 0.00 | 0.00 | 1,295.13 | 1,178.00 | 596.16 | 22.72 | 2.17 | False | held-out | 0.33 |

## Volume-gap scenarios
| scenario | status | volume_factor | payload_factor | in_pile_density_t_m3 | largest_load_t | fms_tonnes | unattributed_tonnes | record_period_tonnes | record_period_cu_t | record_period_au_kg | unattributed_volume_m3 | pre_record_tonnes | total_tonnes | total_cu_t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 | base case | 1.47 | 1.00 | 1.40 | 304.00 | 44,650.00 | 3,901.28 | 48,551.28 | 4,159.03 | 391.52 | 2,869.27 | 89,794.55 | 138,345.83 | 11,721.53 |
| S1 | inside the Monte Carlo range (upper end) | 1.47 | 1.19 | 1.67 | 361.76 | 53,133.50 | 4,642.52 | 57,776.02 | 4,949.25 | 465.91 | 2,869.27 | 106,855.52 | 164,631.54 | 13,948.62 |
| S2 | sensitivity (not in Monte Carlo) | 1.47 | 1.00 | 1.40 | 304.00 | 44,650.00 | 14,031.52 | 58,681.52 | 4,977.44 | 472.29 | 10,106.82 | 78,613.84 | 137,295.36 | 11,598.29 |
| X1 | EXCLUDED | 1.47 | 1.47 | 2.07 | 447.41 | 65,713.10 | 5,741.66 | 71,454.76 | 6,121.01 | 576.21 | 2,869.27 | 132,154.06 | 203,608.82 | 17,251.02 |
| X2 | NOT INCLUDED in the ranges (cannot be excluded) | 1.00 | 1.00 | 2.07 | 304.00 | 44,650.00 | 26,687.71 | 71,337.71 | 6,090.84 | 574.19 | 13,018.27 | 132,154.06 | 203,491.76 | 17,220.85 |

## Volume reconciliation
| item | value |
|---|---|
| survey change-solid volume (m3) | 35,095.56 |
| observed fill used by model (m3) | 35,104.79 |
|   of which unobserved fill on first-surveyed cells (m3) | 0.00 |
| cut / re-handled volume (m3) | 564.99 |
| sub-threshold change not modelled (m3) | 136.74 |
| FMS volume (tonnes / density) (m3) | 31,849.11 |
| FMS volume placed into observed fill (m3) | 32,241.25 |
| unattributed fill volume (m3) | 2,869.27 |
| FMS volume never reconciled (provisional) (m3) | 169.64 |
| max Sinkhorn column residual (relative) | 0.00 |

## Mass / metal balance
| quantity | unit | FMS_input | column_model | block_model_grid | block_table | abs_diff_block_vs_input | rel_diff_ppm |
|---|---|---|---|---|---|---|---|
| FMS tonnes | t | 44,650.00 | 44,650.00 | 44,650.00 | 44,650.00 | 0.00 | 0.00 |
| FMS Cu | t Cu | 3,760.42 | 3,760.42 | 3,760.42 |  | -0.00 | -0.00 |
| FMS Au | kg Au | 357.12 | 357.12 | 357.12 |  | -0.00 | -0.00 |
| FMS Ag | kg Ag | 8,824.14 | 8,824.14 | 8,824.14 |  | -0.00 | -0.00 |

## Inventory by information class
| class | tonnes | cu_t | au_kg | ag_kg | cu_pct | au_gpt | share_of_tonnes |
|---|---|---|---|---|---|---|---|
| FMS-tracked (reconciled + provisional) | 44,650.00 | 3,760.42 | 357.12 | 8,824.14 | 8.42 | 8.00 | 0.32 |
| Unattributed (imputed grade) | 3,901.28 | 398.61 | 34.39 | 773.84 | 10.22 | 8.82 | 0.03 |
| Legacy (assumed grade) | 89,794.55 | 7,562.50 | 718.20 | 17,746.01 | 8.42 | 8.00 | 0.65 |
| TOTAL | 138,345.83 | 11,721.53 | 1,109.72 | 27,343.99 | 8.47 | 8.02 | 1.00 |

## Block model summary: by_dominant_info_class
| info_class | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| FMS-reconciled | 955.00 | 34,410.36 | 48,188.74 | 8.50 | 8.02 | 197.47 | 4,097.50 | 386.45 | 12.42 | 9,515.66 |
| Legacy-assumed | 1,724.00 | 64,045.16 | 89,900.24 | 8.45 | 8.02 | 197.70 | 7,600.48 | 720.82 | 23.17 | 17,773.30 |
| Provisional | 7.00 | 91.03 | 123.49 | 8.21 | 9.73 | 223.55 | 10.14 | 1.20 | 0.04 | 27.61 |
| Unattributed-imputed | 13.00 | 100.23 | 133.36 | 10.06 | 9.35 | 205.68 | 13.41 | 1.25 | 0.04 | 27.43 |

## Block model summary: by_confidence
| confidence | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| High | 695.00 | 25,653.17 | 36,117.04 | 8.26 | 7.90 | 197.22 | 2,983.20 | 285.15 | 9.17 | 7,122.85 |
| Low | 122.00 | 4,732.57 | 6,574.20 | 8.97 | 8.30 | 198.53 | 589.64 | 54.57 | 1.75 | 1,305.17 |
| Medium | 242.00 | 7,770.20 | 10,703.14 | 9.22 | 8.40 | 198.32 | 987.30 | 89.89 | 2.89 | 2,122.70 |
| Uninformed | 1,640.00 | 60,490.86 | 84,951.45 | 8.43 | 8.01 | 197.68 | 7,161.40 | 680.10 | 21.87 | 16,793.26 |

## Block model summary: by_bench_4m
| bench | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| 4490 | 18.00 | 37.09 | 49.82 | 8.72 | 9.96 | 223.68 | 4.34 | 0.50 | 0.02 | 11.14 |
| 4486 | 460.00 | 10,292.25 | 14,305.12 | 8.75 | 8.15 | 198.26 | 1,251.44 | 116.62 | 3.75 | 2,836.20 |
| 4482 | 671.00 | 28,952.55 | 40,591.31 | 8.45 | 8.02 | 197.72 | 3,429.01 | 325.44 | 10.46 | 8,025.82 |
| 4478 | 757.00 | 33,397.51 | 46,927.69 | 8.43 | 8.00 | 197.43 | 3,957.13 | 375.21 | 12.06 | 9,265.07 |
| 4474 | 793.00 | 25,967.38 | 36,471.89 | 8.44 | 8.00 | 197.57 | 3,079.61 | 291.95 | 9.39 | 7,205.75 |

## Block model summary: by_material_source
| material class (exact tonnage split) | tonnes |
|---|---|
| FMS (survey-reconciled) | 44,422.00 |
| FMS (provisional, unreconciled) | 228.00 |
| Unattributed (imputed grade) | 3,901.28 |
| Legacy (assumed grade) | 89,794.55 |

## Block model summary: grade_tonnage
| index | cutoff_cu_pct | tonnes_all | cu_pct_all | au_gpt_all | tonnes_tracked_blocks | cu_pct_tracked_blocks |
|---|---|---|---|---|---|---|
| 0 | 0 | 138,345.83 | 8.47 | 8.02 | 46,820.18 | 8.48 |
| 1 | 4 | 138,345.83 | 8.47 | 8.02 | 46,820.18 | 8.48 |
| 2 | 6 | 132,605.58 | 8.58 | 8.05 | 41,079.93 | 8.84 |
| 3 | 8 | 118,302.28 | 8.79 | 8.13 | 27,033.26 | 9.86 |
| 4 | 9 | 24,460.06 | 10.13 | 8.57 | 21,250.23 | 10.22 |
| 5 | 10 | 12,145.37 | 10.76 | 8.70 | 11,687.33 | 10.78 |
| 6 | 11 | 4,227.88 | 11.34 | 8.76 | 4,227.88 | 11.34 |
| 7 | 12 | 53.61 | 12.02 | 8.63 | 53.61 | 12.02 |

## Geometry check
| cells | mean_m | rmse_m | p01_m | p99_m | max_abs_m | volume_diff_m3 | frac_within_tau |
|---|---|---|---|---|---|---|---|
| 6813 | -0.01 | 0.03 | -0.13 | 0.01 | 0.20 | -54.56 | 1.00 |

## Forward model temporal validation (means)
| set | mode | w1_m | capture | centroid_err_m |
|---|---|---|---|---|
| calibration | no-push baseline | 18.96 | 0.32 | 17.55 |
| calibration | push (calibrated) | 16.37 | 0.36 | 15.31 |
| calibration | push (default) | 17.07 | 0.36 | 16.01 |
| calibration | uniform baseline | 23.23 | 0.17 | 12.75 |
| test (unseen) | no-push baseline | 14.34 | 0.46 | 11.15 |
| test (unseen) | push (calibrated) | 14.08 | 0.53 | 11.87 |
| test (unseen) | push (default) | 14.02 | 0.58 | 11.82 |
| test (unseen) | uniform baseline | 30.56 | 0.20 | 28.00 |

## Synthetic twin experiment
| method | blocks | cu_rmse | cu_mae | cu_corr | au_rmse | au_corr | tonnes_corr | recovered_fms_tonnes_frac |
|---|---|---|---|---|---|---|---|---|
| CPST eps=2 m | 684 | 0.81 | 0.54 | 0.90 | 0.31 | 0.95 | 1.00 | 0.81 |
| CPST eps=6 m (base) | 684 | 0.68 | 0.48 | 0.93 | 0.28 | 0.96 | 1.00 | 0.81 |
| CPST eps=15 m | 684 | 0.65 | 0.47 | 0.94 | 0.28 | 0.96 | 1.00 | 0.81 |
| CPST eps=6, no uphill penalty | 684 | 0.66 | 0.47 | 0.94 | 0.28 | 0.96 | 1.00 | 0.80 |
| Baseline: period-average (eps=1e4) | 684 | 1.19 | 0.91 | 0.82 | 0.66 | 0.82 | 0.99 | 0.74 |
| Reference: global mean grade | 684 | 1.87 | 1.58 |  |  |  |  |  |

## Monte Carlo global summary
| index | P10 | P50 | P90 | mean | cv |
|---|---|---|---|---|---|
| total_tonnes | 134,036.38 | 147,624.14 | 158,568.00 | 146,977.89 | 0.07 |
| cu_t | 11,284.21 | 12,413.00 | 13,790.62 | 12,433.60 | 0.08 |
| au_kg | 1,076.56 | 1,175.82 | 1,308.66 | 1,178.84 | 0.08 |
| fms_tonnes | 45,203.10 | 47,124.91 | 49,666.79 | 47,298.76 | 0.04 |
| cu_pct | 8.00 | 8.54 | 8.83 | 8.46 | 0.04 |
| au_gpt | 7.54 | 8.03 | 8.53 | 8.02 | 0.05 |
| class_t_f | 45,203.10 | 47,124.91 | 49,666.79 | 47,298.76 | 0.04 |
| class_cu_f | 3,721.70 | 3,971.85 | 4,266.85 | 3,983.00 | 0.06 |
| class_au_f | 352.18 | 377.43 | 409.61 | 378.59 | 0.07 |
| class_t_u | 1,660.51 | 4,660.75 | 8,890.87 | 5,042.16 | 0.53 |
| class_cu_u | 167.01 | 447.67 | 781.84 | 474.75 | 0.50 |
| class_au_u | 14.92 | 40.14 | 71.67 | 42.81 | 0.52 |
| class_t_l | 86,603.64 | 94,912.28 | 103,077.82 | 94,636.97 | 0.07 |
| class_cu_l | 7,193.36 | 7,930.49 | 8,886.09 | 7,975.84 | 0.08 |
| class_au_l | 684.68 | 759.63 | 843.11 | 757.44 | 0.09 |
| record_period_tonnes | 48,083.63 | 52,496.89 | 56,006.40 | 52,340.92 | 0.06 |
| record_period_cu_t | 4,084.61 | 4,427.36 | 4,951.81 | 4,457.75 | 0.08 |
| record_period_au_kg | 381.19 | 416.75 | 464.04 | 421.40 | 0.08 |
| class_fms_cu_pct | 7.98 | 8.50 | 8.79 | 8.42 | 0.04 |
| class_fms_au_gpt | 7.51 | 8.00 | 8.51 | 8.00 | 0.05 |
