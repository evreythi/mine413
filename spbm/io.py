"""Data import: source scanning, file registry (SHA-256), FMS and survey readers.

Raw inputs are never modified. Zip archives are read in place. Every file
that enters the analysis is registered with its hash so that any model
version can be traced back to the exact bytes that produced it.
"""
from __future__ import annotations

import fnmatch
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import resolve


@dataclass
class SourceFile:
    name: str          # base file name
    kind: str          # 'fms' | 'survey'
    origin: str        # zip path or directory
    member: str        # member path inside zip, or full path
    sha256: str
    size: int

    def read_bytes(self) -> bytes:
        if self.origin.lower().endswith(".zip"):
            with zipfile.ZipFile(resolve(self.origin)) as zf:
                return zf.read(self.member)
        return Path(self.member).read_bytes()


def _kind(name: str, cfg: dict) -> str | None:
    if fnmatch.fnmatch(name.lower(), cfg["inputs"]["fms_pattern"].lower()):
        return "fms"
    if fnmatch.fnmatch(name.lower(), cfg["inputs"]["survey_pattern"].lower()):
        return "survey"
    return None


def scan_sources(cfg: dict) -> list[SourceFile]:
    """Find all FMS/survey files in the configured sources. Duplicate content
    (same SHA-256) is registered once; the first occurrence wins."""
    found: list[SourceFile] = []
    seen: set[str] = set()
    for src in cfg["inputs"]["sources"]:
        p = resolve(src)
        if not p.exists():
            continue
        entries = []
        if p.is_file() and p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as zf:
                for m in zf.namelist():
                    if m.endswith("/"):
                        continue
                    entries.append((Path(m).name, str(src), m, zf.read(m)))
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    entries.append((f.name, str(src), str(f), f.read_bytes()))
        for name, origin, member, data in entries:
            kind = _kind(name, cfg)
            if kind is None:
                continue
            h = hashlib.sha256(data).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            found.append(SourceFile(name, kind, origin, member, h, len(data)))
    return found


# --------------------------------------------------------------------- FMS
FMS_COLUMNS = {
    "Cycle ID": "cycle_id",
    "Truck PayLoad": "payload_t",
    "Au": "au_gpt",
    "Ag": "ag_gpt",
    "Cu": "cu_pct",
    "Dens": "density",
    "X (Dump Event)": "x",
    "Y (Dump Event)": "y",
    "Z (Dump Event)": "z",
    "Dump_tstamp": "timestamp_raw",
}


def read_fms(files: list[SourceFile]) -> pd.DataFrame:
    """Read and standardise all FMS files. Original values are retained in
    the returned frame (columns *_raw / source_file / source_row) so every
    cleaning action stays traceable."""
    frames = []
    for f in files:
        df = pd.read_csv(io.BytesIO(f.read_bytes()))
        df.columns = [c.strip() for c in df.columns]
        missing = [c for c in FMS_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{f.name}: missing FMS columns {missing}")
        df = df.rename(columns=FMS_COLUMNS)
        df["source_file"] = f.name
        df["source_sha256"] = f.sha256[:12]
        df["source_row"] = np.arange(len(df)) + 2  # 1-based incl. header
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp_raw"], format="%m/%d/%Y %H:%M", errors="coerce")
    return df


# ------------------------------------------------------------------ surveys
_DATE_RE = re.compile(r"(\d{6})")


def parse_survey_date(name: str) -> datetime | None:
    m = _DATE_RE.search(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%y%m%d")
    except ValueError:
        return None


def read_dxf_triangles(f: SourceFile) -> tuple[np.ndarray, dict]:
    """Return (n,3,3) triangles from 3DFACE (quads are split) plus metadata."""
    import ezdxf

    text = f.read_bytes().decode("cp1252", errors="replace").replace("\r\n", "\n")
    doc = ezdxf.read(io.StringIO(text))
    msp = doc.modelspace()
    tris, layers, types = [], set(), {}
    for e in msp:
        t = e.dxftype()
        types[t] = types.get(t, 0) + 1
        if t != "3DFACE":
            continue
        layers.add(e.dxf.layer)
        v = [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]
        v = [(p.x, p.y, p.z) for p in v]
        tris.append(v[:3])
        if np.linalg.norm(np.subtract(v[3], v[2])) > 1e-9 and np.linalg.norm(np.subtract(v[3], v[0])) > 1e-9:
            tris.append([v[0], v[2], v[3]])  # genuine quad
    T = np.asarray(tris, dtype=float)
    meta = {
        "entity_types": types,
        "layers": sorted(layers),
        "insunits": doc.header.get("$INSUNITS"),
        "created_by": doc.header.get("$COMMENTS", ""),
        "n_triangles": len(T),
    }
    return T, meta


def survey_register(files: list[SourceFile], cfg: dict) -> pd.DataFrame:
    """Survey list with dates parsed from file names, then documented manual
    overrides applied (config/survey_overrides.csv)."""
    rows = []
    for f in files:
        d = parse_survey_date(f.name)
        rows.append({"file": f.name, "sha256": f.sha256[:12], "date_from_name": d})
    reg = pd.DataFrame(rows)
    reg["assigned_date"] = reg["date_from_name"]
    reg["survey_time"] = cfg["time"]["survey_time"]
    reg["override_reason"] = ""
    ov_path = resolve(cfg["inputs"]["survey_overrides"])
    if ov_path.exists():
        ov = pd.read_csv(ov_path, dtype=str).fillna("")
        for _, o in ov.iterrows():
            m = reg["file"] == o["file"]
            if not m.any():
                continue
            if o["assigned_date"]:
                reg.loc[m, "assigned_date"] = pd.to_datetime(o["assigned_date"])
            if o.get("survey_time", ""):
                reg.loc[m, "survey_time"] = o["survey_time"]
            reg.loc[m, "override_reason"] = o["reason"]
    reg["survey_datetime"] = [
        pd.Timestamp(d) + pd.to_timedelta(t + ":00") if t != "23:59" else pd.Timestamp(d) + pd.Timedelta("23:59:00")
        for d, t in zip(reg["assigned_date"], reg["survey_time"])
    ]
    reg = reg.sort_values("survey_datetime").reset_index(drop=True)
    reg["index"] = np.arange(len(reg))
    return reg
