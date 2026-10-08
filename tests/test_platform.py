"""Platform tests (Task 8): command line, managed raw store, manual
interventions in the engine, audit trail and incremental updating."""
import dataclasses
import json

import pandas as pd
import pytest
import yaml

from conftest import DATA_ZIP, make_cfg


def _write_cfg(cfg, path):
    path.write_text(yaml.safe_dump({k: v for k, v in cfg.items() if not k.startswith("_")}, sort_keys=False))
    return str(path)


def test_cli_ingest_and_status(tmp_path, capsys):
    from spbm.__main__ import main
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Topo_260401.dxf").write_text("0\nEOF\n")
    cfg = make_cfg(tmp_path, sources=[])
    p = _write_cfg(cfg, tmp_path / "c.yaml")
    assert main(["ingest", "--config", p, str(inbox)]) == 0
    assert "1 new file(s)" in capsys.readouterr().out
    assert main(["ingest", "--config", p, str(inbox)]) == 0
    assert "0 new file(s)" in capsys.readouterr().out
    log = pd.read_csv(tmp_path / "raw_store" / "ingest_log.csv")
    assert log["name"].tolist() == ["Topo_260401.dxf"] and len(log["sha256"][0]) == 64
    assert main(["status", "--config", p]) == 0


def test_cli_rejects_bad_intervention_file(tmp_path):
    from spbm.__main__ import main
    cfg = make_cfg(tmp_path, sources=[])
    iv = pd.read_csv(cfg["inputs"]["manual_interventions"], dtype=str)
    iv.loc[0, "reason"] = ""
    iv.to_csv(cfg["inputs"]["manual_interventions"], index=False)
    with pytest.raises(ValueError, match="MI-001: 'reason' is required"):
        main(["ingest", "--config", _write_cfg(cfg, tmp_path / "c.yaml"), str(tmp_path)])


def _with_interventions(ds, rows):
    iv = pd.concat([ds.interventions, pd.DataFrame(rows)], ignore_index=True).fillna("")
    return dataclasses.replace(ds, interventions=iv)


def test_fms_exclude_intervention_removes_load(real_ds, resolved_cfg):
    from spbm.movement import prepare_loads
    cid = int(real_ds.fms["cycle_id"].iloc[10])
    ds2 = _with_interventions(real_ds, [{"id": "MI-T1", "type": "fms_exclude", "target": str(cid), "reason": "test",
                                         "author": "t", "date": "2026-10-08"}])
    L = prepare_loads(ds2, resolved_cfg)
    assert cid not in set(L["cycle_id"]) and len(L) == len(prepare_loads(real_ds, resolved_cfg)) - 1


def test_fms_location_unknown_intervention(real_ds, resolved_cfg):
    from spbm.movement import prepare_loads
    base = prepare_loads(real_ds, resolved_cfg)
    cid = int(base.loc[~base["loc_unknown"], "cycle_id"].iloc[0])
    ds2 = _with_interventions(real_ds, [{"id": "MI-T2", "type": "fms_location_unknown", "target": str(cid), "reason": "test",
                                         "author": "t", "date": "2026-10-08"}])
    L = prepare_loads(ds2, resolved_cfg)
    assert L.loc[L["cycle_id"] == cid, "loc_unknown"].item()
    assert L["loc_unknown"].sum() == base["loc_unknown"].sum() + 1


def test_manifest_history_and_change_report(tmp_path):
    from datetime import datetime
    from spbm import audit
    from spbm.config import load_config
    from spbm.io import SourceFile
    cfg = load_config()
    root = tmp_path / "out"
    f1 = SourceFile("Dump Data.csv", "fms", "x", "x", "a" * 64, 10)
    f2 = SourceFile("Topo_260401.dxf", "survey", "x", "x", "b" * 64, 10)
    audit.write_manifest(cfg, [f1], root, {"total_tonnes": 100.0, "last_survey": "A"}, datetime(2026, 10, 8, 1, 0, 0), [])
    assert audit.change_report(root) is None                    # one version only
    man = audit.write_manifest(cfg, [f1, f2], root, {"total_tonnes": 130.0, "last_survey": "B"}, datetime(2026, 10, 8, 2, 0, 0), ["n"])
    assert [m["id"] for m in man["manual_interventions"]] == ["MI-001", "MI-002"]
    rep = audit.change_report(root)
    assert "| total_tonnes | 100.00 | 130.00 | +30.00 |" in rep
    assert "New input files: Topo_260401.dxf" in rep
    assert len(list((root / "history").iterdir())) == 2
    assert len(pd.read_csv(root / "audit" / "run_log.csv")) == 2


def test_incremental_update_reconciles_pending_loads(real_cfg):
    """Data to 03-26 00:00: loads after the 03-22 survey cut-off are provisional.
    With the full record they fall in interval 7 and are survey-reconciled."""
    from spbm.dataset import load_dataset
    from spbm.movement import prepare_loads
    from spbm.volume import resolve_density
    early = load_dataset(real_cfg, until="2026-03-26 00:00", verbose=False)
    ce = resolve_density(early, real_cfg)
    Le = prepare_loads(early, ce)
    pending = set(Le.loc[Le["period"] == len(early.surveys), "cycle_id"])
    assert len(early.surveys) == 7 and len(pending) > 0
    full = load_dataset(real_cfg, verbose=False)
    Lf = prepare_loads(full, resolve_density(full, real_cfg)).set_index("cycle_id")
    assert (Lf.loc[sorted(pending), "period"] == 7).all()


@pytest.mark.slow
def test_pipeline_fast_run_and_update(tmp_path):
    """End to end in a temporary folder: a run with data to 03-23 07:00, then
    an update with all data; outputs, manifest and change report are written."""
    if not DATA_ZIP.exists():
        pytest.skip("project data zip not present")
    from spbm.pipeline import run
    cfg = make_cfg(tmp_path)
    kw = dict(do_mc=False, do_twin=False, do_robust=False, do_sens=False, do_temporal=False, do_scen=False, verbose=False)
    run(cfg, until="2026-03-23 07:00", **kw)
    out = run(cfg, **kw)
    root = tmp_path / "outputs"
    for rel in ["summary.json", "qaqc/qa_rule_catalogue.csv", "growth/temporal_alignment.csv", "growth/volume_factor_calibration.csv",
                "audit/run_manifest.json", "audit/ingest_log.csv", "audit/manual_interventions_applied.csv",
                "blockmodel/stockpile_block_model.csv", "blockmodel/stockpile_block_model.vtk", "audit/change_report.md"]:
        assert (root / rel).exists(), rel
    s = json.loads((root / "summary.json").read_text())["key_results"]
    assert s["survey_cutoff_hours"] == 31.0 and 1.40 < s["volume_factor"] < 1.55
    assert s["mass_balance_rel_err_ppm"] < 1e-3
    assert out["summary"]["n_surveys"] == 10
    rep = (root / "audit" / "change_report.md").read_text()
    assert "| n_surveys | 7.00 | 10.00 | +3.00 |" in rep
