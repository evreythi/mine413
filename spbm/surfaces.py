"""Stockpile floor, model domain and inference of unobserved surface elevations."""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import Delaunay

from .grid import Grid


def fit_base_plane(ds, cfg) -> dict:
    """A-12: robust least-squares plane through toe cells (lowest elevations of
    the solid bottoms). Returns coefficients and the plane on the grid."""
    g = ds.grid
    X, Y = g.mesh()
    zs = [s.bot for s in ds.surveys]
    zmin = np.nanmin([np.nanmin(z) for z in zs])
    band = cfg["base"]["toe_band"]
    pts = []
    for z in zs:
        m = np.isfinite(z) & (z < zmin + band)
        pts.append(np.c_[X[m], Y[m], z[m]])
    P = np.vstack(pts)
    xm, ym = X.mean(), Y.mean()
    keep = np.ones(len(P), bool)
    for _ in range(cfg["base"]["robust_iterations"]):
        A = np.c_[P[keep, 0] - xm, P[keep, 1] - ym, np.ones(keep.sum())]
        coef, *_ = np.linalg.lstsq(A, P[keep, 2], rcond=None)
        r = P[:, 2] - np.c_[P[:, 0] - xm, P[:, 1] - ym, np.ones(len(P))] @ coef
        sd = r[keep].std()
        keep = np.abs(r) < 2.5 * sd
    B = coef[2] + coef[0] * (X - xm) + coef[1] * (Y - ym)
    dip = np.degrees(np.arctan(np.hypot(coef[0], coef[1])))
    return {"B": B, "coef": coef.tolist(), "xm": xm, "ym": ym, "resid_sd": float(sd),
            "n_points": int(keep.sum()), "n_rejected": int((~keep).sum()), "dip_deg": float(dip),
            "points": P, "keep": keep}


def model_domain(ds, extra_xy=None) -> np.ndarray:
    """Model domain = convex hull of all surveyed solid cells and dump points
    (A-14). The back of the pile beyond this hull is not represented."""
    g = ds.grid
    X, Y = g.mesh()
    obs = np.zeros((g.ny, g.nx), bool)
    for s in ds.surveys:
        obs |= s.mask
    pts = [np.c_[X[obs], Y[obs]], ds.fms[["x", "y"]].dropna().values]
    if extra_xy is not None:
        pts.append(extra_xy)
    P = np.vstack(pts)
    hull = Delaunay(P[np.unique(_hull_idx(P))])
    dom = hull.find_simplex(np.c_[X.ravel(), Y.ravel()]) >= 0
    return dom.reshape(g.ny, g.nx) | obs


def _hull_idx(P):
    from scipy.spatial import ConvexHull
    return ConvexHull(P).vertices


def infer_surface(z_known: np.ndarray, known: np.ndarray, B: np.ndarray, domain: np.ndarray,
                  cell: float, repose_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Fill unknown cells of a partially observed surface (A-13).

    For each unknown cell the nearest known cell (elevation z_n, distance d)
    decides the side of the face:
      * behind the crest (z_n in the upper half of the pile height) -> platform,
        elevation z_n (flat platform behind the crest);
      * in front of the face -> face continued at the angle of repose down to
        the floor: max(B, z_n - d tan(phi)).
    Returns (surface, side) where side = 0 known, 1 platform, 2 front.
    """
    if not known.any():
        return np.where(domain, B, np.nan), np.where(domain, 2, 0)
    dist, (jj, ii) = ndimage.distance_transform_edt(~known, return_indices=True)
    zn = z_known[jj, ii]
    Bn = B[jj, ii]
    h_known = (z_known - B)[known]
    H = np.percentile(h_known, 90) if h_known.size else 1.0
    # downslope direction of the known surface at the nearest known cell
    zf = ndimage.gaussian_filter(np.where(known, z_known, zn), 1.5)
    gy, gx = np.gradient(zf, cell)
    gnx, gny = -gx[jj, ii], -gy[jj, ii]
    gn = np.hypot(gnx, gny)
    J, I = np.indices(known.shape)
    vx, vy = (I - ii).astype(float), (J - jj).astype(float)
    vn = np.hypot(vx, vy)
    with np.errstate(invalid="ignore", divide="ignore"):
        dot = (vx * gnx + vy * gny) / (vn * gn)
    steep = gn > np.tan(np.radians(15))
    by_dir = steep & np.isfinite(dot) & (np.abs(dot) > 0.3)
    behind = np.where(by_dir, dot < 0, (zn - Bn) >= 0.5 * H)
    front_z = np.maximum(B, zn - dist * cell * np.tan(np.radians(repose_deg)))
    out = np.where(known, z_known, np.where(behind, zn, front_z))
    side = np.where(known, 0, np.where(behind, 1, 2))
    out = np.where(domain | known, out, np.nan)
    return out, side


def extend_outside(z: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Nearest-neighbour continuation of a surface beyond the model domain
    (used only by the forward model so the domain edge is not a cliff)."""
    ok = np.isfinite(z)
    _, (jj, ii) = ndimage.distance_transform_edt(~ok, return_indices=True)
    return np.where(ok, z, z[jj, ii])


def slope_deg(z: np.ndarray, cell: float) -> np.ndarray:
    gy, gx = np.gradient(z, cell)
    return np.degrees(np.arctan(np.hypot(gx, gy)))
