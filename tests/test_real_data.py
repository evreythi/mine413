"""Tests on the supplied project data (Data_Topo 2026.zip). They pin the
facts the report relies on, so a change in code or data that moves them is
caught. Fixtures in conftest.py; the reconstruction fixture takes ~15 s."""
import numpy as np
import pandas as pd
import pytest

from spbm.movement import NP, P


# ------------------------------------------------------------ inventory of inputs
def test_inventory_counts(real_ds):
    assert len(real_ds.fms) == 275
    assert len(real_ds.surveys) == 10
    assert real_ds.fms["payload_t"].sum() == pytest.approx(44650.0)


def test_payloads_are_whole_passes_of_38t(real_ds):
    assert ((real_ds.fms["payload_t"] % 38) == 0).all()


def test_grade_signatures(real_qa):
    assert real_qa["summary"]["n_grade_signatures"] == 21


def test_two_surveys_redated_by_logged_interventions(real_ds):
    reg = real_ds.register.set_index("file")
    assert reg.loc["Topo_250328.dxf", "intervention_ids"] == "MI-001"
    assert reg.loc["Topo_250329.dxf", "intervention_ids"] == "MI-002"
    assert [s.file for s in real_ds.surveys][-2:] == ["Topo_250328.dxf", "Topo_250329.dxf"]
    assert str(real_ds.surveys[-1].datetime) == "2026-03-30 07:00:00"     # D+1 07:00 (A-05)


def test_dxf_header_declares_inches_but_data_are_metres(real_ds, real_qa):
    assert {s.meta["insunits"] for s in real_ds.surveys} == {1}
    assert {s.meta["measurement"] for s in real_ds.surveys} == {0}
    cat = real_qa["catalogue"].set_index("rule_id")
    assert cat.loc["DXF_UNITS_HEADER", "count"] == 10
    # metres: pile extent ~100 m and elevations ~4,480 m (in inches it would be 2.5 m wide at 114 m)
    g = real_ds.grid
    assert 80 < g.nx * g.cell < 250
    assert 4470 < np.nanmin(real_ds.surveys[0].bot) < 4490


def test_survey_solids_are_closed_and_total_volume(real_ds):
    for s in real_ds.surveys:
        assert s.meta["closed_solid_frac"] > 0.98, s.file
        assert s.meta["zero_plan_area"] > 0          # vertical walls present, ignored
    vol = sum(np.nansum(s.thickness) * real_ds.grid.area for s in real_ds.surveys)
    assert vol == pytest.approx(35100, rel=0.01)


def test_repose_angle_from_faces(real_qa):
    assert 33.0 <= real_qa["summary"]["repose"]["p50"] <= 38.0


# ------------------------------------------------------------ QA rule counts
@pytest.mark.parametrize("rule, n, tonnes", [
    ("LOC_DEFAULT", 14, 2356.0),
    ("TIME_AFTER_LAST_SURVEY", 1, 228.0),
    ("TIME_DUPLICATE", 2, None),
    ("PAYLOAD_PARTIAL", 3, None),
    ("PAYLOAD_HIGH", 3, None),
    ("PAYLOAD_OFF_QUANTUM", 0, None),
    ("DUP_CONFLICT", 0, None),
    ("SURVEY_NAME_YEAR", 2, None),
])
def test_qa_rule_counts(real_qa, rule, n, tonnes):
    cat = real_qa["catalogue"].set_index("rule_id")
    assert cat.loc[rule, "count"] == n
    if tonnes is not None:
        assert cat.loc[rule, "tonnes"] == pytest.approx(tonnes)


def test_dump_z_mostly_inside_interval_envelope(real_qa):
    assert real_qa["catalogue"].set_index("rule_id").loc["LOC_Z_INCONSISTENT", "count"] <= 5


def test_qa_never_deletes_records(real_qa):
    assert len(real_qa["fms"]) == 275 and real_qa["summary"]["n_excluded"] == 0


# ------------------------------------------------------------ timing (A-05)
def test_cutoff_scan_supports_31h(real_ds, real_cfg, tmp_path):
    from spbm.growth import temporal_alignment
    al = temporal_alignment(real_ds, real_cfg, tmp_path).set_index("cutoff_hours")
    best = al["r_daily"].idxmax()
    assert 29.0 <= best <= 32.0
    assert al.loc[31.0, "r_daily"] > al.loc[24.0, "r_daily"] + 0.02
    assert al.loc[31.0, "ratio_rcv_daily"] < 0.5 * al.loc[24.0, "ratio_rcv_daily"]


def test_shift_change_lull_in_dump_times(real_ds):
    t = pd.to_datetime(real_ds.fms["timestamp"])
    h = t.dt.hour + t.dt.minute / 60
    assert ((h >= 6.0) & (h < 7.5)).sum() <= 2
    assert ((h >= 18.5) & (h < 20.0)).sum() == 0


# ------------------------------------------------------------ volume factor (A-06)
def test_volume_factor_calibration(real_cal):
    assert 1.40 <= real_cal["f_v"] <= 1.55
    assert real_cal["consistent_intervals"] == [1, 2, 3, 4, 5, 6, 8]
    assert real_cal["excluded_intervals"] == [0, 7, 9]


