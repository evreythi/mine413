"""Data import: managed raw store (SHA-256), manual interventions, FMS and
survey readers.

Every input file (zip member, inbox file or path given to `spbm ingest`) is
copied once into the managed raw store `data/raw_store/` under its hash and
logged in `ingest_log.csv`. The analysis reads only from the store. A new file
with the same name as a stored file but different content is refused unless a
`supersede` manual intervention authorises it. Raw files are never edited:
corrections are made only through `config/manual_interventions.csv`, which
requires an id, type, target, reason, author and date for every row.
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


def _iter_entries(cfg: dict, extra=()):
    """(name, origin, bytes) for every candidate input in the configured
    sources plus `extra` paths (zip archives, directories or files)."""
    for src in list(cfg["inputs"]["sources"]) + [str(e) for e in extra]:
        p = resolve(src)
        if not p.exists():
            continue
        if p.is_file() and p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as zf:
                for m in zf.namelist():
                    if not m.endswith("/") and not Path(m).name.startswith("._"):
                        yield Path(m).name, f"{src}::{m}", zf.read(m)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    yield f.name, str(f), f.read_bytes()
        elif p.is_file():
            yield p.name, str(p), p.read_bytes()


def ingest(cfg: dict, extra=(), interventions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Copy new inputs into the managed raw store (idempotent). Returns the
    rows appended to the ingest log. Raises if a file with an existing name
    but different content arrives without a `supersede` intervention."""
    store = resolve(cfg["inputs"]["raw_store"])
    store.mkdir(parents=True, exist_ok=True)
    log_path = store / "ingest_log.csv"
    log = pd.read_csv(log_path, dtype=str) if log_path.exists() else pd.DataFrame(
        columns=["ingested", "name", "kind", "sha256", "bytes", "origin", "stored_as", "status"])
    known = set(log["sha256"])
    by_name = log[log["status"] != "duplicate"].groupby("name")["sha256"].apply(set).to_dict()
    sup = set()
    if interventions is not None and len(interventions):
        sup = {(r.target, r.value) for r in interventions.itertuples() if r.type == "supersede"}
    rows = []
    now = datetime.now().isoformat(timespec="seconds")
    for name, origin, data in _iter_entries(cfg, extra):
        kind = _kind(name, cfg)
        if kind is None:
            continue
        h = hashlib.sha256(data).hexdigest()
        if h in known:
            continue
        status = "new"
        if name in by_name and h not in by_name[name]:
            if not any(t == name and h.startswith(v) for t, v in sup):
                raise ValueError(
                    f"ingest refused: '{name}' already in the raw store with different content "
                    f"(new sha256 {h[:12]}). Add a 'supersede' row to manual_interventions.csv "
                    f"(target={name}, value={h[:12]}) with reason/author/date to accept it.")
            status = "supersedes"
        stored = store / f"{h[:16]}__{name}"
        stored.write_bytes(data)
        known.add(h)
        by_name.setdefault(name, set()).add(h)
        rows.append({"ingested": now, "name": name, "kind": kind, "sha256": h, "bytes": len(data),
                     "origin": origin, "stored_as": stored.name, "status": status})
    new = pd.DataFrame(rows, columns=log.columns)
    if len(new):
        pd.concat([log, new], ignore_index=True).to_csv(log_path, index=False)
    return new


def scan_sources(cfg: dict, interventions: pd.DataFrame | None = None) -> list[SourceFile]:
    """Ingest the configured sources, then return the current version of
    every stored input (a superseded file is replaced by its successor)."""
    ingest(cfg, interventions=interventions)
    store = resolve(cfg["inputs"]["raw_store"])
    log = pd.read_csv(store / "ingest_log.csv", dtype=str)
    log = log[log["status"] != "duplicate"]
    current = log.groupby("name").tail(1)          # latest accepted version per name
    found = []
    for r in current.sort_values(["kind", "name"]).itertuples():
        path = store / r.stored_as
        found.append(SourceFile(r.name, r.kind, str(store), str(path), r.sha256, int(r.bytes)))
    return found


# ------------------------------------------------------ manual interventions
INTERVENTION_TYPES = {
    "survey_date": "target = survey file; value = YYYY-MM-DD (corrected nominal date)",
    "survey_cutoff_hours": "target = survey file; value = hours after 00:00 of the nominal date",
    "fms_exclude": "target = Cycle ID; record kept in the register but not modelled",
    "fms_location_unknown": "target = Cycle ID; dump X/Y treated as unknown",
    "supersede": "target = file name; value = first 12 characters of the new SHA-256",
}
INTERVENTION_COLUMNS = ["id", "type", "target", "value", "reason", "author", "date", "approved_by"]


