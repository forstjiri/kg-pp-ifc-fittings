import json
import math
from pathlib import Path


DATA = json.loads((Path(__file__).parents[1] / "data/kg_ostendorf.json").read_text())


def test_kg_catalogue_dimensions():
    elbows = DATA["elbows"]
    assert len(elbows) == 15
    assert len({row["article"] for row in elbows}) == 15
    assert {row["angle_deg"] for row in elbows} == {15, 30, 45, 67, 87}
    assert {row["dn_od"] for row in elbows} == {110, 125, 160}
    assert len(DATA["branches"]) == 12
    assert len(DATA["reducers"]) == 3
    assert len(DATA["caps"]) == 3
    assert len(DATA["cleanouts"]) == 3
    for group in ("elbows", "branches", "reducers", "caps", "cleanouts"):
        assert all({"status", "source", "series"} <= row.keys() for row in DATA[group])


def test_kg_elbow_geometry_identity():
    radii = {110: 60, 125: 69, 160: 88}
    for dn in (110, 125, 160):
        bases = [
            row["l1_mm"] - radii[dn] * math.tan(math.radians(row["angle_deg"]) / 2)
            for row in DATA["elbows"] if row["dn_od"] == dn
        ]
        assert max(bases) - min(bases) <= 2.0, (dn, bases)
