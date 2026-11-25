import json
from pathlib import Path


DATA = json.loads(
    (Path(__file__).parents[1] / "data/pipelife_master3plus.json").read_text()
)


def test_current_rows_have_catalogue_metadata_and_nominal_dn():
    for family in ("elbows", "simple_branches", "reducers", "cleanouts", "caps"):
        for row in DATA[family]:
            assert row["status"] == "catalogue"
            assert row["source"].startswith("handbook 2026, str. ")
            assert row["series"] == "current"
            assert "DN" in row
    assert all("branch_DN" in row for row in DATA["simple_branches"])


def test_handbook_elbows_and_l1_geometry():
    elbows = DATA["elbows"]
    assert {row["angle_deg"] for row in elbows} == {15, 30, 45, 67.5, 87.5}
    assert len({row["article"] for row in elbows}) == len(elbows)
    assert all(row["l1_mm"] == row["length_mm"] - row["z1_mm"] - 7 for row in elbows)
    row = next(
        row for row in elbows if row["dn_od"] == 110 and row["angle_deg"] == 45
    )
    assert row["DN"] == 100
    assert (row["length_mm"], row["z1_mm"], row["article"]) == (
        92,
        26,
        "M3-B100/45",
    )


def test_branch_dimensions_and_counts():
    branches = DATA["simple_branches"]
    assert len([row for row in branches if row["angle_deg"] == 45]) == 20
    assert len([row for row in branches if row["angle_deg"] == 67.5]) == 4
    assert len([row for row in branches if row["angle_deg"] == 87.5]) == 19
    branch = next(
        row
        for row in branches
        if row["dn_od"] == 110
        and row["branch_dn_od"] == 50
        and row["angle_deg"] == 87.5
    )
    assert (branch["length_mm"], branch["z1_mm"], branch["z2_mm"], branch["z3_mm"]) == (
        128,
        27,
        35,
        60,
    )
    assert branch["DN"] == 100
    assert branch["branch_DN"] == 50
    assert branch["l1_mm"] == 59
    assert DATA["legacy_article_examples"]["3496102512"]["series"] == "legacy"


def test_reducers_cleanouts_and_caps():
    assert len(DATA["reducers"]) == 13
    assert all(row["large_dn_od"] > row["small_dn_od"] for row in DATA["reducers"])
    row = next(
        row
        for row in DATA["reducers"]
        if row["large_dn_od"] == 160 and row["small_dn_od"] == 110
    )
    assert (row["DN"], row["length_mm"], row["z1_mm"], row["article"]) == (
        150,
        120,
        39,
        "M3-R150/100",
    )
    assert {row["dn_od"] for row in DATA["cleanouts"]} == {50, 75, 90, 110, 125, 160}
    assert len(DATA["caps"]) == 8
    assert [(row["dn_od"], row["length_mm"]) for row in DATA["caps"]] == [
        (32, 33),
        (40, 39),
        (50, 39),
        (75, 39),
        (90, 42),
        (110, 46),
        (125, 50),
        (160, 58),
    ]