def test_volume_factor_holdout(real_cal):
    assert real_cal["holdout_mae_fv"] < 0.05
    assert real_cal["holdout_mae_fv"] < 0.5 * real_cal["holdout_mae_const_density"]
    assert real_cal["holdout_mae_dens_as_inpile"] > 0.2      # f_v = 1 fails badly
    assert abs(real_cal["f_v_first_half"] - real_cal["f_v"]) < 0.05


def test_bootstrap_brackets_f_v_within_ratio_range(real_cal):
    t = real_cal["table"]
    c = t[t["consistent"]]["ratio"]
    assert real_cal["f_v_p10"] < real_cal["f_v"] < real_cal["f_v_p90"]
    assert c.min() <= real_cal["f_v_p10"] and real_cal["f_v_p90"] <= c.max()


def test_excluded_intervals_have_fms_coverage_evidence(real_cal):
    t = real_cal["table"].set_index("interval")
    assert t.loc[7, "longest_fms_silence_h"] > 48          # 03-23 to 03-27 FMS outage
    assert (t.loc[[0, 7, 9], "ratio"] > 2.0).all()          # surveyed fill well above FMS volume


@pytest.mark.parametrize("fpay", [1.0, 1.19])
def test_in_pile_volume_independent_of_payload_split(real_ds, resolved_cfg, fpay):
    from spbm.config import apply_overrides
    from spbm.movement import prepare_loads
    c = apply_overrides(resolved_cfg, {"density.payload_factor": fpay})
    L = prepare_loads(real_ds, c)
    fv = c["density"]["volume_factor_resolved"]
    assert np.allclose(L["vol"], L["m_recorded"] * fv / L["dens_fms"])
    assert np.allclose(L["m"], L["m_recorded"] * fpay)


def test_unknown_location_loads(real_ds, resolved_cfg):
    from spbm.movement import prepare_loads
    L = prepare_loads(real_ds, resolved_cfg)
    assert L["loc_unknown"].sum() == 14
    assert L.loc[L["loc_unknown"], "m"].sum() == pytest.approx(2356.0)


# ------------------------------------------------------------ reconstruction
def test_mass_and_metal_conserved_exactly(real_ds, real_rec, resolved_cfg):
    from spbm import blockmodel as bm
    bg = bm.make_block_grid(real_rec, resolved_cfg)
    agg = bm.aggregate(real_rec, bg).reshape(-1, NP).sum(0)
    for k in ["T_F", "CU_F", "AU_F", "AG_F"]:
        assert agg[P[k]] == pytest.approx(real_rec.totals_in[k], rel=1e-9)
    assert real_rec.totals_in["T_F"] == pytest.approx(real_ds.fms["payload_t"].sum())


def test_record_period_inventory(real_rec, resolved_cfg):
    from spbm import blockmodel as bm
    from spbm.validation import class_inventory
    bg = bm.make_block_grid(real_rec, resolved_cfg)
    inv = class_inventory(real_rec, bm.aggregate(real_rec, bg))
    rp = inv.loc[0, "tonnes"] + inv.loc[1, "tonnes"]
    assert 42_000 < rp < 56_000
    assert inv.loc[1, "tonnes"] < 0.15 * rp                 # unattributed is a small share once f_v is calibrated
    assert real_rec.periods["unattributed_volume"].sum() < 4_000


def test_model_reproduces_surveyed_surface(real_rec, real_ds, tmp_path):
    from spbm.validation import geometry_check
    assert geometry_check(real_rec, real_ds, tmp_path)["rmse_m"] < 0.1


def test_unknown_location_loads_fully_placed(real_rec):
    d = real_rec.destinations
    assert "loc_unknown" in d and d["loc_unknown"].sum() > 0
    u = d[d["loc_unknown"] & ~d["kind"].str.startswith("provisional")]
    assert (u["placed_volume"] + u["retained_volume"]).sum() == pytest.approx(u["volume_in"].sum(), rel=1e-6)


def test_flat_cost_ablation_changes_allocation_not_totals(real_ds, real_rec, resolved_cfg):
    """The push term only re-allocates material inside each interval's fill:
    totals are unchanged, block grades move."""
    from spbm import blockmodel as bm
    from spbm.config import apply_overrides
    from spbm.movement import reconstruct
    flat = reconstruct(real_ds, apply_overrides(resolved_cfg, {"movement.cost": "flat"}))
    bg = bm.make_block_grid(real_rec, resolved_cfg)
    a0 = bm.aggregate(real_rec, bg).reshape(-1, NP)
    a1 = bm.aggregate(flat, bg).reshape(-1, NP)
    for k in ["T_F", "CU_F", "AU_F"]:
        assert a1[:, P[k]].sum() == pytest.approx(a0[:, P[k]].sum(), rel=1e-9)
    assert flat.periods["unattributed_volume"].sum() == pytest.approx(real_rec.periods["unattributed_volume"].sum(), rel=0.02)
    moved = np.abs(a1[:, P["CU_F"]] - a0[:, P["CU_F"]]).sum() / a0[:, P["CU_F"]].sum()
    assert moved > 0.01                                  # allocation does change
