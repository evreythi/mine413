"""Predictive (unconstrained) physics model: dozer push to the crest + gravity
avalanche cellular automaton at the angle of repose.

Used for (i) temporal validation - predicting the next survey without seeing
it, (ii) placing loads recorded after the last survey (provisional nowcast),
(iii) generating synthetic ground truth for the twin experiment.

Only 'mobile' material (the load being placed) can avalanche; the existing
pile is treated as stable, which reflects that faces measured in the surveys
already sit at their angle of repose.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from .surfaces import slope_deg

_OFFS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def crest_mask(z, cell, crest_slope_deg, relief=5.0, window=11.0):
    """Crest = gentle cell at the top edge of a real face. A face cell has a
    smoothed slope above `crest_slope_deg` and at least `relief` metres of
    local drop within ~3 m (rejects small steps on the inferred platform)."""
    zz = np.where(np.isfinite(z), z, np.nanmin(z))
    zs = ndimage.gaussian_filter(zz, 1.5 / cell)
    s = slope_deg(zs, cell)
    w = max(3, int(round(window / cell)) | 1)
    drop = zz - ndimage.minimum_filter(zz, size=w)
    face = (s > crest_slope_deg) & (drop > relief)
    near_face = ndimage.binary_dilation(face, structure=np.ones((3, 3)), iterations=max(1, int(round(1.5 / cell))))
    top = (ndimage.maximum_filter(zz, size=max(3, int(round(5 / cell)) | 1)) - zz) < 0.75
    crest = (~face) & near_face & top
    return crest


def avalanche(z, mobile, cell, tanphi, tol=0.01, max_iter=6000, floor=None):
    """Relax slopes steeper than the angle of repose by moving mobile material
    to lower neighbours. Volume (height x area) is conserved exactly."""
    z = z.copy()
    mob = mobile.copy()
    ny, nx = z.shape
    dist = np.array([cell * np.hypot(a, b) for a, b in _OFFS])
    it = 0
    for it in range(max_iter):
        zp = np.pad(z, 1, constant_values=np.inf)
        ex = np.empty((8, ny, nx))
        for k, (dj, di) in enumerate(_OFFS):
            zn = zp[1 + dj:1 + dj + ny, 1 + di:1 + di + nx]
            ex[k] = np.maximum(0.0, (z - zn) - dist[k] * tanphi)
        E = ex.sum(0)
        D = ex.max(0)
        out = np.minimum(0.5 * D, mob)
        if out.max() < tol:
            break
        with np.errstate(invalid="ignore", divide="ignore"):
            share = np.where(E > 0, ex / E, 0.0) * out
        z -= out
        mob -= out
        for k, (dj, di) in enumerate(_OFFS):
            q = share[k]
            # receiver of flow from (j,i) is (j+dj, i+di)
            js = slice(max(0, -dj), ny - max(0, dj))
            jd = slice(max(0, dj), ny - max(0, -dj))
            is_ = slice(max(0, -di), nx - max(0, di))
            id_ = slice(max(0, di), nx - max(0, -di))
            z[jd, id_] += q[js, is_]
            mob[jd, id_] += q[js, is_]
    return z, it


def disc(shape, j, i, r_cells):
    ny, nx = shape
    J, I = np.ogrid[:ny, :nx]
    return (J - j) ** 2 + (I - i) ** 2 <= r_cells ** 2


def place_loads(z0, loads_xy_vol, g, fcfg, rng=None, push_jitter=0.0, sequential=False, B=None, crest_region=None):
    """Push each load to the nearest crest and let it avalanche.
    loads_xy_vol: array (n,3) of x, y, volume.  Returns final surface and, if
    sequential, a list of per-load footprints (thickness arrays)."""
    tanphi = np.tan(np.radians(fcfg["repose_deg"]))
    r = max(1, int(round(fcfg["deposit_radius"] / g.cell)))
    z = z0.copy()
    feet = []
    batch = loads_xy_vol if sequential else loads_xy_vol
    def _crest(zz):
        c = crest_mask(zz, g.cell, fcfg["crest_slope_deg"])
        if crest_region is not None:
            c &= crest_region
        return c

    crest = _crest(z)
    mobile_total = np.zeros_like(z)
    for n, (x, y, v) in enumerate(batch):
        if sequential and n % 1 == 0:
            crest = _crest(z)
        if not crest.any():
            crest = np.ones_like(z, bool)
        xx, yy = x, y
        if rng is not None and push_jitter > 0:
            xx += rng.normal(0, push_jitter); yy += rng.normal(0, push_jitter)
        j = int(np.clip((yy - g.y0) // g.cell, 0, g.ny - 1))
        i = int(np.clip((xx - g.x0) // g.cell, 0, g.nx - 1))
        _, (tj, ti) = ndimage.distance_transform_edt(~crest, return_indices=True)
        cj, ci = tj[j, i], ti[j, i]
        # push over the edge: move the release point down-slope onto the face
        zs = ndimage.gaussian_filter(z, 1.5 / g.cell)
        gy_, gx_ = np.gradient(zs, g.cell)
        ux, uy = -gx_[cj, ci], -gy_[cj, ci]
        nrm = np.hypot(ux, uy)
        if nrm > 0:
            off = fcfg.get("release_offset", 2.0) / g.cell + r
            cj = int(np.clip(round(cj + uy / nrm * off), 0, g.ny - 1))
            ci = int(np.clip(round(ci + ux / nrm * off), 0, g.nx - 1))
        m = disc(z.shape, cj, ci, r)
        add = np.zeros_like(z)
        add[m] = v / (m.sum() * g.area)
        if sequential:
            z_before = z.copy()
            z, _ = avalanche(z + add, add, g.cell, tanphi, fcfg["ca_tol"], fcfg["ca_max_iter"])
            feet.append(z - z_before)
        else:
            z = z + add
            mobile_total += add
    if not sequential:
        z, _ = avalanche(z, mobile_total, g.cell, tanphi, fcfg["ca_tol"], fcfg["ca_max_iter"])
    return z, feet


def place_at_dump(z0, loads_xy_vol, g, fcfg):
    """Baseline: no dozer push - each load relaxes where it was dumped."""
    tanphi = np.tan(np.radians(fcfg["repose_deg"]))
    r = max(1, int(round(fcfg["deposit_radius"] / g.cell)))
    add = np.zeros_like(z0)
    for x, y, v in loads_xy_vol:
        j = int(np.clip((y - g.y0) // g.cell, 0, g.ny - 1))
        i = int(np.clip((x - g.x0) // g.cell, 0, g.nx - 1))
        m = disc(z0.shape, j, i, r)
        add[m] += v / (m.sum() * g.area)
    z, _ = avalanche(z0 + add, add, g.cell, tanphi, fcfg["ca_tol"], fcfg["ca_max_iter"])
    return z
