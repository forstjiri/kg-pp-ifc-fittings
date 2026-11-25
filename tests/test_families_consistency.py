"""Každý lathe se musí vytvořit sám a porty musí sedět na tělese.

Chyby, které to chytá: degenerovaný oblouk (PP DN125), těleso v jiné ose než
porty (čistící kus), límec na hrotu místo hnízda, hnízdo visící ve vzduchu.
"""

import numpy as np
import pytest

import kg_generator
import pp_generator
from swept_geometrie import SweptBody
from tests.silhouette import tessellate

ITEMS = [
    (f"{standard}:{definition.article}", definition, body)
    for standard, module in (("KG", kg_generator), ("PP", pp_generator))
    for definition, body in module.__dict__[f"{standard.lower()}_items"]()
]

# rodiny s bočním hrdlem: rovina SPIGOTu protíná i boční větev, kontrola
# maximálního poloměru na ní neplatí
SIDE_OPENING_FAMILIES = {"USERDEFINED"}


@pytest.mark.parametrize("item_id,definition,body", ITEMS, ids=[i[0] for i in ITEMS])
def test_every_lathe_tessellates(item_id, definition, body):
    assert isinstance(body, SweptBody)
    for lathe in body.lathes:
        vertices, faces = tessellate(SweptBody((lathe,)))
        assert len(faces) > 0, (item_id, "lathe bez trojúhelníků")


def _cross_section(vertices, faces, position, axis):
    """Body a poloměry průsečíku sítě s rovinou portu (poloha, osa ven)."""
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
    if not points:
        return np.zeros((0, 3))
    return np.asarray(points)


@pytest.mark.parametrize("item_id,definition,body", ITEMS, ids=[i[0] for i in ITEMS])
def test_ports_sit_on_the_body(item_id, definition, body):
    vertices, faces = tessellate(body)
    for port in definition.ports:
        position = np.asarray(port.position_mm, float)
        axis = np.asarray(port.axis, float)
        axis = axis / np.linalg.norm(axis)
        section = _cross_section(vertices, faces, position, axis)
        assert len(section) >= 8, (item_id, port.name, "rovina portu neprotíná těleso")

        d = (vertices - position) @ axis
        band = vertices[(d >= -8.0) & (d <= 8.0)]
        delta = band - position
        radial = np.linalg.norm(delta - np.outer(delta @ axis, axis), axis=1)
        max_radius = float(radial.max()) if len(radial) else 0.0

        if port.end_type == "SOCKET":
            # port.od_mm je vnější průměr límce; pás ±8 mm musí límec chytit
            assert max_radius >= port.od_mm / 2 - 0.5, (
                item_id, port.name, f"na ústí SOCKET chybí límec (r={max_radius:.1f})")
        elif definition.family not in SIDE_OPENING_FAMILIES and port.insertion_mm:
            # čelní kroužek na konci tělesa (port je o t uvnitř): hrot bez límce
            end_ring = vertices[(d >= port.insertion_mm * 0.85) & (d <= port.insertion_mm * 1.05)]
            assert len(end_ring) > 0, (item_id, port.name, "čelo hrotu bez vrcholů")
            delta_end = end_ring - position
            radial_end = np.linalg.norm(delta_end - np.outer(delta_end @ axis, axis), axis=1)
            end_radius = float(radial_end.max())
            assert end_radius <= port.od_mm / 2 + 1.5, (
                item_id, port.name, f"límec na čele hrotu (r={end_radius:.1f})")
