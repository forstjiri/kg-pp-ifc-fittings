"""KG branches, reducer and cleanout: swept recipes vs STEP references."""

from pathlib import Path

import numpy as np
import pytest

from swept_geometrie import branch_lathes, cleanout_lathes, reducer_lathes
from tests.silhouette import iou, pca_register, tessellate
from tools.measure_reference import load_mesh

ROOT = Path(__file__).parents[1]
TABLE = __import__("kg_generator").load_table()

# ze STEP naměřené hodnoty (příloha plánu "KG: naměřeno ze STEP"):
# (celá délka, průsečík od hrotu, délka odbočky, úhel, DN hlavní, DN odbočky)
BRANCH_MEASURED = {
    "220300z": (215.7, 90.65, 187.3, 45, 110, 110),
    "220400z": (179.0, 132.15, 118.6, 87, 110, 110),
    "222320z": (317.5, 86.0, 227.4, 45, 160, 110),
    "222420z": (273.5, 143.7, 143.0, 87, 160, 110),
}


def _scores(body, article):
    model = tessellate(body)
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    rotation = pca_register(model, (vertices, faces))
    return iou(model, (vertices @ rotation, faces))


@pytest.mark.parametrize("article", BRANCH_MEASURED)
def test_kg_branch_matches_step_reference(article):
    length, vertex, branch_len, angle, dn, branch_dn = BRANCH_MEASURED[article]
    sock = TABLE["sockets"][str(dn)]
    bsock = TABLE["sockets"][str(branch_dn)]
    body, _ = branch_lathes(
        length, dn, 3.2 if dn <= 125 else 4.0, sock["collar_diameter_mm"],
        sock["insertion_depth_t_mm"],
        branch_dn, 3.2 if branch_dn <= 125 else 4.0, bsock["collar_diameter_mm"],
        bsock["insertion_depth_t_mm"],
        vertex - length / 2, branch_len, angle,
    )
    scores = _scores(body, article)
    # hrubá kontrola: bez booleanů je průnik těl u odbočky jen překryv,
    # hnízda jsou aproximovaná; X/Z jsou nejcitlivější na délky a úhel
    assert min(scores.values()) >= 0.55 and max(scores.values()) >= 0.75, (article, scores)


def test_kg_eccentric_reducer_matches_step_reference():
    body, mouths = reducer_lathes(
        176.5, 160, 110, 4.0, 3.2, 182, 127, 84, 66, offset_mm=23.1,
    )
    scores = _scores(body, "222700z")
    # kužel je souosý, excentricita je jen na hnízdu malého konce
    assert min(scores.values()) >= 0.45 and max(scores.values()) >= 0.60, scores


def test_kg_cleanout_matches_step_reference():
    body, _ = cleanout_lathes(238.5, 110, 3.2, 127, 66, 143.0, 71.5)
    scores = _scores(body, "175600z")
    # víčko a boční hrdlo jsou odhad (katalog nemá rozměry), tělo sedí
    assert min(scores.values()) >= 0.25 and max(scores.values()) >= 0.75, scores
