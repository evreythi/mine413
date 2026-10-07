"""Task 8 - audit trail: data registry, run manifest, model-version history and
change report between consecutive model versions."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import __version__
from .config import ROOT, config_hash


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    """Code identity for the manifest. In a Git checkout: the commit hash
    (with '+modified' if tracked files differ). In a packaged copy (e.g. the
    submission zip, no .git): the commit recorded in BUILD_INFO.json when the
    package was made. Never fails, never writes to stderr."""
    try:
        h = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True,
                                    stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", "spbm", "config"],
                               stderr=subprocess.DEVNULL).returncode != 0
        return h + ("+modified" if dirty else "")
    except Exception:
        info = ROOT / "BUILD_INFO.json"
        if info.exists():
            b = json.loads(info.read_text())
            return f"not a git checkout; packaged from commit {b.get('git_commit', '?')} ({b.get('packaged', '?')}); code identity via spbm_source_sha256"
        return "not a git checkout; code identity via spbm_source_sha256"


def source_hash() -> str:
    """SHA-256 over the platform source and configuration, so code identity is
    verifiable even without Git."""
    h = hashlib.sha256()
    for p in sorted(list((ROOT / "spbm").glob("*.py")) + list((ROOT / "config").glob("*"))):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()[:16]


def update_registry(files, out: Path) -> pd.DataFrame:
    """Append newly seen input files to the persistent data registry."""
    reg_path = out / "data_registry.csv"
    old = pd.read_csv(reg_path) if reg_path.exists() else pd.DataFrame(columns=["sha256"])
    now = datetime.now().isoformat(timespec="seconds")
    rows = [{"file": f.name, "kind": f.kind, "origin": f.origin, "member": f.member, "bytes": f.size,
             "sha256": f.sha256, "first_registered": now} for f in files if f.sha256 not in set(old["sha256"])]
    new = pd.DataFrame(rows)
    reg = pd.concat([old, new], ignore_index=True) if len(old) else new
    reg.to_csv(reg_path, index=False)
    return new


def versions() -> dict:
    import ezdxf
    import matplotlib
    import numpy
    import scipy
    import yaml
    return {"python": sys.version.split()[0], "platform": platform.platform(), "spbm": __version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__, "ezdxf": ezdxf.__version__, "pyyaml": yaml.__version__}


def write_manifest(cfg, files, outputs_root: Path, summary: dict, started: datetime, notes: list[str]) -> dict:
    run_id = started.strftime("%Y%m%dT%H%M%S")
    audit = outputs_root / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    outs = []
    for p in sorted(outputs_root.rglob("*")):
        if p.is_file() and "history" not in p.parts and p.suffix in {".csv", ".png", ".vtk", ".asc", ".json", ".md"} and p.name != "run_manifest.json":
            outs.append({"path": str(p.relative_to(outputs_root)), "bytes": p.stat().st_size})
    man = {
        "run_id": run_id, "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(), "spbm_source_sha256": source_hash(), "config_file": cfg.get("_path"), "config_hash": config_hash(cfg),
        "software": versions(),
        "inputs": [{"file": f.name, "kind": f.kind, "sha256": f.sha256, "bytes": f.size, "origin": f.origin} for f in files],
        "manual_interventions": pd.read_csv(ROOT / cfg["inputs"]["survey_overrides"]).to_dict("records")
        if (ROOT / cfg["inputs"]["survey_overrides"]).exists() else [],
        "notes": notes, "key_results": summary, "outputs": outs,
    }
    with open(audit / "run_manifest.json", "w") as fh:
        json.dump(man, fh, indent=2, default=str)
    # copy of the configuration actually used
    with open(audit / "config_used.json", "w") as fh:
        json.dump({k: v for k, v in cfg.items() if not k.startswith("_")}, fh, indent=2, default=str)
    # run log
    log = audit / "run_log.csv"
    row = pd.DataFrame([{"run_id": run_id, "git_commit": man["git_commit"], "config_hash": man["config_hash"],
                         "n_inputs": len(files), "last_survey": summary.get("last_survey"),
                         "total_tonnes": summary.get("total_tonnes"), "fms_tonnes": summary.get("fms_tonnes")}])
    row.to_csv(log, mode="a", header=not log.exists(), index=False)
    # model-version history
    hist = outputs_root / "history" / run_id
    hist.mkdir(parents=True, exist_ok=True)
    shutil.copy(audit / "run_manifest.json", hist / "run_manifest.json")
    for rel in ["blockmodel/summary_by_dominant_info_class.csv", "blockmodel/summary_by_bench_4m.csv", "growth/period_reconciliation.csv"]:
        src = outputs_root / rel
        if src.exists():
            shutil.copy(src, hist / src.name)
    return man


def change_report(outputs_root: Path) -> str | None:
    """Compare the two most recent model versions (Task 8 item 11)."""
    hist = sorted((outputs_root / "history").glob("*/run_manifest.json"))
    if len(hist) < 2:
        return None
    a, b = [json.load(open(p)) for p in hist[-2:]]
    ka, kb = a["key_results"], b["key_results"]
    lines = [f"# Model change report: {a['run_id']} -> {b['run_id']}", "",
             "| item | previous | current | change |", "|---|---|---|---|"]
    for k in kb:
        va, vb = ka.get(k), kb.get(k)
        if isinstance(vb, (int, float)) and isinstance(va, (int, float)):
            lines.append(f"| {k} | {va:,.2f} | {vb:,.2f} | {vb - va:+,.2f} |")
        elif va != vb:
            lines.append(f"| {k} | {va} | {vb} | changed |")
    ia = {x["sha256"] for x in a["inputs"]}
    new = [x["file"] for x in b["inputs"] if x["sha256"] not in ia]
    lines += ["", f"New input files: {', '.join(new) if new else 'none'}",
              f"Config hash: {a['config_hash']} -> {b['config_hash']}", f"Code: {a['git_commit']} -> {b['git_commit']}"]
    txt = "\n".join(lines)
    (outputs_root / "audit" / "change_report.md").write_text(txt)
    return txt
