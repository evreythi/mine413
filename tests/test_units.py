"""Unit tests on small synthetic inputs (no project data needed)."""
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


# ------------------------------------------------------------ grid / geometry
def test_grid_index_inside_mask_and_anchor():
    g = Grid.from_extent(511291.3, 511400.0, 7122281.0, 7122390.0, 1.0, 6.0, anchor=10.0)
    assert g.x0 % 10 == 0 and g.y0 % 10 == 0
    j, i, inside = g.index([g.x0 + 0.5, g.x0 - 5.0], [g.y0 + 0.5, g.y0 + 0.5])
    assert inside.tolist() == [True, False] and (i[0], j[0]) == (0, 0)


def test_triangle_stats_counts_vertical_and_degenerate_faces():
    from spbm.grid import triangle_stats
    T = np.array([[(0, 0, 0), (1, 0, 0), (0, 1, 0)],        # horizontal
                  [(0, 0, 0), (1, 0, 0), (1, 0, 1)],        # vertical wall: zero plan area
                  [(0, 0, 0), (1, 1, 1), (2, 2, 2)]], float)  # collinear: degenerate
    st = triangle_stats(T)
    assert st["zero_plan_area"] == 1 and st["degenerate"] == 1


def test_read_dxf_header_units_and_quad_split(tmp_path):
    import ezdxf
    from spbm.io import SourceFile, read_dxf_triangles
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 1
    msp = doc.modelspace()
    msp.add_3dface([(0, 0, 1), (10, 0, 1), (10, 10, 1), (0, 10, 1)], dxfattribs={"layer": "250315_STOCK"})
    msp.add_3dface([(0, 0, 0), (10, 0, 0), (10, 10, 0), (10, 10, 0)], dxfattribs={"layer": "250315_STOCK"})
    p = tmp_path / "Topo_260315.dxf"
    doc.saveas(p)
    T, meta = read_dxf_triangles(SourceFile(p.name, "survey", str(tmp_path), str(p), "0" * 64, p.stat().st_size))
    assert T.shape == (3, 3, 3)                  # quad -> 2 triangles, triangle -> 1
    assert meta["insunits"] == 1 and meta["layers"] == ["250315_STOCK"]
    assert len(meta["tdupdate"]) == 10           # Julian date converted to YYYY-MM-DD


def test_parse_survey_date():
    from spbm.io import parse_survey_date
    assert str(parse_survey_date("Topo_260327.dxf").date()) == "2026-03-27"
    assert str(parse_survey_date("Topo_250328.dxf").date()) == "2025-03-28"
    assert parse_survey_date("Topo_final.dxf") is None


# ------------------------------------------------------------ config
def test_apply_overrides_copies_and_hash_changes():
    from spbm.config import apply_overrides, config_hash, load_config
    cfg = load_config()
    c2 = apply_overrides(cfg, {"movement.epsilon": 99.0})
    assert cfg["movement"]["epsilon"] != 99.0 and c2["movement"]["epsilon"] == 99.0
    assert config_hash(cfg) == config_hash(load_config()) != config_hash(c2)


def test_every_config_assumption_is_in_the_register():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ids = set(re.findall(r"\bA-\d+\b", (root / "config" / "project.yaml").read_text()))
    reg = (root / "tools" / "templates" / "D2_Data_and_Assumption_Register.template.md").read_text()
    missing = sorted(i for i in ids if not re.search(rf"\b{i}\b", reg))
    assert not missing, f"config cites assumptions not in D2: {missing}"


# ------------------------------------------------------------ QA rules
def _fms(rows):
    import pandas as pd
    cols = ["cycle_id", "payload_t", "cu_pct", "au_gpt", "ag_gpt", "density", "x", "y", "z", "timestamp_raw"]
    f = pd.DataFrame(rows, columns=cols)
    f["timestamp"] = pd.to_datetime(f["timestamp_raw"], errors="coerce")
    return f


def _rows():
    t = "2026-03-16 08:%02d"
    base = [(i, 152.0, 8.0, 8.0, 50.0, 2.1, 100.0 + i, 200.0, 4480.0, t % i) for i in range(1, 9)]
    base += [(9, 150.0, 8.0, 8.0, 50.0, 2.1, 1.0, 2.0, 3.0, t % 20),      # off quantum
             (10, 38.0, 8.0, 8.0, 50.0, 2.1, 1.0, 2.0, 3.0, t % 21),      # partial
             (11, 304.0, 8.0, 8.0, 50.0, 2.1, 1.0, 2.0, 3.0, t % 22),     # high; 9-11 share X/Y/Z
             (12, 152.0, -1.0, 8.0, 50.0, 2.1, 5.0, 5.0, 5.0, t % 23),    # invalid grade
             (13, 152.0, 8.0, 8.0, 50.0, 3.4, 6.0, 6.0, 6.0, t % 24),     # invalid density
             (14, None, 8.0, 8.0, 50.0, 2.1, 7.0, 7.0, 7.0, t % 25),      # missing payload
             (1, 152.0, 8.0, 8.0, 50.0, 2.1, 101.0, 200.0, 4480.0, t % 1),  # identical repeat of 1
             (2, 190.0, 8.0, 8.0, 50.0, 2.1, 102.0, 200.0, 4480.0, t % 2),  # conflicting repeat of 2
             (15, 152.0, 8.0, 8.0, 50.0, 2.1, 8.0, 8.0, 8.0, t % 25)]     # same time as 14
    return base


