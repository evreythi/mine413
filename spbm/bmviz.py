"""Block model visualisations (plans per bench, sections, 3-D view, curves)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import plots as pl


def _grid(df, bg, col):
    a = np.full(bg.shape, np.nan)
    a[df["iz"], df["iy"], df["ix"]] = df[col].values
    return a


def bench_plans(df, bg, rec, col, label, cmap, out: Path, vmin=None, vmax=None, fname=None, title=None):
    import matplotlib.pyplot as plt
    a = _grid(df, bg, col)
    levels = [k for k in range(bg.nz) if np.isfinite(a[k]).any()][::-1]
    n = len(levels)
    ncol = min(5, n)
    nrow = int(np.ceil(n / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(3.6 * ncol, 3.4 * nrow), squeeze=False)
    ext = [bg.x0, bg.x0 + bg.nx * bg.dx, bg.y0, bg.y0 + bg.ny * bg.dy]
    vmin = np.nanpercentile(df[col], 2) if vmin is None else vmin
    vmax = np.nanpercentile(df[col], 98) if vmax is None else vmax
    for ax, k in zip(axs.flat, levels):
        im = ax.imshow(a[k], origin="lower", extent=ext, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.contour(rec.grid.xc, rec.grid.yc, rec.domain.astype(float), [0.5], colors=[pl.MUTED], linewidths=0.5)
        ax.set_title(f"z {bg.z0 + k * bg.dz:.0f}-{bg.z0 + (k + 1) * bg.dz:.0f} m", loc="left", fontsize=9)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for ax in list(axs.flat)[n:]:
        ax.axis("off")
    fig.colorbar(im, ax=axs, shrink=0.6, label=label)
    fig.suptitle(title or f"Block model plans by {bg.dz:.0f} m bench - {label}", x=0.01, ha="left", fontsize=11, fontweight="bold")
    return pl.save(fig, out / (fname or f"fig_bm_plans_{col}.png"))


def sections(df, bg, rec, out: Path, col="cu_pct", label="Cu (%)", cmap=pl.SEQ):
    import matplotlib.pyplot as plt
    a = _grid(df, bg, col)
    g = rec.grid
    t = _grid(df, bg, "tonnes")
    # choose section lines through the tonnage-weighted centre of FMS material
    fms = df[df["t_fms"] > 0]
    xc = np.average(fms["xc"], weights=fms["t_fms"])
    yc = np.average(fms["yc"], weights=fms["t_fms"])
    ix = int((xc - bg.x0) // bg.dx)
    iy = int((yc - bg.y0) // bg.dy)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7.5))
    vmin, vmax = np.nanpercentile(df[col], 2), np.nanpercentile(df[col], 98)
    # N-S section (constant x)
    sec = a[:, :, ix]
    im = a1.imshow(sec, origin="lower", extent=[bg.y0, bg.y0 + bg.ny * bg.dy, bg.z0, bg.z0 + bg.nz * bg.dz],
                   cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", interpolation="nearest")
    i_cells = slice(ix * bg.fx, (ix + 1) * bg.fx)
    ys = g.yc
    a1.plot(ys, np.nanmean(rec.diagnostics["final_surface"][:, i_cells], axis=1), color=pl.INK, lw=1.2, label="model top surface")
    a1.plot(ys, np.nanmean(rec.legacy_top[:, i_cells], axis=1), color=pl.CAT[1], lw=1.2, ls="--", label="pre-record surface (top of legacy)")
    a1.plot(ys, np.nanmean(rec.B[:, i_cells], axis=1), color=pl.MUTED, lw=1.0, ls=":", label="fitted floor")
    a1.set_title(f"N-S section at E {bg.x0 + (ix + 0.5) * bg.dx:.1f} (looking west)", loc="left")
    a1.set_xlabel("Northing (m)"); a1.set_ylabel("Elevation (m)"); a1.legend(loc="upper right", ncol=3)
    a1.ticklabel_format(useOffset=False, style="plain"); a1.grid(False)
    sec2 = a[:, iy, :]
    a2.imshow(sec2, origin="lower", extent=[bg.x0, bg.x0 + bg.nx * bg.dx, bg.z0, bg.z0 + bg.nz * bg.dz],
              cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", interpolation="nearest")
    j_cells = slice(iy * bg.fy, (iy + 1) * bg.fy)
    a2.plot(g.xc, np.nanmean(rec.diagnostics["final_surface"][j_cells, :], axis=0), color=pl.INK, lw=1.2)
    a2.plot(g.xc, np.nanmean(rec.legacy_top[j_cells, :], axis=0), color=pl.CAT[1], lw=1.2, ls="--")
    a2.plot(g.xc, np.nanmean(rec.B[j_cells, :], axis=0), color=pl.MUTED, lw=1.0, ls=":")
    a2.set_title(f"E-W section at N {bg.y0 + (iy + 0.5) * bg.dy:.1f} (looking north)", loc="left")
    a2.set_xlabel("Easting (m)"); a2.set_ylabel("Elevation (m)")
    a2.ticklabel_format(useOffset=False, style="plain"); a2.grid(False)
    fig.colorbar(im, ax=[a1, a2], shrink=0.7, label=label)
    return pl.save(fig, out / f"fig_bm_sections_{col}.png")


def view3d(df, bg, out: Path, col="cu_pct", label="Cu (%)", only_tracked=True):
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    d = df[df["frac_fms"] >= 0.5] if only_tracked else df
    fig = plt.figure(figsize=(10, 7.5))
    ax = fig.add_subplot(projection="3d")
    norm = colors.Normalize(np.nanpercentile(d[col], 2), np.nanpercentile(d[col], 98))
    filled = np.zeros((bg.nx, bg.ny, bg.nz), bool)
    fc = np.zeros((bg.nx, bg.ny, bg.nz, 4))
    filled[d["ix"], d["iy"], d["iz"]] = True
    fc[d["ix"], d["iy"], d["iz"]] = pl.SEQ(norm(d[col].values))
    leg = df[df["frac_fms"] < 0.5]
    filled2 = np.zeros_like(filled)
    filled2[leg["ix"], leg["iy"], leg["iz"]] = True
    x = bg.x0 + np.arange(bg.nx + 1) * bg.dx
    y = bg.y0 + np.arange(bg.ny + 1) * bg.dy
    z = bg.z0 + np.arange(bg.nz + 1) * bg.dz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    ax.voxels(X, Y, Z, filled2, facecolors=(0.84, 0.83, 0.8, 0.10), edgecolor=(0.7, 0.7, 0.7, 0.05))
    ax.voxels(X, Y, Z, filled, facecolors=fc, edgecolor=(1, 1, 1, 0.25), linewidth=0.2)
    ax.set_box_aspect((bg.nx * bg.dx, bg.ny * bg.dy, bg.nz * bg.dz * 2))
    ax.view_init(elev=28, azim=-115)
    ax.set_xlabel("E"); ax.set_ylabel("N"); ax.set_zlabel("Z")
    ax.ticklabel_format(useOffset=False, style="plain")
    m = cm.ScalarMappable(norm=norm, cmap=pl.SEQ)
    fig.colorbar(m, ax=ax, shrink=0.55, label=label + " (blocks >= 50% FMS-tracked)")
    ax.set_title("3-D block model: FMS-tracked blocks coloured by grade; grey = legacy / unattributed", loc="left")
    return pl.save(fig, out / f"fig_bm_3d_{col}.png")


def grade_tonnage(gt: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    a1.plot(gt["cutoff_cu_pct"], gt["tonnes_all"] / 1000, marker="o", ms=5, label="all modelled material")
    a1.plot(gt["cutoff_cu_pct"], gt["tonnes_tracked_blocks"] / 1000, marker="o", ms=5, label="blocks >= 50% FMS-tracked")
    a1.set_xlabel("Cu cut-off (%)"); a1.set_ylabel("tonnes above cut-off (kt)")
    a1.set_title("Grade-tonnage: tonnage", loc="left"); a1.legend()
    a2.plot(gt["cutoff_cu_pct"], gt["cu_pct_all"], marker="o", ms=5, label="all modelled material")
    a2.plot(gt["cutoff_cu_pct"], gt["cu_pct_tracked_blocks"], marker="o", ms=5, label="blocks >= 50% FMS-tracked")
    a2.set_xlabel("Cu cut-off (%)"); a2.set_ylabel("mean Cu above cut-off (%)")
    a2.set_title("Grade-tonnage: grade", loc="left"); a2.legend()
    return pl.save(fig, out / "fig_bm_grade_tonnage.png")


def class_maps(df, bg, rec, out: Path):
    import matplotlib.pyplot as plt
    # column (plan) summaries
    col = df.groupby(["iy", "ix"]).agg(t=("tonnes", "sum"), tf=("t_fms", "sum"), tu=("t_unattributed", "sum"),
                                       tl=("t_legacy", "sum")).reset_index()
    ext = [bg.x0, bg.x0 + bg.nx * bg.dx, bg.y0, bg.y0 + bg.ny * bg.dy]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8))
    for ax, key, lab in zip(axs, ["tf", "tu", "tl"], ["FMS-tracked", "unattributed (imputed grade)", "legacy (assumed grade)"]):
        a = np.full((bg.ny, bg.nx), np.nan)
        a[col["iy"], col["ix"]] = col[key] / col["t"]
        im = ax.imshow(a, origin="lower", extent=ext, cmap=pl.SEQ, vmin=0, vmax=1, interpolation="nearest")
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        ax.set_title(f"Share of column tonnes: {lab}", loc="left", fontsize=9.5)
    fig.colorbar(im, ax=axs, shrink=0.7, label="fraction of tonnes in block column")
    pl.save(fig, out / "fig_bm_information_class.png")
    if "confidence" in df:
        order = ["High", "Medium", "Low", "Uninformed"]
        t = df.groupby("confidence")["tonnes"].sum().reindex(order).fillna(0)
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [1.6, 1]})
        # dominant confidence per column (by tonnes)
        dom = df.groupby(["iy", "ix", "confidence"])["tonnes"].sum().reset_index()
        dom = dom.loc[dom.groupby(["iy", "ix"])["tonnes"].idxmax()]
        code = {k: i for i, k in enumerate(order)}
        a = np.full((bg.ny, bg.nx), np.nan)
        a[dom["iy"], dom["ix"]] = dom["confidence"].map(code)
        a1.imshow(a, origin="lower", extent=ext, cmap=pl.discrete_cmap([pl.CONF_COLORS[k] for k in order]), vmin=-0.5, vmax=3.5, interpolation="nearest")
        a1.set_aspect("equal"); a1.grid(False); a1.set_xticks([]); a1.set_yticks([])
        a1.set_title("Dominant confidence class per block column", loc="left")
        from matplotlib.patches import Patch
        a1.legend(handles=[Patch(color=pl.CONF_COLORS[k], label=k) for k in order], loc="upper center",
                  bbox_to_anchor=(0.5, -0.02), ncol=4)
        a2.barh(order[::-1], t[order[::-1]].values / 1000, color=[pl.CONF_COLORS[k] for k in order[::-1]], zorder=3)
        for yv, v in enumerate(t[order[::-1]].values / 1000):
            a2.text(v, yv, f" {v:.1f} kt", va="center", fontsize=8, color=pl.INK2)
        a2.set_xlabel("kt"); a2.set_title("Tonnes by confidence class", loc="left")
        pl.save(fig, out / "fig_bm_confidence.png")


def uncertainty_maps(df, bg, out: Path):
    import matplotlib.pyplot as plt
    if "cu_cv" not in df:
        return
    d = df[df["frac_fms"] >= 0.5]   # Monte Carlo ranges; other blocks carry the prior range
    col = d.groupby(["iy", "ix"]).apply(lambda q: pd.Series({
        "cv": np.average(q["cu_cv"], weights=q["tonnes"]),
        "w": np.average(q["cu_p90"] - q["cu_p10"], weights=q["tonnes"])}), include_groups=False).reset_index()
    ext = [bg.x0, bg.x0 + bg.nx * bg.dx, bg.y0, bg.y0 + bg.ny * bg.dy]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, key, lab, vmax in zip(axs, ["cv", "w"], ["Cu grade coefficient of variation", "Cu P90 - P10 (% Cu)"], [0.2, 2.5]):
        a = np.full((bg.ny, bg.nx), np.nan)
        a[col["iy"], col["ix"]] = col[key]
        im = ax.imshow(a, origin="lower", extent=ext, cmap=pl.SEQ_OR, vmin=0, vmax=vmax, interpolation="nearest")
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        ax.set_title(lab + "\nblocks >= 50% FMS-tracked, column tonnes-weighted", loc="left", fontsize=9.5)
        fig.colorbar(im, ax=ax, shrink=0.75)
    pl.save(fig, out / "fig_unc_block_maps.png")
