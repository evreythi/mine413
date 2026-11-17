"""Shared fixtures. Real-data fixtures ingest the supplied zip into a
temporary raw store (the repository's data/raw_store is never touched by
the tests); rasterised surveys are cached in data/cache, keyed by file hash."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA_ZIP = ROOT / "Data_Topo 2026.zip"


def make_cfg(tmp: Path, sources=None, interventions=True, **over):
    """Project config with the raw store, interventions file and outputs in `tmp`."""
    from spbm.config import apply_overrides, load_config
    cfg = load_config()
    iv = tmp / "manual_interventions.csv"
    if interventions and not iv.exists():
        shutil.copy(ROOT / "config" / "manual_interventions.csv", iv)
    o = {"inputs.raw_store": str(tmp / "raw_store"), "inputs.manual_interventions": str(iv),
         "outputs.root": str(tmp / "outputs"),
         "inputs.sources": [str(DATA_ZIP)] if sources is None else [str(s) for s in sources]}
    o.update(over)
    return apply_overrides(cfg, o)


@pytest.fixture(scope="session")
def real_cfg(tmp_path_factory):
    if not DATA_ZIP.exists():
        pytest.skip("project data zip not present")
    return make_cfg(tmp_path_factory.mktemp("real"))


@pytest.fixture(scope="session")
def real_ds(real_cfg):
    from spbm.dataset import load_dataset
    return load_dataset(real_cfg, verbose=False)


@pytest.fixture(scope="session")
def real_cal(real_ds, real_cfg):
    from spbm.volume import calibrate
    return calibrate(real_ds, real_cfg)


@pytest.fixture(scope="session")
def resolved_cfg(real_ds, real_cfg):
    from spbm.volume import resolve_density
    return resolve_density(real_ds, real_cfg)


@pytest.fixture(scope="session")
def real_rec(real_ds, resolved_cfg):
    from spbm.movement import reconstruct
    return reconstruct(real_ds, resolved_cfg)


@pytest.fixture(scope="session")
def real_qa(real_ds, real_cfg, tmp_path_factory):
    from spbm.qaqc import run_qaqc
    return run_qaqc(real_ds, real_cfg, tmp_path_factory.mktemp("qa"))
