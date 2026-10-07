"""Task 2 - characterisation of stockpile growth and FMS <-> survey reconciliation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import plots as pl
from .config import apply_overrides
from .dataset import load_dataset
from .movement import prepare_loads


def temporal_alignment(cfg, out: Path, until=None) -> pd.DataFrame:
    """A-05: choose the survey time-of-day that best aligns FMS tonnage with
    surveyed volume. Periods with a calendar gap (missing survey) or that the
    FMS record only partially covers (first period) are excluded from the score."""
    rows = []
    for st in cfg["time"]["survey_time_candidates"]:
        c = apply_overrides(cfg, {"time.survey_time": st})
        ds = load_dataset(c, until=until, verbose=False)
        L = prepare_loads(ds, c)
        times = [s.datetime for s in ds.surveys]
        vol = np.array([np.nansum(s.thickness) * ds.grid.area for s in ds.surveys])
        fv = np.array([L["vol"][L["period"] == p].sum() for p in range(len(times))])
        ok = np.array([p for p in range(1, len(times)) if times[p] - times[p - 1] <= pd.Timedelta("36h")])
        r = np.corrcoef(fv[ok], vol[ok])[0, 1]
        rows.append({"survey_time": st, "pearson_r": r, "sum_abs_diff_m3": float(np.abs(fv[ok] - vol[ok]).sum()),
                     "volume_ratio_fms_over_survey": float(fv[ok].sum() / vol[ok].sum()),
                     "loads_after_last_survey": int((L["period"] >= len(times)).sum()),
                     "periods_scored": len(ok)})
    df = pd.DataFrame(rows)
    df.to_csv(out / "temporal_alignment.csv", index=False)
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    a1.plot(df["survey_time"], df["pearson_r"], marker="o", ms=6, color=pl.CAT[0])
    a1.set_title("Correlation FMS volume vs surveyed volume", loc="left")
    a1.set_ylabel("Pearson r (complete periods)")
    a2.plot(df["survey_time"], df["sum_abs_diff_m3"] / 1000, marker="o", ms=6, color=pl.CAT[1])
    a2.set_title("Sum |FMS - survey| volume (k m³)", loc="left")
    for a in (a1, a2):
        a.tick_params(axis="x", labelrotation=60)
        a.set_xlabel("assumed survey time of day")
    best = df.loc[df["pearson_r"].idxmax(), "survey_time"]
    a1.axvline(list(df["survey_time"]).index(best), color=pl.INK, lw=1)
    pl.save(fig, out / "fig_temporal_alignment.png")
    return df


def period_table(rec, ds, out: Path) -> pd.DataFrame:
    p = rec.periods.copy()
    L = rec.loads
    p["fms_cu_pct"] = [np.average(L.cu[L.period == s], weights=L.m[L.period == s]) if (L.period == s).any() else np.nan for s in p.period]
    p["fms_au_gpt"] = [np.average(L.au[L.period == s], weights=L.m[L.period == s]) if (L.period == s).any() else np.nan for s in p.period]
    p["apparent_density_t_m3"] = p["fms_tonnes"] / p["solid_volume"]
    p["fms_explains_frac"] = p["placed_volume"] / p["fill_volume"]
    p["mean_fms_density"] = [L.rho[L.period == s].mean() if (L.period == s).any() else np.nan for s in p.period]
    p.to_csv(out / "period_reconciliation.csv", index=False)
    return p


def growth_figures(rec, ds, ptab, out: Path):
    import matplotlib.pyplot as plt
    g = ds.grid
    L = rec.loads
    # cumulative curves
    fig, ax = plt.subplots(figsize=(9, 4.5))
    t_s = [s.datetime for s in ds.surveys]
    vol = np.cumsum([np.nansum(s.thickness) * g.area for s in ds.surveys])
    rho = float(np.average(L.rho, weights=L.m))
    ax.step(t_s, vol * rho / 1000, where="post", color=pl.CAT[2], label=f"surveyed volume × {rho:.2f} t/m³ (FMS mean density)")
    Ls = L.sort_values("time")
    ax.plot(Ls["time"], Ls["m"].cumsum() / 1000, color=pl.CAT[0], label="cumulative FMS tonnes")
    ax.set_ylabel("kt")
    ax.set_title("Cumulative placement: FMS vs surveyed change solids", loc="left")
    ax.legend(loc="upper left")
    ax.tick_params(axis="x", labelrotation=30)
    pl.save(fig, out / "fig_growth_cumulative.png")

    # per-period bar: fill / FMS / unattributed / retained (grouped, one axis)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(ptab))
    w = 0.26
    ax.bar(x - w, ptab["fill_volume"], w, color=pl.CAT[2], label="observed fill (survey)")
    ax.bar(x, ptab["fms_volume"] + ptab["carried_in_volume"], w, color=pl.CAT[0], label="FMS volume available (incl. carried)")
    ax.bar(x + w, ptab["unattributed_volume"], w, color=pl.CAT[1], label="unattributed (fill not explained by FMS)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{e:%m-%d}" + (" gap" if gflag else "") for e, gflag in zip(ptab["end"], ptab["gap_detected"])], rotation=0)
    ax.set_ylabel("m³")
    ax.set_title("Period reconciliation: surveyed fill vs FMS volume", loc="left")
    ax.legend(loc="upper right")
    pl.save(fig, out / "fig_growth_period_reconciliation.png")

    # face advance map: period of first fill + crest lines
    fig, ax = plt.subplots(figsize=(8.5, 7))
    fp = np.where(rec.first_period >= 0, rec.first_period, np.nan)
    cols = pl.period_colors(len(ds.surveys))
    im = ax.imshow(fp, origin="lower", extent=g.extent, cmap=pl.discrete_cmap(cols), vmin=-0.5, vmax=len(ds.surveys) - 0.5, interpolation="nearest")
    ax.contour(g.xc, g.yc, rec.domain.astype(float), [0.5], colors=[pl.MUTED], linewidths=0.8, linestyles="--")
    pl.plan_axes(ax, g, "Stockpile growth: survey period in which each cell first received fill")
    cb = fig.colorbar(im, ax=ax, shrink=0.75, ticks=range(len(ds.surveys)))
    cb.ax.set_yticklabels([f"{s.datetime:%m-%d}" for s in ds.surveys])
    ax.plot([], [], ls="--", color=pl.MUTED, label="model domain")
    ax.legend(loc="upper right")
    pl.save(fig, out / "fig_growth_face_advance.png")

    # elevation change per period with dumps
    n = len(ds.surveys)
    fig, axs = plt.subplots(2, 5, figsize=(18, 7.5))
    for s, ax in zip(range(n), axs.flat):
        snap = rec.diagnostics["snapshots"][s] if s < len(rec.diagnostics["snapshots"]) else None
        if snap is None:
            continue
        im = pl.raster(ax, np.where(snap["fill"] > 0, snap["fill"], np.nan), g, vmin=0, vmax=6)
        Lp = L[L.period == s]
        ax.scatter(Lp.x, Lp.y, s=7, color=pl.CAT[1], edgecolor=pl.SURFACE, linewidth=0.4)
        ax.contour(g.xc, g.yc, snap["observed_before"].astype(float), [0.5], colors=[pl.MUTED], linewidths=0.6)
        pl.plan_axes(ax, g, f"{ds.surveys[s].datetime:%m-%d}  fill {ptab.fill_volume[s]:.0f} m³", ticks=False)
        ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axs, shrink=0.6, label="elevation increase (m)")
    fig.suptitle("Elevation increase per survey period (blue) and truck dumps of that period (orange); grey = previously surveyed area", x=0.01, ha="left", fontsize=10)
    pl.save(fig, out / "fig_growth_period_maps.png")

    # dump-to-face distance and push distance histogram
    d = rec.destinations
    d = d[d["kind"].isin(["load", "carried"]) & d["mean_push"].notna()]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.hist(d["mean_push"], bins=np.arange(0, 100, 4), weights=d["placed_volume"], color=pl.CAT[0])
    ax.set_xlabel("volume-weighted mean push distance (m, geodesic)")
    ax.set_ylabel("m³")
    ax.set_title("Reconstructed dozer push distances", loc="left")
    pl.save(fig, out / "fig_growth_push_distance.png")
