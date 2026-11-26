"""Shared silhouette helpers: tessellate a swept body and score IoU per view.

Used by the IoU tests and by tools/build_preview.py diagnostics. The mask is
rasterised from the triangle mesh directly (PIL-free); do not feed it OCCT
display tessellation settings output — always pass meshes from tessellate().
"""

import json
from pathlib import Path

import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.geom
import numpy as np

from swept_geometrie import lathes_to_ifc

ALIGN_JSON = Path(__file__).resolve().parents[1] / "data/ostendorf/align.json"


def tessellate(body):
    """Vertices (mm) and triangles of the geometry kernel's mesh of a swept body."""
    file = ifcopenshell.api.project.create_file(version="IFC4")
    project = ifcopenshell.api.root.create_entity(file, ifc_class="IfcProject", name="t")
    ifcopenshell.api.unit.assign_unit(file)
    context = ifcopenshell.api.context.add_context(file, context_type="Model", target_view="MODEL_VIEW")
    project.RepresentationContexts = [context]
    product = ifcopenshell.api.root.create_entity(file, ifc_class="IfcPipeFitting", predefined_type="BEND")
    product.Representation = file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[
            file.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=context,
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=lathes_to_ifc(file, body),
            )
        ],
    )
    geometry = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), product).geometry
    vertices = np.asarray(geometry.verts, float).reshape(-1, 3) * 1000.0
    return vertices, np.asarray(geometry.faces, int).reshape(-1, 3)


def _mask(points, triangles, low, high, pixels_per_mm=2.0):
    """Filled silhouette of a triangle mesh (2 px/mm), PIL-free."""
    size = np.ceil((high - low) * pixels_per_mm).astype(int) + 1
    mask = np.zeros((size[1], size[0]), bool)
    corners = np.rint((points - low) * pixels_per_mm).astype(np.int64)[triangles]
    for x0, y0, x1, y1, x2, y2 in corners.reshape(-1, 6):
        if max(x0, x1, x2) < 0 or max(y0, y1, y2) < 0:
            continue
        if min(x0, x1, x2) >= size[0] or min(y0, y1, y2) >= size[1]:
            continue
        xa, xb = max(min(x0, x1, x2), 0), min(max(x0, x1, x2), size[0] - 1)
        ya, yb = max(min(y0, y1, y2), 0), min(max(y0, y1, y2), size[1] - 1)
        grid_x, grid_y = np.meshgrid(np.arange(xa, xb + 1), np.arange(ya, yb + 1))
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if denominator == 0:
            continue
        w0 = ((y1 - y2) * (grid_x - x2) + (x2 - x1) * (grid_y - y2)) / denominator
        w1 = ((y2 - y0) * (grid_x - x2) + (x0 - x2) * (grid_y - y2)) / denominator
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (1 - w0 - w1 >= -1e-9)
        mask[ya : yb + 1, xa : xb + 1] |= inside
    return mask


def canonical_two_mouths(vertices, faces):
    """Deterministická kanonizace dvústí (redukce, bez registrace).

    Osa podle čela většího ústí, směr k malému ústí, excentricita do +X;
    větší ústí v počátku. Vrací nové vrcholy. PCA registrace se u excentrické
    redukce chytá špatných permutací, proto ji testy redukce nepoužívají.
    """
    from tools.measure_reference import mouth_annuli
    mouths = mouth_annuli(vertices, faces)
    # spojení rozpůlených ústí: stejná osa a blízké středy
    merged = []
    for m in mouths:
        for g in merged:
            if float(np.dot(m["axis_in"], g["axis_in"])) > 0.99 and np.linalg.norm(m["center"] - g["center"]) < 120.0:
                n = len(g["_members"])
                g["center"] = (g["center"] * n + m["center"]) / (n + 1)
                g["outer_od"] = max(g["outer_od"], m["outer_od"])
                g["_members"].append(m)
                break
        else:
            merged.append({**m, "_members": [m]})
    if len(merged) != 2:
        raise ValueError(f"očekávány 2 ústí, nalezeno {len(merged)}")
    wide, narrow = sorted(merged, key=lambda m: -m["outer_od"])
    y = wide["axis_in"] if np.dot(wide["axis_in"], narrow["center"] - wide["center"]) > 0 else -wide["axis_in"]
    line = narrow["center"] - wide["center"]
    x = line - np.dot(line, y) * y
    if np.linalg.norm(x) < 1e-6:
        x = np.array((1.0, 0.0, 0.0)) - y * y[0]
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    return (vertices - wide["center"]) @ np.column_stack((x, y, z))


