"""Configuration loading. All parameters come from config/project.yaml."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path = "config/project.yaml", overrides: dict | None = None) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p) as fh:
        cfg = yaml.safe_load(fh)
    cfg["_path"] = str(p)
    if overrides:
        cfg = apply_overrides(cfg, overrides)
    return cfg


def apply_overrides(cfg: dict, overrides: dict) -> dict:
    """overrides: {"movement.epsilon": 3.0, ...} (dotted keys)."""
    cfg = copy.deepcopy(cfg)
    for key, val in overrides.items():
        node = cfg
        parts = key.split(".")
        for k in parts[:-1]:
            node = node[k]
        node[parts[-1]] = val
    return cfg


def config_hash(cfg: dict) -> str:
    clean = {k: v for k, v in cfg.items() if not k.startswith("_")}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, default=str).encode()).hexdigest()[:12]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
