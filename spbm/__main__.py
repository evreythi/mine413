"""Command line interface.

    python -m spbm run      [--config C] [--until DATE] [--mc N] [--fast]
    python -m spbm ingest   PATH [PATH ...]       # copy new files into the managed raw store
    python -m spbm update   [--config C]          # pick up new files in data/inbox and re-run
    python -m spbm qaqc     [--config C]          # data checks only
    python -m spbm status   [--config C]          # registered data and last run
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import load_config, resolve


def main(argv=None):
    ap = argparse.ArgumentParser(prog="spbm", description="Stockpile reconstruction & block model platform")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["run", "update", "ingest", "qaqc", "status"]:
        p = sub.add_parser(name)
        p.add_argument("--config", default="config/project.yaml")
        if name == "ingest":
            p.add_argument("paths", nargs="+", help="files, folders or zip archives to add to the raw store")
        if name in ("run", "update"):
            p.add_argument("--until", default=None, help="only use data up to this date-time (re-run history / demonstrate updating)")
            p.add_argument("--mc", type=int, default=None, help="number of Monte Carlo realisations (default from config)")
            p.add_argument("--fast", action="store_true", help="skip Monte Carlo, forward-model validation, twin experiment, robustness and sensitivity")
            p.add_argument("--out", default=None, help="output folder (default from config)")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    if getattr(a, "out", None):
        cfg["outputs"]["root"] = a.out

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
            from .audit import update_registry
            files = sio.scan_sources(cfg, sio.load_interventions(cfg))
            reg = resolve(cfg["outputs"]["root"]) / "audit" / "data_registry.csv"
            import pandas as pd
            known = set(pd.read_csv(reg)["sha256"]) if reg.exists() else set()
            newf = [f for f in files if f.sha256 not in known]
            print(f"update: {len(newf)} new file(s): " + ", ".join(f.name for f in newf))
            if not newf:
                print("nothing new - re-running anyway for reproducibility check")
        fast = a.fast
        run(cfg, until=a.until, n_mc=a.mc, do_mc=not fast, do_twin=not fast, do_robust=not fast, do_sens=not fast, do_temporal=not fast)
    elif a.cmd == "qaqc":
        from pathlib import Path
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
