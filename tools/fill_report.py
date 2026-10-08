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
    body = "\n".join("| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |" for r in d.values)
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
        "TW_E15": f"{twi.loc['CPST eps=15 m', 'cu_rmse']:.2f}" if "CPST eps=15 m" in twi.index else "n/a",
        "PRIOR_CU": f"{wq(loads['cu'].values, 0.1):.1f}-{wq(loads['cu'].values, 0.9):.1f}",
        "AU3_F": f"{F.au_gpt:.3f}", "AU3_U": f"{U.au_gpt:.3f}", "AU3_L": f"{L.au_gpt:.3f}",
        "UNATT_VOL": f"{S['key_results']['unattributed_volume_m3']:,.0f}",
        "FWD_U": f"{ft.loc['uniform baseline', 'w1_m']:.1f}" if "uniform baseline" in ft.index else "n/a",
        "CUT_F": f"{F.cu_t:,.0f}", "AUK_F": f"{F.au_kg / 31.1035:,.1f}", "CUT_U": f"{U.cu_t:,.0f}", "AUK_U": f"{U.au_kg / 31.1035:,.1f}",
    }
    k = S["key_results"]
    rp_t, rp_cu, rp_au = F.tonnes + U.tonnes, F.cu_t + U.cu_t, F.au_kg + U.au_kg
    v.update({"T_RP": f"{rp_t:,.0f}", "CU_RP": f"{rp_cu / rp_t * 100:.2f}", "AU_RP": f"{rp_au / rp_t * 1000:.2f}",
              "CUT_RP": f"{rp_cu:,.0f}", "AUK_RP": f"{rp_au / 31.1035:,.1f}", "RP_FMS_SHARE": f"{F.tonnes / rp_t:.0%}"})
    if "record_period_tonnes" in mc.index:
        v["MC_RP"] = " / ".join(f"{x / 1000:,.1f}" for x in mc.loc["record_period_tonnes", ["P10", "P50", "P90"]])
        v["MC_RP_RANGE"] = "-".join(f"{x / 1000:,.1f}" for x in mc.loc["record_period_tonnes", ["P10", "P90"]])
        v["MC_RP_CU"] = " / ".join(f"{x / 1000:,.2f}" for x in mc.loc["record_period_cu_t", ["P10", "P50", "P90"]])
    # volume factor (A-06)
    vf = pd.read_csv(OUT / "growth" / "volume_factor_summary.csv", index_col=0).iloc[:, 0]
    fv = float(vf["f_v"])
    v.update({"F_V": f"{fv:.3f}", "F_V_P10": f"{float(vf['f_v_p10']):.2f}", "F_V_P90": f"{float(vf['f_v_p90']):.2f}",
              "HO_MAE": f"{float(vf['holdout_mae_fv']):.1%}", "HO_CONST": f"{float(vf['holdout_mae_const_density']):.1%}",
              "HO_DENS": f"{float(vf['holdout_mae_dens_as_inpile']):.0%}", "LOO": f"{float(vf['loo_mae']):.1%}",
              "RHO_PILE": f"{float(vf['in_pile_density_base']):.2f}", "X2_SHARE": f"{1 - 1 / fv:.0%}"})
    vt = pd.read_csv(OUT / "growth" / "volume_factor_calibration.csv")
    if "survey_date" not in vt:                       # outputs from before the column existed
        vt["survey_date"] = (pd.to_datetime(vt["end"]) - pd.Timedelta(hours=31)).dt.strftime("%Y-%m-%d")
    v.update({"FILL_VOL": f"{vt['fill_m3'].sum():,.0f}", "CUT_VOL": f"{vt['cut_m3'].sum():,.0f}", "NET_VOL": f"{vt['net_m3'].sum():,.0f}",
              "VDENS": f"{vt['vdens_m3'].sum():,.0f}",
              "UNATT_SHARE": f"{k['unattributed_volume_m3'] / vt['fill_m3'].sum():.0%}"})
    vtt = pd.DataFrame({"interval": vt["interval"], "survey (D)": vt["survey_date"].str[5:], "fill m³": vt["fill_m3"], "cut m³": vt["cut_m3"],
                        "net fill m³": vt["net_m3"], "FMS t": vt["fms_t"], "Σ T/Dens m³": vt["vdens_m3"],
                        "longest FMS silence (h)": vt["longest_fms_silence_h"], "ratio": vt["ratio"],
                        "used for f_v": np.where(vt["consistent"], "yes", "no (FMS gap)"), "role in hold-out": vt["role"],
                        "hold-out error": np.where(vt["role"] == "held-out", vt["err_fv_first_half"], np.nan)})
    v["TABLE_VF"] = md(vtt, "Volume budget per survey interval (interval of survey D ends at D+1 07:00)",
                       {"fill m³": "{:,.0f}", "cut m³": "{:,.0f}", "net fill m³": "{:,.0f}", "FMS t": "{:,.0f}", "Σ T/Dens m³": "{:,.0f}",
                        "longest FMS silence (h)": "{:.0f}", "ratio": "{:.2f}", "hold-out error": "{:+.1%}"})
    # survey cut-off scan (A-05)
    al = pd.read_csv(OUT / "growth" / "temporal_alignment.csv").set_index("cutoff_hours")
    v.update({"R_31": f"{al.loc[31.0, 'r_daily']:.3f}", "RCV_31": f"{al.loc[31.0, 'ratio_rcv_daily']:.2f}",
              "R_24": f"{al.loc[24.0, 'r_daily']:.3f}", "RCV_24": f"{al.loc[24.0, 'ratio_rcv_daily']:.2f}"})
    sel = al.loc[[h for h in [0, 6, 12, 18, 21, 24, 27, 29, 30, 31, 31.5, 32, 34, 36] if h in al.index]].reset_index()
    sel = sel[["cutoff_hours", "clock_time", "r_daily", "ratio_rcv_daily", "r_all", "loads_after_last_survey"]].rename(columns={
        "cutoff_hours": "cut-off (h after 00:00 of D)", "clock_time": "clock time", "r_daily": "r (consecutive-day intervals)",
        "ratio_rcv_daily": "robust CV of ratio", "r_all": "r (all intervals after the first)", "loads_after_last_survey": "loads after last survey"})
    v["TABLE_CUTOFF"] = md(sel, "Survey cut-off scan (selected rows of outputs/growth/temporal_alignment.csv)",
                           {"cut-off (h after 00:00 of D)": "{:g}", "r (consecutive-day intervals)": "{:.3f}", "robust CV of ratio": "{:.2f}",
                            "r (all intervals after the first)": "{:.3f}"})
    # QA rule catalogue
    cat = pd.read_csv(OUT / "qaqc" / "qa_rule_catalogue.csv").fillna({"items": ""})
    v["QA_N_RULES"] = str(len(cat))
    v["QA_N_TRIG"] = str(int((cat["count"] > 0).sum()))
    ct = cat[["rule_id", "level", "severity", "count", "tonnes", "items", "treatment"]].copy()
    ct["tonnes"] = ct["tonnes"].where(ct["level"] == "record")
    ct["items"] = ct["items"].map(lambda x: x if len(str(x)) <= 90 else str(x)[:87] + "...")
    v["TABLE_QA_CAT"] = md(ct, "QA rule catalogue (counts from the run; tonnes for record rules)", {"count": "{:,.0f}", "tonnes": "{:,.0f}"})
    trig = ct[ct["count"] > 0].drop(columns=["treatment"])
    v["TABLE_QA_TRIG"] = md(trig, "Table 4.1 - QA rules triggered by the supplied data (full catalogue in D2)", {"count": "{:,.0f}", "tonnes": "{:,.0f}"})
    # volume-gap scenarios
    sc = pd.read_csv(OUT / "uncertainty" / "scenarios.csv").set_index("scenario")
    s0 = sc.loc["S0", "record_period_tonnes"]
    v.update({"X2_RP": f"{sc.loc['X2', 'record_period_tonnes']:,.0f}", "X2_UPLIFT": f"{sc.loc['X2', 'record_period_tonnes'] / s0 - 1:.0%}",
              "S1_UPLIFT": f"{sc.loc['S1', 'record_period_tonnes'] / s0 - 1:.0%}", "X2_TOT": f"{sc.loc['X2', 'total_tonnes']:,.0f}",
              "S2_SHIFT": f"{(sc.loc['S2', 'unattributed_tonnes'] - sc.loc['S0', 'unattributed_tonnes']) / 1000:,.0f}"})
    st_ = sc.reset_index()[["scenario", "status", "volume_factor", "payload_factor", "in_pile_density_t_m3", "largest_load_t", "fms_tonnes",
                            "unattributed_tonnes", "record_period_tonnes", "record_period_cu_t", "pre_record_tonnes", "total_tonnes", "description"]]
    st_ = st_.rename(columns={"volume_factor": "f_v", "payload_factor": "f_pay", "in_pile_density_t_m3": "in-pile t/m³",
                              "largest_load_t": "largest load t", "fms_tonnes": "FMS t", "unattributed_tonnes": "unattributed t",
                              "record_period_tonnes": "record-period t", "record_period_cu_t": "record-period Cu t",
                              "pre_record_tonnes": "pre-record core t", "total_tonnes": "whole pile t"})
    v["TABLE_SCEN"] = md(st_, "Table 10.2 - Interpretations of the volume gap (outputs/uncertainty/scenarios.csv)",
                         {"f_v": "{:.3f}", "f_pay": "{:.2f}", "in-pile t/m³": "{:.2f}", "largest load t": "{:,.0f}", "FMS t": "{:,.0f}",
                          "unattributed t": "{:,.0f}", "record-period t": "{:,.0f}", "record-period Cu t": "{:,.0f}",
                          "pre-record core t": "{:,.0f}", "whole pile t": "{:,.0f}"})
    # one-at-a-time sensitivity of the survey cut-off
    so = pd.read_csv(OUT / "uncertainty" / "sensitivity_oat.csv")
    b0 = so.loc[so["parameter"] == "base", "record_period_tonnes"].iloc[0]
    sc_ = so[so["parameter"] == "survey_cutoff_hours"]
    ch = (sc_["record_period_tonnes"] / b0 - 1).abs()
    v.update({"CUT_SENS_T": f"{ch.min():.0%}-{ch.max():.0%}", "CUT_SENS_CU": f"{sc_['mean_abs_block_cu_change'].max():.2f}"})
    # push distances
    dst = pd.read_csv(OUT / "movement" / "load_destinations.csv")
    dl = dst[dst["kind"] == "load"]
    v.update({"PUSH_P50": f"{np.nanmedian(dl['mean_push']):.0f}", "PUSH_P90": f"{np.nanpercentile(dl['mean_push'].dropna(), 90):.0f}",
              "SPREAD_P50": f"{2 * np.nanmedian(dl['spread']):.0f}"})
    # cross-implementation check (B's values quoted from its report, not re-run)
    cq = cat.set_index("rule_id")
    rows = [
        ["Survey cut-off", "D+1 07:00 (scan plateau 30-31.5 h)", "D+1 07:00 (scan peak about 30 h)"],
        ["Fill / revealed cut / net fill (m³)", f"{vt['fill_m3'].sum():,.0f} / {vt['cut_m3'].sum():,.0f} / {vt['net_m3'].sum():,.0f}", "35,107 / 583 / 34,627"],
        ["Volume factor f_v", f"{fv:.3f}", "1.476"],
        ["Intervals used for f_v", " ".join(str(i) for i in vt.loc[vt['consistent'], 'interval']), "1 2 3 4 5 6 8"],
        ["Hold-out error (first half predicts second)", f"{float(vf['holdout_mae_fv']):.1%}", "3.2%"],
        ["Unattributed volume (m³) and intervals", f"{k['unattributed_volume_m3']:,.0f} (" + ", ".join(
            str(int(i)) for i in pd.read_csv(OUT / 'growth' / 'period_reconciliation.csv').query('unattributed_volume > 1')['period']) + ")",
         "2,431 (0, 7, 8, 9)"],
        ["Record-period tonnes, base case", f"{rp_t:,.0f}", "47,600"],
        ["Record-period contained Cu (t), base case", f"{rp_cu:,.0f}", "4,062"],
        ["FMS material if Dens is the in-pile density (t)", f"{sc.loc['X1', 'fms_tonnes']:,.0f} (X1)", "65,600 (reported outside its ranges)"],
        ["LOC_DEFAULT records / t", f"{int(cq.loc['LOC_DEFAULT', 'count'])} / {cq.loc['LOC_DEFAULT', 'tonnes']:,.0f}", "14 / 2,356"],
        ["LOC_OUTSIDE_SURVEYS records / t", f"{int(cq.loc['LOC_OUTSIDE_SURVEYS', 'count'])} / {cq.loc['LOC_OUTSIDE_SURVEYS', 'tonnes']:,.0f}", "58 / 9,462"],
        ["LOC_Z_INCONSISTENT / TIME_AFTER_LAST_SURVEY", f"{int(cq.loc['LOC_Z_INCONSISTENT', 'count'])} / {int(cq.loc['TIME_AFTER_LAST_SURVEY', 'count'])}", "2 / 1"],
        ["PAYLOAD_PARTIAL / PAYLOAD_HIGH", f"{int(cq.loc['PAYLOAD_PARTIAL', 'count'])} / {int(cq.loc['PAYLOAD_HIGH', 'count'])}", "3 / 3"],
        ["DXF header units", "$INSUNITS = 1 (inches) in all files; ignored", "$INSUNITS = 1 in all files; ignored"],
        ["Forward model, held-out earth-mover distance: push / no push / uniform (m)",
         f"{v['FWD_P']} / {v['FWD_B']} / {v['FWD_U']}", "12.2 / 14.5 / 27.9"],
        ["Block size", "5 × 5 × 2 m", "2 × 2 × 1 m"],
        ["Automated tests", "66", "65"],
    ]
    v["TABLE_XIMPL"] = md(pd.DataFrame(rows, columns=["quantity", "A (this platform, v2.0)", "B (independent implementation)"]),
                          "Table 9.7 - Cross-implementation comparison (B's values from its own report)")
    # ------------------------------------------------------------ tables
    src = pd.read_csv(OUT / "blockmodel" / "summary_by_material_source.csv", index_col=0)["tonnes"]
    tf_r, tf_p = src.iloc[0], src.iloc[1]
    rows = [["FMS-tracked, survey-reconciled", tf_r, "measured inputs; location model-generated"],
            ["FMS-tracked, provisional (after last survey)", tf_p, "measured inputs; location from forward model"],
            ["Unattributed (surveyed volume, no FMS record)", U.tonnes, "imputed (same/adjacent intervals)"],
            ["**Record-period total**", F.tonnes + U.tonnes, ""],
            ["Pre-record core (legacy)", L.tonnes, "assumed (FMS mean); geometry inferred"],
            ["Whole pile modelled", T.tonnes, ""]]
    ti = pd.DataFrame(rows, columns=["class", "tonnes", "basis of grade"])
    ti["share"] = ti["tonnes"] / T.tonnes
    rcu, rau = F.cu_t + U.cu_t, F.au_kg + U.au_kg
    rt = F.tonnes + U.tonnes
    ti["Cu %"] = [F.cu_pct, np.nan, U.cu_pct, rcu / rt * 100, L.cu_pct, T.cu_pct]
    ti["Au g/t"] = [F.au_gpt, np.nan, U.au_gpt, rau / rt * 1000, L.au_gpt, T.au_gpt]
    ti["Cu (t)"] = [F.cu_t, np.nan, U.cu_t, rcu, L.cu_t, T.cu_t]
    ti["Au (koz)"] = [F.au_kg / 31.1035, np.nan, U.au_kg / 31.1035, rau / 31.1035, L.au_kg / 31.1035, T.au_kg / 31.1035]
    v["TABLE_INV"] = md(ti[["class", "tonnes", "share", "Cu %", "Au g/t", "Cu (t)", "Au (koz)", "basis of grade"]],
                        "Inventory by information class (FMS grades/metal shown for the whole FMS class)",
                        {"tonnes": "{:,.0f}", "share": "{:.1%}", "Cu %": "{:.2f}", "Au g/t": "{:.2f}", "Cu (t)": "{:,.0f}", "Au (koz)": "{:,.1f}"})
    v["N_BLOCKS"] = f"{len(bm):,}"
    trk = bm[(bm["frac_fms"] >= 0.5) & bm["cu_cv"].notna()]
    v["BLK_CV_P50"] = f"{trk['cu_cv'].median():.0%}" if len(trk) else "n/a"
    v["BLK_CV_P90"] = f"{trk['cu_cv'].quantile(0.9):.0%}" if len(trk) else "n/a"
    flags = pd.read_csv(OUT / "qaqc" / "fms_flag_summary.csv")
    v["TABLE_FLAGS"] = md(flags, "FMS record rules (records retained; treatment as stated)", {"records": "{:,.0f}", "tonnes": "{:,.0f}"})
    p = pd.read_csv(OUT / "growth" / "period_reconciliation.csv", parse_dates=["end"])
    dmap = dict(zip(vt["survey"], vt["survey_date"].str[5:]))
    cons = set(vt.loc[vt["consistent"], "interval"])
    v["UNATT_NONGAP"] = f"{p.loc[p['period'].isin(cons), 'unattributed_volume'].sum():,.0f}"
    pt = pd.DataFrame({"survey (D)": p["survey"].map(dmap), "gap": np.where(p["gap_detected"], "yes", ""),
                       "loads": p["n_loads"], "FMS t": p["fms_tonnes"], "FMS m³": p["fms_volume"] + p["carried_in_volume"],
                       "solid m³": p["solid_volume"], "fill m³": p["fill_volume"], "cut m³": p["cut_volume"],
                       "unattributed m³": p["unattributed_volume"], "retained m³": p["retained_volume"],
                       "FMS explains": p["fms_explains_frac"], "FMS Cu %": p["fms_cu_pct"], "FMS Au g/t": p["fms_au_gpt"]})
    v["TABLE_PERIODS"] = md(pt, "Table 5.2 - Interval reconciliation in the base case (FMS m³ = in-pile volume T·f_v/Dens, including volume carried over from the previous interval)",
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
    vr["item"] = vr["item"].replace({
        "FMS volume (tonnes / density) (m3)": "FMS in-pile volume, T × f_v / Dens (m3)",
        "FMS volume placed into observed fill (m3)": "volume placed into observed fill from loads, carried parcels and cuts (m3)"})
    v["TABLE_VOLUME"] = md(vr, "Table 9.2 - Volume reconciliation over the record", {"value": "{:,.6g}"})
    fw = fwd.copy()
    v["TABLE_FORWARD"] = md(fw.rename(columns={"w1_m": "W1 (m)", "capture": "capture", "centroid_err_m": "centroid error (m)"}),
                            "Table 9.3 - Forward model: calibration and unseen test periods (means)",
                            {"W1 (m)": "{:.1f}", "capture": "{:.2f}", "centroid error (m)": "{:.1f}"})
    v["TABLE_TWIN"] = md(tw[["method", "blocks", "cu_rmse", "cu_mae", "cu_corr", "au_rmse", "au_corr", "tonnes_corr"]],
                         "Table 9.4 - Synthetic twin: block-level accuracy vs known truth (blocks with > 25 t of true FMS material)",
                         {"cu_rmse": "{:.2f}", "cu_mae": "{:.2f}", "cu_corr": "{:.2f}", "au_rmse": "{:.2f}", "au_corr": "{:.2f}", "tonnes_corr": "{:.2f}"})
    ta = pd.read_csv(OUT / "validation" / "twin_alternative_truths.csv")
    v["TABLE_TWIN_ALT"] = md(ta[["truth", "method", "blocks", "cu_rmse", "cu_corr", "au_rmse"]],
                             "Table 9.5 - Twin stress tests: truth generated with placement rules CPST does not assume",
                             {"cu_rmse": "{:.2f}", "cu_corr": "{:.2f}", "au_rmse": "{:.2f}"})
    tai = ta.set_index(["truth", "method"])
    rc = "random-crest (dump position uninformative)"
    v["TWA_RC_CPST"] = f"{tai.loc[(rc, 'CPST eps=6 m (base)'), 'cu_rmse']:.2f}"
    v["TWA_RC_R"] = f"{tai.loc[(rc, 'CPST eps=6 m (base)'), 'cu_corr']:.2f}"
    v["TWA_RC_PA"] = f"{tai.loc[(rc, 'Baseline: period-average (eps=1e4)'), 'cu_rmse']:.2f}"
    v["TWA_RC_GM"] = f"{tai.loc[(rc, 'Reference: global mean grade'), 'cu_rmse']:.2f}"
    pu = "period-uniform mixing"
    v["TWA_PU_CPST"] = f"{tai.loc[(pu, 'CPST eps=6 m (base)'), 'cu_rmse']:.2f}"
    v["TWA_PU_PA"] = f"{tai.loc[(pu, 'Baseline: period-average (eps=1e4)'), 'cu_rmse']:.2f}"
    rb = pd.read_csv(OUT / "validation" / "robustness_numerical.csv")
    v["TABLE_ROBUST"] = md(rb[["variant", "total_tonnes", "fms_tonnes", "unattributed_tonnes", "legacy_tonnes", "tracked_blocks_cu_pct",
                               "top_bench_cu_pct", "mean_abs_block_cu_change"]],
                           "Table 9.6 - Robustness to numerical settings",
                           {"total_tonnes": "{:,.0f}", "fms_tonnes": "{:,.0f}", "unattributed_tonnes": "{:,.0f}", "legacy_tonnes": "{:,.0f}",
                            "tracked_blocks_cu_pct": "{:.2f}", "top_bench_cu_pct": "{:.2f}", "mean_abs_block_cu_change": "{:.2f}"})
    m = mc.loc[[r for r in ["record_period_tonnes", "record_period_cu_t", "record_period_au_kg", "fms_tonnes", "class_t_u", "class_fms_cu_pct",
                            "class_fms_au_gpt", "class_t_l", "total_tonnes", "cu_t", "au_kg", "cu_pct", "au_gpt"] if r in mc.index],
               ["P10", "P50", "P90", "cv"]].reset_index().rename(columns={"index": "quantity"})
    v["TABLE_MC"] = md(m, "Table 10.1 - Monte Carlo summary (60 realisations): record-period rows first; class_t_l = pre-record core",
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
        dest = ROOT if t.name.startswith("README") else ROOT / "docs"
        fill(t, dest / t.name.replace(".template", ""), vals)
