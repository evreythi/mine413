"""Local web front end:  python -m spbm serve  ->  http://127.0.0.1:8413

A small standard-library HTTP server that serves one page (spbm/webui/
index.html) and a JSON API around the normal command line:

    GET  /api/ping              {"app": "spbm"} (used by SPBM.html and the launchers)
    GET  /api/state             inbox files, registered inputs, current/last job
    PUT  /api/upload?name=F     store the request body as data/inbox/F (.csv/.dxf/.zip)
    GET  /api/params            editable parameters: official and custom values
    POST /api/params            {"values": {key: value}} or {"yaml": text} -> config/project_custom.yaml
    POST /api/params/reset      delete the custom configuration
    POST /api/run               {"mode": "fast"|"full", "mc": n, "config": "official"|"custom"}
    POST /api/cancel            stop the running job
    GET  /api/results?set=S     summary, manifest, tables and figures (S = official | custom)
    GET  /out/<S>/<path>        a file from that output folder (figures, CSV, VTK)

Changed parameters never touch config/project.yaml or outputs/: they are
saved as config/project_custom.yaml, whose runs write to outputs_custom/.

The analysis always runs as a separate `python -m spbm update` process, so
the web page uses exactly the same code path and audit trail as the command
line. Only one job runs at a time. The server binds to 127.0.0.1 by default;
it has no authentication, so do not expose it on a shared network.
"""
from __future__ import annotations

import copy
import csv
import json
import mimetypes
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from .config import ROOT, load_config, resolve

UI = Path(__file__).resolve().parent / "webui" / "index.html"
ALLOWED_UPLOAD = {".csv", ".dxf", ".zip"}
MAX_UPLOAD = 1024 ** 3          # 1 GB per file

# Progress model: the log line that opens each stage, the optional step it
# belongs to (None = always runs) and its duration in seconds in a timed full
# run on the supplied data. "mc" is per realisation.
_STAGES = [
    ("1-2 import", None, 1, "Import FMS records and surveys"),
    ("3   data-quality", None, 2, "Data-quality checks"),
    ("4   survey cut-off", "align", 1, "Survey cut-off scan"),
    ("4b  volume factor", None, 3, "Volume factor calibration"),
    ("5   material-movement", None, 13, "Movement reconstruction (CPST)"),
    ("6-7 block model", None, 1, "Block model and inventories"),
    ("8   Monte Carlo", "mc", 12.6, "Monte Carlo uncertainty"),
    ("    figures", "figures", 5, "Block-model figures"),
    ("9   validation", None, 1, "Balances and geometry check"),
    ("forward-model temporal", "temporal", 375, "Forward-model temporal test"),
    ("synthetic twin", "twin", 87, "Synthetic twin experiment"),
    ("numerical robustness", "robust", 272, "Numerical robustness"),
    ("volume-gap scenarios", "scenarios", 41, "Volume-gap scenarios"),
    ("one-at-a-time sensitivity", "sensitivity", 515, "Sensitivity analysis"),
    ("done - run", None, 1, "Write summary and audit trail"),
]
_N_OAT = 22                     # one-at-a-time cases in the sensitivity step


def plan(skip, n_mc):
    """Stages that will run and their expected durations (s)."""
    return [(key, label, dur * (n_mc if step == "mc" else 1))
            for key, step, dur, label in _STAGES if step is None or step not in skip]


def progress(lines, skip, n_mc):
    """Estimated fraction done, from the stages reached in the log."""
    st = plan(skip, n_mc)
    total = sum(d for _, _, d in st)
    text = "\n".join(lines)
    reached = -1
    for i, (key, _, _) in enumerate(st):
        if key in text:
            reached = i
    if reached < 0:
        return 0.0, st
    done = sum(d for _, _, d in st[:reached])
    key, _, dur = st[reached]
    part = 0.0
    if key.startswith("8"):
        mc = re.findall(r"MC (\d+)/(\d+)", text)
        if mc:
            part = int(mc[-1][0]) / int(mc[-1][1])
    elif "sensitivity" in key:
        part = min(sum(1 for l in lines if l.strip().startswith("OAT ")), _N_OAT) / (_N_OAT + 1)
    elif key == "done - run":
        part = 1.0
    return min((done + part * dur) / total, 1.0), st


