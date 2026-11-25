"""Geometrie výrobkov: převod katalogového meshe do lokální IFC polohy."""

import numpy as np


def kg_cap_mesh(od_mm, length_mm, socket_od_mm, wall_mm, clearance_mm=0.5, sides=32):
    """Closed PVC-U KG end cap; socket entry and wall profile are approximate."""
    stations = max(12, int(length_mm / 3))
    vertices, faces = [], []
    inner_radius = od_mm / 2 + clearance_mm
    body_radius = od_mm / 2 + wall_mm
    for t in np.linspace(0, 1, stations):
        center = np.array([0.0, t * length_mm, 0.0])
        blend = np.clip(t * length_mm / max(1, length_mm - wall_mm * 2), 0, 1)
        blend = blend * blend * (3 - 2 * blend)
        outer_radius = socket_od_mm / 2 * (1 - blend) + body_radius * blend
        for radius in (outer_radius, inner_radius):
            vertices.extend(
                center + radius * np.array([np.cos(a), 0, np.sin(a)])
                for a in np.linspace(0, 2 * np.pi, sides, endpoint=False)
            )
    for k in range(stations - 1):
        outer0, inner0 = k * 2 * sides, k * 2 * sides + sides
        outer1, inner1 = (k + 1) * 2 * sides, (k + 1) * 2 * sides + sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend(
                (
                    (outer0 + i, outer0 + j, outer1 + j),
                    (outer0 + i, outer1 + j, outer1 + i),
                    (inner0 + i, inner1 + i, inner1 + j),
                    (inner0 + i, inner1 + j, inner0 + j),
                )
            )
    # Open socket mouth at y=0; close the back of the cap at y=L.
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(((i, sides + i, sides + j), (i, sides + j, j)))
    back_inner = (stations - 1) * 2 * sides + sides
    back_outer = (stations - 1) * 2 * sides
    center_index = len(vertices)
    vertices.append((0.0, length_mm, 0.0))
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(
            (
                (back_outer + i, back_outer + j, back_inner + j),
                (back_outer + i, back_inner + j, back_inner + i),
            )
        )
        faces.append((back_inner + i, center_index, back_inner + j))
    return np.asarray(vertices), np.asarray(faces, dtype=int)


def transform_catalogue_points(points_mm, *, anchor_mm, along, side, origin=(0, 0, 0)):
    points = np.asarray(points_mm, dtype=float)
    anchor = np.asarray(anchor_mm, dtype=float)
    y = np.asarray(along, dtype=float)
    x = np.asarray(side, dtype=float)
    base = np.asarray(origin, dtype=float)

    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("points_mm musí být konečné pole N×3")
    if anchor.shape != (3,) or base.shape != (3,):
        raise ValueError("anchor_mm a origin musí mít tři souřadnice")
    if y.shape != (3,) or x.shape != (3,) or not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("along a side musí být konečné 3D vektory")

    y_norm, x_norm = np.linalg.norm(y), np.linalg.norm(x)
    if y_norm == 0 or x_norm == 0:
        raise ValueError("along a side nesmí být nulové")
    y, x = y / y_norm, x / x_norm
    if abs(float(x @ y)) >= 1e-8:
        raise ValueError("along a side musí být kolmé")

    frame = np.column_stack((x, y, np.cross(x, y)))
    return base + (points - anchor) @ frame.T / 1000.0


def transform_catalogue_mesh(vertices_mm, faces, *, anchor_mm, along, side, origin=(0, 0, 0)):
    """Převede výrobní mesh [mm] do lokálních IFC souřadnic [m]."""
    vertices = np.asarray(vertices_mm, dtype=float)
    triangles = np.asarray(faces, dtype=int)
    if triangles.ndim != 2 or triangles.shape[1] != 3 or not triangles.size:
        raise ValueError("faces musí být neprázdné pole M×3")
    if triangles.min() < 0 or triangles.max() >= len(vertices):
        raise ValueError("faces obsahují neplatný index vrcholu")
    return (
        transform_catalogue_points(
            vertices, anchor_mm=anchor_mm, along=along, side=side, origin=origin
        ),
        triangles,
    )
