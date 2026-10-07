"""Task 7 - uncertainty (Monte Carlo) and one-at-a-time sensitivity analysis."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import blockmodel as bm
from . import plots as pl
from .config import apply_overrides
from .movement import NP, P, prepare_loads, reconstruct
from .validation import _key_metrics


def monte_carlo(ds_loader, cfg, bg, base_df, out: Path, n=None, verbose=True) -> dict:
    """Joint sampling of measurement errors and model parameters.
    Every realisation is a full reconstruction; block statistics are taken
    on the base block grid."""
    u = cfg["uncertainty"]
    n = n or u["n_realizations"]
    rng = np.random.default_rng(u["seed"])
    ds_cache = {}
    T = np.zeros((n,) + bg.shape)
    CU = np.zeros_like(T)
    AU = np.zeros_like(T)
    TF = np.zeros_like(T)
    rows = []
    cls_tot = []
    t0 = time.time()
    for r in range(n):
        prm = {
            "survey_time": str(rng.choice(u["survey_time_choices"])),
            "epsilon": float(rng.uniform(*u["epsilon_range"])),
            "alpha_up": float(rng.uniform(*u["alpha_range"])),
            "max_push": float(rng.uniform(*u["max_push_range"])),
            "compaction": float(rng.uniform(*u["compaction_range"])),
            "payload_bias": float(rng.normal(0, u["payload_bias_sd"])),
        }
        c2 = apply_overrides(cfg, {"time.survey_time": prm["survey_time"], "movement.epsilon": prm["epsilon"],
                                   "movement.alpha_up": prm["alpha_up"], "movement.max_push": prm["max_push"],
                                   "movement.retain_cost": max(prm["max_push"], cfg["movement"]["retain_cost"]),
                                   "density.compaction_factor": prm["compaction"]})
        c2["_mc_impute"] = True
        if prm["survey_time"] not in ds_cache:
            ds_cache[prm["survey_time"]] = ds_loader(c2)
        ds = ds_cache[prm["survey_time"]]
        loads = prepare_loads(ds, c2, rng=rng, perturb={"gps_sigma": u["gps_sigma"], "payload_cv": u["payload_cv"],
                                                         "payload_bias": prm["payload_bias"], "assay_cv": u["assay_cv"],
                                                         "compaction": prm["compaction"]})
        bias = rng.normal(0, u["survey_bias_sd"], len(ds.surveys) + 1)
        rec = reconstruct(ds, c2, loads=loads, rng=rng, survey_bias=bias)
        a = bm.aggregate(rec, bg)
        T[r] = a[..., P["T_F"]] + a[..., P["T_U"]] + a[..., P["T_L"]]
        CU[r] = a[..., P["CU_F"]] + a[..., P["CU_U"]] + a[..., P["CU_L"]]
        AU[r] = a[..., P["AU_F"]] + a[..., P["AU_U"]] + a[..., P["AU_L"]]
        TF[r] = a[..., P["T_F"]]
        sums = a.reshape(-1, NP).sum(0)
        cls_tot.append({f"{k.lower()}": sums[P[k]] for k in ["T_F", "CU_F", "AU_F", "T_U", "CU_U", "AU_U", "T_L", "CU_L", "AU_L"]})
        df = bm.block_table(rec, bg, a, c2)
        km = _key_metrics(f"mc{r}", rec, df, base_df)
        km.update(prm)
        rows.append(km)
        if verbose and (r + 1) % 5 == 0:
            print(f"    MC {r + 1}/{n}  ({time.time() - t0:.0f} s)")
    real = pd.DataFrame(rows)
    real.to_csv(out / "mc_realizations.csv", index=False)
    with np.errstate(invalid="ignore", divide="ignore"):
        cu = np.where(T > 0, CU / T * 100, np.nan)
        au = np.where(T > 0, AU / T * 1000, np.nan)
    stats = {}
    for name, arr in [("cu", cu), ("au", au), ("tonnes", T), ("t_fms", TF)]:
        stats[name + "_mean"] = np.nanmean(arr, 0)
        stats[name + "_p10"] = np.nanpercentile(arr, 10, axis=0)
        stats[name + "_p50"] = np.nanpercentile(arr, 50, axis=0)
        stats[name + "_p90"] = np.nanpercentile(arr, 90, axis=0)
        stats[name + "_sd"] = np.nanstd(arr, 0)
    # global distributions
    tot = pd.DataFrame({"total_tonnes": T.sum((1, 2, 3)), "cu_t": CU.sum((1, 2, 3)), "au_kg": AU.sum((1, 2, 3)),
                        "fms_tonnes": TF.sum((1, 2, 3))})
    tot["cu_pct"] = tot["cu_t"] / tot["total_tonnes"] * 100
    tot["au_gpt"] = tot["au_kg"] / tot["total_tonnes"] * 1000
    ct = pd.DataFrame(cls_tot)
    for c in ct.columns:
        tot["class_" + c] = ct[c].values
    tot["class_fms_cu_pct"] = tot["class_cu_f"] / tot["class_t_f"] * 100
    tot["class_fms_au_gpt"] = tot["class_au_f"] / tot["class_t_f"] * 1000
    q = tot.quantile([0.1, 0.5, 0.9]).T
    q.columns = ["P10", "P50", "P90"]
    q["mean"] = tot.mean()
    q["cv"] = tot.std() / tot.mean()
    q.to_csv(out / "mc_global_summary.csv")
    return {"realizations": real, "stats": stats, "global": q, "totals": tot}


def attach_block_stats(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    df = df.copy()
    k, j, i = df["iz"].values, df["iy"].values, df["ix"].values
    for key in ["cu_p10", "cu_p50", "cu_p90", "au_p10", "au_p50", "au_p90", "tonnes_p10", "tonnes_p90"]:
        df[key] = stats[key][k, j, i]
    with np.errstate(invalid="ignore", divide="ignore"):
        df["cu_cv"] = stats["cu_sd"][k, j, i] / stats["cu_mean"][k, j, i]
        df["au_cv"] = stats["au_sd"][k, j, i] / stats["au_mean"][k, j, i]
        df["tonnes_cv"] = stats["tonnes_sd"][k, j, i] / stats["tonnes_mean"][k, j, i]
    return df


def apply_prior_ranges(df: pd.DataFrame, loads: pd.DataFrame, min_tracked=0.5) -> pd.DataFrame:
    """Blocks dominated by legacy or unattributed material have an ASSUMED or
    IMPUTED grade; Monte Carlo spread for them only reflects the inputs that
    were perturbed and would understate the real uncertainty. For those blocks
    the grade range is replaced by the load-scale (tonnage-weighted) P10/P90 of
    all FMS loads (a 5x5x2 m block holds ~100 t, i.e. less than one truck load),
    and `grade_range_basis` says which basis applies."""
    df = df.copy()
    w = loads["m"].values

    def wq(x, q):
        o = np.argsort(x)
        c = np.cumsum(w[o]) / w.sum()
        return float(np.interp(q, c, x[o]))
    cu, au = loads["cu"].values, loads["au"].values
    prior = {"cu_p10": wq(cu, 0.1), "cu_p50": wq(cu, 0.5), "cu_p90": wq(cu, 0.9),
             "au_p10": wq(au, 0.1), "au_p50": wq(au, 0.5), "au_p90": wq(au, 0.9)}
    cv_cu = float(np.sqrt(np.average((cu - np.average(cu, weights=w)) ** 2, weights=w)) / np.average(cu, weights=w))
    cv_au = float(np.sqrt(np.average((au - np.average(au, weights=w)) ** 2, weights=w)) / np.average(au, weights=w))
    m = df["frac_fms"] < min_tracked
    df["grade_range_basis"] = np.where(m, "prior: FMS load-scale distribution (grade assumed/imputed)", "Monte Carlo")
    if "cu_p10" in df:
        for k, v in prior.items():
            df.loc[m, k] = v
        df.loc[m, "cu_cv"] = cv_cu
        df.loc[m, "au_cv"] = cv_au
    return df


def sensitivity_oat(ds_loader, cfg, base_df, base_rec, out: Path, verbose=True) -> pd.DataFrame:
    s = cfg["sensitivity"]
    keymap = {"epsilon": "movement.epsilon", "alpha_up": "movement.alpha_up", "max_push": "movement.max_push",
              "compaction_factor": "density.compaction_factor", "sigma_z": "survey.sigma_z",
              "survey_time": "time.survey_time", "cell": "grid.cell",
              "front_unobserved_fill": "infill.front_unobserved_fill"}
    rows = [dict(_key_metrics("base", base_rec, base_df, base_df), parameter="base", level="base", value="")]
    for name, (lo, hi) in s.items():
        for level, val in [("low", lo), ("high", hi)]:
            if name == "block":
                c2 = cfg
                ds = ds_loader(c2)
                rec = base_rec
                bg = bm.make_block_grid(rec, c2, block=val)
            else:
                ov = {keymap[name]: val}
                if name == "max_push":
                    ov["movement.retain_cost"] = max(val, cfg["movement"]["retain_cost"])
                c2 = apply_overrides(cfg, ov)
                ds = ds_loader(c2)
                rec = reconstruct(ds, c2)
                bg = bm.make_block_grid(rec, c2)
            a = bm.aggregate(rec, bg)
            df = bm.block_table(rec, bg, a, c2)
            km = _key_metrics(f"{name}_{level}", rec, df, base_df if name != "block" else None)
            km.update(parameter=name, level=level, value=str(val))
            rows.append(km)
            if verbose:
                print(f"    OAT {name} {level}={val}")
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "sensitivity_oat.csv", index=False)
    _tornado(tab, out)
    return tab


def _tornado(tab, out):
    import matplotlib.pyplot as plt
    base = tab[tab.parameter == "base"].iloc[0]
    metrics = [("top_bench_cu_pct", "Cu grade of top bench (>4484 m), %"),
               ("tracked_blocks_cu_pct", "Cu grade of FMS-tracked blocks, %"),
               ("total_tonnes", "Total modelled tonnes"),
               ("mean_abs_block_cu_change", "Mean |block Cu change| vs base, % Cu")]
    fig, axs = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (m, lab) in zip(axs.flat, metrics):
        d = tab[tab.parameter != "base"].pivot(index="parameter", columns="level", values=m)
        if m == "mean_abs_block_cu_change":
            b = 0.0
        else:
            b = base[m]
        lo = d["low"] - b
        hi = d["high"] - b
        rng_ = (np.abs(lo).fillna(0) + np.abs(hi).fillna(0))
        order = rng_.sort_values().index
        y = np.arange(len(order))
        ax.barh(y - 0.18, lo[order], height=0.34, color=pl.CAT[0], label="low value")
        ax.barh(y + 0.18, hi[order], height=0.34, color=pl.CAT[1], label="high value")
        ax.set_yticks(y)
        ax.set_yticklabels(order)
        ax.axvline(0, color=pl.INK, lw=0.8)
        ax.set_title(lab + (f" (base {b:,.2f})" if m != "mean_abs_block_cu_change" else ""), loc="left", fontsize=9.5)
        ax.set_xlabel("change from base")
    axs[0, 0].legend(loc="lower right")
    fig.suptitle("One-at-a-time sensitivity (tornado)", x=0.01, ha="left", fontsize=11, fontweight="bold")
    pl.save(fig, out / "fig_sens_tornado.png")


def mc_figures(mc, base_df, out: Path):
    import matplotlib.pyplot as plt
    tot = mc["totals"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
    for ax, (col, lab, sc) in zip(axs, [("total_tonnes", "total modelled tonnes (kt)", 1e-3), ("cu_t", "contained Cu (kt)", 1e-3),
                                         ("au_kg", "contained Au (koz)", 1 / 31.1035)]):
        v = tot[col] * sc
        ax.hist(v, bins=15, color=pl.CAT[0])
        for p, ls in [(10, ":"), (50, "-"), (90, ":")]:
            ax.axvline(np.percentile(v, p), color=pl.INK, lw=1, ls=ls)
        ax.set_title(lab + f"\nP10 {np.percentile(v, 10):,.1f}  P50 {np.percentile(v, 50):,.1f}  P90 {np.percentile(v, 90):,.1f}", loc="left", fontsize=9)
    pl.save(fig, out / "fig_unc_global_histograms.png")
    real = mc["realizations"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
    for ax, (x, lab) in zip(axs, [("epsilon", "mixing length ε (m)"), ("compaction", "compaction factor κ"), ("max_push", "max push (m)")]):
        ax.scatter(real[x], real["top_bench_cu_pct"], s=14, color=pl.CAT[0])
        ax.set_xlabel(lab)
        ax.set_ylabel("top-bench Cu (%)")
    fig.suptitle("Monte Carlo: top-bench Cu grade vs sampled parameters", x=0.01, ha="left", fontsize=10)
    pl.save(fig, out / "fig_unc_param_scatter.png")