def test_record_rules_flag_without_deleting():
    from spbm.config import load_config
    from spbm.rules import record_rules
    f = _fms(_rows())
    r = record_rules(f, load_config())
    assert len(r) == len(f)                                 # nothing deleted
    hit = lambda k: sorted(f.loc[r[k], "cycle_id"].astype(int).tolist())  # noqa: E731
    assert hit("PAYLOAD_OFF_QUANTUM") == [9]
    assert hit("PAYLOAD_PARTIAL") == [10]
    assert hit("PAYLOAD_HIGH") == [11]
    assert hit("GRADE_INVALID") == [12]
    assert hit("DENS_INVALID") == [13]
    assert hit("MISSING_PAYLOAD") == [14]
    assert hit("DUP_IDENTICAL") == [1] and r["DUP_IDENTICAL"].sum() == 1
    assert hit("DUP_CONFLICT") == [2] and r["DUP_CONFLICT"].sum() == 1
    assert hit("LOC_DEFAULT") == [9, 10, 11]
    assert hit("TIME_DUPLICATE")[-2:] == [14, 15]


def test_model_exclusions_drop_errors_and_repeats_only():
    from spbm.config import load_config
    from spbm.rules import model_exclusions
    f = _fms(_rows())
    ex = model_exclusions(f, load_config())
    excluded = sorted(f.loc[ex, "cycle_id"].astype(int).tolist())
    assert excluded == [1, 2, 12, 13, 14]                  # second copies of 1 and 2, plus three errors
    assert not ex[f["cycle_id"] == 9].any()                 # warnings are modelled


def test_read_fms_coerces_bad_values(tmp_path):
    from spbm.io import SourceFile, read_fms
    p = tmp_path / "Dump Data.csv"
    p.write_text("Cycle ID,Truck PayLoad,Au,Ag,Cu,Dens,X (Dump Event),Y (Dump Event),Z (Dump Event),Dump_tstamp\n"
                 "1,152,8,50,8.4,2.1,511300,7122300,4480,3/16/2026 8:05\n"
                 "2,abc,8,50,8.4,2.1,511300,7122300,4480,not a time\n")
    f = read_fms([SourceFile(p.name, "fms", str(tmp_path), str(p), "0" * 64, p.stat().st_size)])
    assert f["payload_t"].isna().tolist() == [False, True]
    assert f.loc[1, "coerced_fields"] == "payload_t"
    assert f["timestamp"].isna().tolist() == [False, True]


# ------------------------------------------------------------ governance
def _iv_file(tmp_path, rows):
    import pandas as pd
    from spbm.io import INTERVENTION_COLUMNS
    p = tmp_path / "mi.csv"
    pd.DataFrame(rows, columns=INTERVENTION_COLUMNS).to_csv(p, index=False)
    return {"inputs": {"manual_interventions": str(p)}}


def test_valid_interventions_load(tmp_path):
    from spbm.io import load_interventions
    cfg = _iv_file(tmp_path, [["MI-1", "survey_date", "Topo_250328.dxf", "2026-03-28", "year typo", "A. Surveyor", "2026-10-01", ""]])
    assert len(load_interventions(cfg)) == 1


@pytest.mark.parametrize("row, msg", [
    (["MI-1", "survey_date", "Topo_250328.dxf", "2026-03-28", "", "A. Surveyor", "2026-10-01", ""], "'reason' is required"),
    (["MI-1", "survey_date", "Topo_250328.dxf", "2026-03-28", "typo", "", "2026-10-01", ""], "'author' is required"),
    (["MI-1", "survey_date", "Topo_250328.dxf", "2026-03-28", "typo", "A. S", "yesterday", ""], "not a valid date"),
    (["MI-1", "delete_record", "1234", "", "typo", "A. S", "2026-10-01", ""], "unsupported type"),
])
def test_intervention_without_reason_author_or_date_is_rejected(tmp_path, row, msg):
    from spbm.io import load_interventions
    with pytest.raises(ValueError, match=msg):
        load_interventions(_iv_file(tmp_path, [row]))


def test_duplicate_intervention_ids_rejected(tmp_path):
    from spbm.io import load_interventions
    r = ["MI-1", "fms_exclude", "1", "", "bad record", "A. S", "2026-10-01", ""]
    with pytest.raises(ValueError, match="duplicate ids"):
        load_interventions(_iv_file(tmp_path, [r, r]))


