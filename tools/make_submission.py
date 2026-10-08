"""Assemble the Canvas submission zip (course outline: '.Zip file on Canvas').

    python tools/make_submission.py [--team TeamName]

Contents: deliverables (PDF/DOCX/XLSX/PPTX), Markdown sources, platform source
code, configuration, tests, tools, outputs of the submitted run, and the raw
data archive as supplied (so the run can be reproduced).
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["README.md", "requirements.txt", "pytest.ini", ".gitignore", "Data_Topo 2026.zip",
           "Surface_Mining_Stockpile_Block_Model_Project.pdf", "config", "spbm", "tests", "tools", "examples", "docs", "outputs"]
EXCLUDE_PARTS = {"__pycache__", "node_modules", ".pytest_cache", "_scratch", "history"}
EXCLUDE_NAMES = {"package-lock.json"}


def main():
    ap = argparse.ArgumentParser()
    import yaml
    default_team = yaml.safe_load((ROOT / "config" / "team.yaml").read_text()).get("team_name", "Team")
    ap.add_argument("--team", default=default_team)
    a = ap.parse_args()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"MINE413_TermProject_{a.team}.zip"
    import json
    import subprocess
    from datetime import datetime
    try:
        commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = "unknown"
    build_info = json.dumps({"git_commit": commit, "packaged": datetime.now().isoformat(timespec="seconds"),
                             "note": "Submission package (no .git). The platform reads this file to record code identity."}, indent=2)
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"MINE413_TermProject_{a.team}/BUILD_INFO.json", build_info)
        for item in INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(p.rglob("*")) if p.exists() else []
            for f in files:
                if f.is_dir() or EXCLUDE_PARTS & set(f.parts) or f.name in EXCLUDE_NAMES:
                    continue
                z.write(f, Path(f"MINE413_TermProject_{a.team}") / f.relative_to(ROOT))
                n += 1
    print(f"{out}  ({n} files, {out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
