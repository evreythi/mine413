"""Stockpile block model: aggregation of the column model into 3-D blocks,
derived grades / metal / uncertainty fields, and export formats."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .movement import NP, P, PROPS

INFO_CLASSES = ["FMS-reconciled", "Unattributed-imputed", "Legacy-assumed", "Provisional"]


@dataclass
class BlockGrid:
    x0: float
    y0: float
    z0: float
    dx: float
    dy: float
    dz: float
    nx: int
    ny: int
    nz: int
    fx: int  # grid cells per block in x
    fy: int

    @property
    def shape(self):
        return (self.nz, self.ny, self.nx)


def make_block_grid(rec, cfg, block=None) -> BlockGrid:
    g = rec.grid
    dx, dy, dz = block or cfg["blockmodel"]["block"]
    fx, fy = int(round(dx / g.cell)), int(round(dy / g.cell))
    if abs(fx * g.cell - dx) > 1e-6 or abs(fy * g.cell - dy) > 1e-6:
        raise ValueError("block size must be a multiple of the grid cell")
    z0 = cfg["blockmodel"]["origin_z"]
    zmin = np.nanmin(rec.B)
    z0 = min(z0, np.floor(zmin / dz) * dz)
    ztop = np.nanmax(rec.cols.top)
    nz = int(np.ceil((ztop - z0) / dz)) + 1
    return BlockGrid(g.x0, g.y0, z0, dx, dy, dz, int(np.ceil(g.nx / fx)), int(np.ceil(g.ny / fy)), nz, fx, fy)


def layer_table(cols):
    """All layers as flat arrays: cell, zb, zt, props(n,NP)."""
    cells, zb, zt, pr = [], [], [], []
    for c, lay in cols.layers.items():
        for a, b, p in lay:
            if b - a <= 0:
                continue
            cells.append(c); zb.append(a); zt.append(b); pr.append(p)
    return np.asarray(cells), np.asarray(zb), np.asarray(zt), np.asarray(pr).reshape(-1, NP)


def aggregate(rec, bg: BlockGrid) -> np.ndarray:
    """Integrate layer properties into blocks -> array (nz,ny,nx,NP)."""
    g = rec.grid
    cells, zb, zt, pr = layer_table(rec.cols)
    out = np.zeros((bg.nz, bg.ny, bg.nx, NP))
    if len(cells) == 0:
        return out
    j, i = np.divmod(cells, g.nx)
    bj, bi = j // bg.fy, i // bg.fx
    th = zt - zb
    k0 = np.floor((zb - bg.z0) / bg.dz).astype(int)
    k1 = np.floor((zt - bg.z0 - 1e-9) / bg.dz).astype(int)
    flat = out.reshape(-1, NP)
    for k in range(max(k0.min(), 0), min(k1.max(), bg.nz - 1) + 1):
        lo, hi = bg.z0 + k * bg.dz, bg.z0 + (k + 1) * bg.dz
        h = np.minimum(zt, hi) - np.maximum(zb, lo)
        m = h > 0
        f = h[m] / th[m]
        contrib = pr[m] * f[:, None]
        contrib[:, P["MSQ_F"]] = pr[m, P["MSQ_F"]] * f * f
        idx = (k * bg.ny + bj[m]) * bg.nx + bi[m]
        np.add.at(flat, idx, contrib)
    return out


def provenance(rec, bg: BlockGrid):
    """Sparse matrix (loads x blocks) of FMS tonnes, from the stored transport
    plans (requires reconstruct(..., keep_plans=True)). Material re-handled by
    later cuts keeps its original block attribution (cut volume is reported
    separately and is small)."""
    from scipy.sparse import coo_matrix
    g = rec.grid
    L = rec.loads
    rows, cols, vals = [], [], []
    nblk = bg.nz * bg.ny * bg.nx

    def add(load_idx, cells, tonnes, zb, zt):
        if len(cells) == 0:
            return
        j, i = np.divmod(cells, g.nx)
        bj, bi = j // bg.fy, i // bg.fx
        th = np.maximum(zt - zb, 1e-12)
        k0 = np.floor((zb - bg.z0) / bg.dz).astype(int)
        k1 = np.floor((zt - bg.z0 - 1e-9) / bg.dz).astype(int)
        for k in range(max(k0.min(), 0), min(k1.max(), bg.nz - 1) + 1):
            h = np.minimum(zt, bg.z0 + (k + 1) * bg.dz) - np.maximum(zb, bg.z0 + k * bg.dz)
            m = h > 0
            rows.append(load_idx[m]); cols.append((k * bg.ny + bj[m]) * bg.nx + bi[m]); vals.append(tonnes[m] * h[m] / th[m])

    for pl_ in rec.plans:
        if pl_.get("provisional"):
            ld = L.iloc[pl_["load"]]
            n = len(pl_["cells"])
            add(np.full(n, pl_["load"]), pl_["cells"], pl_["vol"] * ld.m / ld.vol, pl_["zb"], pl_["zt"])
            continue
        Pm, fc = pl_["P"], pl_["fill_cells"]
        nF = len(fc)
        for i_src, (kind, li) in enumerate(zip(pl_["src_kind"], pl_["src_load"])):
            if kind not in ("load", "carried"):
                continue
            ld = L.iloc[li]
            w = Pm[i_src, :nF].astype(float)
            m = w > 1e-9
            add(np.full(m.sum(), li), fc[m], w[m] * ld.m / ld.vol, pl_["zb"][m], pl_["zt"][m])
    if not rows:
        return coo_matrix((len(L), nblk)).tocsc()
    return coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(L), nblk)).tocsc()


def provenance_fields(df: pd.DataFrame, prov, bg: BlockGrid, loads: pd.DataFrame, top=3):
    lin = ((df["iz"] * bg.ny + df["iy"]) * bg.nx + df["ix"]).values
    sub = prov[:, lin].tocsc()
    neff, nl, topc = [], [], []
    ids = loads["cycle_id"].values
    for b in range(sub.shape[1]):
        col = sub.getcol(b)
        v = col.data
        if v.size == 0 or v.sum() < 0.5:   # trace FMS material (< 0.5 t): no meaningful provenance
            neff.append(np.nan); nl.append(0); topc.append("")
            continue
        s = v.sum()
        neff.append(s * s / (v * v).sum())
        nl.append(int((v / s >= 0.01).sum()))
        o = np.argsort(v)[::-1][:top]
        topc.append(";".join(f"{ids[col.indices[q]]}:{v[q] / s:.0%}" for q in o))
    df = df.copy()
    df["n_eff_loads"] = neff
    df["n_loads_ge1pct"] = nl
    df["top_loads"] = topc
    return df


def block_table(rec, bg: BlockGrid, agg: np.ndarray, cfg) -> pd.DataFrame:
    """Derived block model table (one row per non-empty block)."""
    vol_blk = bg.dx * bg.dy * bg.dz
    a = agg.reshape(-1, NP)
    keep = a[:, P["VOL"]] > max(cfg["blockmodel"]["min_fill_fraction"] * vol_blk, 1e-6)
    idx = np.nonzero(keep)[0]
    k, rem = np.divmod(idx, bg.ny * bg.nx)
    j, i = np.divmod(rem, bg.nx)
    A = a[keep]
    T = A[:, P["T_F"]] + A[:, P["T_U"]] + A[:, P["T_L"]]
    CU = A[:, P["CU_F"]] + A[:, P["CU_U"]] + A[:, P["CU_L"]]
    AU = A[:, P["AU_F"]] + A[:, P["AU_U"]] + A[:, P["AU_L"]]
    AG = A[:, P["AG_F"]] + A[:, P["AG_U"]] + A[:, P["AG_L"]]
    TF = A[:, P["T_F"]]
    with np.errstate(divide="ignore", invalid="ignore"):
        trace = TF < 0.5   # < 0.5 t of FMS material: FMS-derived fields left blank
        cu_f = np.where(~trace, A[:, P["CU_F"]] / TF * 100, np.nan)
        au_f = np.where(~trace, A[:, P["AU_F"]] / TF * 1000, np.nan)
        cu_sd = np.sqrt(np.maximum(A[:, P["CU2_F"]] / TF - cu_f ** 2, 0))
        au_sd = np.sqrt(np.maximum(A[:, P["AU2_F"]] / TF - au_f ** 2, 0))
        age = np.where(~trace, A[:, P["AGE_F"]] / TF, np.nan)
        cu_sd = np.where(~trace, cu_sd, np.nan)
        au_sd = np.where(~trace, au_sd, np.nan)
    t_ref = pd.Timestamp(rec.diagnostics["t0"])
    # geometry: fraction of the block footprint whose top surface was surveyed
    g = rec.grid
    obs = np.isfinite(rec.observed_top)
    pad = np.zeros((bg.ny * bg.fy, bg.nx * bg.fx), bool)
    pad[: g.ny, : g.nx] = obs
    obs_frac = pad.reshape(bg.ny, bg.fy, bg.nx, bg.fx).mean(axis=(1, 3))
    df = pd.DataFrame({
        "ix": i, "iy": j, "iz": k,
        "xc": bg.x0 + (i + 0.5) * bg.dx, "yc": bg.y0 + (j + 0.5) * bg.dy, "zc": bg.z0 + (k + 0.5) * bg.dz,
        "dx": bg.dx, "dy": bg.dy, "dz": bg.dz,
        "volume_m3": A[:, P["VOL"]], "fill_frac": A[:, P["VOL"]] / vol_blk,
        "tonnes": T, "density": T / A[:, P["VOL"]],
        "cu_pct": CU / T * 100, "au_gpt": AU / T * 1000, "ag_gpt": AG / T * 1000,
        "cu_t": CU, "au_kg": AU, "ag_kg": AG,
        "t_fms": TF, "t_unattributed": A[:, P["T_U"]], "t_legacy": A[:, P["T_L"]], "t_provisional": A[:, P["T_R"]],
        "frac_fms": TF / T, "frac_unattributed": A[:, P["T_U"]] / T, "frac_legacy": A[:, P["T_L"]] / T,
        "cu_pct_fms": cu_f, "au_gpt_fms": au_f, "cu_sd_within": cu_sd, "au_sd_within": au_sd,
        "mean_place_date": [(t_ref + pd.Timedelta(days=float(d))).strftime("%Y-%m-%d %H:%M") if np.isfinite(d) else "" for d in age],
        "top_surveyed_frac": obs_frac[j, i],
    })
    fr = df[["frac_fms", "frac_unattributed", "frac_legacy"]].values
    cls = np.array(INFO_CLASSES[:3])[np.argmax(fr, axis=1)]
    cls = np.where((df["t_provisional"] / df["tonnes"]) > 0.5, "Provisional", cls)
    df["info_class"] = cls
    return df.reset_index(drop=True)


def classify_confidence(df: pd.DataFrame, cfg) -> pd.Series:
    """High / Medium / Low / Uninformed using tracked fraction and Monte-Carlo
    CV of block Cu grade (if available)."""
    c = cfg["confidence"]
    cv = df["cu_cv"] if "cu_cv" in df else pd.Series(0.0, index=df.index)
    tr = df["frac_fms"]
    out = np.full(len(df), "Uninformed", dtype=object)
    out[(tr >= c["low"]["min_tracked"])] = "Low"
    out[(tr >= c["medium"]["min_tracked"]) & (cv <= c["medium"]["max_cv"])] = "Medium"
    out[(tr >= c["high"]["min_tracked"]) & (cv <= c["high"]["max_cv"]) & (df["top_surveyed_frac"] >= 0.5)] = "High"
    return pd.Series(out, index=df.index)


def summary_tables(df: pd.DataFrame, cfg) -> dict:
    def agg(g):
        t = g["tonnes"].sum()
        return pd.Series({"blocks": len(g), "volume_m3": g["volume_m3"].sum(), "tonnes": t,
                          "cu_pct": g["cu_t"].sum() / t * 100 if t else np.nan,
                          "au_gpt": g["au_kg"].sum() / t * 1000 if t else np.nan,
                          "ag_gpt": g["ag_kg"].sum() / t * 1000 if t else np.nan,
                          "cu_t": g["cu_t"].sum(), "au_kg": g["au_kg"].sum(), "au_koz": g["au_kg"].sum() / 31.1035,
                          "ag_kg": g["ag_kg"].sum()})
    out = {"by_info_class": df.groupby("info_class").apply(agg, include_groups=False)}
    if "confidence" in df:
        out["by_confidence"] = df.groupby("confidence").apply(agg, include_groups=False)
    bench = (np.floor((df["zc"] - df["dz"] / 2 - cfg["blockmodel"]["origin_z"]) / 4.0) * 4 + cfg["blockmodel"]["origin_z"]).astype(int)
    out["by_bench_4m"] = df.assign(bench=bench).groupby("bench").apply(agg, include_groups=False).sort_index(ascending=False)
    # material source split (tonnes-weighted, exact)
    src = pd.DataFrame({
        "tonnes": [df["t_fms"].sum() - df["t_provisional"].sum(), df["t_provisional"].sum(), df["t_unattributed"].sum(), df["t_legacy"].sum()],
    }, index=["FMS (survey-reconciled)", "FMS (provisional, unreconciled)", "Unattributed (imputed grade)", "Legacy (assumed grade)"])
    out["by_material_source"] = src
    # grade-tonnage on Cu (all material and FMS-tracked only)
    rows = []
    for co in cfg["blockmodel"]["cutoff_cu"]:
        m = df["cu_pct"] >= co
        t = df.loc[m, "tonnes"].sum()
        mf = df["frac_fms"] >= 0.5
        m2 = m & mf
        t2 = df.loc[m2, "tonnes"].sum()
        rows.append({"cutoff_cu_pct": co, "tonnes_all": t,
                     "cu_pct_all": df.loc[m, "cu_t"].sum() / t * 100 if t else np.nan,
                     "au_gpt_all": df.loc[m, "au_kg"].sum() / t * 1000 if t else np.nan,
                     "tonnes_tracked_blocks": t2,
                     "cu_pct_tracked_blocks": df.loc[m2, "cu_t"].sum() / t2 * 100 if t2 else np.nan})
    out["grade_tonnage"] = pd.DataFrame(rows)
    return out


def export_vtk(df: pd.DataFrame, bg: BlockGrid, path, fields):
    """Legacy-ASCII VTK STRUCTURED_POINTS (opens in ParaView)."""
    n = bg.nx * bg.ny * bg.nz
    with open(path, "w") as fh:
        fh.write("# vtk DataFile Version 3.0\nSPBM stockpile block model\nASCII\nDATASET STRUCTURED_POINTS\n")
        fh.write(f"DIMENSIONS {bg.nx + 1} {bg.ny + 1} {bg.nz + 1}\n")
        fh.write(f"ORIGIN {bg.x0} {bg.y0} {bg.z0}\nSPACING {bg.dx} {bg.dy} {bg.dz}\n")
        fh.write(f"CELL_DATA {n}\n")
        lin = (df["iz"] * bg.ny + df["iy"]) * bg.nx + df["ix"]
        for f in fields:
            arr = np.full(n, -1.0)
            vals = df[f]
            if not pd.api.types.is_numeric_dtype(vals):
                codes = {v: i for i, v in enumerate(sorted(vals.unique()))}
                vals = vals.map(codes)
            arr[lin.values] = np.nan_to_num(vals.values.astype(float), nan=-1.0)
            fh.write(f"SCALARS {f} float 1\nLOOKUP_TABLE default\n")
            fh.write("\n".join(f"{v:.5g}" for v in arr))
            fh.write("\n")


def export_grid_asc(z, g, path):
    """ESRI ASCII grid of a surface (row 0 = north)."""
    with open(path, "w") as fh:
        fh.write(f"ncols {g.nx}\nnrows {g.ny}\nxllcorner {g.x0}\nyllcorner {g.y0}\ncellsize {g.cell}\nNODATA_value -9999\n")
        zz = np.where(np.isfinite(z), z, -9999)[::-1]
        for row in zz:
            fh.write(" ".join(f"{v:.3f}" for v in row) + "\n")