def _ingest_cfg(tmp_path, src):
    from spbm.config import load_config
    cfg = load_config()
    cfg["inputs"].update(sources=[str(src)], raw_store=str(tmp_path / "store"))
    return cfg


def test_ingest_is_idempotent_and_refuses_conflicts(tmp_path):
    import pandas as pd
    from spbm.io import ingest, scan_sources
    src = tmp_path / "inbox"
    src.mkdir()
    (src / "Dump Data.csv").write_text("a,b\n1,2\n")
    (src / "notes.txt").write_text("not a data file")
    cfg = _ingest_cfg(tmp_path, src)
    first = ingest(cfg)
    assert first["name"].tolist() == ["Dump Data.csv"] and first["status"].tolist() == ["new"]
    assert len(ingest(cfg)) == 0                                    # idempotent
    (src / "Dump Data.csv").write_text("a,b\n1,3\n")               # same name, new content
    with pytest.raises(ValueError, match="ingest refused"):
        ingest(cfg)
    # authorised by a supersede intervention -> accepted, and becomes the current version
    import hashlib
    h = hashlib.sha256(b"a,b\n1,3\n").hexdigest()
    iv = pd.DataFrame([{"id": "MI-9", "type": "supersede", "target": "Dump Data.csv", "value": h[:12]}])
    new = ingest(cfg, interventions=iv)
    assert new["status"].tolist() == ["supersedes"]
    files = scan_sources(cfg, iv)
    assert [f.sha256 for f in files] == [h]
    log = pd.read_csv(tmp_path / "store" / "ingest_log.csv")
    assert len(log) == 2 and (tmp_path / "store" / log.loc[0, "stored_as"]).read_text() == "a,b\n1,2\n"   # raw kept


def test_ingest_reads_zip_and_skips_resource_forks(tmp_path):
    import zipfile
    from spbm.io import ingest
    z = tmp_path / "d.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("d/Topo_260315.dxf", "0\nEOF\n")
        zf.writestr("__MACOSX/d/._Topo_260315.dxf", "junk")
    new = ingest(_ingest_cfg(tmp_path, z))
    assert new["name"].tolist() == ["Topo_260315.dxf"] and new["kind"].tolist() == ["survey"]


def _register(cfg_over, files=("Topo_260315.dxf", "Topo_260316.dxf"), iv=None):
    from spbm.config import apply_overrides, load_config
    from spbm.io import SourceFile, survey_register
    cfg = apply_overrides(load_config(), cfg_over)
    return survey_register([SourceFile(n, "survey", "", "", "0" * 64, 0) for n in files], cfg, iv)


def test_survey_cutoff_hours_and_intervention():
    import pandas as pd
    reg = _register({"time.survey_cutoff_hours": 31.0})
    assert str(reg.loc[0, "survey_datetime"]) == "2026-03-16 07:00:00"
    iv = pd.DataFrame([{"id": "MI-5", "type": "survey_cutoff_hours", "target": "Topo_260316.dxf", "value": "26.5", "reason": "r"}])
    reg = _register({"time.survey_cutoff_hours": 31.0}, iv=iv)
    assert str(reg.loc[1, "survey_datetime"]) == "2026-03-17 02:30:00" and reg.loc[1, "intervention_ids"] == "MI-5"


def test_non_increasing_cutoffs_rejected():
    import pandas as pd
    iv = pd.DataFrame([{"id": "MI-6", "type": "survey_date", "target": "Topo_260316.dxf", "value": "2026-03-15", "reason": "r"}])
    with pytest.raises(ValueError, match="strictly increasing"):
        _register({}, iv=iv)


# ------------------------------------------------------------ volume factor
def _budget(ratios, vd=1000.0):
    import pandas as pd
    r = np.asarray(ratios, float)
    return pd.DataFrame({"interval": np.arange(len(r)), "net_m3": r * vd, "vdens_m3": vd, "ratio": r})


def test_robust_volume_factor_rejects_outliers():
    from spbm.volume import robust_factor
    res = robust_factor(_budget([2.4, 1.48, 1.52, 1.50, 1.46, 1.55, 2.3]), 3.0)
    assert res["excluded"] == [0, 6]
    assert res["f_v"] == pytest.approx(1.502, abs=1e-3)


def test_density_factors_identity_and_overrides():
    from spbm.config import apply_overrides, load_config
    from spbm.movement import density_factors
    cfg = apply_overrides(load_config(), {"density.volume_factor": 1.5, "density.payload_factor": 1.1})
    assert density_factors(cfg) == (1.5, 1.1)
    assert density_factors(cfg, {"volume_factor": 1.3, "payload_factor": 1.0}) == (1.3, 1.0)
    auto = apply_overrides(load_config(), {"density.volume_factor": "auto"})
    with pytest.raises(ValueError, match="not resolved"):
        density_factors(auto)
