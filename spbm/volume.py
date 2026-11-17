"""A-06: volume conversion between FMS tonnes and surveyed volume.

For every survey interval k:

    N_k  = measured net fill  = CPST fill - inferred toe fill (A-13b) - cut
    V_k  = sum over the interval's loads of  T_i / Dens_i   (recorded tonnes,
           FMS density)
    r_k  = N_k / V_k

On intervals whose FMS and survey records are both complete, r_k is a
consistent 1.4-1.6; intervals with FMS outages are far higher (missing
records). The volume factor f_v is the pooled ratio over the internally
consistent intervals (robust exclusion: |r - median| > k * 1.4826 * MAD),
with a bootstrap distribution and two hold-out tests (first-half calibration
predicting the second half; leave-one-out).

f_v is identifiable from the data. How it splits between bulking (in-pile
density below Dens) and systematic payload under-recording is NOT: the
platform carries the split as `payload_factor` (f_pay), with in-pile
density = Dens * f_pay / f_v.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import plots as pl
from .config import apply_overrides

_CACHE: dict = {}


def interval_budget(ds, cfg) -> pd.DataFrame:
    """Geometry pass (f_v = 1): per-interval measured net fill and FMS volume."""
    from .movement import reconstruct
    c = apply_overrides(cfg, {"density.volume_factor": 1.0, "density.payload_factor": 1.0})
    rec = reconstruct(ds, c)
    p = rec.periods
    L = rec.loads
    t = pd.DataFrame({"interval": p["period"], "survey": p["survey"], "end": p["end"],
                      "solid_m3": p["solid_volume"], "fill_m3": p["fill_volume"],
                      "inferred_toe_fill_m3": p["unobserved_fill_new_cells"], "cut_m3": p["cut_volume"]})
    t.insert(2, "survey_date", t["survey"].map(dict(zip(ds.register["file"], pd.to_datetime(ds.register["assigned_date"]).dt.strftime("%Y-%m-%d")))))
    t["net_m3"] = t["fill_m3"] - t["inferred_toe_fill_m3"] - t["cut_m3"]
    vd = L.assign(vd=L["m_recorded"] / L["dens_fms"])
    t["fms_t"] = t["interval"].map(vd.groupby("period")["m_recorded"].sum()).fillna(0.0)
    t["vdens_m3"] = t["interval"].map(vd.groupby("period")["vd"].sum()).fillna(0.0)
    t["n_loads"] = t["interval"].map(vd.groupby("period").size()).fillna(0).astype(int)
    # FMS coverage evidence: longest silence inside the interval (h)
    starts = [None] + list(p["end"][:-1])
    sil = []
    for k, (a, b) in enumerate(zip(starts, p["end"])):
        a = b - pd.Timedelta(hours=float(cfg["time"].get("first_interval_hours", 24.0))) if a is None else a
        tt = np.sort(L.loc[L["period"] == k, "time"].values.astype("datetime64[ns]"))
        pts = np.r_[np.datetime64(a), tt, np.datetime64(b)]
        sil.append(float(np.max(np.diff(pts)).astype("timedelta64[m]").astype(float) / 60.0))
    t["longest_fms_silence_h"] = sil
    t["ratio"] = t["net_m3"] / t["vdens_m3"].replace(0, np.nan)
    return t


def robust_factor(t: pd.DataFrame, k_mad: float) -> dict:
    r = t["ratio"]
    ok0 = r.notna() & (t["vdens_m3"] > 0)
    med = float(np.median(r[ok0]))
    sd = 1.4826 * float(np.median(np.abs(r[ok0] - med)))
    ok = ok0 & (np.abs(r - med) <= k_mad * max(sd, 1e-9))
    f = float(t.loc[ok, "net_m3"].sum() / t.loc[ok, "vdens_m3"].sum())
    return {"f_v": f, "median_ratio": med, "robust_sd": sd,
            "consistent": t.loc[ok, "interval"].tolist(), "excluded": t.loc[~ok, "interval"].tolist()}


def _cache_key(ds, cfg) -> str:
    """Calibration depends on the data and on the geometry settings only (not
    on transport parameters), so Monte Carlo / sensitivity runs reuse it."""
    import json
    fp = {"surveys": list(ds.register["sha256"]), "ends": [str(t) for t in ds.register["survey_datetime"]],
          "n_fms": int(len(ds.fms)), "fms_last": str(ds.fms["timestamp"].max()),
          "interventions": ds.interventions.to_dict("records") if len(ds.interventions) else []}
    geo = {k: cfg.get(k) for k in ("grid", "survey", "base", "infill", "time", "fms")}
    geo["k_mad"] = cfg["density"]["calibration_outlier_k_mad"]
    return json.dumps([fp, geo], sort_keys=True, default=str)


def calibrate(ds, cfg, n_boot: int = 2000, seed: int = 413) -> dict:
    key = _cache_key(ds, cfg)
    if key in _CACHE:
        return _CACHE[key]
    k_mad = cfg["density"]["calibration_outlier_k_mad"]
    t = interval_budget(ds, cfg)
    cal = robust_factor(t, k_mad)
    t["consistent"] = t["interval"].isin(cal["consistent"])
    c = t[t["consistent"]]
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(c), len(c))
        boot.append(c["net_m3"].values[idx].sum() / c["vdens_m3"].values[idx].sum())
    boot = np.array(boot)
    # hold-out 1: calibrate on the first half of the record, predict the second
    split = t["interval"].median()
    first = robust_factor(t[t["interval"] <= split], k_mad)
    cal_first = t[t["interval"].isin(first["consistent"])]
    k_const = cal_first["net_m3"].sum() / cal_first["fms_t"].sum()
    t["role"] = np.where(t["interval"] <= split, "calibration", "held-out")
    t["pred_fv_first_half_m3"] = first["f_v"] * t["vdens_m3"]
    t["err_fv_first_half"] = (t["net_m3"] - t["pred_fv_first_half_m3"]) / t["net_m3"]
    t["pred_const_density_m3"] = k_const * t["fms_t"]
    t["err_const_density"] = (t["net_m3"] - t["pred_const_density_m3"]) / t["net_m3"]
    t["pred_dens_as_inpile_m3"] = t["vdens_m3"]
    t["err_dens_as_inpile"] = (t["net_m3"] - t["vdens_m3"]) / t["net_m3"]
    # hold-out 2: leave one consistent interval out
    loo = np.full(len(t), np.nan)
    for i in c.index:
        o = c.drop(index=i)
        loo[t.index.get_loc(i)] = (t.loc[i, "net_m3"] - o["net_m3"].sum() / o["vdens_m3"].sum() * t.loc[i, "vdens_m3"]) / t.loc[i, "net_m3"]
    t["err_leave_one_out"] = loo
    held = t[(t["role"] == "held-out") & t["consistent"]]
    res = {
        "f_v": cal["f_v"], "median_ratio": cal["median_ratio"], "robust_sd": cal["robust_sd"],
        "consistent_intervals": cal["consistent"], "excluded_intervals": cal["excluded"],
        "boot": boot, "f_v_p10": float(np.percentile(boot, 10)), "f_v_p50": float(np.percentile(boot, 50)),
        "f_v_p90": float(np.percentile(boot, 90)), "f_v_first_half": first["f_v"],
        "holdout_mae_fv": float(held["err_fv_first_half"].abs().mean()) if len(held) else np.nan,
        "holdout_mae_const_density": float(held["err_const_density"].abs().mean()) if len(held) else np.nan,
        "holdout_mae_dens_as_inpile": float(held["err_dens_as_inpile"].abs().mean()) if len(held) else np.nan,
        "loo_mae": float(np.nanmean(np.abs(loo))),
        "table": t,
    }
    _CACHE[key] = res
    return res


def resolve_density(ds, cfg) -> dict:
    """Return a copy of cfg with density.volume_factor_resolved set (and the
    cut-off it was calibrated for)."""
    d = cfg["density"]
    if d["volume_factor"] != "auto":
        return apply_overrides(cfg, {"density.volume_factor_resolved": float(d["volume_factor"])})
    if d.get("volume_factor_resolved") is not None and d.get("volume_factor_cutoff") == cfg["time"]["survey_cutoff_hours"]:
        return cfg
    cal = calibrate(ds, cfg)
    return apply_overrides(cfg, {"density.volume_factor_resolved": round(cal["f_v"], 6),
                                 "density.volume_factor_cutoff": cfg["time"]["survey_cutoff_hours"]})


def write_outputs(cal: dict, cfg, out: Path) -> pd.DataFrame:
    import matplotlib.pyplot as plt
    t = cal["table"]
    t.to_csv(out / "volume_factor_calibration.csv", index=False)
    summ = {k: v for k, v in cal.items() if k not in ("boot", "table")}
    rho = float(np.average(t["fms_t"] / t["vdens_m3"].replace(0, np.nan), weights=t["fms_t"]))
    summ["mean_fms_density"] = rho
    summ["in_pile_density_base"] = rho * cfg["density"].get("payload_factor", 1.0) / cal["f_v"]
    pd.Series({k: (v if not isinstance(v, list) else " ".join(map(str, v))) for k, v in summ.items()}).to_csv(out / "volume_factor_summary.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
    x = np.arange(len(t))
    colors = [pl.CAT[0] if c else pl.CAT[1] for c in t["consistent"]]
    a1.bar(x, t["ratio"], color=colors, width=0.7)
    a1.axhline(cal["f_v"], color=pl.INK, lw=1)
    a1.axhspan(cal["f_v_p10"], cal["f_v_p90"], color=pl.GRID, alpha=0.8, lw=0, zorder=0)
    a1.axhline(1.0, color=pl.MUTED, lw=1, ls=":")
    a1.set_xticks(x)
    a1.set_xticklabels([d[5:] for d in t["survey_date"]], rotation=0)
    a1.set_xlabel("survey (nominal date D; interval ends D+1 07:00)")
    a1.set_ylim(0, max(2.9, float(t["ratio"].max()) * 1.2))
    a1.set_ylabel("measured net fill / sum(T / Dens)")
    a1.set_title(f"Volume ratio per interval: f_v = {cal['f_v']:.3f} (P10-P90 {cal['f_v_p10']:.2f}-{cal['f_v_p90']:.2f})", loc="left")
    a1.bar(0, 0, color=pl.CAT[0], label="consistent (used)")
    a1.bar(0, 0, color=pl.CAT[1], label="excluded (FMS gap / partial)")
    a1.plot([], [], color=pl.MUTED, ls=":", label="Dens = in-pile density")
    a1.legend(loc="upper center", ncol=3)
    held = t[t["role"] == "held-out"]
    xx = np.arange(len(held))
    w = 0.26
    a2.bar(xx - w, held["err_fv_first_half"] * 100, w, color=pl.CAT[0], label="f_v (Dens-weighted)")
    a2.bar(xx, held["err_const_density"] * 100, w, color=pl.CAT[2], label="constant density")
    a2.bar(xx + w, held["err_dens_as_inpile"] * 100, w, color=pl.CAT[1], label="Dens as in-pile density")
    a2.axhline(0, color=pl.INK, lw=0.8)
    a2.set_xticks(xx)
    a2.set_xticklabels([d[5:] + ("" if c else "*") for d, c in zip(held["survey_date"], held["consistent"])])
    a2.set_xlabel("held-out survey (* = excluded interval, FMS gap)")
    a2.set_ylabel("volume prediction error (%)")
    a2.set_title(f"Hold-out (calibrated on first half): MAE {cal['holdout_mae_fv'] * 100:.1f}%", loc="left")
    a2.legend(loc="upper left", fontsize=7)
    pl.save(fig, out / "fig_volume_factor.png")
    return t
