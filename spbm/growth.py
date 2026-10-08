"""Task 2 - characterisation of stockpile growth and FMS <-> survey reconciliation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import plots as pl


def _scan_sets(ds) -> dict:
    """Scoring sets for the cut-off scan, fixed independently of the cut-off:
    every interval after the first (the FMS record starts part-way through
    interval 0), and the subset whose surveys are on consecutive days."""
    d = pd.to_datetime(ds.register["assigned_date"]).dt.normalize().values
    gap = np.r_[np.nan, np.diff(d).astype("timedelta64[D]").astype(float)]
    n = len(d)
    return {"daily": np.array([k for k in range(1, n) if gap[k] == 1]), "all": np.arange(1, n)}


def temporal_alignment(ds, cfg, out: Path) -> pd.DataFrame:
    """A-05: scan the survey cut-off (hours after 00:00 of the survey's nominal
    date, `time.cutoff_scan_hours`) and score how well the FMS volume
    sum(T / Dens) of each interval tracks the surveyed solid volume.

    Scores: Pearson r and the robust coefficient of variation of the volume
    ratio (scale-free, so it does not need the volume factor) on intervals between
    consecutive-day surveys (primary) and on all intervals after the first.
    The dump-time histogram is plotted alongside: shift-change lulls in
    dumping are independent evidence for where the production day ends."""
    reg = ds.register
    d = pd.to_datetime(reg["assigned_date"]).dt.normalize().values
    vol = np.array([np.nansum(s.thickness) * ds.grid.area for s in ds.surveys])
    f = ds.fms
    t = pd.to_datetime(f["timestamp"]).values
    vd = (pd.to_numeric(f["payload_t"], errors="coerce") / pd.to_numeric(f["density"], errors="coerce")).values
    ok = np.isfinite(vd) & ~pd.isna(t)
    t, vd = t[ok], vd[ok]
    sets = _scan_sets(ds)
    a, b, step = cfg["time"]["cutoff_scan_hours"]
    rows = []
    for h in np.arange(a, b + 1e-9, step):
        ends = d + np.timedelta64(int(round(h * 60)), "m")
        k = np.searchsorted(ends, t, side="left")
        fv = np.bincount(k, weights=vd, minlength=len(ends) + 1)[:len(ends)]
        row = {"cutoff_hours": float(h), "clock_time": f"D+{int(h // 24)} {int(h % 24):02d}:{int(round(h % 1 * 60)):02d}"}
        for name, s in sets.items():
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = vol[s] / fv[s]
                row[f"r_{name}"] = float(np.corrcoef(fv[s], vol[s])[0, 1])
                med = np.median(ratio)
                # robust coefficient of variation (1.4826 MAD / median): one FMS-outage interval does not dominate it
                row[f"ratio_rcv_{name}"] = float(1.4826 * np.median(np.abs(ratio - med)) / med) if np.all(fv[s] > 0) else np.nan
        row["loads_after_last_survey"] = int((k >= len(ends)).sum())
        row["empty_intervals"] = int((fv[sets["all"]] == 0).sum())
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out / "temporal_alignment.csv", index=False)
    hours = pd.to_datetime(f["timestamp"]).dropna()
    hh = (hours.dt.hour * 2 + hours.dt.minute // 30).to_numpy()
    counts = np.bincount(hh, minlength=48)
    pd.DataFrame({"half_hour_start": np.arange(48) / 2, "dumps": counts}).to_csv(out / "dump_time_of_day.csv", index=False)
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.0), gridspec_kw={"width_ratios": [1.35, 1]})
    adopted = float(cfg["time"]["survey_cutoff_hours"])
    a1.plot(df["cutoff_hours"], df["r_daily"], color=pl.CAT[0], lw=1.8, label="r, consecutive-day intervals")
    a1.plot(df["cutoff_hours"], df["r_all"], color=pl.CAT[1], lw=1.2, ls="--", label="r, all intervals after the first")
    a1.axvline(24, color=pl.MUTED, lw=1, ls=":")
    a1.axvline(adopted, color=pl.INK, lw=1)
    a1.text(24, -0.45, " 24:00 (D)", color=pl.MUTED, fontsize=8, va="bottom")
    a1.text(adopted, -0.45, f" adopted {adopted:g} h\n (D+1 {int(adopted % 24):02d}:00)", fontsize=8, va="bottom")
    a1.set_xlim(a, b)
    a1.set_ylim(-0.5, 1.02)
    a1.set_xticks(np.arange(a, b + 1, 6))
    a1.set_xlabel("survey cut-off, hours after 00:00 of the nominal survey date")
    a1.set_ylabel("Pearson r, FMS volume vs surveyed volume")
    best = df.loc[df["r_daily"].idxmax()]
    a1.set_title(f"Cut-off scan: best r = {best['r_daily']:.3f} at {best['cutoff_hours']:g} h; r = "
                 f"{df.loc[(df['cutoff_hours'] - 24).abs().idxmin(), 'r_daily']:.3f} at 24 h", loc="left")
    a1.legend(loc="upper left")
    x = np.arange(48) / 2
    a2.bar(x + 0.25, counts, width=0.45, color=pl.CAT[0])
    for lo, hi in [(0.0, 1.5), (6.0, 7.5), (18.5, 20.0)]:
        a2.axvspan(lo, hi, color=pl.CAT[1], alpha=0.15, lw=0)
    a2.axvline(adopted % 24, color=pl.INK, lw=1)
    a2.set_xticks(np.arange(0, 25, 3))
    a2.set_xlim(0, 24)
    a2.set_xlabel("dump time of day (h)")
    a2.set_ylabel("FMS dumps per half hour (all days)")
    a2.set_title("Dump times: lulls at 00:00-01:30, 06:00-07:30, 18:30-20:00", loc="left")
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
    ax.set_xticklabels([s.label + (" gap" if gflag else "") for s, gflag in zip(ds.surveys, ptab["gap_detected"])], rotation=0)
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
    cb.ax.set_yticklabels([s.label for s in ds.surveys])
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
        pl.plan_axes(ax, g, f"{ds.surveys[s].label}  fill {ptab.fill_volume[s]:.0f} m³", ticks=False)
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
