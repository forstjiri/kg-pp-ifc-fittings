"""Shared silhouette helpers: tessellate a swept body and score IoU per view.

Used by the IoU tests and by tools/build_preview.py diagnostics. The mask is
rasterised from the triangle mesh directly (PIL-free); do not feed it OCCT
display tessellation settings output — always pass meshes from tessellate().
"""

import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.geom
import numpy as np

from swept_geometrie import lathes_to_ifc


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


def iou(model, reference):
    """IoU per orthogonal view with bbox-centre registration."""
    scores = {}
    for view, axes in {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}.items():
        (mv, mt), (rv, rt) = model, reference
        m, r = mv[:, axes], rv[:, axes]
        mc, rc = (m.min(0) + m.max(0)) / 2, (r.min(0) + r.max(0)) / 2
        extents = np.vstack((m - mc, r - rc))
        low = extents.min(0) - 3
        high = extents.max(0) + 3
        a = _mask(m - mc, mt, low, high)
        b = _mask(r - rc, rt, low, high)
        scores[view] = float(np.count_nonzero(a & b) / np.count_nonzero(a | b))
    return scores