def load_interventions(cfg: dict) -> pd.DataFrame:
    """Read and validate config/manual_interventions.csv. Every row needs an
    id, a supported type, a target, a reason, an author and a date."""
    p = resolve(cfg["inputs"]["manual_interventions"])
    if not p.exists():
        return pd.DataFrame(columns=INTERVENTION_COLUMNS)
    df = pd.read_csv(p, dtype=str).fillna("")
    missing_cols = [c for c in INTERVENTION_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"{p.name}: missing columns {missing_cols}")
    problems = []
    for r in df.itertuples():
        rid = r.id or f"row {r.Index + 2}"
        if r.type not in INTERVENTION_TYPES:
            problems.append(f"{rid}: unsupported type '{r.type}' (allowed: {', '.join(INTERVENTION_TYPES)})")
        for col in ("id", "target", "reason", "author", "date"):
            if not str(getattr(r, col)).strip():
                problems.append(f"{rid}: '{col}' is required")
        if r.date and pd.isna(pd.to_datetime(r.date, errors="coerce")):
            problems.append(f"{rid}: date '{r.date}' is not a valid date")
    if df["id"].duplicated().any():
        problems.append(f"duplicate ids: {sorted(df.loc[df['id'].duplicated(), 'id'])}")
    if problems:
        raise ValueError("manual_interventions.csv rejected:\n  " + "\n  ".join(problems))
    return df


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
    # numeric fields: non-numeric text becomes NaN (caught by the MISSING_* /
    # GRADE_* rules); the field names are kept in `coerced_fields`
    coerced = pd.Series("", index=df.index)
    for c in ("cycle_id", "payload_t", "au_gpt", "ag_gpt", "cu_pct", "density", "x", "y", "z"):
        v = pd.to_numeric(df[c], errors="coerce")
        bad = v.isna() & df[c].notna()
        coerced[bad] = coerced[bad] + c + " "
        df[c] = v
    df["coerced_fields"] = coerced.str.strip()
    ts = pd.to_datetime(df["timestamp_raw"], format="%m/%d/%Y %H:%M", errors="coerce")
    alt = pd.to_datetime(df.loc[ts.isna() & df["timestamp_raw"].notna(), "timestamp_raw"], errors="coerce")
    ts.loc[alt.index] = alt
    df["timestamp"] = ts
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
    h = doc.header

    def _jd(v):
        try:
            return (datetime(2000, 1, 1, 12) + pd.Timedelta(days=float(v) - 2451545.0)).strftime("%Y-%m-%d")
        except Exception:
            return ""
    meta = {
        "entity_types": types,
        "layers": sorted(layers),
        "insunits": h.get("$INSUNITS"),          # 1 = inches, 6 = metres (DXF spec)
        "measurement": h.get("$MEASUREMENT"),    # 0 = imperial, 1 = metric
        "tdupdate": _jd(h.get("$TDUPDATE")),     # last-saved date in the header
        "acadver": h.get("$ACADVER"),
        "created_by": h.get("$COMMENTS", ""),
        "n_triangles": len(T),
    }
    return T, meta


def survey_register(files: list[SourceFile], cfg: dict, interventions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Survey list: nominal date parsed from the file name, then documented
    manual interventions (survey_date, survey_cutoff_hours) applied.

    A-05: survey labelled day D closes its interval at D 00:00 +
    `time.survey_cutoff_hours` (31 h = 07:00 the following morning, chosen by
    the cut-off scan in growth.temporal_alignment)."""
    rows = []
    for f in files:
        d = parse_survey_date(f.name)
        rows.append({"file": f.name, "sha256": f.sha256[:12], "date_from_name": d})
    reg = pd.DataFrame(rows)
    reg["assigned_date"] = reg["date_from_name"]
    reg["cutoff_hours"] = float(cfg["time"]["survey_cutoff_hours"])
    reg["intervention_ids"] = ""
    reg["override_reason"] = ""
    if interventions is not None and len(interventions):
        for o in interventions.itertuples():
            m = reg["file"] == o.target
            if not m.any() or o.type not in ("survey_date", "survey_cutoff_hours"):
                continue
            if o.type == "survey_date":
                reg.loc[m, "assigned_date"] = pd.to_datetime(o.value)
            else:
                reg.loc[m, "cutoff_hours"] = float(o.value)
            reg.loc[m, "intervention_ids"] = (reg.loc[m, "intervention_ids"] + " " + o.id).str.strip()
            reg.loc[m, "override_reason"] = o.reason
    reg["survey_datetime"] = [pd.Timestamp(d).normalize() + pd.Timedelta(hours=float(h))
                              for d, h in zip(reg["assigned_date"], reg["cutoff_hours"])]
    reg = reg.sort_values("survey_datetime").reset_index(drop=True)
    if not reg["survey_datetime"].is_monotonic_increasing or reg["survey_datetime"].duplicated().any():
        raise ValueError("survey cut-offs must be strictly increasing after interventions")
    reg["index"] = np.arange(len(reg))
    return reg
