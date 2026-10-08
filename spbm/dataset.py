"""Assemble the analysis dataset: registry, FMS table, survey solids on the grid.

Rasterised survey grids are cached under data/cache keyed by file hash and
grid definition, so repeated runs are fast and a changed file is detected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import io as sio
from .config import resolve
from .grid import Grid, rasterize_triangles, triangle_stats

TRI_CACHE_VERSION = 2   # bump when read_dxf_triangles / triangle_stats metadata changes


@dataclass
class Survey:
    index: int
    file: str
    sha256: str
    datetime: pd.Timestamp
    top: np.ndarray        # (ny,nx) upper surface of the change solid (NaN outside)
    bot: np.ndarray        # (ny,nx) lower surface of the change solid
    count: np.ndarray      # triangles through each cell centre
    meta: dict = field(default_factory=dict)
    nominal: pd.Timestamp | None = None   # nominal survey date D (the interval closes at `datetime`)

    @property
    def label(self) -> str:
        """Nominal survey date as MM-DD (for figures and tables)."""
        return f"{(self.nominal if self.nominal is not None else self.datetime):%m-%d}"

    @property
    def mask(self) -> np.ndarray:
        return np.isfinite(self.top)

    @property
    def thickness(self) -> np.ndarray:
        return self.top - self.bot


@dataclass
class Dataset:
    grid: Grid
    fms: pd.DataFrame
    register: pd.DataFrame
    surveys: list[Survey]
    files: list
    interventions: pd.DataFrame = field(default_factory=pd.DataFrame)

    def survey_times(self):
        return [s.datetime for s in self.surveys]


def load_dataset(cfg: dict, until: str | None = None, verbose=True) -> Dataset:
    interventions = sio.load_interventions(cfg)
    files = sio.scan_sources(cfg, interventions)
    fms_files = [f for f in files if f.kind == "fms"]
    srv_files = [f for f in files if f.kind == "survey"]
    if not fms_files or not srv_files:
        raise RuntimeError("No FMS or survey files found in configured sources")
    fms = sio.read_fms(fms_files)
    reg = sio.survey_register(srv_files, cfg, interventions)
    if until is not None:
        cut = pd.Timestamp(until)
        reg = reg[reg["survey_datetime"] <= cut].reset_index(drop=True)
        reg["index"] = np.arange(len(reg))
        fms = fms[fms["timestamp"] <= cut].reset_index(drop=True)

    cache = resolve(cfg["inputs"]["cache_dir"])
    cache.mkdir(parents=True, exist_ok=True)
    by_name = {f.name: f for f in srv_files}

    # triangles (cached as npz per file hash)
    tri, meta = {}, {}
    for name in reg["file"]:
        f = by_name[name]
        cp = cache / f"tri{TRI_CACHE_VERSION}_{f.sha256[:16]}.npz"
        if cp.exists():
            z = np.load(cp, allow_pickle=False)
            tri[name] = z["T"]
            meta[name] = json.loads(str(z["meta"]))
        else:
            if verbose:
                print(f"  reading {name}")
            T, m = sio.read_dxf_triangles(f)
            m.update(triangle_stats(T))
            np.savez_compressed(cp, T=T, meta=json.dumps(m, default=str))
            tri[name], meta[name] = T, m

    # grid extent: all triangles + dumps
    allT = np.concatenate([t.reshape(-1, 3) for t in tri.values()])
    xs = np.r_[allT[:, 0], fms["x"].dropna().values]
    ys = np.r_[allT[:, 1], fms["y"].dropna().values]
    g = Grid.from_extent(xs.min(), xs.max(), ys.min(), ys.max(), cfg["grid"]["cell"], cfg["grid"]["margin"],
                            anchor=cfg["blockmodel"]["block"][0] * 2)

    surveys = []
    for _, r in reg.iterrows():
        name = r["file"]
        key = f"ras_{by_name[name].sha256[:16]}_{g.x0}_{g.y0}_{g.nx}_{g.ny}_{g.cell}.npz"
        cp = cache / key
        if cp.exists():
            z = np.load(cp)
            zmax, zmin, cnt = z["zmax"], z["zmin"], z["cnt"]
        else:
            zmax, zmin, cnt = rasterize_triangles(tri[name], g)
            np.savez_compressed(cp, zmax=zmax, zmin=zmin, cnt=cnt)
        hit = cnt > 0
        top = np.where(hit, zmax, np.nan)
        bot = np.where(hit, zmin, np.nan)
        m = dict(meta[name])
        m["closed_solid_frac"] = float((cnt[hit] == 2).mean()) if hit.any() else 0.0
        m["open_cells"] = int((cnt == 1).sum())
        m["fold_cells"] = int((cnt > 2).sum())
        surveys.append(Survey(int(r["index"]), name, by_name[name].sha256, r["survey_datetime"], top, bot, cnt, m,
                              pd.Timestamp(r["assigned_date"]).normalize()))
    return Dataset(g, fms, reg, surveys, files, interventions)
