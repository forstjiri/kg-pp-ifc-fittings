import json
from pathlib import Path


DATA = json.loads(
    (Path(__file__).parents[1] / "data/pipelife_master3plus.json").read_text()
)


def test_current_handbook_elbow_rows_and_real_size_coverage():
    elbows = DATA["elbows"]
    assert {row["dn_od"] for row in elbows} == {32, 40, 50, 75, 110, 125, 160}
    assert {row["angle_deg"] for row in elbows} == {15, 30, 45, 67.5, 87.5}
    assert len({row["article"] for row in elbows}) == len(elbows)
    assert next(
        row for row in elbows if row["dn_od"] == 110 and row["angle_deg"] == 45
    ) == {
        "angle_deg": 45,
        "dn_od": 110,
        "od_mm": 111.3,
        "socket_od_mm": 127.0,
        "l1_mm": 59,
        "l2_mm": 60.6,
        "length_mm": 92,
        "z1_mm": 26,
        "z2_mm": 31,
        "article": "M3-B100/45",
        "status": "current catalogue",
    }


def test_branch_dimensions_and_legacy_current_are_not_conflated():
    branch = next(
        row
        for row in DATA["simple_branches"]
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
    assert DATA["legacy_article_examples"]["3496102512"]["z1_mm"] == -16
    assert DATA["legacy_article_examples"]["3496102512"]["source_series"].startswith("legacy")
    assert DATA["dimension_status"]["socket"]["depth_status"].startswith("catalogue")


def test_current_handbook_reducer_rows_are_sold_pairs():
    rows = DATA["reducers"]
    assert len(rows) == 9
    assert all(row["large_dn_od"] > row["small_dn_od"] for row in rows)
    row = next(row for row in rows if row["large_dn_od"] == 160 and row["small_dn_od"] == 110)
    assert (row["length_mm"], row["z1_mm"], row["article"]) == (120, 39, "M3-R150/100")


def test_inspection_piece_catalogue_rows_flag_unlisted_cover_dimensions():
    rows = DATA["cleanouts"]
    assert {row["dn_od"] for row in rows} == {50, 75, 110, 125, 160}
    assert all("approximate" in row["service_dimensions_status"] for row in rows)
    row = next(row for row in rows if row["dn_od"] == 110)
    assert (row["length_mm"], row["z1_mm"], row["article"]) == (128, 62, "M3-RE100")