# Tables shown on the results page: (key, title, path in the output folder).
TABLES = [
    ("material", "Inventory by material class (exact tonnage split)", "blockmodel/summary_by_material_source.csv"),
    ("info_class", "Inventory by information class", "validation/inventory_by_class.csv"),
    ("mc", "Monte Carlo global summary", "uncertainty/mc_global_summary.csv"),
    ("scenarios", "Volume-gap scenarios", "uncertainty/scenarios.csv"),
    ("balance", "Mass and metal balance", "validation/mass_metal_balance.csv"),
    ("periods", "Survey-interval reconciliation", "growth/period_reconciliation.csv"),
    ("vf", "Volume factor calibration", "growth/volume_factor_calibration.csv"),
    ("confidence", "Blocks by confidence class", "blockmodel/summary_by_confidence.csv"),
    ("bench", "Inventory by 4 m bench", "blockmodel/summary_by_bench_4m.csv"),
    ("grade_tonnage", "Grade-tonnage", "blockmodel/summary_grade_tonnage.csv"),
    ("twin", "Synthetic twin experiment", "validation/twin_alternative_truths.csv"),
    ("forward", "Forward-model temporal validation", "validation/forward_temporal_summary.csv"),
    ("sensitivity", "One-at-a-time sensitivity", "uncertainty/sensitivity_oat.csv"),
    ("qa", "QA rule catalogue", "qaqc/qa_rule_catalogue.csv"),
]
DOWNLOADS = ["blockmodel/stockpile_block_model.csv", "blockmodel/stockpile_block_model.vtk",
             "blockmodel/block_model_definition.json", "movement/load_destinations.csv",
             "audit/run_manifest.json", "audit/change_report.md", "summary_tables.md"]


CUSTOM_CONFIG = "config/project_custom.yaml"
CUSTOM_OUTPUTS = "outputs_custom"
LOCKED = ("inputs", "outputs")     # data sources and output folder cannot be changed from the page

# Editable parameters shown as a form: (group, [items]).  Item fields:
#   keys  - dotted config keys written with this value (several = kept equal)
#   kind  - number | int | bool | choice | numlist | auto_number | null_number | multichoice
P = lambda keys, label, kind, help, unit="", a="", **kw: dict(keys=[keys] if isinstance(keys, str) else keys, label=label,
                                                              kind=kind, help=help, unit=unit, a=a, **kw)
