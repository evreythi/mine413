# Key result tables (auto-generated - do not edit)

## FMS flags
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
| F11_z_residual | abs(Dump Z - surface) > 3 m where surface known | 29 | Retained; Z not used by algorithm (XY only) |
| F12_after_last_survey | Dump after the last survey | 1 | Placed provisionally (unreconciled) - updated when next survey arrives |
| F13_survey_gap_period | Dump inside a period with a missing survey | 18 | Retained; period flagged in reconciliation |
| F14_repeated_location | Identical X/Y/Z shared by >= 3 records (default / stuck FMS position) | 14 | Retained; X/Y imputed as tonnage-weighted centroid of the period's other dumps, GPS error x5 in Monte Carlo |

## Survey QA
| file | assigned_datetime | footprint_m2 | volume_m3 | slope_p50 | reaches_floor | normals_inverted | frac_bottom_mismatch_gt_0.14 |
|---|---|---|---|---|---|---|---|
| Topo_260315.dxf | 2026-03-15 23:59:00 | 1,996.00 | 2,867.01 | 35.96 | True | False |  |
| Topo_260316.dxf | 2026-03-16 23:59:00 | 1,330.00 | 2,305.84 | 36.18 | False | False | 0.00 |
| Topo_260318.dxf | 2026-03-18 23:59:00 | 2,290.00 | 4,842.78 | 36.16 | True | False | 0.23 |
| Topo_260319.dxf | 2026-03-19 23:59:00 | 2,568.00 | 8,708.00 | 34.66 | True | False | 0.00 |
| Topo_260320.dxf | 2026-03-20 23:59:00 | 1,607.00 | 2,150.86 | 36.82 | True | False | 0.00 |
| Topo_260321.dxf | 2026-03-21 23:59:00 | 1,327.00 | 1,425.73 | 36.16 | False | False | 0.01 |
| Topo_260322.dxf | 2026-03-22 23:59:00 | 1,642.00 | 2,887.79 | 35.90 | False | False | 0.09 |
| Topo_260327.dxf | 2026-03-27 23:59:00 | 2,147.00 | 3,679.46 | 35.34 | True | False | 0.14 |
| Topo_250328.dxf | 2026-03-28 23:59:00 | 3,173.00 | 4,918.55 | 34.21 | True | True | 0.07 |
| Topo_250329.dxf | 2026-03-29 23:59:00 | 1,352.00 | 1,309.54 | 35.46 | False | False | 0.00 |

