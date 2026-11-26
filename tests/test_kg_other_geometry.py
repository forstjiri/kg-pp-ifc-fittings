"""KG branches, reducer and cleanout: swept recipes vs STEP references."""

from pathlib import Path

import numpy as np
import pytest

from swept_geometrie import branch_lathes, cleanout_lathes, reducer_lathes
from tests.silhouette import canonical_two_mouths, iou, register_cached, tessellate
from tools.measure_reference import load_mesh

ROOT = Path(__file__).parents[1]
TABLE = __import__("kg_generator").load_table()

# ze STEP naměřené hodnoty (ústí z mouth_annuli, příloha plánu "KG: naměřeno ze STEP"):
# (celá délka hrot→hnízdo, průsečík od hrotu, délka odbočky, úhel, DN hlavní, DN odbočky)
# 220300z: spigot −215,7 → hnízdo +61,3; vrchol 90,65 od hrotu; čelo odbočky (129,1; 10,8) = 187,5 od vrcholu
# 220400z: spigot −179,0 → hnízdo +61,5; čelo odbočky (118,7; −50,5) ⇒ vrchol 122,3 od hrotu, odbočka 118,9
BRANCH_MEASURED = {
    "220300z": (277.0, 90.65, 187.3, 45, 110, 110),
    "220400z": (240.5, 122.3, 118.9, 87, 110, 110),
    "222320z": (317.5, 86.0, 227.4, 45, 160, 110),
    "222420z": (273.5, 143.7, 143.0, 87, 160, 110),
}


def _scores(body, article):
    model = tessellate(body)
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    rotation = register_cached(model, (vertices, faces), article)
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
    # pohled X (kolmo na rovinu ohybu) a Z musejí sedět na tvaru; Y je podél
    # hlavní osy, tam brzdí aproximovaná hnízda a překryv těl bez booleanů.
    # Výjimka 220300z: Z pohled, šikmé čelo odbočky bez zkosení.
    assert scores["X"] >= 0.90, (article, scores)
    assert scores["Z"] >= (0.70 if article == "220300z" else 0.85), (article, scores)
    assert scores["Y"] >= 0.55, (article, scores)


def test_kg_eccentric_reducer_matches_step_reference():
    body, mouths = reducer_lathes(
        176.5, 160, 110, 4.0, 3.2, 194, 127, 84, 66, offset_mm=23.1,
        straight_large_mm=88, cone_len_mm=29, plain_large_end=True,
    )
    model_vertices, model_faces = tessellate(body)
    vertices, faces = load_mesh(ROOT / "data/ostendorf/222700z.json")
    # kanonizace přes ústí: PCA registrace se u excentrické redukce chytá
    # špatných permutací. Model je postavený přímo v kanonickém rámu
    # (široký konec v počátku, osa +Y, excentricita do +X) — jen posunout.
    model_c = model_vertices - mouths[0][0]
    ref_c = canonical_two_mouths(vertices, faces)
    scores = iou((model_c, model_faces), (ref_c, faces))
    # kužel je aproximován revolucí kolem nakloněné osy (skutečný excentrický
    # kužel má rovnoběžné osy), Y brzdí neviditelné bory
    assert min(scores.values()) >= 0.78 and max(scores.values()) >= 0.82, scores


def test_kg_cleanout_matches_step_reference():
    body, _ = cleanout_lathes(
        238.5, 110, 3.2, 127, 66, 120.0, 111.5, 86.5,
        cover_thickness_mm=17.0, neck_diameter_mm=98.0,
    )
    scores = _scores(body, "175600z")
    # víčko a krk ze STEP, délka článku z katalogu (jiný kus než STEP)
    assert min(scores.values()) >= 0.45 and max(scores.values()) >= 0.85, scores
