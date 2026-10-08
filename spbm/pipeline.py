"""End-to-end workflow (Task 8). Each step writes to outputs/<step>/."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import audit, blockmodel as bm, bmviz, growth, qaqc, uncertainty, validation, volume
from .config import resolve
from .dataset import load_dataset
from .movement import reconstruct


def _md(df: pd.DataFrame, floatfmt="{:,.2f}") -> str:
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else floatfmt.format(v))
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(v).replace("|", "\\|") for v in r.values) + " |")
    return "\n".join(lines)


def run(cfg, until=None, n_mc=None, do_mc=True, do_twin=True, do_robust=True, do_sens=True, do_align=True, do_temporal=True,
        do_scen=True, verbose=True):
    started = datetime.now()
    t0 = time.time()
    cfg_loaded = cfg      # configuration as supplied (hashed in the manifest); cfg gains resolved values below
    root = resolve(cfg["outputs"]["root"])
    dirs = {k: root / k for k in ["qaqc", "growth", "movement", "blockmodel", "validation", "uncertainty", "audit"]}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    notes = []

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)

    loader = lambda c: load_dataset(c, until=until, verbose=False)  # noqa: E731
    # 1-2 import -----------------------------------------------------------
    log("1-2 import FMS records and survey surfaces")
    ds = load_dataset(cfg, until=until, verbose=verbose)
    new = audit.update_registry(ds.files, dirs["audit"])
    log(f"    {len(ds.fms)} FMS records, {len(ds.surveys)} surveys; {len(new)} newly registered files")
    ds.register.to_csv(dirs["audit"] / "survey_register.csv", index=False)
    ds.interventions.to_csv(dirs["audit"] / "manual_interventions_applied.csv", index=False)
    store_log = resolve(cfg["inputs"]["raw_store"]) / "ingest_log.csv"
    if store_log.exists():
        pd.read_csv(store_log).to_csv(dirs["audit"] / "ingest_log.csv", index=False)
    # 3 QA/QC ---------------------------------------------------------------
    log("3   data-quality checks")
    q = qaqc.run_qaqc(ds, cfg, dirs["qaqc"])
    # 4 periods / alignment --------------------------------------------------
    if do_align:
        log("4   survey cut-off scan (temporal alignment of FMS and surveys)")
        al = growth.temporal_alignment(ds, cfg, dirs["growth"])
        best = float(al.loc[al["r_daily"].idxmax(), "cutoff_hours"])
        if abs(best - float(cfg["time"]["survey_cutoff_hours"])) > 1.0:
            notes.append(f"Cut-off scan peaks at {best:g} h but config uses {cfg['time']['survey_cutoff_hours']} h - review A-05")
    log("4b  volume factor calibration (A-06)")
    cfg = volume.resolve_density(ds, cfg)
    cal = volume.calibrate(ds, cfg)
    volume.write_outputs(cal, cfg, dirs["growth"])
    qaqc.add_calibration_rules(q, cal, dirs["qaqc"])
    log(f"    f_v = {cal['f_v']:.3f} on intervals {cal['consistent_intervals']}; hold-out MAE {cal['holdout_mae_fv'] * 100:.1f}%")
    # 5 movement -------------------------------------------------------------
    log("5   material-movement reconstruction (CPST)")
    rec = reconstruct(ds, cfg, keep_plans=True, verbose=verbose)
    ptab = growth.period_table(rec, ds, dirs["growth"])
    rec.destinations.to_csv(dirs["movement"] / "load_destinations.csv", index=False)
    rec.loads.to_csv(dirs["movement"] / "loads_used.csv", index=False)
    np.savez_compressed(dirs["movement"] / "transport_plans.npz",
                        **{f"P_{p['period']}": p["P"] for p in rec.plans if not p.get("provisional")},
                        **{f"cells_{p['period']}": p["fill_cells"] for p in rec.plans if not p.get("provisional")})
    g = ds.grid
    for name, z in [("floor_plane", rec.B), ("pre_record_surface", rec.legacy_top), ("final_model_surface", rec.diagnostics["final_surface"]),
                    ("latest_surveyed_surface", rec.observed_top)]:
        bm.export_grid_asc(np.where(rec.domain | np.isfinite(z), z, np.nan), g, dirs["movement"] / f"{name}.asc")
    growth.growth_figures(rec, ds, ptab, dirs["growth"])
    # 6-7 block model --------------------------------------------------------
    log("6-7 block model and inventories")
    bg = bm.make_block_grid(rec, cfg)
    agg = bm.aggregate(rec, bg)
    df = bm.block_table(rec, bg, agg, cfg)
    prov = bm.provenance(rec, bg)
    df = bm.provenance_fields(df, prov, bg, rec.loads)
    # 8 uncertainty ----------------------------------------------------------
    mc = None
    if do_mc:
        log(f"8   Monte Carlo uncertainty ({n_mc or cfg['uncertainty']['n_realizations']} realisations)")
        mc = uncertainty.monte_carlo(loader, cfg, bg, df, dirs["uncertainty"], n=n_mc, verbose=verbose)
        df = uncertainty.attach_block_stats(df, mc["stats"])
        df = uncertainty.apply_prior_ranges(df, rec.loads)
        uncertainty.mc_figures(mc, df, dirs["uncertainty"])
    df["confidence"] = bm.classify_confidence(df, cfg)
    df.to_csv(dirs["blockmodel"] / "stockpile_block_model.csv", index=False, float_format="%.5g")
    vtk_fields = [c for c in ["tonnes", "cu_pct", "au_gpt", "ag_gpt", "fill_frac", "frac_fms", "frac_legacy", "cu_cv", "cu_p10", "cu_p90",
                              "info_class", "confidence"] if c in df]
    bm.export_vtk(df, bg, dirs["blockmodel"] / "stockpile_block_model.vtk", vtk_fields)
    st = bm.summary_tables(df, cfg)
    for k, v in st.items():
        v.to_csv(dirs["blockmodel"] / f"summary_{k}.csv")
    with open(dirs["blockmodel"] / "block_model_definition.json", "w") as fh:
        json.dump({"origin": [bg.x0, bg.y0, bg.z0], "block_size": [bg.dx, bg.dy, bg.dz], "n_blocks": [bg.nx, bg.ny, bg.nz],
                   "crs": cfg["project"]["crs_note"], "units": {"cu_pct": "% Cu", "au_gpt": "g/t Au", "ag_gpt": "g/t Ag", "tonnes": "dry t (as FMS)",
                   "cu_t": "t Cu", "au_kg": "kg Au", "ag_kg": "kg Ag"}}, fh, indent=2)
    log("    figures")
    bmviz.bench_plans(df, bg, rec, "cu_pct", "Cu (%)", bmviz.pl.SEQ, dirs["blockmodel"])
    bmviz.bench_plans(df, bg, rec, "au_gpt", "Au (g/t)", bmviz.pl.SEQ_OR, dirs["blockmodel"])
    bmviz.bench_plans(df, bg, rec, "frac_fms", "fraction FMS-tracked", bmviz.pl.SEQ, dirs["blockmodel"], 0, 1)
    bmviz.bench_plans(df, bg, rec, "tonnes", "tonnes per block", bmviz.pl.SEQ, dirs["blockmodel"])
    bmviz.sections(df, bg, rec, dirs["blockmodel"])
    bmviz.sections(df, bg, rec, dirs["blockmodel"], "frac_fms", "fraction FMS-tracked")
    bmviz.view3d(df, bg, dirs["blockmodel"])
    bmviz.grade_tonnage(st["grade_tonnage"], dirs["blockmodel"])
    bmviz.class_maps(df, bg, rec, dirs["blockmodel"])
    if mc is not None:
        bmviz.uncertainty_maps(df, bg, dirs["uncertainty"])
        bmviz.bench_plans(df, bg, rec, "cu_cv", "Cu grade CV (Monte Carlo)", bmviz.pl.SEQ_OR, dirs["uncertainty"], 0, 0.3)
    # 9 validation -----------------------------------------------------------
    log("9   validation and reconciliation")
    vb = validation.mass_metal_balance(rec, agg, df)
    vb.to_csv(dirs["validation"] / "mass_metal_balance.csv", index=False)
    inv = validation.class_inventory(rec, agg)
    inv.to_csv(dirs["validation"] / "inventory_by_class.csv", index=False)
    vr = validation.volume_reconciliation(rec)
    vr.to_csv(dirs["validation"] / "volume_reconciliation.csv", index=False)
    geo = validation.geometry_check(rec, ds, dirs["validation"])
    pd.Series(geo).to_csv(dirs["validation"] / "geometry_check.csv")
    tv = None
    if do_temporal:
        log("    forward-model temporal validation")
        tv = validation.temporal_validation(rec, cfg, dirs["validation"])
    tw = None
    if do_twin:
        log("    synthetic twin experiment")
        tw = validation.twin_experiment(rec, ds, cfg, dirs["validation"])
    if do_robust:
        log("    numerical robustness")
        validation.robustness(loader, cfg, dirs["validation"], df)
    scen = None
    if do_scen:
        log("    volume-gap scenarios (A-06)")
        scen = uncertainty.scenarios(ds, cfg, bg, dirs["uncertainty"], verbose=verbose)
    if do_sens:
        log("    one-at-a-time sensitivity")
        uncertainty.sensitivity_oat(loader, cfg, df, rec, dirs["uncertainty"], verbose=verbose)
    # 10 summary -------------------------------------------------------------
    summary = {
        "last_survey": str(ds.surveys[-1].datetime), "n_surveys": len(ds.surveys), "n_fms_records": int(len(ds.fms)),
        "fms_tonnes": float(rec.totals_in["T_F"]), "fms_cu_t": float(rec.totals_in["CU_F"]), "fms_au_kg": float(rec.totals_in["AU_F"]),
        "total_tonnes": float(df["tonnes"].sum()), "total_cu_t": float(df["cu_t"].sum()), "total_au_kg": float(df["au_kg"].sum()),
        "tonnes_fms_in_model": float(df["t_fms"].sum()), "tonnes_unattributed": float(df["t_unattributed"].sum()),
        "tonnes_legacy": float(df["t_legacy"].sum()), "mass_balance_rel_err_ppm": float(vb.loc[0, "rel_diff_ppm"]),
        "cu_balance_rel_err_ppm": float(vb.loc[1, "rel_diff_ppm"]), "au_balance_rel_err_ppm": float(vb.loc[2, "rel_diff_ppm"]),
        "geometry_rmse_m": geo["rmse_m"], "survey_volume_m3": float(rec.periods["solid_volume"].sum()),
        "unattributed_volume_m3": float(rec.periods["unattributed_volume"].sum()),
        "blocks": int(len(df)), "block_size": cfg["blockmodel"]["block"],
        "survey_cutoff_hours": float(cfg["time"]["survey_cutoff_hours"]),
        "volume_factor": float(cal["f_v"]), "volume_factor_p10_p90": [cal["f_v_p10"], cal["f_v_p90"]],
        "volume_factor_consistent_intervals": cal["consistent_intervals"],
        "volume_factor_holdout_mae": float(cal["holdout_mae_fv"]),
        "payload_factor": float(cfg["density"]["payload_factor"]),
        "in_pile_density_t_m3": float(np.average(rec.loads["rho"], weights=rec.loads["m"])),
        "tonnes_record_period": float(df["t_fms"].sum() + df["t_unattributed"].sum()),
        "cu_t_record_period": float(inv.loc[:1, "cu_t"].sum()),
    }
    if tw is not None:
        summary["twin_cu_rmse_base"] = float(tw["table"].iloc[1]["cu_rmse"])
        summary["twin_cu_corr_base"] = float(tw["table"].iloc[1]["cu_corr"])
    for r in (scen.itertuples() if scen is not None else []):
        summary[f"scenario_{r.scenario}_record_period_tonnes"] = float(r.record_period_tonnes)
        summary[f"scenario_{r.scenario}_total_tonnes"] = float(r.total_tonnes)
    if mc is not None:
        summary["mc_record_period_tonnes_p10_p50_p90"] = mc["global"].loc["record_period_tonnes", ["P10", "P50", "P90"]].tolist()
        summary["mc_record_period_cu_t_p10_p50_p90"] = mc["global"].loc["record_period_cu_t", ["P10", "P50", "P90"]].tolist()
        summary["mc_total_tonnes_p10_p50_p90"] = mc["global"].loc["total_tonnes", ["P10", "P50", "P90"]].tolist()
        summary["mc_cu_t_p10_p50_p90"] = mc["global"].loc["cu_t", ["P10", "P50", "P90"]].tolist()
        summary["mc_au_kg_p10_p50_p90"] = mc["global"].loc["au_kg", ["P10", "P50", "P90"]].tolist()
    with open(root / "summary.json", "w") as fh:
        json.dump({"key_results": summary, "qaqc": q["summary"], "geometry": geo, "forward_best": tv["best"] if tv else None}, fh, indent=2, default=str)
    _tables_md(root, q, ptab, st, vb, inv, vr, geo, tv, tw, mc, cal, scen)
    used = [f for f in ds.files if f.kind == "fms" or f.name in set(ds.register["file"])]
    if until:
        notes.append(f"Data restricted to records/surveys up to {until}")
    man = audit.write_manifest(cfg_loaded, used, root, summary, started, notes)
    rep = audit.change_report(root)
    log(f"done - run {man['run_id']}" + (" (change report written)" if rep else ""))
    return {"rec": rec, "df": df, "bg": bg, "summary": summary}


def _tables_md(root, q, ptab, st, vb, inv, vr, geo, tv, tw, mc, cal=None, scen=None):
    parts = ["# Key result tables (auto-generated - do not edit)", ""]
    parts += ["## QA rule catalogue", _md(q["catalogue"].drop(columns=["treatment"]), "{:,.0f}"), ""]
    parts += ["## FMS record rules", _md(q["flags"], "{:,.0f}"), ""]
    parts += ["## Survey QA", _md(q["surveys"][["file", "assigned_datetime", "footprint_m2", "volume_m3", "slope_p50", "reaches_floor",
                                                 "normals_inverted", "frac_bottom_mismatch_gt_0.14"]]), ""]
    cols = ["period", "survey", "end", "gap_detected", "n_loads", "fms_tonnes", "fms_volume", "carried_in_volume", "solid_volume",
            "fill_volume", "cut_volume", "unobserved_fill_new_cells", "placed_volume", "unattributed_volume", "retained_volume", "apparent_density_t_m3"]
    parts += ["## Period reconciliation", _md(ptab[cols]), ""]
    if cal is not None:
        parts += ["## Volume factor calibration (A-06)", _md(cal["table"][["interval", "survey", "end", "fill_m3", "inferred_toe_fill_m3", "cut_m3",
                                                                            "net_m3", "fms_t", "vdens_m3", "longest_fms_silence_h", "ratio",
                                                                            "consistent", "role", "err_fv_first_half"]]), ""]
    if scen is not None:
        parts += ["## Volume-gap scenarios", _md(scen.drop(columns=["description"])), ""]
    parts += ["## Volume reconciliation", _md(vr), ""]
    parts += ["## Mass / metal balance", _md(vb), ""]
    parts += ["## Inventory by information class", _md(inv), ""]
    for k, v in st.items():
        parts += [f"## Block model summary: {k}", _md(v.reset_index()), ""]
    parts += ["## Geometry check", _md(pd.DataFrame([geo])), ""]
    if tv is not None:
        parts += ["## Forward model temporal validation (means)", _md(tv["summary"].reset_index()), ""]
    if tw is not None:
        parts += ["## Synthetic twin experiment", _md(tw["table"]), ""]
    if mc is not None:
        parts += ["## Monte Carlo global summary", _md(mc["global"].reset_index()), ""]
    (root / "report_tables.md").write_text("\n".join(parts))