## Period reconciliation
| period | survey | end | gap_detected | n_loads | fms_tonnes | fms_volume | carried_in_volume | solid_volume | fill_volume | cut_volume | unobserved_fill_new_cells | placed_volume | unattributed_volume | retained_volume | apparent_density_t_m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Topo_260315.dxf | 2026-03-15 23:59:00 | False | 11 | 1,976.00 | 997.94 | 0.00 | 2,867.01 | 2,853.02 | 0.00 | 0.00 | 997.94 | 1,855.09 | 0.00 | 0.69 |
| 1 | Topo_260316.dxf | 2026-03-16 23:59:00 | False | 28 | 4,598.00 | 2,144.82 | 0.00 | 2,305.84 | 2,932.06 | 0.00 | 628.46 | 2,144.82 | 787.24 | 0.00 | 1.99 |
| 2 | Topo_260318.dxf | 2026-03-18 23:59:00 | True | 17 | 2,698.00 | 1,264.57 | 0.00 | 4,842.78 | 5,682.88 | 318.85 | 887.29 | 1,583.42 | 4,099.46 | 0.00 | 0.56 |
| 3 | Topo_260319.dxf | 2026-03-19 23:59:00 | False | 75 | 12,616.00 | 5,919.50 | 0.00 | 8,708.00 | 11,286.25 | 0.19 | 2,587.04 | 5,919.69 | 5,366.56 | 0.00 | 1.45 |
| 4 | Topo_260320.dxf | 2026-03-20 23:59:00 | False | 36 | 6,004.00 | 2,818.84 | 0.00 | 2,150.86 | 2,474.02 | 0.34 | 330.26 | 2,474.44 | 0.00 | 344.74 | 2.79 |
| 5 | Topo_260321.dxf | 2026-03-21 23:59:00 | False | 11 | 1,710.00 | 804.45 | 344.74 | 1,425.73 | 1,564.40 | 4.00 | 144.72 | 1,153.20 | 411.20 | 0.00 | 1.20 |
| 6 | Topo_260322.dxf | 2026-03-22 23:59:00 | False | 27 | 4,522.00 | 2,260.52 | 0.00 | 2,887.79 | 3,279.94 | 57.43 | 371.71 | 2,317.95 | 961.99 | 0.00 | 1.57 |
| 7 | Topo_260327.dxf | 2026-03-27 23:59:00 | True | 1 | 152.00 | 72.07 | 0.00 | 3,679.46 | 5,085.98 | 12.82 | 1,314.78 | 84.89 | 5,001.09 | 0.00 | 0.04 |
| 8 | Topo_250328.dxf | 2026-03-28 23:59:00 | False | 50 | 7,182.00 | 3,744.44 | 0.00 | 4,918.55 | 5,500.99 | 173.32 | 574.76 | 3,917.77 | 1,583.22 | 0.00 | 1.46 |
| 9 | Topo_250329.dxf | 2026-03-29 23:59:00 | False | 18 | 2,964.00 | 1,498.04 | 0.00 | 1,309.54 | 1,693.23 | 0.00 | 392.54 | 1,498.04 | 195.19 | 0.00 | 2.26 |

## Volume reconciliation
| item | value |
|---|---|
| survey change-solid volume (m3) | 35,095.56 |
| observed fill used by model (m3) | 42,352.77 |
|   of which unobserved fill on first-surveyed cells (m3) | 7,231.56 |
| cut / re-handled volume (m3) | 566.95 |
| sub-threshold change not modelled (m3) | 96.21 |
| FMS volume (tonnes / density) (m3) | 21,640.47 |
| FMS volume placed into observed fill (m3) | 22,092.15 |
| unattributed fill volume (m3) | 20,261.03 |
| FMS volume never reconciled (provisional) (m3) | 115.27 |
| max Sinkhorn column residual (relative) | 0.00 |

## Mass / metal balance
| quantity | unit | FMS_input | column_model | block_model_grid | block_table | abs_diff_block_vs_input | rel_diff_ppm |
|---|---|---|---|---|---|---|---|
| FMS tonnes | t | 44,650.00 | 44,650.00 | 44,650.00 | 44,650.00 | -0.00 | -0.00 |
| FMS Cu | t Cu | 3,760.42 | 3,760.42 | 3,760.42 |  | -0.00 | -0.00 |
| FMS Au | kg Au | 357.12 | 357.12 | 357.12 |  | -0.00 | -0.00 |
| FMS Ag | kg Ag | 8,824.14 | 8,824.14 | 8,824.14 |  | -0.00 | -0.00 |

## Inventory by information class
| class | tonnes | cu_t | au_kg | ag_kg | cu_pct | au_gpt | share_of_tonnes |
|---|---|---|---|---|---|---|---|
| FMS-tracked (reconciled + provisional) | 44,650.00 | 3,760.42 | 357.12 | 8,824.14 | 8.42 | 8.00 | 0.22 |
| Unattributed (imputed grade) | 41,758.25 | 3,597.56 | 334.14 | 8,196.44 | 8.62 | 8.00 | 0.21 |
| Legacy (assumed grade) | 115,699.16 | 9,744.18 | 925.40 | 22,865.52 | 8.42 | 8.00 | 0.57 |
| TOTAL | 202,107.42 | 17,102.16 | 1,616.66 | 39,886.09 | 8.46 | 8.00 | 1.00 |

