"""KG swept recipes vs manufacturer STEP references (IoU per orthogonal view)."""

from pathlib import Path

import numpy as np
import pytest

import kg_generator
from tests.silhouette import iou, tessellate
from tools.measure_reference import canonical_elbow_frame, load_mesh, mouth_annuli

ROOT = Path(__file__).parents[1]
TABLE = kg_generator.load_table()

# (mesh, katalogový úhel, DN) — všechny dostupné kolení reference
ELBOW_REFS = (
    ("220200z", 15, 110),
    ("220210z", 30, 110),
    ("220220z", 45, 110),
    ("222200z", 15, 160),
    ("222210z", 30, 160),
)


def _reference(article, origin_mouth):
    """Reference mesh v kanonickém rámu: hnízdo v počátku, osa +Y, ohyb do +X."""
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    mouths = mouth_annuli(vertices, faces)
    socket = max(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    spigot = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    canon, _, _, _ = canonical_elbow_frame(
        vertices, mouths=[socket, spigot],
        origin_mouth=origin_mouth,
    )
    return canon, faces


@pytest.mark.parametrize("article,angle,dn", ELBOW_REFS)
def test_kg_elbow_matches_step_reference(article, angle, dn):
    row = next(r for r in TABLE["elbows"] if r["article"] == article[:-1])
    assert row["angle_deg"] == angle and row["dn_od"] == dn
    body, _ = kg_generator.kg_elbow_lathes(row, TABLE)
    scores = iou(tessellate(body), _reference(article, row["reference_origin"]))
    assert all(score >= 0.85 for score in scores.values()), (article, scores)
