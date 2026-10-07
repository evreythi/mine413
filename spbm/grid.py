"""Regular 2-D grid and triangulation rasterisation."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Grid:
    x0: float  # west edge
    y0: float  # south edge
    nx: int
    ny: int
    cell: float

    @property
    def xc(self) -> np.ndarray:
        return self.x0 + (np.arange(self.nx) + 0.5) * self.cell

    @property
    def yc(self) -> np.ndarray:
        return self.y0 + (np.arange(self.ny) + 0.5) * self.cell

    @property
    def extent(self):
        return [self.x0, self.x0 + self.nx * self.cell, self.y0, self.y0 + self.ny * self.cell]

    @property
    def area(self) -> float:
        return self.cell * self.cell

    def mesh(self):
        return np.meshgrid(self.xc, self.yc)

    def index(self, x, y):
        """(row j, col i) of points, clipped to grid; also returns inside mask."""
        i = np.floor((np.asarray(x) - self.x0) / self.cell).astype(int)
        j = np.floor((np.asarray(y) - self.y0) / self.cell).astype(int)
        inside = (i >= 0) & (i < self.nx) & (j >= 0) & (j < self.ny)
        return np.clip(j, 0, self.ny - 1), np.clip(i, 0, self.nx - 1), inside

    @staticmethod
    def from_extent(xmin, xmax, ymin, ymax, cell, margin=0.0, anchor=None):
        """Origin snapped to multiples of `anchor` (default: cell) so that grids
        of different resolution share block boundaries."""
        a = anchor or cell
        x0 = np.floor((xmin - margin) / a) * a
        y0 = np.floor((ymin - margin) / a) * a
        nx = int(np.ceil((xmax + margin - x0) / cell))
        ny = int(np.ceil((ymax + margin - y0) / cell))
        return Grid(float(x0), float(y0), nx, ny, float(cell))


def rasterize_triangles(T: np.ndarray, g: Grid):
    """Sample a triangulation at cell centres.

    Returns (zmax, zmin, count): highest / lowest triangle elevation through
    each cell centre and the number of triangles hit. For a closed
    'change solid' count==2 (top and bottom); count==1 indicates an open
    surface; count>2 indicates folds/overhangs (QA artefact).
    """
    zmax = np.full(g.ny * g.nx, -np.inf)
    zmin = np.full(g.ny * g.nx, np.inf)
    cnt = np.zeros(g.ny * g.nx, dtype=np.int32)
    if len(T) == 0:
        return zmax.reshape(g.ny, g.nx), zmin.reshape(g.ny, g.nx), cnt.reshape(g.ny, g.nx)
    xs, ys = T[:, :, 0], T[:, :, 1]
    i0 = np.ceil((xs.min(1) - g.x0) / g.cell - 0.5).astype(int)
    i1 = np.floor((xs.max(1) - g.x0) / g.cell - 0.5).astype(int)
    j0 = np.ceil((ys.min(1) - g.y0) / g.cell - 0.5).astype(int)
    j1 = np.floor((ys.max(1) - g.y0) / g.cell - 0.5).astype(int)
    i0 = np.clip(i0, 0, g.nx - 1); i1 = np.clip(i1, -1, g.nx - 1)
    j0 = np.clip(j0, 0, g.ny - 1); j1 = np.clip(j1, -1, g.ny - 1)
    ni = np.maximum(i1 - i0 + 1, 0)
    nj = np.maximum(j1 - j0 + 1, 0)
    n = ni * nj
    keep = n > 0
    tri_id = np.repeat(np.nonzero(keep)[0], n[keep])
    # local offsets inside each bbox
    starts = np.repeat(np.cumsum(n[keep]) - n[keep], n[keep])
    k = np.arange(len(tri_id)) - starts
    nik = ni[tri_id]
    ii = i0[tri_id] + k % nik
    jj = j0[tri_id] + k // nik
    px = g.x0 + (ii + 0.5) * g.cell
    py = g.y0 + (jj + 0.5) * g.cell
    a, b, c = T[tri_id, 0], T[tri_id, 1], T[tri_id, 2]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(det) > 1e-12
    det = np.where(ok, det, 1.0)
    l1 = ((b[:, 1] - c[:, 1]) * (px - c[:, 0]) + (c[:, 0] - b[:, 0]) * (py - c[:, 1])) / det
    l2 = ((c[:, 1] - a[:, 1]) * (px - c[:, 0]) + (a[:, 0] - c[:, 0]) * (py - c[:, 1])) / det
    l3 = 1.0 - l1 - l2
    eps = 1e-9
    m = ok & (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps)
    z = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
    flat = (jj * g.nx + ii)[m]
    np.maximum.at(zmax, flat, z[m])
    np.minimum.at(zmin, flat, z[m])
    np.add.at(cnt, flat, 1)
    return zmax.reshape(g.ny, g.nx), zmin.reshape(g.ny, g.nx), cnt.reshape(g.ny, g.nx)


def triangle_stats(T: np.ndarray) -> dict:
    """Geometric QA of a triangulation."""
    e1 = T[:, 1] - T[:, 0]
    e2 = T[:, 2] - T[:, 0]
    n = np.cross(e1, e2)
    area3d = 0.5 * np.linalg.norm(n, axis=1)
    edges = np.concatenate([np.linalg.norm(T[:, 1] - T[:, 0], axis=1),
                            np.linalg.norm(T[:, 2] - T[:, 1], axis=1),
                            np.linalg.norm(T[:, 0] - T[:, 2], axis=1)])
    _, vid = np.unique(np.round(T, 3).reshape(-1, 3), axis=0, return_inverse=True)
    tri_v = np.sort(vid.reshape(-1, 3), axis=1)
    _, counts = np.unique(tri_v, axis=0, return_counts=True)
    Ts = T - T.reshape(-1, 3).mean(0)
    signed_vol = np.einsum("ij,ij->i", Ts[:, 0], np.cross(Ts[:, 1], Ts[:, 2])).sum() / 6.0
    return {
        "n_triangles": int(len(T)),
        "degenerate": int((area3d < 1e-6).sum()),
        "duplicate_triangles": int((counts > 1).sum()),
        "edge_median_m": float(np.median(edges)),
        "edge_p95_m": float(np.percentile(edges, 95)),
        "signed_volume_m3": float(signed_vol),
        "normals_up_frac": float((n[:, 2] > 0).mean()),
    }