## Block model summary: by_dominant_info_class
| info_class | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| FMS-reconciled | 691.00 | 22,719.26 | 46,937.09 | 8.37 | 7.96 | 197.42 | 3,929.50 | 373.56 | 12.01 | 9,266.16 |
| Legacy-assumed | 1,571.00 | 57,436.81 | 118,697.35 | 8.45 | 8.01 | 197.61 | 10,033.52 | 950.75 | 30.57 | 23,455.86 |
| Provisional | 5.00 | 69.25 | 138.58 | 8.15 | 9.65 | 222.87 | 11.29 | 1.34 | 0.04 | 30.89 |
| Unattributed-imputed | 428.00 | 17,644.67 | 36,334.40 | 8.61 | 8.01 | 196.32 | 3,127.85 | 291.01 | 9.36 | 7,133.19 |

## Block model summary: by_confidence
| confidence | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| High | 172.00 | 4,378.55 | 8,971.43 | 8.62 | 8.18 | 200.59 | 773.23 | 73.41 | 2.36 | 1,799.56 |
| Low | 412.00 | 16,208.59 | 33,533.58 | 8.40 | 7.95 | 196.57 | 2,818.05 | 266.62 | 8.57 | 6,591.68 |
| Medium | 478.00 | 16,652.65 | 34,468.45 | 8.29 | 7.90 | 196.78 | 2,857.15 | 272.40 | 8.76 | 6,782.80 |
| Uninformed | 1,633.00 | 60,630.21 | 125,133.96 | 8.51 | 8.03 | 197.48 | 10,653.73 | 1,004.23 | 32.29 | 24,712.06 |

## Block model summary: by_bench_4m
| bench | blocks | volume_m3 | tonnes | cu_pct | au_gpt | ag_gpt | cu_t | au_kg | au_koz | ag_kg |
|---|---|---|---|---|---|---|---|---|---|---|
| 4490 | 18.00 | 25.60 | 50.70 | 9.22 | 9.59 | 217.00 | 4.67 | 0.49 | 0.02 | 11.00 |
| 4486 | 459.00 | 10,236.10 | 20,958.34 | 8.76 | 8.10 | 197.48 | 1,836.25 | 169.85 | 5.46 | 4,138.76 |
| 4482 | 671.00 | 28,679.75 | 59,209.11 | 8.46 | 8.00 | 197.29 | 5,011.45 | 473.43 | 15.22 | 11,681.25 |
| 4478 | 755.00 | 33,141.50 | 68,506.06 | 8.46 | 7.99 | 197.25 | 5,794.33 | 547.58 | 17.61 | 13,512.90 |
| 4474 | 792.00 | 25,787.04 | 53,383.21 | 8.35 | 7.97 | 197.48 | 4,455.46 | 425.32 | 13.67 | 10,542.18 |

## Block model summary: by_material_source
| material class (exact tonnage split) | tonnes |
|---|---|
| FMS (survey-reconciled) | 44,422.00 |
| FMS (provisional, unreconciled) | 228.00 |
| Unattributed (imputed grade) | 41,758.25 |
| Legacy (assumed grade) | 115,699.16 |

## Block model summary: grade_tonnage
| index | cutoff_cu_pct | tonnes_all | cu_pct_all | au_gpt_all | tonnes_tracked_blocks | cu_pct_tracked_blocks |
|---|---|---|---|---|---|---|
| 0 | 0 | 202,107.42 | 8.46 | 8.00 | 43,445.83 | 8.36 |
| 1 | 4 | 202,107.42 | 8.46 | 8.00 | 43,445.83 | 8.36 |
| 2 | 6 | 201,662.06 | 8.47 | 8.00 | 43,000.48 | 8.38 |
| 3 | 8 | 159,813.51 | 8.89 | 8.15 | 23,535.58 | 9.85 |
| 4 | 9 | 40,247.60 | 10.17 | 8.59 | 18,965.53 | 10.18 |
| 5 | 10 | 20,900.57 | 10.86 | 8.83 | 8,673.57 | 11.02 |
| 6 | 11 | 8,262.61 | 11.34 | 8.86 | 4,847.61 | 11.45 |
| 7 | 12 | 0.00 |  |  | 0.00 |  |

