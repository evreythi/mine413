"""Unit and integration tests: `python -m pytest -q`."""
import numpy as np
import pytest

from spbm.forward import avalanche
from spbm.grid import Grid, rasterize_triangles
from spbm.movement import NP, P, ColumnModel, bulk_props, sinkhorn
from spbm.surfaces import infer_surface


def test_rasterize_closed_box():
    # 10 x 10 m square at z=1 (top) and z=0 (bottom), two triangles each
    top = [[(0, 0, 1), (10, 0, 1), (10, 10, 1)], [(0, 0, 1), (10, 10, 1), (0, 10, 1)]]
    bot = [[(0, 0, 0), (10, 10, 0), (10, 0, 0)], [(0, 0, 0), (0, 10, 0), (10, 10, 0)]]
    T = np.array(top + bot, float)
    g = Grid(0.0, 0.3, 10, 9, 1.0)  # centres off the shared diagonal
    zmax, zmin, cnt = rasterize_triangles(T, g)
    assert (cnt == 2).all()
    assert np.allclose(zmax, 1) and np.allclose(zmin, 0)
    assert np.isclose(((zmax - zmin) * g.area).sum(), 90.0)


def test_sinkhorn_marginals_exact_rows():
    rng = np.random.default_rng(0)
    a = rng.random(6) + 0.1
    b = rng.random(9) + 0.1
    b *= a.sum() / b.sum()
    C = rng.random((6, 9)) * 50
    Pm, col_err, _ = sinkhorn(a, b, C, eps=2.0, tol=1e-9, max_iter=20000)
    assert np.allclose(Pm.sum(1), a, rtol=1e-12)
    assert col_err < 1e-6


def test_sinkhorn_small_eps_approaches_assignment():
    a = np.array([1.0, 1.0])
    b = np.array([1.0, 1.0])
    C = np.array([[0.0, 10.0], [10.0, 0.0]])
    Pm, _, _ = sinkhorn(a, b, C, eps=0.5, tol=1e-10)
    assert Pm[0, 0] > 0.99 and Pm[1, 1] > 0.99


def test_column_remove_top_conserves():
    cm = ColumnModel(1, 1)
    cm.start(0, 0.0)
    cm.add(0, 2.0, bulk_props(2.0, 2.0, 8.0, 7.0, 200.0, "L"))
    cm.add(0, 1.0, bulk_props(1.0, 2.0, 10.0, 9.0, 200.0, "U"))
    before = cm.totals()
    removed = cm.remove_top(0, 1.5)
    after = cm.totals()
    assert np.isclose(cm.top[0], 1.5)
    assert np.allclose((after + removed)[:P["MSQ_F"]], before[:P["MSQ_F"]])
    assert np.isclose(removed[P["VOL"]], 1.5)


def test_avalanche_conserves_volume_and_limits_slope():
    z = np.zeros((40, 40))
    add = np.zeros_like(z)
    add[18:22, 18:22] = 5.0
    tanphi = np.tan(np.radians(37))
    z2, _ = avalanche(z + add, add, 1.0, tanphi, tol=1e-4, max_iter=20000)
    assert np.isclose(z2.sum(), (z + add).sum())
    dx = np.abs(np.diff(z2, axis=1)).max()
    assert dx <= tanphi + 0.05


def test_infer_surface_platform_and_front():
    ny, nx = 30, 30
    B = np.zeros((ny, nx))
    known = np.zeros((ny, nx), bool)
    z = np.zeros((ny, nx))
    # a face sloping down to the south between rows 10 and 20, platform north (rows>20) at 10 m
    for j in range(10, 20):
        known[j, :] = True
        z[j, :] = (j - 10) * 1.0
    dom = np.ones((ny, nx), bool)
    out, side = infer_surface(z, known, B, dom, 1.0, 37.0)
    assert out[28, 15] == pytest.approx(9.0)     # behind crest: platform level
    assert out[2, 15] == pytest.approx(0.0)      # in front: floor
    assert side[28, 15] == 1 and side[2, 15] == 2


@pytest.mark.slow
def test_end_to_end_mass_and_metal_conservation():
    from spbm import blockmodel as bm
    from spbm.config import load_config
    from spbm.dataset import load_dataset
    from spbm.movement import reconstruct
    cfg = load_config()
    ds = load_dataset(cfg, verbose=False)
    rec = reconstruct(ds, cfg)
    bg = bm.make_block_grid(rec, cfg)
    agg = bm.aggregate(rec, bg).reshape(-1, NP).sum(0)
    for k in ["T_F", "CU_F", "AU_F", "AG_F"]:
        assert agg[P[k]] == pytest.approx(rec.totals_in[k], rel=1e-9)
    # every FMS record is accounted for
    assert np.isclose(rec.totals_in["T_F"], ds.fms["payload_t"].sum())


def test_survey_override_redates_files():
    from spbm.config import load_config
    from spbm.dataset import load_dataset
    ds = load_dataset(load_config(), verbose=False)
    names = [s.file for s in ds.surveys]
    assert names[-2:] == ["Topo_250328.dxf", "Topo_250329.dxf"]
    assert str(ds.surveys[-1].datetime.date()) == "2026-03-29"


def test_markdown_tables_escape_pipes():
    import importlib.util
    import pandas as pd
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("fill_report", Path(__file__).resolve().parents[1] / "tools" / "fill_report.py")
    fr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fr)
    txt = fr.md(pd.DataFrame({"a": ["|x| > 3"], "b": [1]}), "t")
    row = [l for l in txt.splitlines() if "x" in l][0]
    assert row.count(" | ") == 1 and "\\|x\\|" in row


def test_code_identity_without_git(tmp_path, monkeypatch):
    from spbm import audit
    monkeypatch.setattr(audit, "ROOT", tmp_path)   # a folder that is not a git checkout
    (tmp_path / "spbm").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "BUILD_INFO.json").write_text('{"git_commit": "abc123", "packaged": "2026-11-26"}')
    s = audit.git_commit()
    assert "not a git checkout" in s and "abc123" in s
