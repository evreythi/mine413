"""Collect numbers/figures from outputs/ and build docs/build/D7_Presentation.pptx
with pptxgenjs (tools/deck.js).   python tools/make_presentation.py"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def _flat_block_change() -> float:
    so = pd.read_csv(OUT / "uncertainty" / "sensitivity_oat.csv")
    fl = so[(so["parameter"] == "cost") & (so["value"] == "flat")]
    return float(fl["mean_abs_block_cu_change"].iloc[0]) if len(fl) else float("nan")


def _ximpl_rows(k, vf, cat, fwd) -> list:
    """Key rows of D6 Table 9.7 (B's values quoted from its own report)."""
    c = cat.set_index("rule_id")
    ft = fwd[fwd["set"].str.startswith("test")].set_index("mode")["w1_m"]
    return [
        ["Survey cut-off", "D+1 07:00", "D+1 07:00"],
        ["Volume factor f_v", f"{float(vf['f_v']):.3f}", "1.476"],
        ["Intervals used for f_v", " ".join(str(i) for i in k["volume_factor_consistent_intervals"]), "1 2 3 4 5 6 8"],
        ["Hold-out error", f"{float(vf['holdout_mae_fv']):.1%}", "3.2%"],
        ["Unattributed volume (m³)", f"{k['unattributed_volume_m3']:,.0f}", "2,431"],
        ["Record-period tonnes", f"{k['tonnes_record_period']:,.0f}", "47,600"],
        ["Record-period Cu (t)", f"{k['cu_t_record_period']:,.0f}", "4,062"],
        ["LOC_DEFAULT records / t", f"{int(c.loc['LOC_DEFAULT', 'count'])} / {c.loc['LOC_DEFAULT', 'tonnes']:,.0f}", "14 / 2,356"],
        ["Forward EMD push / no push / uniform (m)", f"{ft['push (calibrated)']:.1f} / {ft['no-push baseline']:.1f} / {ft['uniform baseline']:.1f}", "12.2 / 14.5 / 27.9"],
        ["Block size", "5 × 5 × 2 m", "2 × 2 × 1 m"],
    ]


def build() -> Path:
    S = json.loads((OUT / "summary.json").read_text())
    k = S["key_results"]
    q = S["qaqc"]
    inv = pd.read_csv(OUT / "validation" / "inventory_by_class.csv")
    per = pd.read_csv(OUT / "growth" / "period_reconciliation.csv", parse_dates=["end"])
    conf = pd.read_csv(OUT / "blockmodel" / "summary_by_confidence.csv").set_index("confidence")
    fwd = pd.read_csv(OUT / "validation" / "forward_temporal_summary.csv")
    twin = pd.read_csv(OUT / "validation" / "twin_experiment.csv")
    mc = pd.read_csv(OUT / "uncertainty" / "mc_global_summary.csv", index_col=0)
    geo = pd.read_csv(OUT / "validation" / "geometry_check.csv", index_col=0).iloc[:, 0]
    al = pd.read_csv(OUT / "growth" / "temporal_alignment.csv")
    figs = {}
    for name, rel in {
        "solids": "qaqc/fig_qaqc_survey_solids.png", "dumpmap": "qaqc/fig_qaqc_dump_map.png",
        "daily": "qaqc/fig_qaqc_daily_tonnage_volume.png", "align": "growth/fig_temporal_alignment.png",
        "advance": "growth/fig_growth_face_advance.png", "periodmaps": "growth/fig_growth_period_maps.png",
        "algo": "../docs/figures/fig_algorithm.png", "workflow": "../docs/figures/fig_workflow.png",
        "plans": "blockmodel/fig_bm_plans_cu_pct.png", "sections": "blockmodel/fig_bm_sections_cu_pct.png",
        "view3d": "blockmodel/fig_bm_3d_cu_pct.png", "classes": "blockmodel/fig_bm_information_class.png",
        "confidence": "blockmodel/fig_bm_confidence.png", "fwdtest": "validation/fig_val_forward_test.png",
        "twin": "validation/fig_val_twin_scatter.png", "tornado": "uncertainty/fig_sens_tornado.png",
        "mchist": "uncertainty/fig_unc_global_histograms.png", "uncmap": "uncertainty/fig_unc_block_maps.png",
        "geometry": "validation/fig_val_geometry.png", "push": "growth/fig_growth_push_distance.png",
        "repose": "qaqc/fig_qaqc_repose.png", "volfac": "growth/fig_volume_factor.png",
        "scen": "uncertainty/fig_scenarios.png", "mcscatter": "uncertainty/fig_unc_param_scatter.png",
    }.items():
        p = (OUT / rel).resolve()
        if p.exists():
            w, h = Image.open(p).size
            figs[name] = {"path": str(p), "w": w, "h": h}
    al = al.set_index("cutoff_hours")
    vf = pd.read_csv(OUT / "growth" / "volume_factor_summary.csv", index_col=0).iloc[:, 0]
    scen = pd.read_csv(OUT / "uncertainty" / "scenarios.csv")
    cat = pd.read_csv(OUT / "qaqc" / "qa_rule_catalogue.csv")
    data = {
        "k": k, "repose": q["repose"], "base": q["base_plane"],
        "n_sig": q["n_grade_signatures"], "payload38": q["payload_multiple_of_38_frac"],
        "align_best": float(al["r_daily"].idxmax()), "align_r": float(al.loc[31.0, "r_daily"]), "align_r24": float(al.loc[24.0, "r_daily"]),
        "align_rcv": float(al.loc[31.0, "ratio_rcv_daily"]), "align_rcv24": float(al.loc[24.0, "ratio_rcv_daily"]),
        "vf": {k_: (float(v_) if k_ not in ("consistent_intervals", "excluded_intervals") else v_) for k_, v_ in vf.items()},
        "scen": scen.to_dict("records"),
        "qa": {"n_rules": int(len(cat)), "n_trig": int((cat["count"] > 0).sum())},
        "flat_blk": _flat_block_change(),
        "ximpl": _ximpl_rows(k, vf, cat, fwd),
        "inv": inv.to_dict("records"),
        "periods": [{"label": f"{e:%m-%d}" + ("*" if g else ""), "fill": float(f), "fms": float(v + c), "unatt": float(u)}
                    for e, g, f, v, c, u in zip(per["end"], per["gap_detected"], per["fill_volume"], per["fms_volume"],
                                                per["carried_in_volume"], per["unattributed_volume"])],
        "conf": {c: float(conf.loc[c, "tonnes"]) if c in conf.index else 0.0 for c in ["High", "Medium", "Low", "Uninformed"]},
        "fwd": fwd.to_dict("records"), "twin": twin.to_dict("records"),
        "mc": {r: mc.loc[r, ["P10", "P50", "P90"]].tolist() for r in mc.index},
        "geo": {k2: float(v) for k2, v in geo.items()},
        "figs": figs,
        "out": str(ROOT / "docs" / "build" / "D7_Presentation.pptx"),
        "team": __import__("yaml").safe_load((ROOT / "config" / "team.yaml").read_text()),
        "twin_alt": pd.read_csv(OUT / "validation" / "twin_alternative_truths.csv").to_dict("records"),
    }
    jp = ROOT / "tools" / "_deck_data.json"
    def clean(o):
        if isinstance(o, dict):
            return {k_: clean(v_) for k_, v_ in o.items()}
        if isinstance(o, list):
            return [clean(v_) for v_ in o]
        if isinstance(o, float) and o != o:
            return None
        return o
    jp.write_text(json.dumps(clean(data), indent=1, default=float))
    subprocess.run(["node", str(ROOT / "tools" / "deck.js"), str(jp)], check=True, cwd=ROOT / "tools")
    jp.unlink()
    return Path(data["out"])


if __name__ == "__main__":
    print(build())