PARAMS = [
    ("Timing", [
        P("time.survey_cutoff_hours", "Survey cut-off", "number", "A survey dated day D closes its interval this many hours after D 00:00. 31 h = D+1 07:00, the shift change found by the cut-off scan.", "h", "A-05", min=0, max=48),
        P("time.first_interval_hours", "Length of the first interval", "number", "The first survey has no earlier survey; its interval starts this many hours before its cut-off.", "h", "", min=1, max=240),
    ]),
    ("Volume, swell and density", [
        P("density.volume_factor", "Volume factor f_v (swell)", "auto_number", "In-pile volume of a load = T × f_v / Dens. 'auto' calibrates it from the surveys (1.472 on the supplied data).", "", "A-06", min=0.5, max=3),
        P("density.payload_factor", "Payload factor f_pay", "number", "True tonnes = recorded tonnes × f_pay. 1.0 = payloads correct and the extra volume is bulking. In-pile density = Dens × f_pay / f_v.", "", "A-06", min=0.5, max=3),
        P("density.legacy_density", "Pre-record core density", "null_number", "In-pile density of material placed before the record. Blank = mean in-pile density of the FMS loads.", "t/m³", "A-22", min=0.5, max=5),
        P("density.calibration_outlier_k_mad", "f_v outlier limit", "number", "Intervals whose fill/FMS ratio is more than this many robust SDs from the median are left out of the f_v calibration.", "× MAD", "A-06", min=0.5, max=20),
    ]),
    ("Pile geometry", [
        P(["infill.repose_deg", "forward.repose_deg"], "Angle of repose", "number", "Slope of loose material on the faces. Used to infer unsurveyed faces and in the forward (prediction) model. Measured median face slope 36.7°.", "°", "A-03", min=20, max=50),
        P("infill.front_unobserved_fill", "Count toe-clipped fill (A-13b)", "bool", "If on, first-surveyed cells in front of an earlier face start at the repose extrapolation of that face, and the volume between is fill no solid captured (about 7,200 m³ moves from the pre-record core to unattributed).", "", "A-13b"),
        P("base.toe_band", "Toe band for the floor fit", "number", "Cells within this height of the lowest surveyed elevation are used to fit the floor plane.", "m", "A-12", min=0.1, max=5),
        P("forward.crest_slope_deg", "Face slope threshold (forward model)", "number", "A cell steeper than this is part of a face when locating the crest.", "°", "", min=5, max=45),
        P("forward.deposit_radius", "Load footprint radius (forward model)", "number", "Radius of a pushed load where it is released over the crest.", "m", "", min=0.5, max=10),
    ]),
    ("Survey precision", [
        P("survey.sigma_z", "Vertical survey precision σz", "number", "1-sigma vertical error of a survey surface.", "m", "A-08", min=0.001, max=1),
        P("survey.lod_k", "Detection limit factor k", "number", "Changes smaller than τ = k·√2·σz are treated as noise (k = 2 gives τ ≈ 0.14 m).", "", "A-09", min=0, max=10),
        P("survey.min_patch_cells", "Smallest change patch", "int", "Isolated change patches with fewer cells than this are treated as noise.", "cells", "", min=0, max=1000),
    ]),
    ("Dozer movement (reconstruction)", [
        P("movement.cost", "Push-cost form", "choice", "geodesic = slope-aware dozer push distance over the terrain; flat = no push term (each load may fill any fill cell of its interval at equal cost).", "", "A-15", choices=["geodesic", "flat"]),
        P("movement.epsilon", "Mixing length ε", "number", "Entropy regularisation of the transport: how much loads are smeared together (GPS error, spill, rolling).", "m", "A-18", min=0.5, max=100),
        P("movement.alpha_up", "Uphill push penalty α", "number", "Extra push cost per metre of lift, in metres of horizontal push.", "m/m", "A-16", min=0, max=50),
        P("movement.max_push", "Maximum push distance", "number", "Loads cannot be pushed further than this (geodesic); beyond it they stay on the platform.", "m", "A-17", min=5, max=500),
        P("movement.retain_cost", "Cost of leaving volume on the platform", "number", "Cost of the dummy 'retained' destination; keep above the maximum push so reachable fill is used first.", "m", "A-23", min=1, max=1000),
        P("movement.unattributed_cost", "Cost of unattributed fill", "number", "Cost of filling surveyed volume from the dummy 'unknown source'.", "m", "A-21", min=1, max=1000),
        P("movement.retain_sigma", "Spread of retained material", "number", "Gaussian kernel used to spread material still on the platform at the end of the record.", "m", "A-23", min=0.5, max=50),
        P("movement.cut_as_source", "Re-handle dozer cuts", "bool", "Material removed by elevation decreases is re-deposited in the same interval.", "", "A-20"),
        P("movement.sinkhorn_tol", "Sinkhorn tolerance", "number", "Relative marginal error at which the transport solver stops.", "", "", min=1e-12, max=1e-2),
        P("movement.sinkhorn_max_iter", "Sinkhorn iteration limit", "int", "", "", "", min=10, max=100000),
    ]),
    ("FMS data rules", [
        P("fms.repeated_location_min", "Default-position count", "int", "An X/Y/Z shared by at least this many records is a stuck FMS position; those loads get an unknown location.", "records", "A-32", min=2, max=1000),
        P("fms.pass_quantum_t", "Bucket pass size", "number", "Payloads are passes × this many tonnes; others are flagged.", "t", "A-10", min=1, max=500),
        P("fms.dump_z_tolerance_m", "Dump Z tolerance", "number", "Dump elevations further than this outside the interval's surface envelope are flagged.", "m", "A-29", min=0, max=100),
    ]),
    ("Grid and block model", [
        P("grid.cell", "Simulation grid cell", "number", "Horizontal resolution of the reconstruction. Smaller is slower (0.5 m is about 4× the run time).", "m", "A-24", min=0.25, max=10),
        P("grid.dz", "Vertical integration step", "number", "Step used to integrate layers into blocks.", "m", "A-24", min=0.05, max=2),
        P("blockmodel.block", "Block size (x, y, z)", "numlist", "Three numbers, comma-separated.", "m", "A-25", n=3, min=0.5, max=100),
        P("blockmodel.origin_z", "Block z origin", "number", "Elevation of the bottom of the lowest block row.", "m", "", min=-10000, max=10000),
        P("blockmodel.cutoff_cu", "Grade-tonnage cut-offs", "numlist", "Cu cut-off grades for the grade-tonnage table, comma-separated.", "% Cu", "", min=0, max=100),
    ]),
    ("Confidence classes", [
        P("confidence.high.min_tracked", "High: min FMS-tracked share", "number", "", "fraction", "", min=0, max=1),
        P("confidence.high.max_cv", "High: max Cu CV", "number", "", "fraction", "", min=0, max=5),
        P("confidence.medium.min_tracked", "Medium: min FMS-tracked share", "number", "", "fraction", "", min=0, max=1),
        P("confidence.medium.max_cv", "Medium: max Cu CV", "number", "", "fraction", "", min=0, max=5),
        P("confidence.low.min_tracked", "Low: min FMS-tracked share", "number", "Below this, a block is 'Uninformed'.", "fraction", "", min=0, max=1),
    ]),
    ("Uncertainty (Monte Carlo)", [
        P("uncertainty.n_realizations", "Realisations", "int", "Default number of Monte Carlo runs (the run form can override it). Each takes about 13 s.", "", "", min=1, max=1000),
        P("uncertainty.seed", "Random seed", "int", "Same seed and inputs give identical results.", "", "", min=0, max=2**31 - 1),
        P("uncertainty.gps_sigma", "Truck GPS error", "number", "1-sigma horizontal error added to each dump position.", "m", "A-07", min=0, max=50),
        P("uncertainty.payload_cv", "Payload error per load", "number", "Coefficient of variation of each recorded payload.", "CV", "A-10", min=0, max=1),
        P("uncertainty.payload_factor_range", "Payload factor range", "numlist", "Systematic under-recording, sampled triangular with the mode at the first value.", "", "A-06", n=2, min=0.5, max=3),
        P("uncertainty.volume_factor_bootstrap", "Sample f_v from its bootstrap", "bool", "If off, every realisation uses the calibrated f_v.", "", "A-06"),
        P("uncertainty.assay_cv", "Grade error per source", "number", "Coefficient of variation of each source grade signature (Cu, Au, Ag independently).", "CV", "A-11", min=0, max=1),
        P("uncertainty.epsilon_range", "Mixing length range", "numlist", "Uniform range for ε.", "m", "A-18", n=2, min=0.5, max=100),
        P("uncertainty.cost_modes", "Push-cost forms sampled", "multichoice", "Each realisation picks one of the checked forms at random.", "", "A-15", choices=["geodesic", "flat"]),
        P("uncertainty.alpha_range", "Uphill penalty range", "numlist", "Uniform range for α.", "m/m", "A-16", n=2, min=0, max=50),
        P("uncertainty.max_push_range", "Maximum push range", "numlist", "Uniform range for the maximum push distance.", "m", "A-17", n=2, min=5, max=500),
        P("uncertainty.survey_bias_sd", "Survey datum error", "number", "1-sigma vertical bias of each survey.", "m", "A-08", min=0, max=1),
        P("uncertainty.survey_cutoff_range", "Survey cut-off range", "numlist", "Hours sampled in 0.5 h steps; f_v is re-calibrated for each.", "h", "A-05", n=2, min=0, max=48),
    ]),
]


