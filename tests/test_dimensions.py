"""Katalogová data: metadata, počty, kóty a geometrická identita."""

import math

import kg_generator
import pp_generator

# Načtení přes generátory = rozvinutí sdílených hodnot na původní kóty.
KG = kg_generator.load_table()
PP = pp_generator.TABLE


def test_kg_catalogue_dimensions():
    assert len(KG["elbows"]) == 15
    assert len({row["article"] for row in KG["elbows"]}) == 15
    assert {row["angle_deg"] for row in KG["elbows"]} == {15, 30, 45, 67, 87}
    assert {row["dn_od"] for row in KG["elbows"]} == {110, 125, 160}
    assert len(KG["branches"]) == 12
    assert len(KG["reducers"]) == 3
    assert len(KG["caps"]) == 3
    assert len(KG["cleanouts"]) == 3
    for group in ("elbows", "branches", "reducers", "caps", "cleanouts"):
        assert all({"status", "source", "series"} <= row.keys() for row in KG[group])


def test_kg_elbow_geometry_identity():
    for dn, radius in ((110, 60), (125, 69), (160, 88)):
        bases = [row["l1_mm"] - radius * math.tan(math.radians(row["angle_deg"]) / 2)
                 for row in KG["elbows"] if row["dn_od"] == dn]
        assert max(bases) - min(bases) <= 2.0, (dn, bases)


def test_pp_rows_have_catalogue_metadata_and_nominal_dn():
    for family in ("elbows", "simple_branches", "reducers", "cleanouts", "caps"):
        for row in PP[family]:
            assert row["status"] == "catalogue"
            assert row["source"].startswith(("handbook 2026, str. ", "brochure str. "))
            assert row["series"] == "current" and "DN" in row
    assert all("branch_DN" in row for row in PP["simple_branches"])


def test_pp_handbook_elbows_and_l1_geometry():
    elbows = PP["elbows"]
    assert {row["angle_deg"] for row in elbows} == {15, 30, 45, 67.5, 87.5}
    assert len({row["article"] for row in elbows}) == len(elbows)
    assert all(row["l1_mm"] == row["length_mm"] - row["z1_mm"] - 7 for row in elbows)
    row = next(r for r in elbows if r["dn_od"] == 110 and r["angle_deg"] == 45)
    assert row["DN"] == 100
    assert (row["length_mm"], row["z1_mm"], row["article"]) == (92, 26, "M3-B100/45")


def test_pp_branch_dimensions_and_counts():
    branches = PP["simple_branches"]
    assert len([r for r in branches if r["angle_deg"] == 45]) == 20
    assert len([r for r in branches if r["angle_deg"] == 67.5]) == 4
    assert len([r for r in branches if r["angle_deg"] == 87.5]) == 19
    branch = next(r for r in branches if (r["dn_od"], r["branch_dn_od"],
                                          r["angle_deg"]) == (110, 50, 87.5))
    assert (branch["length_mm"], branch["z1_mm"], branch["z2_mm"], branch["z3_mm"]) == (
        128, 27, 35, 60)
    assert (branch["DN"], branch["branch_DN"], branch["l1_mm"]) == (100, 50, 59)
    assert PP["legacy_article_examples"]["3496102512"]["series"] == "legacy"


def test_pp_reducers_cleanouts_and_caps():
    assert len(PP["reducers"]) == 13
    assert all(r["large_dn_od"] > r["small_dn_od"] for r in PP["reducers"])
    row = next(r for r in PP["reducers"] if (r["large_dn_od"],
                                             r["small_dn_od"]) == (160, 110))
    assert (row["DN"], row["length_mm"], row["z1_mm"], row["article"]) == (
        150, 120, 39, "M3-R150/100")
    assert {r["dn_od"] for r in PP["cleanouts"]} == {50, 75, 90, 110, 125, 160}
    re110 = next(r for r in PP["cleanouts"] if r["dn_od"] == 110)
    assert (re110["length_mm"], re110["z1_mm"], re110["service_diameter_mm"],
            re110["service_reach_mm"]) == (192, 126, 64, 80)
    assert len(PP["caps"]) == 8
    assert [(r["dn_od"], r["length_mm"]) for r in PP["caps"]] == [
        (32, 33), (40, 39), (50, 39), (75, 39), (90, 42),
        (110, 46), (125, 50), (160, 58),
    ]
