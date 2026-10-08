"""Material-movement algorithm: Constrained Push-and-Settle Transport (CPST).

For each survey period s (previous survey -> survey s) the algorithm

  1. derives the observed accumulation field from the survey change solid
     (fill capacity per 1 m column) and any cuts on previously observed cells;
  2. computes a dozer push cost from every source (truck load, carried-over
     platform parcel, cut cell) to every fill cell = slope-aware geodesic
     distance over the pre-period surface (uphill pushes penalised, pushes
     longer than the maximum push distance forbidden);
  3. allocates source volume to fill volume by entropy-regularised optimal
     transport (Sinkhorn) with two dummy nodes:
        U  'unattributed' source: observed fill that the FMS cannot explain,
        R  'retained'    sink  : FMS volume not seen on the surveyed face,
           which stays on the unsurveyed platform and is carried forward;
     (partial optimal transport). epsilon is the mixing length;
  4. deposits the allocated mixture as a new layer on each fill column
     (gravity / repose behaviour is honoured because the layer top is the
     surveyed surface, whose face is at the angle of repose);
  5. the updated column stack is the initial condition of the next period.

All quantities moved are extensive (volume, tonnes, metal), so mass and
metal are conserved exactly by construction (verified in validation.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.special import logsumexp

from .surfaces import fit_base_plane, infer_surface, model_domain

# ---------------------------------------------------------------- properties
PROPS = ["VOL", "T_F", "CU_F", "AU_F", "AG_F", "T_U", "CU_U", "AU_U", "AG_U",
         "T_L", "CU_L", "AU_L", "AG_L", "CU2_F", "AU2_F", "AGE_F", "MSQ_F", "T_R"]
P = {k: i for i, k in enumerate(PROPS)}
NP = len(PROPS)
# CU_* in tonnes of Cu (grade % / 100 * t); AU_*, AG_* in kg (g/t * t / 1000)
# CU2_F = sum m*cu^2 (for within-block heterogeneity); AGE_F = sum m * days
# MSQ_F = sum of squared load contributions (effective number of loads)
# T_R  = FMS tonnes that were never reconciled with a survey (provisional)


def load_props(m, cu, au, ag, day, provisional=False):
    v = np.zeros(NP)
    v[P["T_F"]] = m
    v[P["CU_F"]] = m * cu / 100.0
    v[P["AU_F"]] = m * au / 1000.0
    v[P["AG_F"]] = m * ag / 1000.0
    v[P["CU2_F"]] = m * cu * cu
    v[P["AU2_F"]] = m * au * au
    v[P["AGE_F"]] = m * day
    if provisional:
        v[P["T_R"]] = m
    return v


def bulk_props(vol, rho, cu, au, ag, cls):
    """Props of `vol` m3 of unattributed ('U') or legacy ('L') material."""
    v = np.zeros(NP)
    t = vol * rho
    v[P["VOL"]] = vol
    v[P[f"T_{cls}"]] = t
    v[P[f"CU_{cls}"]] = t * cu / 100.0
    v[P[f"AU_{cls}"]] = t * au / 1000.0
    v[P[f"AG_{cls}"]] = t * ag / 1000.0
    return v


# ------------------------------------------------------------ column model
class ColumnModel:
    """Stratigraphic column per grid cell: list of [z_bottom, z_top, props]."""

    def __init__(self, ny, nx):
        self.ny, self.nx = ny, nx
        self.layers: dict[int, list] = {}
        self.top = np.full(ny * nx, np.nan)

    def has(self, c):
        return c in self.layers

    def start(self, c, z):
        self.layers[c] = []
        self.top[c] = z

    def add(self, c, thickness, props):
        if thickness <= 0:
            return
        zb = self.top[c]
        self.layers[c].append([zb, zb + thickness, props])
        self.top[c] = zb + thickness

    def remove_top(self, c, dz):
        """Remove dz metres from the top of column c; return removed props."""
        out = np.zeros(NP)
        lay = self.layers.get(c, [])
        need = dz
        while need > 1e-12 and lay:
            zb, zt, pr = lay[-1]
            th = zt - zb
            if th <= need + 1e-12:
                out += pr
                lay.pop()
                need -= th
            else:
                f = need / th
                part = pr * f
                part[P["MSQ_F"]] = pr[P["MSQ_F"]] * f * f
                rest = pr * (1 - f)
                rest[P["MSQ_F"]] = pr[P["MSQ_F"]] * (1 - f) ** 2
                out += part
                lay[-1] = [zb, zt - need, rest]
                need = 0.0
        self.top[c] = lay[-1][1] if lay else self.top[c] - (dz - need)
        return out

    def totals(self):
        tot = np.zeros(NP)
        for lay in self.layers.values():
            for _, _, pr in lay:
                tot += pr
        return tot


# ----------------------------------------------------------------- helpers
def geodesic_cost(surface, domain, cell, alpha, src_cells, limit):
    """Directed 8-neighbour graph over domain cells; edge weight
    w = l + alpha * max(0, z_j - z_i)  (uphill penalty).  Returns dict
    src_cell -> distance array over all grid cells (inf outside limit)."""
    ny, nx = surface.shape
    idx = -np.ones(ny * nx, dtype=np.int64)
    dom = domain.ravel() & np.isfinite(surface.ravel())
    idx[dom] = np.arange(dom.sum())
    z = surface.ravel()
    rows, cols, wts = [], [], []
    J, I = np.divmod(np.arange(ny * nx), nx)
    for dj, di in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        j2, i2 = J + dj, I + di
        ok = dom & (j2 >= 0) & (j2 < ny) & (i2 >= 0) & (i2 < nx)
        a = np.nonzero(ok)[0]
        b = j2[ok] * nx + i2[ok]
        ok2 = dom[b]
        a, b = a[ok2], b[ok2]
        length = cell * np.hypot(dj, di)
        w = length + alpha * np.maximum(0.0, z[b] - z[a])
        rows.append(idx[a]); cols.append(idx[b]); wts.append(w)
    n = int(dom.sum())
    G = coo_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    src = np.asarray(src_cells)
    src_nodes = idx[src]
    if (src_nodes < 0).any():
        raise ValueError("source outside domain")
    uniq, inv = np.unique(src_nodes, return_inverse=True)
    D = dijkstra(G, directed=True, indices=uniq, limit=limit)
    full = np.full((len(uniq), ny * nx), np.inf)
    full[:, dom] = D
    return full[inv]


def sinkhorn(a, b, C, eps, tol=1e-6, max_iter=5000):
    """Log-domain entropic OT. Rows are re-scaled at the end so that every
    source is conserved exactly; the column residual is returned."""
    logK = -C / eps
    la, lb = np.log(a), np.log(b)
    u = np.zeros(len(a)); v = np.zeros(len(b))
    err = np.inf
    it = 0
    for it in range(1, max_iter + 1):
        u = la - logsumexp(logK + v[None, :], axis=1)
        v = lb - logsumexp(logK + u[:, None], axis=0)
        if it % 10 == 0 or it == max_iter:
            rows = np.exp(logsumexp(logK + v[None, :], axis=1) + u)
            err = np.abs(rows - a).sum() / a.sum()
            if err < tol:
                break
    Pm = np.exp(logK + u[:, None] + v[None, :])
    Pm *= (a / np.maximum(Pm.sum(1), 1e-300))[:, None]
    col_err = np.abs(Pm.sum(0) - b).sum() / b.sum()
    return Pm, float(col_err), it


# ------------------------------------------------------------------ loads
def density_factors(cfg, perturb=None, ds=None):
    """A-06: (volume factor f_v, payload factor f_pay). In-pile volume of a
    load = T * f_v / Dens; true tonnes = T * f_pay; in-pile density =
    Dens * f_pay / f_v. f_v = "auto" is resolved by spbm.volume.calibrate."""
    d = cfg["density"]
    fpay = float(d.get("payload_factor", 1.0))
    if perturb and perturb.get("payload_factor") is not None:
        fpay = float(perturb["payload_factor"])
    if perturb and perturb.get("volume_factor") is not None:
        return float(perturb["volume_factor"]), fpay
    fv = d["volume_factor"]
    if fv == "auto":
        fv = d.get("volume_factor_resolved")
        if fv is None or d.get("volume_factor_cutoff") != cfg["time"]["survey_cutoff_hours"]:
            if ds is None:
                raise ValueError("density.volume_factor is 'auto' but not resolved - call spbm.volume.resolve_density first")
            from .volume import resolve_density
            fv = resolve_density(ds, cfg)["density"]["volume_factor_resolved"]
    return float(fv), fpay


def _outside_domain(ds, x, y, limit_m=100.0):
    """LOC_OUTSIDE_DOMAIN: dump more than `limit_m` from every survey solid."""
    from scipy import ndimage
    g = ds.grid
    obs = np.zeros((g.ny, g.nx), bool)
    for s in ds.surveys:
        obs |= s.mask
    dist = ndimage.distance_transform_edt(~obs) * g.cell
    j, i, inside = g.index(x, y)
    d = np.where(inside, dist[np.clip(j, 0, g.ny - 1), np.clip(i, 0, g.nx - 1)], np.inf)
    return d > limit_m


def prepare_loads(ds, cfg, rng=None, perturb=None, exclude_ids=()):
    """Standardised load table used by the engine. `perturb` (Monte Carlo)
    may contain gps_sigma, payload_cv, assay_cv, volume_factor, payload_factor."""
    from .rules import model_exclusions
    f = ds.fms.copy()
    f = f[~model_exclusions(f, cfg).values]          # QA error rules (spbm/rules.py)
    iv = getattr(ds, "interventions", None)
    excl = set(exclude_ids)
    unknown_ids = set()
    if iv is not None and len(iv):
        excl |= {int(float(t)) for t in iv.loc[iv["type"] == "fms_exclude", "target"]}
        unknown_ids = {int(float(t)) for t in iv.loc[iv["type"] == "fms_location_unknown", "target"]}
    f = f[~f["cycle_id"].isin(excl)]
    # TIME_BEFORE_FIRST_INTERVAL: belongs to the pre-record pile
    times = [s.datetime for s in ds.surveys]
    first_start = times[0] - pd.Timedelta(hours=float(cfg["time"].get("first_interval_hours", 24.0)))
    f = f[f["timestamp"] > first_start]
    fv, fpay = density_factors(cfg, perturb, ds)
    kappa = fpay / fv
    m = f["payload_t"].values.astype(float) * fpay
    cu, au, ag = f["cu_pct"].values.astype(float), f["au_gpt"].values.astype(float), f["ag_gpt"].values.astype(float)
    x, y = f["x"].values.astype(float), f["y"].values.astype(float)
    if perturb:
        rng = rng or np.random.default_rng()
        n = len(f)
        if perturb.get("gps_sigma"):
            x = x + rng.normal(0, perturb["gps_sigma"], n)
            y = y + rng.normal(0, perturb["gps_sigma"], n)
        if perturb.get("payload_cv"):
            m = m * np.clip(1 + rng.normal(0, perturb["payload_cv"], n), 0.5, 1.5)
        if perturb.get("assay_cv"):
            sig = f["grade_group"].values if "grade_group" in f else pd.factorize(
                f[["cu_pct", "au_gpt", "ag_gpt"]].astype(str).agg("|".join, axis=1))[0]
            ug = np.unique(sig)
            mult = {k: np.clip(1 + rng.normal(0, perturb["assay_cv"], 3), 0.5, 1.5) for k in ug}
            M = np.array([mult[k] for k in sig])
            cu, au, ag = cu * M[:, 0], au * M[:, 1], ag * M[:, 2]
    # A-32: an X/Y/Z shared by >= repeated_location_min records is a default /
    # stuck FMS position (QA rule LOC_DEFAULT): the location is UNKNOWN.
    rep = f.groupby(["x", "y", "z"])["cycle_id"].transform("size").values >= cfg.get("fms", {}).get("repeated_location_min", 3)
    rep |= f["cycle_id"].isin(unknown_ids).values
    rep |= _outside_domain(ds, f["x"].values.astype(float), f["y"].values.astype(float))   # LOC_OUTSIDE_DOMAIN
    rho = f["density"].values.astype(float) * kappa
    t0 = pd.Timestamp(ds.surveys[0].datetime.normalize())
    out = pd.DataFrame({
        "cycle_id": f["cycle_id"].values, "time": f["timestamp"].values,
        "x": x, "y": y, "z": f["z"].values, "m": m, "m_recorded": f["payload_t"].values.astype(float),
        "cu": cu, "au": au, "ag": ag, "rho": rho, "dens_fms": f["density"].values.astype(float),
    })
    out["vol"] = out["m"] / out["rho"]
    out["day"] = (pd.to_datetime(out["time"]) - t0).dt.total_seconds() / 86400.0
    edges = [first_start] + times
    per = np.searchsorted(np.array(edges, dtype="datetime64[ns]"), out["time"].values.astype("datetime64[ns]"), side="left") - 1
    # per == -1 : before record ; per == len(times) : after last survey (provisional)
    out["period"] = per
    out["x_raw"], out["y_raw"] = f["x"].values.astype(float), f["y"].values.astype(float)
    out["loc_unknown"] = rep
    if rep.any():
        # placeholder position (period centroid of located dumps) - used only to
        # index a graph node; the push cost of these loads is set uniform.
        good = ~rep
        for i in np.nonzero(rep)[0]:
            same = good & (per == per[i])
            if same.sum() == 0:
                same = good
            wgt = out["m"].values[same]
            out.loc[i, "x"] = np.average(out["x"].values[same], weights=wgt)
            out.loc[i, "y"] = np.average(out["y"].values[same], weights=wgt)
    return out.sort_values("time").reset_index(drop=True)


def impute_grade(loads, period, cfg, rng=None):
    """A-21: grade/density of unattributed fill."""
    sel = loads[(loads["period"] >= period - 1) & (loads["period"] <= period + 1) & (loads["period"] >= 0)]
    if len(sel) == 0:
        sel = loads
    if rng is not None:
        k = rng.choice(len(sel), size=len(sel), p=(sel["m"] / sel["m"].sum()).values)
        sel = sel.iloc[k]
    w = sel["m"].values
    return (np.average(sel["cu"], weights=w), np.average(sel["au"], weights=w),
            np.average(sel["ag"], weights=w), np.average(sel["rho"], weights=w))


# ------------------------------------------------------------------ engine
@dataclass
class Reconstruction:
    cfg: dict
    grid: object
    B: np.ndarray
    base: dict
    domain: np.ndarray
    cols: ColumnModel
    loads: pd.DataFrame
    periods: pd.DataFrame
    destinations: pd.DataFrame
    observed_top: np.ndarray       # latest surveyed top surface per cell (NaN = never surveyed)
    ever_observed: np.ndarray
    first_period: np.ndarray       # period in which a cell first received fill (-1 none)
    legacy_top: np.ndarray
    plans: list = field(default_factory=list)
    legacy_props: dict = field(default_factory=dict)
    totals_in: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)


def reconstruct(ds, cfg, loads=None, rng=None, survey_bias=None, keep_plans=False, verbose=False):
    g = ds.grid
    ny, nx = g.ny, g.nx
    A = g.area
    mv = cfg["movement"]
    tau = cfg["survey"]["lod_k"] * np.sqrt(2) * cfg["survey"]["sigma_z"]
    repose = cfg["infill"]["repose_deg"]
    base = fit_base_plane(ds, cfg)
    B = base["B"]
    domain = model_domain(ds)
    if loads is None:
        loads = prepare_loads(ds, cfg)
    loads = loads.copy()
    # snap dump cells into the domain
    jj, ii, _ = g.index(loads["x"].values, loads["y"].values)
    cell = jj * nx + ii
    dom_flat = domain.ravel()
    if (~dom_flat[cell]).any():
        from scipy import ndimage
        _, (dj, di) = ndimage.distance_transform_edt(~domain, return_indices=True)
        bad = ~dom_flat[cell]
        cell[bad] = dj.ravel()[cell[bad]] * nx + di.ravel()[cell[bad]]
    loads["cell"] = cell

    # legacy (pre-record) material properties - A-22
    w = loads["m"].values
    leg = {"rho": cfg["density"]["legacy_density"] or float(np.average(loads["rho"], weights=w)),
           "cu": float(np.average(loads["cu"], weights=w)), "au": float(np.average(loads["au"], weights=w)),
           "ag": float(np.average(loads["ag"], weights=w))}

    cols = ColumnModel(ny, nx)
    observed = np.zeros(ny * nx, bool)
    obs_top = np.full(ny * nx, np.nan)
    first_period = -np.ones(ny * nx, int)
    legacy_top = np.full(ny * nx, np.nan)
    Bf = B.ravel()
    S = len(ds.surveys)
    bias = np.zeros(S + 1) if survey_bias is None else np.asarray(survey_bias)  # bias[s+1] for survey s, bias[0] pre-record

    carried = []  # parcels: dict(load_idx, vol, cell)
    rows, dest_rows, plans, snapshots = [], [], [], []
    tot_in = np.zeros(NP)

    for s, sv in enumerate(ds.surveys):
        top = (sv.top + bias[s + 1]).ravel()
        bot = (sv.bot + bias[s]).ravel()
        foot = np.isfinite(top)
        fc = np.nonzero(foot)[0]
        new_cells = fc[~observed[fc]]
        old_cells = fc[observed[fc]]
        # --- previously observed cells: lowering below the model surface = cut
        # (solids record accretion only, so an elevation decrease shows up as a
        # solid bottom below the earlier surface); raising = unobserved fill.
        mis = bot[old_cells] - cols.top[old_cells]
        frac_up = float((mis > tau).mean()) if len(old_cells) else 0.0
        frac_down = float((mis < -tau).mean()) if len(old_cells) else 0.0
        cal_gap = s > 0 and (sv.datetime - ds.surveys[s - 1].datetime) > pd.Timedelta("36h")
        gap = bool(s > 0 and (frac_up > 0.10 or cal_gap))
        # --- prior surface for first-time cells
        prior_new = bot[new_cells].copy()
        gap_fill_new = 0.0
        if s > 0 and len(new_cells) and cfg["infill"].get("front_unobserved_fill", True):
            # A-13b: a first-surveyed cell lying IN FRONT of a previously surveyed
            # face must have been at most the repose-angle extrapolation of that
            # face; a solid bottom above it means fill that no change solid
            # captured (toe-clipped solids, missing surveys). That volume belongs
            # to this period, not to the legacy pile. Platform cells keep the
            # surveyed bottom.
            known = observed.reshape(ny, nx)
            zk = np.where(known, cols.top.reshape(ny, nx), np.nan)
            inf_s, side_s = infer_surface(np.nan_to_num(zk), known, B, domain, g.cell, repose)
            inf_new = inf_s.ravel()[new_cells]
            front = side_s.ravel()[new_cells] == 2
            use = front & np.isfinite(inf_new) & (inf_new < prior_new - tau)
            gap_fill_new = float(((prior_new - inf_new)[use]).sum() * A)
            prior_new = np.where(use, inf_new, prior_new)
        for c, z in zip(new_cells, prior_new):
            zb = min(Bf[c], z)
            cols.start(c, zb)
            th = max(0.0, z - zb)
            if th > 0:
                cols.add(c, th, bulk_props(th * A, leg["rho"], leg["cu"], leg["au"], leg["ag"], "L"))
            legacy_top[c] = z
        observed_before = observed.copy()
        observed[fc] = True
        # --- cuts (re-handled material) then the fill field
        cut_sel = old_cells[mis < -tau]
        cut_depth = -mis[mis < -tau]
        removed_list = [cols.remove_top(c, d) for c, d in zip(cut_sel, cut_depth)]
        dZ = top[fc] - cols.top[fc]
        fill_m = dZ > tau
        neg = (dZ < -tau) & observed_before[fc]
        for c, d in zip(fc[neg], -dZ[neg]):           # surface lowered below the new top too
            cut_sel = np.r_[cut_sel, c]
            removed_list.append(cols.remove_top(c, d))
        fill_cells, fill_cap = fc[fill_m], dZ[fill_m] * A
        noise_vol = float(dZ[~fill_m & ~neg].sum() * A)
        obs_top[fc] = top[fc]
        # --- sources
        src_props, src_vol, src_cell, src_kind, src_msq, src_load = [], [], [], [], [], []
        for p in carried:
            ld = loads.iloc[p["load"]]
            pr = load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day) / ld.vol
            pr[P["VOL"]] = 1.0
            src_props.append(pr); src_vol.append(p["vol"]); src_cell.append(ld.cell)
            src_kind.append("carried"); src_msq.append((ld.m / ld.vol) ** 2); src_load.append(p["load"])
        per_loads = np.nonzero(loads["period"].values == s)[0]
        for k in per_loads:
            ld = loads.iloc[k]
            pr = load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day) / ld.vol
            pr[P["VOL"]] = 1.0
            src_props.append(pr); src_vol.append(ld.vol); src_cell.append(ld.cell)
            src_kind.append("load"); src_msq.append((ld.m / ld.vol) ** 2); src_load.append(k)
            tot_in += load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day) + np.eye(NP)[P["VOL"]] * ld.vol
        for c, removed in zip(cut_sel, removed_list):
            vv = max(removed[P["VOL"]], 1e-12)
            pr = removed / vv
            src_props.append(pr); src_vol.append(vv); src_cell.append(c)
            src_kind.append("cut"); src_msq.append(removed[P["MSQ_F"]] / vv ** 2); src_load.append(-1)
        V_src = float(np.sum(src_vol)) if src_vol else 0.0
        V_fill = float(fill_cap.sum())
        imp = impute_grade(loads, s, cfg, rng if rng is not None and cfg.get("_mc_impute") else None)
        stat = {"period": s, "survey": sv.file, "start": ds.surveys[s - 1].datetime if s else None,
                "end": sv.datetime, "gap_detected": gap, "frac_raised": frac_up, "frac_lowered": frac_down,
                "n_loads": len(per_loads), "n_carried_in": len(carried),
                "fms_tonnes": float(loads["m"].values[per_loads].sum()),
                "fms_volume": float(loads["vol"].values[per_loads].sum()),
                "carried_in_volume": float(sum(p["vol"] for p in carried)),
                "solid_volume": float(np.nansum(sv.thickness) * A),
                "fill_volume": V_fill, "cut_volume": float(sum(r[P["VOL"]] for r in removed_list)), "noise_volume": noise_vol,
                "unobserved_fill_new_cells": gap_fill_new, "n_fill_cells": int(len(fill_cells)),
                "imp_cu": imp[0], "imp_au": imp[1], "imp_ag": imp[2], "imp_rho": imp[3]}
        carried = []
        if len(fill_cells) == 0 and V_src == 0:
            stat.update(placed_volume=0.0, unattributed_volume=0.0, retained_volume=0.0, sinkhorn_col_err=0.0, sinkhorn_iter=0)
            rows.append(stat)
            continue
        # --- cost matrix
        surf = np.where(np.isfinite(cols.top), cols.top, np.nan).reshape(ny, nx)
        known = np.isfinite(surf)
        surf_full, _ = infer_surface(np.nan_to_num(surf), known, B, domain, g.cell, repose)
        nS = len(src_vol)
        nF = len(fill_cells)
        C = np.full((nS + 1, nF + 1), np.inf)
        if nS:
            D = geodesic_cost(surf_full, domain, g.cell, mv["alpha_up"], np.asarray(src_cell), mv["max_push"])
            C[:nS, :nF] = D[:, fill_cells]
            C[:nS, nF] = mv["retain_cost"]
            # A-32: loads with an unknown dump location (default FMS position)
            # get a uniform push cost: they fill whatever part of the period's
            # fill the located loads do not claim.
            unk = np.array([src_kind[i] in ("load", "carried") and bool(loads["loc_unknown"].values[src_load[i]])
                            for i in range(nS)])
            if unk.any():
                known_c = C[:nS, :nF][~unk]
                fin = known_c[np.isfinite(known_c)]
                C[np.nonzero(unk)[0], :nF] = float(np.median(fin)) if fin.size else 0.5 * mv["max_push"]
        C[nS, :nF] = mv["unattributed_cost"]
        C[nS, nF] = 0.0
        a = np.r_[np.asarray(src_vol, float), max(V_fill, 1e-9)]
        b = np.r_[fill_cap, max(V_src, 1e-9)]
        fill_map = np.zeros(ny * nx); fill_map[fill_cells] = fill_cap / A
        snapshots.append({"period": s, "surface_before": surf_full, "fill": fill_map.reshape(ny, nx),
                          "observed_before": observed_before.reshape(ny, nx).copy()})
        Pm, col_err, nit = sinkhorn(a, b, C, mv["epsilon"], mv["sinkhorn_tol"], mv["sinkhorn_max_iter"])
        # --- trace retained fragments (entropic leakage < min_carry m3) are folded back
        #     into the same source's destinations, so mass stays exact and no
        #     microscopic parcels are carried forward
        min_carry = 0.05
        for i in range(nS):
            r_ = Pm[i, nF]
            placed = Pm[i, :nF].sum()
            if 0 < r_ < min_carry and placed > 0:
                Pm[i, :nF] *= (placed + r_) / placed
                Pm[i, nF] = 0.0
        # --- deposit
        U_vol = Pm[nS, :nF]
        Pi = np.asarray(src_props) if nS else np.zeros((0, NP))
        msq = np.asarray(src_msq) if nS else np.zeros(0)
        layer = Pm[:nS, :nF].T @ Pi if nS else np.zeros((nF, NP))
        layer[:, P["MSQ_F"]] = (Pm[:nS, :nF] ** 2).T @ msq if nS else 0.0
        up = bulk_props(1.0, imp[3], imp[0], imp[1], imp[2], "U")
        layer += U_vol[:, None] * up[None, :]
        zb_dep = cols.top[fill_cells].copy()
        for jcell, c in enumerate(fill_cells):
            cols.add(c, layer[jcell, P["VOL"]] / A, layer[jcell])
        zt_dep = cols.top[fill_cells].copy()
        first_period[fill_cells[first_period[fill_cells] < 0]] = s
        # --- retained parcels carry over (load sources only; cut leftovers re-deposited in place)
        ret = Pm[:nS, nF]
        for i in range(nS):
            if ret[i] <= 1e-9:
                continue
            if src_kind[i] in ("load", "carried"):
                carried.append({"load": src_load[i], "vol": float(ret[i])})
            else:
                pr = src_props[i] * ret[i]
                pr[P["MSQ_F"]] = src_msq[i] * ret[i] ** 2
                cols.add(src_cell[i], ret[i] / A, pr)
        # --- destination record per source
        X, Y = g.mesh()
        fx, fy = X.ravel()[fill_cells], Y.ravel()[fill_cells]
        for i in range(nS):
            if src_kind[i] == "cut":
                continue
            w_ = Pm[i, :nF]
            tot = w_.sum()
            ld = loads.iloc[src_load[i]]
            d_ = C[i, :nF]
            rec = {"cycle_id": ld.cycle_id, "period": s, "kind": src_kind[i], "loc_unknown": bool(ld.loc_unknown), "volume_in": src_vol[i],
                   "placed_volume": tot, "retained_volume": ret[i], "dump_x": ld.x, "dump_y": ld.y}
            if tot > 1e-9:
                fin = np.isfinite(d_)
                rec.update(dest_x=float((w_ * fx).sum() / tot), dest_y=float((w_ * fy).sum() / tot),
                           mean_push=float((w_[fin] * d_[fin]).sum() / max(w_[fin].sum(), 1e-12)),
                           spread=float(np.sqrt((w_ * ((fx - (w_ * fx).sum() / tot) ** 2 + (fy - (w_ * fy).sum() / tot) ** 2)).sum() / tot)))
            dest_rows.append(rec)
        if keep_plans:
            plans.append({"period": s, "src_kind": src_kind, "src_load": src_load, "fill_cells": fill_cells,
                          "P": Pm.astype(np.float32), "zb": zb_dep, "zt": zt_dep})
        stat.update(placed_volume=float(Pm[:nS, :nF].sum()), unattributed_volume=float(U_vol.sum()),
                    retained_volume=float(ret.sum()), sinkhorn_col_err=col_err, sinkhorn_iter=nit)
        rows.append(stat)
        if verbose:
            print(f"  period {s} {sv.file}: fill {V_fill:7.0f} m3  src {V_src:7.0f}  U {U_vol.sum():6.0f}  R {ret.sum():6.0f}  it {nit}  err {col_err:.1e}")

    reconciled_surface = cols.top.reshape(ny, nx).copy()
    # ---------------------------------------------------- after last survey
    # legacy columns for never-surveyed domain cells (A-13): unchanged since
    # the start of the record, so inferred from the pre-record surface.
    known = np.isfinite(legacy_top).reshape(ny, nx)
    lt_full, side = infer_surface(np.nan_to_num(legacy_top.reshape(ny, nx)), known, B, domain, g.cell, repose)
    for c in np.nonzero(domain.ravel() & ~known.ravel())[0]:
        z = lt_full.ravel()[c]
        if not np.isfinite(z):
            continue
        zb = min(Bf[c], z)
        cols.start(c, zb)
        th = max(0.0, z - zb)
        if th > 0:
            cols.add(c, th, bulk_props(th * A, leg["rho"], leg["cu"], leg["au"], leg["ag"], "L"))
        legacy_top[c] = z
    # unreconciled FMS volume: carried parcels + loads after the last survey
    post = np.nonzero(loads["period"].values >= S)[0]
    pre = np.nonzero(loads["period"].values < 0)[0]
    # (a) parcels retained on the platform: spread around their dump point over
    #     cells that no survey has seen (the surveys say surveyed cells did not
    #     receive them);  (b) loads after the last survey: provisional nowcast
    #     with the forward physics model (push to crest + avalanche).
    pending = [(p["load"], p["vol"], "retained") for p in carried] + [(k, loads.iloc[k].vol, "retained") for k in pre]
    X, Y = g.mesh()
    Xf, Yf = X.ravel(), Y.ravel()
    sig = cfg["movement"]["retain_sigma"]
    unobs_cells = np.nonzero(domain.ravel() & ~observed)[0]
    if len(unobs_cells) == 0:
        unobs_cells = np.nonzero(domain.ravel())[0]
    placements = []
    for k, vol, how in pending:
        ld = loads.iloc[k]
        if k in pre:
            tot_in += load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day) + np.eye(NP)[P["VOL"]] * ld.vol
        d2 = (Xf[unobs_cells] - ld.x) ** 2 + (Yf[unobs_cells] - ld.y) ** 2
        wk = np.exp(-0.5 * d2 / sig ** 2)
        wk[d2 > (3 * sig) ** 2] = 0
        if wk.sum() == 0:
            wk[np.argsort(d2)[:9]] = 1
        wk /= wk.sum()
        placements.append((k, vol, how, unobs_cells[wk > 0], vol * wk[wk > 0]))
    if len(post):
        from . import forward as fw
        from scipy import ndimage as ndi
        from .surfaces import extend_outside
        zcur = extend_outside(np.where(domain, cols.top.reshape(ny, nx), np.nan), domain)
        creg = ndi.binary_dilation(observed.reshape(ny, nx), iterations=2)
        _, feet = fw.place_loads(zcur, loads.iloc[post][["x", "y", "vol"]].values, g, cfg["forward"], sequential=True, crest_region=creg)
        for k, ft in zip(post, feet):
            ld = loads.iloc[k]
            tot_in += load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day) + np.eye(NP)[P["VOL"]] * ld.vol
            fc_ = np.nonzero((ft.ravel() > 1e-6) & domain.ravel())[0]
            v_ = ft.ravel()[fc_] * A
            v_ *= ld.vol / v_.sum()
            placements.append((k, ld.vol, "nowcast", fc_, v_))
    for k, vol, how, cells_, vols_ in placements:
        ld = loads.iloc[k]
        base_pr = load_props(ld.m, ld.cu, ld.au, ld.ag, ld.day, provisional=True) / ld.vol
        base_pr[P["VOL"]] = 1.0
        pzb, pzt = [], []
        for c, v in zip(cells_, vols_):
            pr = base_pr * v
            pr[P["MSQ_F"]] = (ld.m / ld.vol * v) ** 2
            if not cols.has(c):
                cols.start(c, Bf[c])
            pzb.append(cols.top[c])
            cols.add(c, v / A, pr)
            pzt.append(cols.top[c])
        if keep_plans:
            plans.append({"period": int(ld.period), "provisional": True, "load": k, "cells": np.asarray(cells_),
                          "vol": np.asarray(vols_), "zb": np.array(pzb), "zt": np.array(pzt)})
        dx_ = float(np.average(Xf[cells_], weights=vols_)); dy_ = float(np.average(Yf[cells_], weights=vols_))
        dest_rows.append({"cycle_id": ld.cycle_id, "period": int(ld.period), "kind": "provisional-" + how,
                          "volume_in": vol, "placed_volume": 0.0, "retained_volume": vol,
                          "dump_x": ld.x, "dump_y": ld.y, "dest_x": dx_, "dest_y": dy_,
                          "mean_push": float(np.hypot(dx_ - ld.x, dy_ - ld.y)), "spread": np.nan})

    periods = pd.DataFrame(rows)
    dest = pd.DataFrame(dest_rows)
    return Reconstruction(cfg, g, B, base, domain, cols, loads, periods, dest,
                          obs_top.reshape(ny, nx), observed.reshape(ny, nx), first_period.reshape(ny, nx),
                          legacy_top.reshape(ny, nx), plans, leg, {k: float(v) for k, v in zip(PROPS, tot_in)},
                          {"tau": tau, "side": side, "t0": ds.surveys[0].datetime.normalize(),
                           "snapshots": snapshots, "final_surface": cols.top.reshape(ny, nx).copy(),
                           "reconciled_surface": reconciled_surface})
