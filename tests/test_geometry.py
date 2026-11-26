"""Geometrie: IoU proti STEP referencím, konzistence lathí a portů."""
from pathlib import Path
import numpy as np
import pytest
import kg_generator
import pp_generator
from definice import BRANCH_MEASURED
from swept_geometrie import (
    SweptBody, branch_lathes, cleanout_lathes, elbow_lathes,
    reducer_lathes, swept_bounds,
)
from tests.silhouette import (
    align_by_mouths, align_cleanout, canonical_elbow_frame, canonical_two_mouths,
    iou, load_mesh, mouth_annuli, tessellate,
)
ROOT = Path(__file__).parents[1]
TABLE = kg_generator.load_table()
ELBOW_REFS = (
    ("220200z", 15, 110), ("220210z", 30, 110), ("220220z", 45, 110),
    ("222200z", 15, 160), ("222210z", 30, 160),
)
REFERENCE = ROOT / "tmp/agent_NEW/reference_canonical.npz"
ITEMS = [
    (f"{standard}:{definition.article}", definition, body)
    for standard, module in (("KG", kg_generator), ("PP", pp_generator))
    for definition, body in module.__dict__[f"{standard.lower()}_items"]()
]
SIDE_OPENING_FAMILIES = {"USERDEFINED"}
def _reference(article, origin_mouth):
    """Reference v kanonickém rámu: hnízdo v počátku, osa +Y, ohyb do +X."""
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    mouths = mouth_annuli(vertices, faces)
    socket = max(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    spigot = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    canon, *_ = canonical_elbow_frame(vertices, mouths=[socket, spigot],
                                      origin_mouth=origin_mouth)
    return canon, faces
def _scores(body, article, aligner):
    """IoU proti referenci kanonizované deterministicky přes ústí (bez PCA/cache)."""
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    return iou(tessellate(body), (aligner(vertices, faces), faces))
@pytest.mark.parametrize("article,angle,dn", ELBOW_REFS)
def test_kg_elbow_matches_step_reference(article, angle, dn):
    row = next(r for r in TABLE["elbows"] if r["article"] == article[:-1])
    assert row["angle_deg"] == angle and row["dn_od"] == dn
    body, _ = kg_generator.kg_elbow_lathes(row, TABLE)
    scores = iou(tessellate(body), _reference(article, row["reference_origin"]))
    assert all(score >= 0.85 for score in scores.values()), (article, scores)
@pytest.mark.parametrize("article", BRANCH_MEASURED)
def test_kg_branch_matches_step_reference(article):
    length, vertex, branch_len, angle, dn, small = BRANCH_MEASURED[article]
    sock = TABLE["sockets"][str(dn)]
    bsock = TABLE["sockets"][str(small)]
    body, _ = branch_lathes(
        length, dn, sock["wall_mm"], sock["collar_diameter_mm"],
        sock["insertion_depth_t_mm"], small, bsock["wall_mm"],
        bsock["collar_diameter_mm"], bsock["insertion_depth_t_mm"],
        vertex - length / 2, branch_len, angle,
    )
    scores = _scores(body, article, lambda v, f: align_by_mouths(
        v, f, (0.0, -length / 2, 0.0)))
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
    scores = iou((model_vertices - mouths[0][0], model_faces),
                 (canonical_two_mouths(vertices, faces), faces))
    assert min(scores.values()) >= 0.78 and max(scores.values()) >= 0.82, scores
def test_kg_cleanout_matches_step_reference():
    body, _ = cleanout_lathes(
        238.5, 110, 3.2, 127, 66, 120.0, 111.5, 86.5,
        cover_thickness_mm=17.0, neck_diameter_mm=98.0,
    )
    scores = _scores(body, "175600z", align_cleanout)
    assert min(scores.values()) >= 0.45 and max(scores.values()) >= 0.85, scores
@pytest.mark.parametrize("angle", [15, 30, 45, 67.5, 87.5])
@pytest.mark.parametrize("od", [110.4, 126.3, 161.5])
def test_swept_elbow_matches_analytic_bounds(angle, od):
    body, mouths = elbow_lathes(angle, od)
    low, high = swept_bounds(body)
    vertices, triangles = tessellate(body)
    assert len(triangles) > 100
    assert np.allclose(np.r_[vertices.min(0), vertices.max(0)], np.r_[low, high], atol=0.6)
    for position, _ in mouths:
        assert np.linalg.norm(vertices - position, axis=1).min() < 60 * od / 110.4
def test_swept_elbow_matches_the_measured_reference():
    if not REFERENCE.exists():
        pytest.skip("reference mesh not available")
    data = np.load(REFERENCE)
    body, _ = elbow_lathes(45.0, 110.4)
    scores = iou(tessellate(body), (np.asarray(data["vertices"], float),
                                    np.asarray(data["faces"], int)))
    assert all(score >= 0.85 for score in scores.values()), scores
@pytest.mark.parametrize("item_id,definition,body", ITEMS, ids=[i[0] for i in ITEMS])
def test_every_lathe_tessellates(item_id, definition, body):
    assert isinstance(body, SweptBody)
    for lathe in body.lathes:
        assert len(tessellate(SweptBody((lathe,)))[1]) > 0, (item_id, "lathe bez trojúhelníků")
def _cross_section(vertices, faces, position, axis):
    """Průsečík sítě s rovinou portu (poloha, osa ven)."""
    axis = axis / np.linalg.norm(axis)
    d = (vertices - position) @ axis
    points = []
    for tri in faces:
        heights = d[tri]
        below, above = heights <= 0, heights >= 0
        if not (below.any() and above.any()):
            continue
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if below[i] != above[i] and heights[i] != heights[j]:
                t = heights[i] / (heights[i] - heights[j])
                points.append(vertices[tri[i]] + t * (vertices[tri[j]] - vertices[tri[i]]))
    return np.asarray(points) if points else np.zeros((0, 3))
@pytest.mark.parametrize("item_id,definition,body", ITEMS, ids=[i[0] for i in ITEMS])
def test_ports_sit_on_the_body(item_id, definition, body):
    vertices, faces = tessellate(body)
    for port in definition.ports:
        position = np.asarray(port.position_mm, float)
        axis = np.asarray(port.axis, float)
        axis /= np.linalg.norm(axis)
        assert len(_cross_section(vertices, faces, position, axis)) >= 8, (
            item_id, port.name, "rovina portu neprotíná těleso")
        d = (vertices - position) @ axis
        band = vertices[(d >= -8.0) & (d <= 8.0)]
        delta = band - position
        radial = np.linalg.norm(delta - np.outer(delta @ axis, axis), axis=1)
        max_radius = float(radial.max()) if len(radial) else 0.0
        if port.end_type == "SOCKET":
            assert max_radius >= port.od_mm / 2 - 0.5, (
                item_id, port.name, f"na ústí SOCKET chybí límec (r={max_radius:.1f})")
        elif definition.family not in SIDE_OPENING_FAMILIES and port.insertion_mm:
            end_ring = vertices[(d >= port.insertion_mm * 0.85) &
                                (d <= port.insertion_mm * 1.05)]
            assert len(end_ring) > 0, (item_id, port.name, "čelo hrotu bez vrcholů")
            delta_end = end_ring - position
            radial_end = np.linalg.norm(
                delta_end - np.outer(delta_end @ axis, axis), axis=1)
            assert float(radial_end.max()) <= port.od_mm / 2 + 1.5, (
                item_id, port.name, "límec na čele hrotu")
def test_pp_items_are_pure_swept_solid_with_ports():
    items = pp_items = pp_generator.pp_items()
    table = pp_generator.TABLE
    sizes = pp_generator.LIBRARY_SIZES
    expected = sum(
        len([r for r in table[family] if all(
            r[key] in sizes for key in keys)])
        for family, keys in (
            ("elbows", ("dn_od",)), ("simple_branches", ("dn_od", "branch_dn_od")),
            ("reducers", ("large_dn_od", "small_dn_od")),
            ("cleanouts", ("dn_od",)), ("caps", ("dn_od",)),
        )
    )
    assert len(pp_items) == expected
    for definition, body in items:
        assert all(np.isfinite(np.asarray(lathe.profile)).all() for lathe in body.lathes)
        assert len(body.lathes) >= 1
        assert len(definition.ports) == (1 if definition.article.startswith("M3-M")
                                         else 3 if definition.family == "JUNCTION" else 2)
        assert len(definition.geometry_status) > 20
