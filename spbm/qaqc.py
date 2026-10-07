"""Task 1 - data investigation and quality assessment.

No record is deleted. Every check adds a flag column; the treatment of each
flag is documented in FLAG_RULES (and in the Data/Assumption Register).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

from . import plots as pl
from .surfaces import fit_base_plane, model_domain, slope_deg

FLAG_RULES = {
    "F01_duplicate_id": ("Duplicate Cycle ID", "Second occurrence excluded from modelling, kept in register"),
    "F02_missing_field": ("Missing mandatory field", "Excluded from modelling (cannot be placed/graded), kept in register"),
    "F03_bad_timestamp": ("Unparseable timestamp", "Excluded from modelling, kept in register"),
    "F04_id_out_of_order": ("Cycle ID not in chronological order", "Information only - timestamp governs ordering"),
    "F05_low_payload": ("Payload < 50% of median (part load)", "Retained; higher payload uncertainty in Monte Carlo"),
    "F06_high_payload": ("Payload > 150% of median", "Retained; checked against truck class; higher uncertainty"),
    "F07_grade_outlier": ("Grade outside Q1-3IQR..Q3+3IQR or <=0", "Retained (source-block grade); flagged"),
    "F08_density_range": ("Density outside 1.5-3.0 t/m3", "Retained; flagged"),
    "F09_far_from_face": ("Dump > 60 m from any surveyed change", "Retained; push distance check"),
    "F10_below_floor": ("Dump Z below fitted stockpile floor - 0.5 m", "Retained; XY used, Z not used by algorithm"),
    "F11_z_residual": ("|Dump Z - surface| > 3 m where surface known", "Retained; Z not used by algorithm (XY only)"),
    "F12_after_last_survey": ("Dump after the last survey", "Placed provisionally (unreconciled) - updated when next survey arrives"),
    "F13_survey_gap_period": ("Dump inside a period with a missing survey", "Retained; period flagged in reconciliation"),
    "F14_repeated_location": ("Identical X/Y/Z shared by >= 3 records (default / stuck FMS position)",
                              "Retained; X/Y imputed as tonnage-weighted centroid of the period's other dumps, GPS error x5 in Monte Carlo"),
}


def run_qaqc(ds, cfg, out: Path, rec=None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    g = ds.grid
    f = ds.fms.copy()
    base = fit_base_plane(ds, cfg)
    B = base["B"]
    times = [s.datetime for s in ds.surveys]

    # ----------------------------------------------------------- FMS checks
    f["F01_duplicate_id"] = f["cycle_id"].duplicated(keep="first")
    req = ["cycle_id", "payload_t", "au_gpt", "ag_gpt", "cu_pct", "density", "x", "y", "z", "timestamp_raw"]
    f["F02_missing_field"] = f[req].isna().any(axis=1)
    f["F03_bad_timestamp"] = f["timestamp"].isna()
    order = f.sort_values("timestamp")
    out_of_order = order["cycle_id"].values[1:] < np.maximum.accumulate(order["cycle_id"].values)[:-1]
    f["F04_id_out_of_order"] = False
    f.loc[order.index[1:][out_of_order], "F04_id_out_of_order"] = True
    med = f["payload_t"].median()
    f["F05_low_payload"] = f["payload_t"] < 0.5 * med
    f["F06_high_payload"] = f["payload_t"] > 1.5 * med
    go = np.zeros(len(f), bool)
    for c in ["cu_pct", "au_gpt", "ag_gpt"]:
        q1, q3 = f[c].quantile([0.25, 0.75])
        iqr = q3 - q1
        go |= (f[c] <= 0) | (f[c] < q1 - 3 * iqr) | (f[c] > q3 + 3 * iqr)
    f["F07_grade_outlier"] = go
    f["F08_density_range"] = (f["density"] < 1.5) | (f["density"] > 3.0)
    obs = np.zeros((g.ny, g.nx), bool)
    for s in ds.surveys:
        obs |= s.mask
    dist = ndimage.distance_transform_edt(~obs) * g.cell
    j, i, inside = g.index(f["x"].values, f["y"].values)
    f["dist_to_survey_m"] = np.where(inside, dist[j, i], np.nan)
    f["F09_far_from_face"] = f["dist_to_survey_m"] > 60
    f["floor_z"] = B[j, i]
    f["F10_below_floor"] = f["z"] < f["floor_z"] - 0.5
    # surface at the time of dump: latest surveyed top before the dump
    zref = np.full(len(f), np.nan)
    comp = np.full((g.ny, g.nx), np.nan)
    tt = f["timestamp"].values.astype("datetime64[ns]")
    prev = np.datetime64("1900-01-01")
    for s in ds.surveys:
        m = (tt > prev) & (tt <= np.datetime64(s.datetime))
        zref[m] = comp[j[m], i[m]]
        comp = np.where(s.mask, s.top, comp)
        prev = np.datetime64(s.datetime)
    m = tt > prev
    zref[m] = comp[j[m], i[m]]
    f["surface_z_at_dump"] = zref
    f["dz_dump_minus_surface"] = f["z"] - zref
    f["F11_z_residual"] = f["dz_dump_minus_surface"].abs() > 3
    f["F12_after_last_survey"] = f["timestamp"] > times[-1]
    gap_periods = []
    for k in range(1, len(times)):
        if times[k] - times[k - 1] > pd.Timedelta("36h"):
            gap_periods.append((times[k - 1], times[k]))
    gp = np.zeros(len(f), bool)
    for a, b in gap_periods:
        gp |= (f["timestamp"] > a) & (f["timestamp"] <= b)
    f["F13_survey_gap_period"] = gp
    rep = f.groupby(["x", "y", "z"])["cycle_id"].transform("size")
    f["F14_repeated_location"] = rep >= 3
    flag_cols = list(FLAG_RULES)
    f["n_flags"] = f[flag_cols].sum(axis=1)
    f["exclude_from_model"] = f["F01_duplicate_id"] | f["F02_missing_field"] | f["F03_bad_timestamp"]
    sig = f[["cu_pct", "au_gpt", "ag_gpt", "density"]].astype(str).agg("|".join, axis=1)
    f["grade_group"] = pd.factorize(sig)[0] + 1
    f.to_csv(out / "fms_records_with_flags.csv", index=False)
    flag_summary = pd.DataFrame([
        {"flag": k, "description": v[0], "records": int(f[k].sum()), "treatment": v[1]} for k, v in FLAG_RULES.items()
    ])
    flag_summary.to_csv(out / "fms_flag_summary.csv", index=False)

    # payload quantisation / grade signatures
    q = (f["payload_t"] % 38 == 0).mean()
    pay = f["payload_t"].value_counts().sort_index().rename_axis("payload_t").reset_index(name="loads")
    pay["passes_of_38t"] = pay["payload_t"] / 38
    pay.to_csv(out / "payload_distribution.csv", index=False)
    groups = f.groupby("grade_group").agg(loads=("cycle_id", "size"), tonnes=("payload_t", "sum"),
                                          cu_pct=("cu_pct", "first"), au_gpt=("au_gpt", "first"),
                                          ag_gpt=("ag_gpt", "first"), density=("density", "first"),
                                          first=("timestamp", "min"), last=("timestamp", "max"))
    groups.to_csv(out / "grade_signatures.csv")

    # daily coverage table (FMS vs surveys)
    days = pd.date_range(min(f["timestamp"].min(), times[0]).normalize(), max(f["timestamp"].max(), times[-1]).normalize())
    daily = pd.DataFrame(index=days)
    daily.index.name = "date"
    dd = f.groupby(f["timestamp"].dt.normalize())
    daily["loads"] = dd.size().reindex(days).fillna(0).astype(int)
    daily["tonnes"] = dd["payload_t"].sum().reindex(days).fillna(0)
    daily["cu_pct_wavg"] = (dd.apply(lambda d: np.average(d["cu_pct"], weights=d["payload_t"]), include_groups=False)).reindex(days)
    daily["au_gpt_wavg"] = (dd.apply(lambda d: np.average(d["au_gpt"], weights=d["payload_t"]), include_groups=False)).reindex(days)
    daily["first_dump"] = dd["timestamp"].min().reindex(days).dt.strftime("%H:%M")
    daily["last_dump"] = dd["timestamp"].max().reindex(days).dt.strftime("%H:%M")
    sv_days = {pd.Timestamp(t).normalize(): s.file for t, s in zip(times, ds.surveys)}
    daily["survey"] = [sv_days.get(d, "") for d in days]
    daily["status"] = np.where((daily["loads"] == 0) & (daily["survey"] != ""), "SURVEY CHANGE, NO FMS",
                       np.where((daily["loads"] == 0), "no FMS, no survey",
                       np.where(daily["survey"] == "", "FMS, no survey", "FMS + survey")))
    daily.to_csv(out / "daily_coverage.csv")

    # ------------------------------------------------------- survey checks
    rows = []
    prev_top = np.full((g.ny, g.nx), np.nan)
    for s, r in zip(ds.surveys, ds.register.itertuples()):
        th = s.thickness[s.mask]
        sl = slope_deg(np.where(s.mask, s.top, np.nan), g.cell)[s.mask]
        sl = sl[np.isfinite(sl)]
        ov = s.mask & np.isfinite(prev_top)
        mis = (s.bot - prev_top)[ov]
        layer = ",".join(s.meta.get("layers", []))
        lay_date = layer[:6]
        rows.append({
            "file": s.file, "layer": layer, "date_from_file_name": r.date_from_name.date() if pd.notna(r.date_from_name) else "",
            "assigned_datetime": s.datetime, "override": r.override_reason[:60] + ("..." if len(r.override_reason) > 60 else ""),
            "layer_date_token": lay_date,
            "layer_vs_name_consistent": lay_date[2:] == s.file.split("_")[-1][2:6] and lay_date[:2] == s.file.split("_")[-1][:2],
            "entity_types": ";".join(f"{k}:{v}" for k, v in s.meta["entity_types"].items()),
            "n_triangles": s.meta["n_triangles"], "degenerate": s.meta["degenerate"],
            "duplicate_triangles": s.meta["duplicate_triangles"],
            "edge_median_m": round(s.meta["edge_median_m"], 2),
            "closed_solid_frac": round(s.meta["closed_solid_frac"], 4),
            "signed_volume_m3": round(s.meta["signed_volume_m3"], 1),
            "normals_inverted": s.meta["signed_volume_m3"] < 0,
            "footprint_m2": float(s.mask.sum() * g.area), "volume_m3": float(th.sum() * g.area),
            "thk_p50": float(np.median(th)), "thk_p95": float(np.percentile(th, 95)), "thk_max": float(th.max()),
            "sliver_frac_lt_0.1m": float((th < 0.1).mean()),
            "z_min": float(np.nanmin(s.bot)), "z_max": float(np.nanmax(s.top)),
            "reaches_floor": bool(np.nanmin(s.bot) < np.nanmean(B[s.mask]) + 0.75),
            "slope_p50": float(np.median(sl)), "slope_p75": float(np.percentile(sl, 75)), "slope_p90": float(np.percentile(sl, 90)),
            "overlap_prev_m2": float(ov.sum() * g.area),
            "bottom_vs_prev_top_p05": float(np.percentile(mis, 5)) if mis.size else np.nan,
            "bottom_vs_prev_top_p95": float(np.percentile(mis, 95)) if mis.size else np.nan,
            "frac_bottom_mismatch_gt_0.14": float((np.abs(mis) > 0.14).mean()) if mis.size else np.nan,
        })
        prev_top = np.where(s.mask, s.top, prev_top)
    sq = pd.DataFrame(rows)
    sq.to_csv(out / "survey_qaqc.csv", index=False)

    # repose angle from all surveyed face cells (upper part of the slope distribution)
    allsl = []
    for s in ds.surveys:
        sl = slope_deg(np.where(s.mask, s.top, np.nan), g.cell)
        face = s.mask & (sl > 25)
        allsl.append(sl[face & np.isfinite(sl)])
    allsl = np.concatenate(allsl)
    repose = {"face_cells": int(allsl.size), "p50": float(np.median(allsl)), "p75": float(np.percentile(allsl, 75)),
              "p90": float(np.percentile(allsl, 90)), "mode": float(np.histogram(allsl, bins=np.arange(25, 55, 0.5))[1][np.argmax(np.histogram(allsl, bins=np.arange(25, 55, 0.5))[0])])}

    summary = {
        "n_fms_records": int(len(f)), "n_excluded": int(f["exclude_from_model"].sum()),
        "n_flagged_any": int((f["n_flags"] > 0).sum()), "payload_multiple_of_38_frac": float(q),
        "n_grade_signatures": int(f["grade_group"].nunique()),
        "fms_first": str(f["timestamp"].min()), "fms_last": str(f["timestamp"].max()),
        "total_tonnes": float(f["payload_t"].sum()),
        "surveys": len(ds.surveys), "survey_volume_m3": float(sq["volume_m3"].sum()),
        "base_plane": {"coef": base["coef"], "resid_sd": base["resid_sd"], "dip_deg": base["dip_deg"], "n": base["n_points"]},
        "repose": repose,
        "dump_z_minus_surface": {"n": int(np.isfinite(f["dz_dump_minus_surface"]).sum()),
                                 "median": float(np.nanmedian(f["dz_dump_minus_surface"])),
                                 "p10": float(np.nanpercentile(f["dz_dump_minus_surface"], 10)),
                                 "p90": float(np.nanpercentile(f["dz_dump_minus_surface"], 90))},
        "gap_periods": [(str(a), str(b)) for a, b in gap_periods],
        "days_survey_no_fms": daily.index[daily["status"] == "SURVEY CHANGE, NO FMS"].strftime("%Y-%m-%d").tolist(),
    }
    _figures(ds, cfg, f, daily, sq, base, allsl, out)
    return {"fms": f, "flags": flag_summary, "daily": daily, "surveys": sq, "summary": summary, "groups": groups, "payload": pay}


def _figures(ds, cfg, f, daily, sq, base, allsl, out):
    import matplotlib.pyplot as plt
    g = ds.grid
    # 1. dump location map with survey footprints, coloured by day
    fig, ax = plt.subplots(figsize=(8.5, 7))
    day = (f["timestamp"] - f["timestamp"].min()).dt.total_seconds() / 86400
    cols = pl.period_colors(len(ds.surveys))
    for s, c in zip(ds.surveys, cols):
        ax.contour(g.xc, g.yc, s.mask.astype(float), [0.5], colors=[c], linewidths=1.0)
    sc = ax.scatter(f["x"], f["y"], c=day, cmap=pl.SEQ_OR, s=16, edgecolor=pl.SURFACE, linewidth=0.6, zorder=3)
    flagged = f[f["F10_below_floor"] | f["F09_far_from_face"]]
    ax.scatter(flagged["x"], flagged["y"], s=80, facecolor="none", edgecolor=pl.INK, linewidth=1.0, zorder=4, label="flagged location (F09/F10)")
    pl.plan_axes(ax, g, "FMS dump locations and survey change-solid footprints")
    cb = fig.colorbar(sc, ax=ax, shrink=0.7)
    cb.set_label("days since first FMS record")
    ax.plot([], [], color=pl.BLUE[5], label="survey footprints (light = early, dark = late)")
    ax.legend(loc="upper right")
    pl.save(fig, out / "fig_qaqc_dump_map.png")

    # 2. daily tonnage + survey volume (two panels, one axis each)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    x = np.arange(len(daily))
    a1.bar(x, daily["tonnes"] / 1000, color=pl.CAT[0], width=0.7)
    for k, st in enumerate(daily["status"]):
        if st == "SURVEY CHANGE, NO FMS":
            a1.axvspan(k - 0.5, k + 0.5, color=pl.CAT[3], alpha=0.18, lw=0)
    a1.set_ylabel("FMS tonnes (kt)")
    a1.set_title("Daily FMS tonnage (shaded = survey shows placement but no FMS record)", loc="left")
    vol = []
    for d in daily.index:
        v = sq.loc[pd.to_datetime(sq["assigned_datetime"]).dt.normalize() == d, "volume_m3"]
        vol.append(v.sum() if len(v) else np.nan)
    a2.bar(x, np.array(vol) / 1000, color=pl.CAT[2], width=0.7)
    a2.set_ylabel("survey solid volume (k m³)")
    a2.set_title("Volume of the survey change solid dated that day", loc="left")
    a2.set_xticks(x)
    a2.set_xticklabels(daily.index.strftime("%m-%d"), rotation=45)
    pl.save(fig, out / "fig_qaqc_daily_tonnage_volume.png")

    # 3. daily grades
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    d = daily.dropna(subset=["cu_pct_wavg"])
    a1.plot(d.index, d["cu_pct_wavg"], marker="o", ms=5, color=pl.CAT[0])
    a1.set_title("Daily tonnage-weighted Cu (%)", loc="left")
    a2.plot(d.index, d["au_gpt_wavg"], marker="o", ms=5, color=pl.CAT[1])
    a2.set_title("Daily tonnage-weighted Au (g/t)", loc="left")
    for a in (a1, a2):
        a.tick_params(axis="x", labelrotation=45)
    pl.save(fig, out / "fig_qaqc_daily_grades.png")

    # 4. payload histogram + grade signature scatter
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    vc = f["payload_t"].value_counts().sort_index()
    a1.bar(vc.index.astype(str), vc.values, color=pl.CAT[0])
    a1.set_title("Truck payload values (all multiples of 38 t)", loc="left")
    a1.set_xlabel("payload (t)")
    a1.set_ylabel("loads")
    gg = f.groupby("grade_group").agg(cu=("cu_pct", "first"), au=("au_gpt", "first"), t=("payload_t", "sum"))
    a2.scatter(gg["cu"], gg["au"], s=gg["t"] / 40, color=pl.CAT[0], alpha=0.75, edgecolor=pl.SURFACE)
    a2.set_xlabel("Cu (%)")
    a2.set_ylabel("Au (g/t)")
    a2.set_title(f"{len(gg)} distinct grade signatures (size = tonnes)", loc="left")
    pl.save(fig, out / "fig_qaqc_payload_grades.png")

    # 5. dump Z vs surface, time of day
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    dz = f["dz_dump_minus_surface"].dropna()
    a1.hist(dz, bins=np.arange(-12, 12.5, 0.5), color=pl.CAT[0])
    a1.axvline(np.median(dz), color=pl.INK, lw=1)
    a1.set_title(f"Dump Z minus surveyed surface (n={len(dz)}, median {np.median(dz):.1f} m)", loc="left")
    a1.set_xlabel("m")
    a2.hist(f["timestamp"].dt.hour + f["timestamp"].dt.minute / 60, bins=np.arange(0, 24.5, 1), color=pl.CAT[0])
    a2.set_title("Dump time of day", loc="left")
    a2.set_xlabel("hour")
    pl.save(fig, out / "fig_qaqc_dumpz_timeofday.png")

    # 6. survey solids: thickness maps
    n = len(ds.surveys)
    ncol = 5
    fig, axs = plt.subplots(int(np.ceil(n / ncol)), ncol, figsize=(17, 3.6 * np.ceil(n / ncol)))
    for ax, s in zip(axs.flat, ds.surveys):
        im = pl.raster(ax, np.where(s.mask, s.thickness, np.nan), g, vmin=0, vmax=6)
        pl.plan_axes(ax, g, f"{s.file}\n{s.datetime:%Y-%m-%d}", ticks=False)
        ax.set_xticks([]); ax.set_yticks([])
    for ax in list(axs.flat)[n:]:
        ax.axis("off")
    fig.colorbar(im, ax=axs, shrink=0.6, label="change-solid thickness (m)")
    pl.save(fig, out / "fig_qaqc_survey_solids.png")

    # 7. slope / repose histogram
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.hist(allsl, bins=np.arange(25, 55, 0.5), color=pl.CAT[0])
    ax.axvline(np.median(allsl), color=pl.INK, lw=1)
    ax.set_title(f"Surveyed face slopes (>25°): median {np.median(allsl):.1f}°, P75 {np.percentile(allsl, 75):.1f}°", loc="left")
    ax.set_xlabel("slope (degrees)")
    pl.save(fig, out / "fig_qaqc_repose.png")

    # 8. floor plane residuals
    P, keep = base["points"], base["keep"]
    X = np.c_[P[:, 0] - base["xm"], P[:, 1] - base["ym"], np.ones(len(P))]
    r = P[:, 2] - X @ np.array(base["coef"])
    fig, ax = plt.subplots(figsize=(7.5, 6))
    sc = ax.scatter(P[keep, 0], P[keep, 1], c=r[keep], cmap=pl.DIV, vmin=-0.75, vmax=0.75, s=6)
    ax.scatter(P[~keep, 0], P[~keep, 1], marker="x", color=pl.INK, s=10, label="rejected (>2.5 sd)")
    pl.plan_axes(ax, g, f"Stockpile floor plane fit (residual sd {base['resid_sd']:.2f} m)")
    fig.colorbar(sc, ax=ax, shrink=0.7, label="residual (m)")
    ax.legend()
    pl.save(fig, out / "fig_qaqc_floor_plane.png")

    # 9. dump density
    fig, ax = plt.subplots(figsize=(8, 6.5))
    hb = ax.hexbin(f["x"], f["y"], C=f["payload_t"], reduce_C_function=np.sum, gridsize=18, cmap=pl.SEQ, mincnt=1)
    pl.plan_axes(ax, g, "Spatial density of dumped tonnage")
    fig.colorbar(hb, ax=ax, shrink=0.7, label="tonnes per hexagon")
    pl.save(fig, out / "fig_qaqc_dump_density.png")
