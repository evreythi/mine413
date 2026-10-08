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

from .rules import RULES, record_rules


def _catalogue(counts: dict) -> pd.DataFrame:
    rows = []
    for rid, (level, sev, desc, treat) in RULES.items():
        c = counts.get(rid, {})
        rows.append({"rule_id": rid, "level": level, "severity": sev, "description": desc, "count": int(c.get("count", 0)),
                     "tonnes": c.get("tonnes", np.nan), "items": c.get("items", ""), "treatment": treat})
    return pd.DataFrame(rows)


def run_qaqc(ds, cfg, out: Path, rec=None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    g = ds.grid
    f = ds.fms.copy()
    base = fit_base_plane(ds, cfg)
    B = base["B"]
    times = [s.datetime for s in ds.surveys]

    # ----------------------------------------------------------- FMS checks
    R = record_rules(f, cfg)
    # LOC_OUTSIDE_SURVEYS / LOC_OUTSIDE_DOMAIN: position vs the union of all change solids
    obs = np.zeros((g.ny, g.nx), bool)
    for s in ds.surveys:
        obs |= s.mask
    dist = ndimage.distance_transform_edt(~obs) * g.cell
    j, i, inside = g.index(f["x"].fillna(g.x0).values, f["y"].fillna(g.y0).values)
    f["dist_to_survey_m"] = np.where(inside & f[["x", "y"]].notna().all(axis=1), dist[j, i], np.nan)
    R["LOC_OUTSIDE_SURVEYS"] = (f["dist_to_survey_m"] > 0).values
    R["LOC_OUTSIDE_DOMAIN"] = (f["dist_to_survey_m"] > 100).values | (f[["x", "y"]].notna().all(axis=1) & ~inside)
    f["floor_z"] = B[j, i]
    # survey interval of each dump (same convention as the engine)
    first_start = times[0] - pd.Timedelta(hours=float(cfg["time"].get("first_interval_hours", 24.0)))
    edges = np.array([first_start] + times, dtype="datetime64[ns]")
    tt = f["timestamp"].values.astype("datetime64[ns]")
    per = np.searchsorted(edges, tt, side="left") - 1
    f["interval"] = np.where(f["timestamp"].notna(), per, -99)
    R["TIME_BEFORE_FIRST_INTERVAL"] = (f["interval"] == -1).values
    R["TIME_AFTER_LAST_SURVEY"] = (f["interval"] == len(times)).values
    dur = np.diff(edges).astype("timedelta64[m]").astype(float) / 60.0
    long_iv = [k for k in range(1, len(times)) if dur[k] > 36]
    R["IN_SURVEY_GAP_INTERVAL"] = f["interval"].isin(long_iv).values
    # LOC_Z_INCONSISTENT: envelope of the surface at the start and end of the dump's interval
    zs, ze, zsv = np.full(len(f), np.nan), np.full(len(f), np.nan), np.full(len(f), np.nan)
    comp = np.full((g.ny, g.nx), np.nan)
    tol = float(cfg.get("fms", {}).get("dump_z_tolerance_m", 5.0))
    for k, sv in enumerate(ds.surveys):
        m = per == k
        zsv[m] = comp[j[m], i[m]]
        zs[m] = np.where(np.isfinite(zsv[m]), zsv[m], B[j[m], i[m]])   # unsurveyed: floor
        comp = np.where(sv.mask, sv.top, comp)
        ze[m] = comp[j[m], i[m]]
    m = per == len(times)
    zs[m] = comp[j[m], i[m]]
    zsv[m] = comp[j[m], i[m]]
    ze[m] = comp[j[m], i[m]]
    f["surface_z_at_dump"] = zsv            # last surveyed surface before the dump (NaN if never surveyed)
    f["surface_z_interval_end"] = ze
    f["dz_dump_minus_surface"] = f["z"] - zsv
    lo, hi = np.fmin(zs, ze) - tol, np.fmax(zs, ze) + tol
    R["LOC_Z_INCONSISTENT"] = (np.isfinite(ze) & ((f["z"].values < lo) | (f["z"].values > hi)))
    R = R[[k for k in RULES if RULES[k][0] == "record"]]
    for k in R.columns:
        f[k] = R[k].values
    f["n_flags"] = R.sum(axis=1).values
    from .rules import EXCLUDING
    f["exclude_from_model"] = R[EXCLUDING + ["DUP_IDENTICAL", "TIME_BEFORE_FIRST_INTERVAL"]].any(axis=1).values
    f["location_unknown"] = R[["LOC_DEFAULT", "LOC_OUTSIDE_DOMAIN"]].any(axis=1).values
    sig = f[["cu_pct", "au_gpt", "ag_gpt", "density"]].astype(str).agg("|".join, axis=1)
    f["grade_group"] = pd.factorize(sig)[0] + 1
    f.to_csv(out / "fms_records_with_flags.csv", index=False)
    counts = {k: {"count": int(R[k].sum()), "tonnes": float(f.loc[R[k].values, "payload_t"].sum())} for k in R.columns}
    for k in ("LOC_DEFAULT", "TIME_DUPLICATE", "DUP_CONFLICT", "TIME_AFTER_LAST_SURVEY", "LOC_Z_INCONSISTENT", "PAYLOAD_PARTIAL", "PAYLOAD_HIGH"):
        if counts[k]["count"]:
            ids = f.loc[R[k].values, "cycle_id"].astype(str).tolist()
            counts[k]["items"] = "cycle " + ", ".join(ids[:16]) + (" ..." if len(ids) > 16 else "")
    flag_summary = pd.DataFrame([{"rule_id": k, "severity": RULES[k][1], "description": RULES[k][2],
                                  "records": counts[k]["count"], "tonnes": counts[k]["tonnes"], "treatment": RULES[k][3]}
                                 for k in R.columns])
    flag_summary.to_csv(out / "fms_flag_summary.csv", index=False)
    gap_periods = [(times[k - 1], times[k]) for k in long_iv]

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

    # daily coverage table by PRODUCTION day: day D runs from D 00:00 + (cut-off - 24 h)
    # to the cut-off of the survey labelled D (D+1 07:00 for a 31 h cut-off)
    shift = pd.Timedelta(hours=float(cfg["time"]["survey_cutoff_hours"]) - 24.0)
    nominal = pd.to_datetime(ds.register["assigned_date"]).dt.normalize()
    pday = (f["timestamp"] - shift).dt.normalize()
    days = pd.date_range(min(pday.min(), nominal.min()), max(pday.max(), nominal.max()))
    daily = pd.DataFrame(index=days)
    daily.index.name = "production_day"
    dd = f.groupby(pday)
    daily["loads"] = dd.size().reindex(days).fillna(0).astype(int)
    daily["tonnes"] = dd["payload_t"].sum().reindex(days).fillna(0)
    daily["cu_pct_wavg"] = (dd.apply(lambda d: np.average(d["cu_pct"], weights=d["payload_t"]), include_groups=False)).reindex(days)
    daily["au_gpt_wavg"] = (dd.apply(lambda d: np.average(d["au_gpt"], weights=d["payload_t"]), include_groups=False)).reindex(days)
    daily["first_dump"] = dd["timestamp"].min().reindex(days).dt.strftime("%H:%M")
    daily["last_dump"] = dd["timestamp"].max().reindex(days).dt.strftime("%H:%M")
    sv_days = dict(zip(nominal, ds.register["file"]))
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
            "nominal_date": pd.Timestamp(r.assigned_date).date(), "assigned_datetime": s.datetime, "override": r.override_reason[:60] + ("..." if len(r.override_reason) > 60 else ""),
            "layer_date_token": lay_date,
            "layer_vs_name_consistent": lay_date[2:] == s.file.split("_")[-1][2:6] and lay_date[:2] == s.file.split("_")[-1][:2],
            "entity_types": ";".join(f"{k}:{v}" for k, v in s.meta["entity_types"].items()),
            "insunits": s.meta.get("insunits"), "measurement": s.meta.get("measurement"), "tdupdate": s.meta.get("tdupdate"),
            "acadver": s.meta.get("acadver"), "zero_plan_area_faces": s.meta.get("zero_plan_area"),
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
    # survey-file rules
    nom = pd.to_datetime(ds.register["assigned_date"]).dt.normalize()
    ivs = ds.interventions
    redated = set(ivs.loc[ivs["type"] == "survey_date", "target"]) if len(ivs) else set()
    sq["DXF_UNITS_HEADER"] = (sq["insunits"] != 6) | (sq["measurement"] != 1)
    sq["DXF_SAVED_BEFORE_SURVEY"] = pd.to_datetime(sq["tdupdate"], errors="coerce").values < nom.values
    sq["SURVEY_NAME_YEAR"] = sq["file"].isin(redated)
    sq["LAYER_DATE_MISMATCH"] = ~sq["layer_vs_name_consistent"]
    sq["ZERO_PLAN_AREA_FACES"] = sq["zero_plan_area_faces"].fillna(0) > 0
    sq["DEGENERATE_FACES"] = sq["degenerate"] > 0
    sq["DUPLICATE_FACES"] = sq["duplicate_triangles"] > 0
    sq["SOLID_NOT_CLOSED"] = sq["closed_solid_frac"] < 0.98
    sq["NORMALS_INVERTED"] = sq["normals_inverted"]
    sq["SOLID_BASE_MISMATCH"] = sq["frac_bottom_mismatch_gt_0.14"].fillna(0) > 0.2
    sq.to_csv(out / "survey_qaqc.csv", index=False)
    for k in [r for r in RULES if RULES[r][0] == "survey"]:
        hit = sq.loc[sq[k], "file"].tolist()
        extra = ""
        if k == "ZERO_PLAN_AREA_FACES" and hit:
            extra = f" ({int(sq['zero_plan_area_faces'].min())}-{int(sq['zero_plan_area_faces'].max())} per file)"
        if k == "DXF_SAVED_BEFORE_SURVEY" and hit:
            extra = f" (TDUPDATE {', '.join(sorted(set(sq.loc[sq[k], 'tdupdate'])))})"
        counts[k] = {"count": len(hit), "items": ("all files" if len(hit) == len(sq) else ", ".join(hit)) + extra if hit else ""}

    # repose angle from all surveyed face cells (upper part of the slope distribution)
    allsl = []
    for s in ds.surveys:
        sl = slope_deg(np.where(s.mask, s.top, np.nan), g.cell)
        face = s.mask & (sl > 25)
        allsl.append(sl[face & np.isfinite(sl)])
    allsl = np.concatenate(allsl)
    repose = {"face_cells": int(allsl.size), "p50": float(np.median(allsl)), "p75": float(np.percentile(allsl, 75)),
              "p90": float(np.percentile(allsl, 90)), "mode": float(np.histogram(allsl, bins=np.arange(25, 55, 0.5))[1][np.argmax(np.histogram(allsl, bins=np.arange(25, 55, 0.5))[0])])}

    # dataset rules (FMS_SILENCE / VOLUME_RATIO_OUTLIER are added after the volume calibration)
    counts["SURVEY_GAP"] = {"count": len(long_iv), "items": "; ".join(f"interval {k} ({times[k - 1]:%m-%d %H:%M} to {times[k]:%m-%d %H:%M}, {dur[k]:.0f} h)" for k in long_iv)}
    late = f["timestamp"].min() > first_start
    counts["FMS_PARTIAL_FIRST_INTERVAL"] = {"count": int(late), "items": f"first FMS record {f['timestamp'].min():%Y-%m-%d %H:%M}, interval 0 starts {first_start:%Y-%m-%d %H:%M}" if late else ""}
    nf = daily.index[daily["status"] == "SURVEY CHANGE, NO FMS"]
    counts["SURVEY_CHANGE_NO_FMS"] = {"count": len(nf), "items": ", ".join(nf.strftime("%Y-%m-%d"))}
    allq = bool((f["payload_t"].dropna() % float(cfg.get("fms", {}).get("pass_quantum_t", 38.0)) == 0).all())
    counts["PAYLOAD_QUANTISED"] = {"count": int(allq), "items": f"{len(f)} records" if allq else ""}
    cu_m = float(np.average(f["cu_pct"].dropna(), weights=f.loc[f["cu_pct"].notna(), "payload_t"]))
    au_m = float(np.average(f["au_gpt"].dropna(), weights=f.loc[f["au_gpt"].notna(), "payload_t"]))
    counts["GRADE_UNITS_UNCONFIRMED"] = {"count": int(cu_m > 3 or au_m > 3), "items": f"mean Cu {cu_m:.2f} %, Au {au_m:.2f} g/t"}
    cat = _catalogue(counts)
    cat.to_csv(out / "qa_rule_catalogue.csv", index=False)

    summary = {
        "n_fms_records": int(len(f)), "n_excluded": int(f["exclude_from_model"].sum()),
        "n_location_unknown": int(f["location_unknown"].sum()), "tonnes_location_unknown": float(f.loc[f["location_unknown"], "payload_t"].sum()),
        "n_rules": len(RULES), "n_rules_triggered": int((cat["count"] > 0).sum()),
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
    return {"fms": f, "flags": flag_summary, "daily": daily, "surveys": sq, "summary": summary, "groups": groups, "payload": pay,
            "catalogue": cat, "counts": counts}


def add_calibration_rules(q: dict, cal: dict, out: Path) -> pd.DataFrame:
    """Dataset rules that need the interval volume budget (spbm.volume)."""
    t = cal["table"]
    sil = t[t["longest_fms_silence_h"] > 24]
    q["counts"]["FMS_SILENCE"] = {"count": len(sil), "items": "; ".join(
        f"interval {int(r.interval)} ({r.longest_fms_silence_h:.0f} h)" for r in sil.itertuples())}
    exc = t[~t["consistent"]]
    q["counts"]["VOLUME_RATIO_OUTLIER"] = {"count": len(exc), "items": "; ".join(
        f"interval {int(r.interval)} (ratio {r.ratio:.2f})" for r in exc.itertuples())}
    cat = _catalogue(q["counts"])
    cat.to_csv(out / "qa_rule_catalogue.csv", index=False)
    q["catalogue"] = cat
    q["summary"]["n_rules_triggered"] = int((cat["count"] > 0).sum())
    return cat


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
    out_s = f[f["LOC_OUTSIDE_SURVEYS"]]
    ax.scatter(out_s["x"], out_s["y"], s=70, facecolor="none", edgecolor=pl.INK, linewidth=0.9, zorder=4, label="LOC_OUTSIDE_SURVEYS")
    dflt = f[f["LOC_DEFAULT"]].drop_duplicates(["x", "y"])
    ax.scatter(dflt["x"], dflt["y"], s=110, marker="X", color=pl.CAT[1], edgecolor=pl.SURFACE, zorder=5, label="LOC_DEFAULT (location unknown)")
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
    a1.set_title("FMS tonnage per production day (D 07:00 to D+1 07:00; shaded = survey change, no FMS record)", loc="left")
    vol = []
    for d in daily.index:
        v = sq.loc[pd.to_datetime(sq["nominal_date"]) == d, "volume_m3"]
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