def _get(cfg, key):
    node = cfg
    for k in key.split("."):
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node


def _set(cfg, key, val):
    node = cfg
    parts = key.split(".")
    for k in parts[:-1]:
        node = node.setdefault(k, {})
    node[parts[-1]] = val


def _clean(cfg):
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def coerce(item, raw):
    """Turn a form value into a config value, or raise ValueError."""
    kind, lab = item["kind"], item["label"]
    lo, hi = item.get("min"), item.get("max")

    def num(v, integer=False):
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"{lab}: '{v}' is not a number")
        if x != x or x in (float("inf"), float("-inf")):
            raise ValueError(f"{lab}: not a finite number")
        if integer:
            if x != int(x):
                raise ValueError(f"{lab}: must be a whole number")
            x = int(x)
        if lo is not None and x < lo or hi is not None and x > hi:
            raise ValueError(f"{lab}: must be between {lo:g} and {hi:g}")
        return x

    if kind == "number":
        return num(raw)
    if kind == "int":
        return num(raw, True)
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        raise ValueError(f"{lab}: must be true or false")
    if kind == "choice":
        if raw not in item["choices"]:
            raise ValueError(f"{lab}: must be one of {', '.join(item['choices'])}")
        return raw
    if kind == "multichoice":
        vals = list(raw) if isinstance(raw, list) else []
        if not vals or any(v not in item["choices"] for v in vals):
            raise ValueError(f"{lab}: choose at least one of {', '.join(item['choices'])}")
        return vals
    if kind == "auto_number":
        return "auto" if str(raw).strip().lower() in ("auto", "") else num(raw)
    if kind == "null_number":
        return None if raw is None or str(raw).strip() == "" else num(raw)
    if kind == "numlist":
        parts = raw if isinstance(raw, list) else [s for s in str(raw).replace(";", ",").split(",") if s.strip()]
        vals = [num(v) for v in parts]
        n = item.get("n")
        if n and len(vals) != n:
            raise ValueError(f"{lab}: needs exactly {n} values")
        if not n and not vals:
            raise ValueError(f"{lab}: needs at least one value")
        if n == 2 and vals[0] > vals[1]:
            raise ValueError(f"{lab}: the first value must not exceed the second")
        return vals
    raise ValueError(f"{lab}: unknown kind {kind}")