def pca_register(model, reference):
    """Rotation aligning a STEP reference mesh to a model mesh.

    Manufacturing meshes have arbitrary frames. PCA supplies the axes; try
    all sign/axis permutations (proper rotations only) and keep the one with
    the best coarse IoU. Returns a 3x3 rotation for the reference vertices.
    """
    import itertools

    mv, mf = model
    rv, rf = reference
    a = mv - mv.mean(axis=0)
    b = rv - rv.mean(axis=0)
    _, va = np.linalg.eigh(a.T @ a)
    _, vb = np.linalg.eigh(b.T @ b)
    best = (-1.0, None)
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            diag = np.diag(signs)
            rotation = va[:, perm] @ diag @ vb.T
            if np.linalg.det(rotation) < 0:
                continue
            aligned = (rv @ rotation, rf)
            # hrubé skóre s malým posunem: 87° odbočky mají PCA osy nestabilní
            # (hlavní běh i odbočka mají podobní rozptyl), bez posunu se zavrhne
            scores = iou(model, aligned, search_mm=6.0, pixels_per_mm=0.5)
            quality = sum(scores.values())
            if quality > best[0]:
                best = (quality, rotation)
    return best[1]


def register_cached(model, reference, article):
    """Rotation aligning a reference, cached in align.json per article.

    pca_register is deterministic but expensive (24 coarse IoU evals); the
    reference meshes never change, so the rotation is computed once and
    stored. Correctness is guarded by the IoU thresholds in the tests: a
    stale entry simply fails them.
    """
    data = json.loads(ALIGN_JSON.read_text()) if ALIGN_JSON.exists() else {}
    stored = data.get("register", {}).get(article)
    if stored is not None:
        return np.asarray(stored, float)
    rotation = pca_register(model, reference)
    data.setdefault("register", {})[article] = np.round(rotation, 8).tolist()
    ALIGN_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return rotation


def iou(model, reference, search_mm=10.0, pixels_per_mm=2.0):
    """IoU per orthogonal view, bbox-centre registration + small shift search.

    A STEP-derived mouth centre can be off by several mm (unevenly tessellated
    flat annuli), so allow a +/-10 mm registration adjustment; the score still
    guards the overall shape, not minute rim details.
    """
    scores = {}
    for view, axes in {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}.items():
        (mv, mt), (rv, rt) = model, reference
        m, r = mv[:, axes], rv[:, axes]
        mc, rc = (m.min(0) + m.max(0)) / 2, (r.min(0) + r.max(0)) / 2
        extents = np.vstack((m - mc, r - rc))
        low = extents.min(0) - 3
        high = extents.max(0) + 3
        a = _mask(m - mc, mt, low, high, pixels_per_mm)
        b = _mask(r - rc, rt, low, high, pixels_per_mm)
        area_a = int(np.count_nonzero(a))
        best = 0.0
        step = max(1, int(round(2 * pixels_per_mm)))
        span = int(search_mm * pixels_per_mm)
        shifts = range(-span, span + 1, step)
        for dy in shifts:
            for dx in shifts:
                shifted = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
                intersection = int(np.count_nonzero(a & shifted))
                union = area_a + int(np.count_nonzero(shifted)) - intersection
                if union:
                    best = max(best, intersection / union)
        scores[view] = best
    return scores