## Geometry check
| cells | mean_m | rmse_m | p01_m | p99_m | max_abs_m | volume_diff_m3 | frac_within_tau |
|---|---|---|---|---|---|---|---|
| 6813 | -0.01 | 0.03 | -0.13 | 0.00 | 0.14 | -48.62 | 1.00 |

## Forward model temporal validation (means)
| set | mode | w1_m | capture | centroid_err_m |
|---|---|---|---|---|
| calibration | no-push baseline | 21.84 | 0.29 | 20.31 |
| calibration | push (calibrated) | 19.02 | 0.34 | 17.79 |
| calibration | push (default) | 20.03 | 0.37 | 18.77 |
| test (unseen) | no-push baseline | 20.37 | 0.34 | 16.14 |
| test (unseen) | push (calibrated) | 18.61 | 0.39 | 14.37 |
| test (unseen) | push (default) | 18.55 | 0.43 | 14.35 |

## Synthetic twin experiment
| method | blocks | cu_rmse | cu_mae | cu_corr | au_rmse | au_corr | tonnes_corr | recovered_fms_tonnes_frac |
|---|---|---|---|---|---|---|---|---|
| CPST eps=2 m | 589 | 0.84 | 0.55 | 0.89 | 0.40 | 0.91 | 0.83 | 0.80 |
| CPST eps=6 m (base) | 589 | 0.79 | 0.55 | 0.90 | 0.39 | 0.93 | 0.83 | 0.80 |
| CPST eps=15 m | 589 | 0.82 | 0.59 | 0.89 | 0.42 | 0.91 | 0.83 | 0.80 |
| CPST eps=6, no uphill penalty | 589 | 0.80 | 0.56 | 0.90 | 0.39 | 0.93 | 0.83 | 0.80 |
| Baseline: period-average (eps=1e4) | 589 | 1.18 | 0.89 | 0.78 | 0.63 | 0.82 | 0.81 | 0.79 |
| Reference: global mean grade | 589 | 1.83 | 1.51 |  |  |  |  |  |

## Monte Carlo global summary
| index | P10 | P50 | P90 | mean | cv |
|---|---|---|---|---|---|
| total_tonnes | 184,798.60 | 201,201.16 | 218,064.47 | 201,350.61 | 0.06 |
| cu_t | 15,390.04 | 16,983.56 | 19,021.86 | 17,166.94 | 0.08 |
| au_kg | 1,459.52 | 1,607.90 | 1,768.71 | 1,609.65 | 0.08 |
| fms_tonnes | 43,147.57 | 44,784.94 | 46,217.64 | 44,844.74 | 0.03 |
| cu_pct | 8.09 | 8.52 | 8.94 | 8.52 | 0.04 |
| au_gpt | 7.56 | 7.96 | 8.55 | 8.00 | 0.05 |
| class_t_f | 43,147.57 | 44,784.94 | 46,217.64 | 44,844.74 | 0.03 |
| class_cu_f | 3,587.07 | 3,783.03 | 4,041.97 | 3,808.38 | 0.05 |
| class_au_f | 339.61 | 357.57 | 384.72 | 359.10 | 0.05 |
| class_t_u | 34,123.54 | 41,710.66 | 47,830.82 | 41,368.81 | 0.13 |
| class_cu_u | 2,915.97 | 3,604.30 | 4,291.05 | 3,575.35 | 0.15 |
| class_au_u | 266.53 | 331.57 | 386.96 | 328.56 | 0.14 |
| class_t_l | 105,774.89 | 115,492.81 | 124,970.66 | 115,137.06 | 0.06 |
| class_cu_l | 8,714.25 | 9,650.86 | 10,769.59 | 9,783.21 | 0.08 |
| class_au_l | 831.75 | 919.85 | 1,007.82 | 921.99 | 0.08 |
| class_fms_cu_pct | 8.05 | 8.49 | 8.88 | 8.49 | 0.04 |
| class_fms_au_gpt | 7.58 | 7.99 | 8.56 | 8.01 | 0.05 |