def _cross_checks(cfg):
    """Relations between parameters that a single field cannot check."""
    m = cfg.get("movement", {})
    if m.get("retain_cost", 0) + m.get("unattributed_cost", 0) <= m.get("max_push", 0):
        raise ValueError("retained + unattributed cost must exceed the maximum push distance, "
                         "or loads would be retained before reachable fill is used")
    c = cfg.get("confidence", {})
    if not c["high"]["min_tracked"] >= c["medium"]["min_tracked"] >= c["low"]["min_tracked"]:
        raise ValueError("confidence classes: High ≥ Medium ≥ Low FMS-tracked share")


def official_config():
    return load_config("config/project.yaml")


def custom_config():
    p = resolve(CUSTOM_CONFIG)
    return load_config(CUSTOM_CONFIG) if p.exists() else None


def changes(official, custom):
    """Leaf values that differ between two configurations (dotted keys)."""
    out = []

    def walk(a, b, pre):
        for k in sorted(set(a) | set(b)):
            if k.startswith("_"):
                continue
            ka = a.get(k) if isinstance(a, dict) else None
            kb = b.get(k) if isinstance(b, dict) else None
            if isinstance(ka, dict) or isinstance(kb, dict):
                walk(ka or {}, kb or {}, pre + k + ".")
            elif ka != kb:
                out.append({"key": pre + k, "official": ka, "custom": kb})
    walk(_clean(official), _clean(custom), "")
    return [c for c in out if c["key"] != "outputs.root"]


def write_custom(cfg_new):
    """Validate a full configuration and save it as the custom configuration."""
    off = official_config()
    if not isinstance(cfg_new, dict):
        raise ValueError("the configuration must be a YAML mapping")
    cfg_new = copy.deepcopy(_clean(cfg_new))
    missing = sorted(set(_clean(off)) - set(cfg_new))
    if missing:
        raise ValueError("missing sections: " + ", ".join(missing))
    for sec in LOCKED:
        cfg_new[sec] = copy.deepcopy(off[sec])
    cfg_new["outputs"]["root"] = CUSTOM_OUTPUTS
    for _, items in PARAMS:                       # every form field must still be valid
        for it in items:
            v = _get(cfg_new, it["keys"][0])
            if v is None and it["kind"] != "null_number":
                raise ValueError(f"{it['label']} ({it['keys'][0]}) is missing")
            coerce(it, v)
    _cross_checks(cfg_new)
    diff = changes(off, cfg_new)
    head = ["# Custom configuration written by the SPBM web page (python -m spbm serve).",
            "# Runs with it write to outputs_custom/; config/project.yaml is unchanged.",
            "# Changes from config/project.yaml:"]
    head += [f"#   {d['key']}: {d['official']!r} -> {d['custom']!r}" for d in diff] or ["#   (none)"]
    resolve(CUSTOM_CONFIG).write_text("\n".join(head) + "\n\n" + yaml.safe_dump(cfg_new, sort_keys=False, allow_unicode=True))
    return diff


