"""Kompaktní katalogová data se při načtení beze ztráty rozvinou."""

import json
from pathlib import Path

import kg_generator as kg
import pp_generator as pp

ROOT = Path(__file__).resolve().parents[1]


def test_kg_pipes_expand_from_sockets():
    raw = json.loads((ROOT / "data/kg_ostendorf.json").read_text())
    assert "pipes" not in raw
    table = kg.load_table()
    for dn, sock in raw["sockets"].items():
        expected = {"dmax_mm": sock["collar_diameter_mm"], "wall_mm": sock["wall_mm"],
                    "insertion_depth_t_mm": sock["insertion_depth_t_mm"],
                    "status": sock["status"], "source": sock["source"]}
        for key in ("socket_zone_mm", "socket_zone_status"):
            if key in sock:
                expected[key] = sock[key]
        assert table["pipes"][dn] == expected


def test_pp_shared_values_expand_exactly():
    raw = json.loads((ROOT / "data/pipelife_master3plus.json").read_text())
    for family, fields in {
        "elbows": ("DN", "od_mm", "socket_od_mm"),
        "cleanouts": ("DN", "od_mm", "socket_od_mm"),
        "reducers": ("DN", "large_socket_od_mm", "small_socket_od_mm"),
        "simple_branches": ("DN", "D_mm", "D1_mm", "D2_mm", "Dmax_mm"),
        "caps": ("DN",),
    }.items():
        assert all(not (set(fields) & row.keys()) for row in raw[family]), family
    expanded = pp.TABLE
    for row in expanded["elbows"] + expanded["cleanouts"]:
        dn = row["dn_od"]
        assert (row["DN"], row["od_mm"], row["socket_od_mm"]) == (
            pp.DN_BY_SIZE[dn], pp.OD[dn], pp.SOCKET_OD[dn])
    for row in expanded["reducers"]:
        assert row["DN"] == pp.DN_BY_SIZE[row["large_dn_od"]]
        assert row["large_socket_od_mm"] == pp.SOCKET_OD[row["large_dn_od"]]
        assert row["small_socket_od_mm"] == pp.SOCKET_OD[row["small_dn_od"]]
    for row in expanded["simple_branches"]:
        assert row["DN"] == pp.DN_BY_SIZE[row["dn_od"]]
        if row["angle_deg"] == 87.5:
            assert row["D_mm"] == pp.OD[row["dn_od"]]
            assert row["D1_mm"] == pp.OD[row["branch_dn_od"]]
            assert row["D2_mm"] == pp.SOCKET_OD[row["branch_dn_od"]]
            assert row["Dmax_mm"] == pp.SOCKET_OD[row["dn_od"]]
    assert all(row["DN"] == pp.DN_BY_SIZE[row["dn_od"]] for row in expanded["caps"])


def test_pp_dn90_socket_diameter_is_documented():
    assert pp.SOCKET_OD[90] == 105.4
    raw = json.loads((ROOT / "data/pipelife_master3plus.json").read_text())
    sockets = raw["dimension_status"]["socket"]["collar_outer_diameter_mm"]
    assert sockets["90"] == 105.4
