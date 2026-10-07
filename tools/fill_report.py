"""Fill the report templates (tools/templates/*.template.md) with numbers and
tables from the latest run in outputs/, so that every figure quoted in D6/D4
is traceable to one run manifest.

    python tools/fill_report.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
TPL = ROOT / "tools" / "templates"


def md(df: pd.DataFrame, caption: str, fmt=None) -> str:
    fmt = fmt or {}
    d = df.copy()
    for c in d.columns:
        f = fmt.get(c)
        if f is not None:
            d[c] = d[c].map(lambda v, f=f: "" if pd.isna(v) else f.format(v))
        elif pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")
    head = "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns) + "\n"
    body = "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in d.values)
    return f"*{caption}*\n\n{head}{body}\n"


def values() -> dict:
    S = json.loads((OUT / "summary.json").read_text())
    man = json.loads((OUT / "audit" / "run_manifest.json").read_text())
    inv = pd.read_csv(OUT / "validation" / "inventory_by_class.csv").set_index("class")
    F, U, L, T = [inv.loc[k] for k in ["FMS-tracked (reconciled + provisional)", "Unattributed (imputed grade)", "Legacy (assumed grade)", "TOTAL"]]
    mc = pd.read_csv(OUT / "uncertainty" / "mc_global_summary.csv", index_col=0)
    geo = pd.read_csv(OUT / "validation" / "geometry_check.csv", index_col=0).iloc[:, 0]
    fwd = pd.read_csv(OUT / "validation" / "forward_temporal_summary.csv")
    tw = pd.read_csv(OUT / "validation" / "twin_experiment.csv")
    bm = pd.read_csv(OUT / "blockmodel" / "stockpile_block_model.csv", low_memory=False)
    loads = pd.read_csv(OUT / "movement" / "loads_used.csv")
    w = loads["m"].values

    def wq(x, q):
        o = np.argsort(x); c = np.cumsum(w[o]) / w.sum()
        return float(np.interp(q, c, x[o]))
    ft = fwd[fwd["set"].str.startswith("test")].set_index("mode")
    twi = tw.set_index("method")
    base = twi.loc["CPST eps=6 m (base)"]
    pa = twi.loc["Baseline: period-average (eps=1e4)"]
    gm = twi.loc["Reference: global mean grade"]
    v = {
        "RUN_ID": man["run_id"],
        "T_F": f"{F.tonnes:,.0f}", "S_F": f"{F.share_of_tonnes:.1%}", "CU_F": f"{F.cu_pct:.2f}", "AU_F": f"{F.au_gpt:.2f}",
        "T_U": f"{U.tonnes:,.0f}", "S_U": f"{U.share_of_tonnes:.1%}", "CU_U": f"{U.cu_pct:.2f}", "AU_U": f"{U.au_gpt:.2f}",
        "T_L": f"{L.tonnes:,.0f}", "S_L": f"{L.share_of_tonnes:.1%}", "CU_L": f"{L.cu_pct:.2f}", "AU_L": f"{L.au_gpt:.2f}",
        "T_T": f"{T.tonnes:,.0f}", "CU_T": f"{T.cu_pct:.2f}", "AU_T": f"{T.au_gpt:.2f}",
        "MC_T": " / ".join(f"{x / 1000:,.0f}" for x in mc.loc["total_tonnes", ["P10", "P50", "P90"]]),
        "MC_CU": " / ".join(f"{x / 1000:,.1f}" for x in mc.loc["cu_t", ["P10", "P50", "P90"]]),
        "MC_AU": " / ".join(f"{x / 31.1035:,.1f}" for x in mc.loc["au_kg", ["P10", "P50", "P90"]]),
        "MC_FCU": " - ".join(f"{x:.2f}" for x in mc.loc["class_fms_cu_pct", ["P10", "P90"]]) if "class_fms_cu_pct" in mc.index else "n/a",
        "GEO_RMSE": f"{geo['rmse_m']:.2f}", "GEO_TAU": f"{geo['frac_within_tau'] * 100:.1f}", "GEO_BIAS": f"{geo['mean_m']:+.3f}",
        "FWD_P": f"{ft.loc['push (calibrated)', 'w1_m']:.1f}", "FWD_B": f"{ft.loc['no-push baseline', 'w1_m']:.1f}",
        "TW_CPST": f"{base.cu_rmse:.2f}", "TW_R": f"{base.cu_corr:.2f}", "TW_PA": f"{pa.cu_rmse:.2f}", "TW_GM": f"{gm.cu_rmse:.2f}",
        "TW_IMPROVE": f"{(1 - base.cu_rmse / pa.cu_rmse) * 100:.0f}",
        "PRIOR_CU": f"{wq(loads['cu'].values, 0.1):.1f}-{wq(loads['cu'].values, 0.9):.1f}",
        "UNATT_VOL": f"{S['key_results']['unattributed_volume_m3']:,.0f}",
    }
    # ------------------------------------------------------------ tables
    src = pd.read_csv(OUT / "blockmodel" / "summary_by_material_source.csv", index_col=0)["tonnes"]
    tf_r, tf_p = src.iloc[0], src.iloc[1]
    rows = [["FMS-tracked, survey-reconciled", tf_r, "measured inputs; location model-generated"],
            ["FMS-tracked, provisional (after last survey)", tf_p, "measured inputs; location from forward model"],
            ["Unattributed (surveyed volume, no FMS record)", U.tonnes, "imputed (same/adjacent periods)"],
            ["Legacy (pre-record pile)", L.tonnes, "assumed (FMS mean)"],
            ["Total modelled", T.tonnes, ""]]
    ti = pd.DataFrame(rows, columns=["class", "tonnes", "basis of grade"])
    ti["share"] = ti["tonnes"] / T.tonnes
    ti["Cu %"] = [F.cu_pct, np.nan, U.cu_pct, L.cu_pct, T.cu_pct]
    ti["Au g/t"] = [F.au_gpt, np.nan, U.au_gpt, L.au_gpt, T.au_gpt]
    ti["Cu (t)"] = [F.cu_t, np.nan, U.cu_t, L.cu_t, T.cu_t]
    ti["Au (koz)"] = [F.au_kg / 31.1035, np.nan, U.au_kg / 31.1035, L.au_kg / 31.1035, T.au_kg / 31.1035]
    v["TABLE_INV"] = md(ti[["class", "tonnes", "share", "Cu %", "Au g/t", "Cu (t)", "Au (koz)", "basis of grade"]],
                        "Inventory by information class (FMS grades/metal shown for the whole FMS class)",
                        {"tonnes": "{:,.0f}", "share": "{:.1%}", "Cu %": "{:.2f}", "Au g/t": "{:.2f}", "Cu (t)": "{:,.0f}", "Au (koz)": "{:,.1f}"})
    v["N_BLOCKS"] = f"{len(bm):,}"
    flags = pd.read_csv(OUT / "qaqc" / "fms_flag_summary.csv")
    v["TABLE_FLAGS"] = md(flags, "Table 4.1 - FMS flags (records retained; treatment as stated)")
    p = pd.read_csv(OUT / "growth" / "period_reconciliation.csv", parse_dates=["end"])
    pt = pd.DataFrame({"period end": p["end"].dt.strftime("%m-%d"), "gap": np.where(p["gap_detected"], "yes", ""),
                       "loads": p["n_loads"], "FMS t": p["fms_tonnes"], "FMS m³": p["fms_volume"] + p["carried_in_volume"],
                       "solid m³": p["solid_volume"], "fill m³": p["fill_volume"], "cut m³": p["cut_volume"],
                       "unattributed m³": p["unattributed_volume"], "retained m³": p["retained_volume"],
                       "FMS explains": p["fms_explains_frac"], "FMS Cu %": p["fms_cu_pct"], "FMS Au g/t": p["fms_au_gpt"]})
    v["TABLE_PERIODS"] = md(pt, "Table 5.1 - Period reconciliation (FMS m³ includes volume carried over from the previous period)",
                            {"FMS t": "{:,.0f}", "FMS m³": "{:,.0f}", "solid m³": "{:,.0f}", "fill m³": "{:,.0f}", "cut m³": "{:,.0f}",
                             "unattributed m³": "{:,.0f}", "retained m³": "{:,.0f}", "FMS explains": "{:.0%}", "FMS Cu %": "{:.2f}", "FMS Au g/t": "{:.2f}"})
    conf = pd.read_csv(OUT / "blockmodel" / "summary_by_confidence.csv").set_index("confidence").reindex(["High", "Medium", "Low", "Uninformed"]).reset_index()
    v["TABLE_CONF"] = md(conf[["confidence", "blocks", "tonnes", "cu_pct", "au_gpt", "cu_t", "au_koz"]],
                         "Table 8.1 - Inventory by confidence class", {"blocks": "{:,.0f}", "tonnes": "{:,.0f}", "cu_t": "{:,.0f}", "au_koz": "{:,.1f}"})
    bench = pd.read_csv(OUT / "blockmodel" / "summary_by_bench_4m.csv")
    bench["bench"] = bench["bench"].map(lambda b: f"{b}-{b + 4}")
    v["TABLE_BENCH"] = md(bench[["bench", "blocks", "tonnes", "cu_pct", "au_gpt", "cu_t", "au_koz"]],
                          "Table 8.2 - Inventory by 4 m reclaim bench (all classes; see D4 for class split)",
                          {"blocks": "{:,.0f}", "tonnes": "{:,.0f}", "cu_t": "{:,.0f}", "au_koz": "{:,.1f}"})
    bal = pd.read_csv(OUT / "validation" / "mass_metal_balance.csv")
    bal = bal[["quantity", "unit", "FMS_input", "block_model_grid", "abs_diff_block_vs_input"]].rename(
        columns={"FMS_input": "FMS input", "block_model_grid": "block model", "abs_diff_block_vs_input": "difference"})
    v["TABLE_BALANCE"] = md(bal, "Table 9.1 - FMS mass and metal balance", {"FMS input": "{:,.3f}", "block model": "{:,.3f}", "difference": "{:.1e}"})
    vr = pd.read_csv(OUT / "validation" / "volume_reconciliation.csv")
    v["TABLE_VOLUME"] = md(vr, "Table 9.2 - Volume reconciliation over the record", {"value": "{:,.6g}"})
    fw = fwd.copy()
    v["TABLE_FORWARD"] = md(fw.rename(columns={"w1_m": "W1 (m)", "capture": "capture", "centroid_err_m": "centroid error (m)"}),
                            "Table 9.3 - Forward model: calibration and unseen test periods (means)",
                            {"W1 (m)": "{:.1f}", "capture": "{:.2f}", "centroid error (m)": "{:.1f}"})
    v["TABLE_TWIN"] = md(tw[["method", "blocks", "cu_rmse", "cu_mae", "cu_corr", "au_rmse", "au_corr", "tonnes_corr"]],
                         "Table 9.4 - Synthetic twin: block-level accuracy vs known truth (blocks with > 25 t of true FMS material)",
                         {"cu_rmse": "{:.2f}", "cu_mae": "{:.2f}", "cu_corr": "{:.2f}", "au_rmse": "{:.2f}", "au_corr": "{:.2f}", "tonnes_corr": "{:.2f}"})
    rb = pd.read_csv(OUT / "validation" / "robustness_numerical.csv")
    v["TABLE_ROBUST"] = md(rb[["variant", "total_tonnes", "fms_tonnes", "unattributed_tonnes", "legacy_tonnes", "tracked_blocks_cu_pct",
                               "top_bench_cu_pct", "mean_abs_block_cu_change"]],
                           "Table 9.5 - Robustness to numerical settings",
                           {"total_tonnes": "{:,.0f}", "fms_tonnes": "{:,.0f}", "unattributed_tonnes": "{:,.0f}", "legacy_tonnes": "{:,.0f}",
                            "tracked_blocks_cu_pct": "{:.2f}", "top_bench_cu_pct": "{:.2f}", "mean_abs_block_cu_change": "{:.2f}"})
    m = mc.loc[[r for r in ["total_tonnes", "cu_t", "au_kg", "cu_pct", "au_gpt", "fms_tonnes", "class_fms_cu_pct", "class_fms_au_gpt",
                            "class_t_u", "class_t_l"] if r in mc.index], ["P10", "P50", "P90", "cv"]].reset_index().rename(columns={"index": "quantity"})
    v["TABLE_MC"] = md(m, "Table 10.1 - Monte Carlo summary (60 realisations); class_* rows by information class",
                       {"P10": "{:,.2f}", "P50": "{:,.2f}", "P90": "{:,.2f}", "cv": "{:.3f}"})
    return v


def fill(template: Path, dest: Path, vals: dict):
    txt = template.read_text()
    missing = set(re.findall(r"\{\{(\w+)\}\}", txt)) - set(vals)
    if missing:
        raise KeyError(f"unfilled placeholders: {missing}")
    for k, val in vals.items():
        txt = txt.replace("{{" + k + "}}", str(val))
    dest.write_text(txt)
    print("written", dest.relative_to(ROOT))


if __name__ == "__main__":
    vals = values()
    for t in sorted(TPL.glob("*.template.md")):
        fill(t, ROOT / "docs" / t.name.replace(".template", ""), vals)