def params_state():
    off, cus = official_config(), custom_config()
    groups = []
    for title, items in PARAMS:
        groups.append({"title": title, "items": [dict(it, official=_get(off, it["keys"][0]),
                                                      custom=None if cus is None else _get(cus, it["keys"][0]))
                                                 for it in items]})
    p = resolve(CUSTOM_CONFIG)
    return {"groups": groups, "custom_exists": cus is not None, "changes": changes(off, cus) if cus else [],
            "yaml": p.read_text() if p.exists() else resolve("config/project.yaml").read_text()}


class Job:
    """One analysis process at a time; its output lines are kept in memory."""

    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.info = None        # dict describing the current or last job

    def start(self, config_path: str, which: str, skip: list[str], n_mc: int):
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                raise RuntimeError("a run is already in progress")
            cmd = [sys.executable, "-u", "-m", "spbm", "update", "--config", config_path]
            if skip:
                cmd += ["--skip", ",".join(skip)]
            if "mc" not in skip:
                cmd += ["--mc", str(int(n_mc))]
            self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, bufsize=1)
            self.info = {"set": which, "skip": skip, "mc": n_mc, "cmd": "python " + " ".join(cmd[1:]),
                         "started": time.time(), "finished": None, "returncode": None, "lines": [], "run_id": None}
            threading.Thread(target=self._read, args=(self.proc, self.info), daemon=True).start()

    @staticmethod
    def _read(proc, info):
        for line in proc.stdout:
            line = line.rstrip("\n")
            info["lines"].append(line)
            m = re.search(r"done - run (\S+)", line)
            if m:
                info["run_id"] = m.group(1)
        proc.wait()
        info["returncode"] = proc.returncode
        info["finished"] = time.time()

    def cancel(self):
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
                self.info["lines"].append("cancelled from the web page")
                return True
        return False

    def status(self):
        if self.info is None:
            return None
        i = self.info
        running = i["finished"] is None
        end = time.time() if running else i["finished"]
        frac, st = progress(i["lines"], i["skip"], i["mc"])
        ok = not running and i["returncode"] == 0
        if ok:
            frac = 1.0
        elapsed = end - i["started"]
        eta = elapsed * (1 - frac) / frac if running and frac > 0.01 else None
        text = "\n".join(i["lines"])
        reached = max([k for k, (key, _, _) in enumerate(st) if key in text], default=-1)
        mc = re.findall(r"MC (\d+)/(\d+)", text)
        stages = [{"label": label, "state": "done" if k < reached or ok else "now" if k == reached and running else
                   "failed" if k == reached else "todo"} for k, (_, label, _) in enumerate(st)]
        return {"set": i["set"], "skip": i["skip"], "mc": i["mc"], "cmd": i["cmd"], "running": running,
                "returncode": i["returncode"], "elapsed_s": round(elapsed, 1), "eta_s": None if eta is None else round(eta),
                "progress": round(frac, 3), "stages": stages, "mc_done": [int(x) for x in mc[-1]] if mc else None,
                "run_id": i["run_id"], "log": i["lines"][-400:]}


def read_csv(path: Path, limit: int = 500):
    if not path.exists():
        return None
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return {"columns": [], "rows": [], "truncated": False}
    return {"columns": rows[0], "rows": rows[1:limit + 1], "truncated": len(rows) - 1 > limit}


def safe_name(name: str) -> str | None:
    name = Path(unquote(name)).name.strip()
    if not name or name.startswith(".") or not re.fullmatch(r"[\w .()+-]+", name):
        return None
    return name if Path(name).suffix.lower() in ALLOWED_UPLOAD else None


