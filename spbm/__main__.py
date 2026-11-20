"""Command line interface.

    python -m spbm run      [--config C] [--until DATE] [--mc N] [--fast] [--skip STEP,...]
    python -m spbm ingest   PATH [PATH ...]       # copy new files into the managed raw store
    python -m spbm update   [--config C]          # pick up new files in data/inbox and re-run
    python -m spbm qaqc     [--config C]          # data checks only
    python -m spbm status   [--config C]          # registered data and last run
    python -m spbm serve    [--port 8413]         # web front end on http://127.0.0.1:8413
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import load_config, resolve

# Optional steps that --skip can turn off (the reconstruction, block model,
# balances and audit trail always run).
STEPS = {
    "align": "survey cut-off scan",
    "mc": "Monte Carlo uncertainty",
    "temporal": "forward-model temporal validation",
    "twin": "synthetic twin experiment",
    "robust": "numerical robustness",
    "scenarios": "volume-gap scenarios",
    "sensitivity": "one-at-a-time sensitivity",
    "figures": "growth, block-model and uncertainty figures",
}
FAST_SKIP = ["mc", "temporal", "twin", "robust", "sensitivity"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="spbm", description="Stockpile reconstruction & block model platform")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["run", "update", "ingest", "qaqc", "status", "serve"]:
        p = sub.add_parser(name)
        p.add_argument("--config", default="config/project.yaml")
        if name == "ingest":
            p.add_argument("paths", nargs="+", help="files, folders or zip archives to add to the raw store")
        if name in ("run", "update"):
            p.add_argument("--until", default=None, help="only use data up to this date-time (re-run history / demonstrate updating)")
            p.add_argument("--mc", type=int, default=None, help="number of Monte Carlo realisations (default from config)")
            p.add_argument("--fast", action="store_true", help="skip Monte Carlo, forward-model validation, twin experiment, robustness and sensitivity")
            p.add_argument("--skip", default="", help="comma-separated optional steps to skip: " + ", ".join(STEPS))
            p.add_argument("--out", default=None, help="output folder (default from config)")
        if name == "serve":
            p.add_argument("--host", default="127.0.0.1", help="address to bind (default: this computer only)")
            p.add_argument("--port", type=int, default=8413)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    if getattr(a, "out", None):
        cfg["outputs"]["root"] = a.out

    if a.cmd == "serve":
        from .web import serve
        serve(cfg, a.host, a.port)
        return 0
    if a.cmd == "ingest":
        from . import io as sio
        new = sio.ingest(cfg, extra=a.paths, interventions=sio.load_interventions(cfg))
        print(f"ingest: {len(new)} new file(s) stored in {cfg['inputs']['raw_store']}")
        if len(new):
            print(new[["name", "kind", "status", "stored_as"]].to_string(index=False))
        return 0
    if a.cmd in ("run", "update"):
        from .pipeline import run
        if a.cmd == "update":
            from . import io as sio
            files = sio.scan_sources(cfg, sio.load_interventions(cfg))
            reg = resolve(cfg["outputs"]["root"]) / "audit" / "data_registry.csv"
            import pandas as pd
            known = set(pd.read_csv(reg)["sha256"]) if reg.exists() else set()
            newf = [f for f in files if f.sha256 not in known]
            print(f"update: {len(newf)} new file(s): " + ", ".join(f.name for f in newf))
            if not newf:
                print("nothing new - re-running anyway for reproducibility check")
        skip = {s.strip() for s in a.skip.split(",") if s.strip()}
        bad = sorted(skip - set(STEPS))
        if bad:
            ap.error(f"unknown step(s) for --skip: {', '.join(bad)} (choose from {', '.join(STEPS)})")
        if a.fast:
            skip |= set(FAST_SKIP)
        if skip:
            print("skipping: " + ", ".join(STEPS[s] for s in STEPS if s in skip), flush=True)
        run(cfg, until=a.until, n_mc=a.mc, do_mc="mc" not in skip, do_twin="twin" not in skip, do_robust="robust" not in skip,
            do_sens="sensitivity" not in skip, do_temporal="temporal" not in skip, do_align="align" not in skip,
            do_scen="scenarios" not in skip, do_figs="figures" not in skip)
    elif a.cmd == "qaqc":
        from .dataset import load_dataset
        from .qaqc import run_qaqc
        ds = load_dataset(cfg)
        q = run_qaqc(ds, cfg, resolve(cfg["outputs"]["root"]) / "qaqc")
        print(json.dumps(q["summary"], indent=2, default=str))
        print(q["flags"].to_string(index=False))
    elif a.cmd == "status":
        root = resolve(cfg["outputs"]["root"])
        for p in [root / "audit" / "data_registry.csv", root / "audit" / "run_log.csv"]:
            print(f"== {p}")
            print(p.read_text() if p.exists() else "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
