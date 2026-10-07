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
        "repose": "qaqc/fig_qaqc_repose.png",
    }.items():
        p = (OUT / rel).resolve()
        if p.exists():
            w, h = Image.open(p).size
            figs[name] = {"path": str(p), "w": w, "h": h}
    best_align = al.loc[al["pearson_r"].idxmax()]
    morning = al[al["survey_time"] <= "10:00"]["pearson_r"].max()
    data = {
        "k": k, "repose": q["repose"], "base": q["base_plane"],
        "n_sig": q["n_grade_signatures"], "payload38": q["payload_multiple_of_38_frac"],
        "align_best": best_align["survey_time"], "align_r": float(best_align["pearson_r"]), "align_morning_r": float(morning),
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