def make_handler(cfg: dict, job: Job):
    inbox = resolve("data/inbox")
    official_path = cfg.get("_path", str(resolve("config/project.yaml")))
    roots = {"official": resolve(cfg["outputs"]["root"]).resolve(), "custom": resolve(CUSTOM_OUTPUTS).resolve()}
    from .__main__ import STEPS

    def rel(p: Path) -> str:
        return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)

    class H(BaseHTTPRequestHandler):
        server_version = "spbm"
        last_seen = time.time()          # last request from any page (for --idle-exit)

        def parse_request(self):
            ok = super().parse_request()
            H.last_seen = time.time()
            return ok

        def log_message(self, fmt, *args):        # keep the console quiet
            pass

        # ---------------------------------------------------------- helpers
        def _send(self, code, body: bytes, ctype="application/json", extra=()):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, default=str).encode())

        def _err(self, code, msg):
            self._json({"error": msg}, code)

        def _body_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 5 * 1024 ** 2:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(n) or b"{}") if n else {}

        # ---------------------------------------------------------- GET
        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                return self._send(200, UI.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/ping":
                return self._json({"app": "spbm"})
            if u.path == "/api/state":
                return self._json(self._state())
            if u.path == "/api/params":
                return self._json(params_state())
            if u.path == "/api/results":
                return self._json(self._results(q.get("set", ["official"])[0]))
            if u.path.startswith("/out/"):
                which, _, path = unquote(u.path[len("/out/"):]).partition("/")
                return self._file(which, path, q.get("download"))
            self._err(404, "not found")

        def _state(self):
            inbox.mkdir(parents=True, exist_ok=True)
            files = [{"name": p.name, "bytes": p.stat().st_size} for p in sorted(inbox.iterdir())
                     if p.is_file() and not p.name.startswith(".")]
            have = {k: (r / "summary.json").exists() for k, r in roots.items()}
            reg = next((roots[k] / "audit" / "data_registry.csv" for k in ("custom", "official")
                        if (roots[k] / "audit" / "data_registry.csv").exists()), None)
            return {"inbox": files, "registered": read_csv(reg) if reg else None, "job": job.status(),
                    "results": have, "custom_config": resolve(CUSTOM_CONFIG).exists(),
                    "roots": {k: rel(r) for k, r in roots.items()},
                    "steps": [{"id": k, "label": v} for k, v in STEPS.items()],
                    "default_mc": cfg["uncertainty"]["n_realizations"]}

        def _results(self, which):
            root = roots.get(which)
            if root is None or not (root / "summary.json").exists():
                return {"available": False, "set": which}
            man = root / "audit" / "run_manifest.json"
            m = json.loads(man.read_text()) if man.exists() else {}
            # files older than this run were left by an earlier run (step skipped this time)
            t_run = (root / "summary.json").stat().st_mtime - 1
            try:
                from datetime import datetime
                t_run = datetime.fromisoformat(str(m.get("started"))).timestamp() - 1
            except (TypeError, ValueError):
                pass
            stale = lambda p: p.stat().st_mtime < t_run      # noqa: E731
            figs = {}
            for p in sorted(root.glob("*/fig_*.png")):
                figs.setdefault(p.parent.name, []).append({"path": p.relative_to(root).as_posix(), "stale": stale(p)})
            tables = {}
            for k, title, path in TABLES:
                f = root / path
                tables[k] = {"title": title, "path": path, "data": read_csv(f), "stale": f.exists() and stale(f)}
            off, cus = official_config(), custom_config()
            return {"available": True, "set": which, "root": rel(root),
                    "summary": json.loads((root / "summary.json").read_text()),
                    "manifest": {k: m.get(k) for k in ("run_id", "started", "finished", "git_commit", "config_hash", "notes")},
                    "inputs": m.get("inputs"), "tables": tables, "figures": figs,
                    "changes": changes(off, cus) if which == "custom" and cus else [],
                    "downloads": [{"path": d, "stale": stale(root / d)} for d in DOWNLOADS if (root / d).exists()],
                    "history": read_csv(root / "audit" / "run_log.csv")}

        def _file(self, which, path, download):
            root = roots.get(which)
            if root is None:
                return self._err(404, "not found")
            p = (root / path).resolve()
            if not p.is_relative_to(root) or not p.is_file():
                return self._err(404, "not found")
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if p.suffix in (".csv", ".md", ".asc", ".vtk"):
                ctype = "text/plain; charset=utf-8"
            extra = [("Content-Disposition", f'attachment; filename="{p.name}"')] if download else []
            self._send(200, p.read_bytes(), ctype, extra)

        # ---------------------------------------------------------- PUT / POST
        def do_PUT(self):
            u = urlparse(self.path)
            if u.path != "/api/upload":
                return self._err(404, "not found")
            name = safe_name(parse_qs(u.query).get("name", [""])[0])
            if name is None:
                return self._err(400, "file name must end in .csv, .dxf or .zip and contain only letters, digits, spaces and . _ - ( ) +")
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_UPLOAD:
                return self._err(400, "empty or too large (limit 1 GB)")
            inbox.mkdir(parents=True, exist_ok=True)
            dest = inbox / name
            if dest.exists():
                return self._err(409, f"{name} is already in data/inbox; remove it first or rename the new file")
            tmp = inbox / f".{name}.part"
            left = n
            with open(tmp, "wb") as fh:
                while left:
                    chunk = self.rfile.read(min(left, 1 << 20))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            if left:
                tmp.unlink(missing_ok=True)
                return self._err(400, "upload interrupted")
            tmp.rename(dest)
            self._json({"stored": f"data/inbox/{name}", "bytes": n})

        def do_POST(self):
            u = urlparse(self.path)
            try:
                if u.path == "/api/run":
                    b = self._body_json()
                    which = b.get("config", "official")
                    if which not in ("official", "custom"):
                        return self._err(400, "config must be official or custom")
                    if which == "custom" and not resolve(CUSTOM_CONFIG).exists():
                        return self._err(400, "no custom parameters saved yet")
                    skip = [s for s in b.get("skip", []) if s in STEPS]
                    if len(skip) != len(b.get("skip", [])):
                        return self._err(400, "unknown step")
                    n_mc = int(b.get("mc") or cfg["uncertainty"]["n_realizations"])
                    if not 1 <= n_mc <= 1000:
                        return self._err(400, "Monte Carlo realisations must be 1-1000")
                    job.start(official_path if which == "official" else str(resolve(CUSTOM_CONFIG)), which, skip, n_mc)
                    return self._json(job.status())
                if u.path == "/api/cancel":
                    return self._json({"cancelled": job.cancel()})
                if u.path == "/api/params":
                    if job.status() and job.status()["running"] and job.info["set"] == "custom":
                        return self._err(409, "a custom run is in progress; wait for it or cancel it first")
                    b = self._body_json()
                    if "yaml" in b:
                        try:
                            new = yaml.safe_load(b["yaml"])
                        except yaml.YAMLError as e:
                            return self._err(400, f"YAML error: {e}")
                    else:
                        base = custom_config() or official_config()
                        new = _clean(base)
                        items = {it["keys"][0]: it for _, its in PARAMS for it in its}
                        for key, raw in (b.get("values") or {}).items():
                            if key not in items:
                                return self._err(400, f"unknown parameter {key}")
                            v = coerce(items[key], raw)
                            for k in items[key]["keys"]:
                                _set(new, k, v)
                    return self._json({"changes": write_custom(new)})
                if u.path == "/api/params/reset":
                    resolve(CUSTOM_CONFIG).unlink(missing_ok=True)
                    return self._json({"reset": True})
                if u.path == "/api/inbox/remove":
                    name = safe_name(self._body_json().get("name", ""))
                    p = inbox / name if name else None
                    if p is None or not p.is_file():
                        return self._err(404, "no such file in data/inbox")
                    p.unlink()
                    return self._json({"removed": name})
            except RuntimeError as e:
                return self._err(409, str(e))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
                return self._err(400, str(e))
            self._err(404, "not found")

    return H


def _already_running(host, port):
    """True if an SPBM front end already answers on this address."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/ping", timeout=2) as r:
            return json.loads(r.read()).get("app") == "spbm"
    except Exception:
        return False


def serve(cfg: dict, host: str = "127.0.0.1", port: int = 8413, open_browser: bool = False, idle_exit_min: float = 0):
    """Start the front end. open_browser opens the page once the server is up.
    idle_exit_min > 0 stops the server after that many minutes without any
    request from a page and with no run in progress (used by the launchers,
    so closing the browser eventually stops the background program)."""
    import webbrowser
    url = f"http://{host}:{port}/"
    if _already_running(host, port):            # e.g. the launcher was double-clicked twice
        print(f"SPBM is already running at {url}")
        if open_browser:
            webbrowser.open(url)
        return
    job = Job()
    handler = make_handler(cfg, job)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"SPBM is running at {url}  (close this window or press Ctrl+C to stop)")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("warning: the page has no login; anyone who can reach this address can upload files and start runs")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    if idle_exit_min > 0:
        def watch():
            while True:
                time.sleep(30)
                st = job.status()
                busy = st is not None and st["running"]
                if not busy and time.time() - handler.last_seen > idle_exit_min * 60:
                    print(f"no page open for {idle_exit_min:g} min - stopping")
                    httpd.shutdown()
                    return
        threading.Thread(target=watch, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        job.cancel()
        httpd.server_close()
