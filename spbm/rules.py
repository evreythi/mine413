"""QA rule catalogue (record, survey-file and dataset level).

Each rule has an ID, a level, a severity and a treatment. Severity:
  error   - the record cannot be modelled as recorded: excluded (kept in the
            register) or its field is treated as unknown;
  warning - modelled, with the treatment stated (e.g. location unknown);
  info    - recorded for traceability, no change to the model.

The context-free record rules live here so that the QA report and the
engine (movement.prepare_loads) use exactly the same definitions. Rules that
need the surveys (location vs footprints, Z envelope, timing) are evaluated
in spbm.qaqc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# id: (level, severity, description, treatment)
RULES = {
    # ---------------------------------------------------------------- FMS records
    "MISSING_PAYLOAD": ("record", "error", "Truck payload missing", "Excluded from modelling, kept in register"),
    "MISSING_TIME": ("record", "error", "Dump timestamp missing or unparseable", "Excluded from modelling, kept in register"),
    "GRADE_MISSING": ("record", "error", "Cu, Au or Ag missing", "Excluded from modelling, kept in register"),
    "DENS_MISSING": ("record", "error", "Density missing", "Excluded from modelling, kept in register"),
    "LOC_MISSING": ("record", "error", "Dump X or Y missing", "Excluded from modelling, kept in register"),
    "DUP_IDENTICAL": ("record", "warning", "Cycle ID repeated with identical content", "First copy modelled, repeats excluded"),
    "DUP_CONFLICT": ("record", "error", "Cycle ID repeated with different content",
                     "First copy modelled, others excluded; resolve with an fms_exclude intervention"),
    "PAYLOAD_NONPOSITIVE": ("record", "error", "Payload <= 0 t", "Excluded from modelling"),
    "PAYLOAD_PARTIAL": ("record", "info", "Payload <= 50% of the median (part load)", "Modelled; payload error in Monte Carlo"),
    "PAYLOAD_HIGH": ("record", "info", "Payload > 150% of the median", "Modelled; bounds the payload factor (A-06)"),
    "PAYLOAD_OFF_QUANTUM": ("record", "warning", "Payload not a multiple of the 38 t pass quantum (A-10)", "Modelled; checked manually"),
    "GRADE_INVALID": ("record", "error", "Cu <= 0 or > 100 %, or Au/Ag < 0", "Excluded from modelling"),
    "GRADE_OUTLIER": ("record", "info", "Grade outside Q1 - 3 IQR .. Q3 + 3 IQR", "Modelled (source-block grade); flagged"),
    "DENS_INVALID": ("record", "error", "Density outside 1.5-3.0 t/m3", "Excluded from modelling"),
    "LOC_OUTSIDE_DOMAIN": ("record", "error", "Dump X/Y more than 100 m outside every survey solid",
                           "Location treated as unknown (as LOC_DEFAULT)"),
    "LOC_DEFAULT": ("record", "warning", "X/Y/Z shared by >= 3 records (default / stuck FMS position, A-32)",
                    "Location treated as unknown: uniform push cost over the interval's fill"),
    "LOC_OUTSIDE_SURVEYS": ("record", "info", "Dump X/Y outside the union of all survey change solids",
                            "Modelled: pushed from the dump point (crest dumping)"),
    "LOC_Z_INCONSISTENT": ("record", "info", "Dump Z outside the interval's [start surface, end surface] envelope +/- 5 m",
                           "Modelled; dump Z is not used by the engine (X/Y only)"),
    "TIME_BEFORE_FIRST_INTERVAL": ("record", "error", "Dump before the start of the first survey interval",
                                   "Excluded (belongs to the pre-record pile)"),
    "TIME_AFTER_LAST_SURVEY": ("record", "warning", "Dump after the last survey cut-off",
                               "Placed provisionally by the forward model; reconciled when the next survey arrives"),
    "TIME_DUPLICATE": ("record", "info", "Timestamp identical to another record", "Modelled; both kept"),
    "ID_OUT_OF_ORDER": ("record", "info", "Cycle ID not in chronological order", "None - the timestamp governs ordering"),
    "IN_SURVEY_GAP_INTERVAL": ("record", "info", "Dump inside a survey interval longer than 36 h",
                               "Modelled; the interval's spatial resolution in time is coarser"),
    # ---------------------------------------------------------------- survey files
    "DXF_UNITS_HEADER": ("survey", "warning", "$INSUNITS = 1 (inches) and $MEASUREMENT = 0 (imperial) in the DXF header",
                         "Header ignored: coordinates are metres (they match the FMS mine grid; in inches the pile would be 0.1 km above sea level)"),
    "DXF_SAVED_BEFORE_SURVEY": ("survey", "info", "$TDUPDATE (last saved) is earlier than the nominal survey date",
                                "Header dates not used for timing; files were exported in one batch"),
    "SURVEY_NAME_YEAR": ("survey", "error", "File-name year contradicts the survey sequence and the FMS record",
                         "Re-dated by manual intervention (MI-001, MI-002)"),
    "LAYER_DATE_MISMATCH": ("survey", "info", "Layer-name date token differs from the file-name date (year 25 vs 26)",
                            "File name (with interventions) governs; month/day agree"),
    "ZERO_PLAN_AREA_FACES": ("survey", "info", "Faces with zero plan area (vertical walls of the closed solid)",
                             "Ignored by the rasteriser (they carry no top/bottom elevation)"),
    "DEGENERATE_FACES": ("survey", "info", "Faces with zero 3-D area", "Ignored"),
    "DUPLICATE_FACES": ("survey", "info", "Faces repeated in the same file", "No effect (per-cell max/min)"),
    "SOLID_NOT_CLOSED": ("survey", "warning", "Under 98% of solid cells have exactly one top and one bottom face",
                         "Single-surface cells take thickness 0; checked against previous surface"),
    "NORMALS_INVERTED": ("survey", "info", "Face orientation gives a negative signed volume", "No effect (orientation-free rasteriser)"),
    "SOLID_BASE_MISMATCH": ("survey", "warning", "Over 20% of cells where the solid's bottom differs from the previous survey top by more than the LOD",
                            "Solid bottom trusted (A-13b off); A-13b sensitivity"),
    # ---------------------------------------------------------------- dataset
    "SURVEY_GAP": ("dataset", "warning", "Survey interval longer than 36 h", "Coarser time resolution; listed in reconciliation"),
    "FMS_PARTIAL_FIRST_INTERVAL": ("dataset", "warning", "FMS record starts after the start of the first survey interval",
                                   "Interval 0 excluded from timing and volume calibration; unexplained fill is unattributed"),
    "FMS_SILENCE": ("dataset", "warning", "No FMS record for more than 24 h inside an interval", "Interval checked in the volume calibration"),
    "VOLUME_RATIO_OUTLIER": ("dataset", "warning", "Interval's surveyed fill / FMS volume outside median +/- 3 robust SD",
                             "Excluded from the f_v calibration; the unexplained fill is unattributed volume"),
    "SURVEY_CHANGE_NO_FMS": ("dataset", "warning", "A day with a survey change solid but no FMS record", "Fill is unattributed"),
    "PAYLOAD_QUANTISED": ("dataset", "info", "Every payload is a multiple of 38 t (pass count x nominal bucket)",
                          "Payload treated as an estimate (A-10): per-load CV and systematic payload factor"),
    "GRADE_UNITS_UNCONFIRMED": ("dataset", "warning", "Mean Cu 8.4 % and Au 8 g/t are about 10x typical Cu-Au feed",
                                "Units used as supplied; flagged in the executive summary (QA-F04)"),
}


def record_rules(f: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Context-free record rules. Returns a boolean frame (one column per rule)."""
    out = pd.DataFrame(index=f.index)
    pay = pd.to_numeric(f["payload_t"], errors="coerce")
    dens = pd.to_numeric(f["density"], errors="coerce")
    out["MISSING_PAYLOAD"] = pay.isna()
    out["MISSING_TIME"] = f["timestamp"].isna()
    out["GRADE_MISSING"] = f[["cu_pct", "au_gpt", "ag_gpt"]].isna().any(axis=1)
    out["DENS_MISSING"] = dens.isna()
    out["LOC_MISSING"] = f[["x", "y"]].isna().any(axis=1)
    dup = f["cycle_id"].duplicated(keep="first")
    content = [c for c in f.columns if c in ("payload_t", "cu_pct", "au_gpt", "ag_gpt", "density", "x", "y", "z", "timestamp_raw")]
    first = f[~dup].set_index("cycle_id")[content]
    conflict = np.zeros(len(f), bool)
    for k in np.nonzero(dup.values)[0]:
        a = f.iloc[k][content]
        b = first.loc[f.iloc[k]["cycle_id"]]
        conflict[k] = not all((pd.isna(x) and pd.isna(y)) or x == y for x, y in zip(a.values, b.values))
    out["DUP_IDENTICAL"] = dup.values & ~conflict
    out["DUP_CONFLICT"] = conflict
    med = pay.median()
    out["PAYLOAD_NONPOSITIVE"] = pay <= 0
    out["PAYLOAD_PARTIAL"] = (pay > 0) & (pay <= 0.5 * med)
    out["PAYLOAD_HIGH"] = pay > 1.5 * med
    qn = float(cfg.get("fms", {}).get("pass_quantum_t", 38.0))
    out["PAYLOAD_OFF_QUANTUM"] = pay.notna() & (np.abs(pay / qn - np.round(pay / qn)) > 1e-6)
    cu, au, ag = (pd.to_numeric(f[c], errors="coerce") for c in ("cu_pct", "au_gpt", "ag_gpt"))
    out["GRADE_INVALID"] = (cu <= 0) | (cu > 100) | (au < 0) | (ag < 0)
    go = np.zeros(len(f), bool)
    for c in (cu, au, ag):
        q1, q3 = c.quantile([0.25, 0.75])
        iqr = q3 - q1
        go |= ((c < q1 - 3 * iqr) | (c > q3 + 3 * iqr)).values
    out["GRADE_OUTLIER"] = go & ~out["GRADE_INVALID"].values
    out["DENS_INVALID"] = (dens < 1.5) | (dens > 3.0)
    rep = f.groupby(["x", "y", "z"], dropna=False)["cycle_id"].transform("size")
    out["LOC_DEFAULT"] = (rep >= cfg.get("fms", {}).get("repeated_location_min", 3)) & f[["x", "y"]].notna().all(axis=1)
    t = f["timestamp"]
    out["TIME_DUPLICATE"] = t.notna() & t.duplicated(keep=False)
    order = f.sort_values("timestamp")
    ooo = order["cycle_id"].values[1:] < np.maximum.accumulate(order["cycle_id"].values)[:-1]
    out["ID_OUT_OF_ORDER"] = False
    out.loc[order.index[1:][ooo], "ID_OUT_OF_ORDER"] = True
    return out.fillna(False).astype(bool)


EXCLUDING = [k for k, v in RULES.items() if v[0] == "record" and v[1] == "error"
             and k not in ("LOC_OUTSIDE_DOMAIN", "TIME_BEFORE_FIRST_INTERVAL")]


def model_exclusions(f: pd.DataFrame, cfg: dict) -> pd.Series:
    """Records the engine must not model (error rules, plus repeated copies)."""
    r = record_rules(f, cfg)
    return r[EXCLUDING + ["DUP_IDENTICAL"]].any(axis=1)
