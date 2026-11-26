"""Sdílené helpery: STEP ústí, kanonizace, tessellace SweptSolid a IoU siluet."""
import itertools, json
from pathlib import Path
import ifcopenshell.geom
import numpy as np
from ifc_util import new_file, product
from swept_geometrie import lathes_to_ifc
def load_mesh(path):
    """(vrcholy, trojúhelníky) z .json [vrcholy, faces] nebo .npz."""
    path = Path(path)
    if path.suffix == ".npz":
        data = np.load(path)
        return np.asarray(data["vertices"], float), np.asarray(data["faces"], int)
    vertices, faces = json.loads(path.read_text())
    return np.asarray(vertices, float), np.asarray(faces, int)
def mouth_annuli(vertices, faces):
    """Rovinné skupiny trojúhelníků => ústí: center, axis_in, OD, ID."""
    pts = vertices[faces]
    normals = np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    keep = lengths > 1e-9
    normals, tri_pts = normals[keep] / lengths[keep, None], pts[keep]
    centroids = tri_pts.mean(axis=1)
    offsets = np.einsum("ij,ij->i", normals, centroids)
    groups = {}
    for index, normal in enumerate(normals):
        n = normal if normal[2] >= 0 else -normal
        groups.setdefault((*np.round(n[:3] * 20).astype(int), round(float(offsets[index]))), []).append(index)
    mouths = []
    for members in groups.values():
        if len(members) < 24:
            continue
        n = normals[members].mean(axis=0)
        norm = np.linalg.norm(n)
        if not np.isfinite(norm) or norm < 1e-12:
            continue
        n /= norm
        center = centroids[members].mean(axis=0)
        side = (vertices - center) @ n
        if np.count_nonzero(side > 1.0) and np.count_nonzero(side < -1.0):
            continue
        radial = np.linalg.norm(tri_pts[members].reshape(-1, 3) - center, axis=1)
        if not len(radial):
            continue
        if np.dot(n, vertices.mean(axis=0) - center) < 0:
            n = -n
        mouths.append(dict(center=center, axis_in=n, outer_od=2.0 * float(radial.max()),
                           inner_id=2.0 * float(radial.min()), triangles=len(members)))
    merged = []
    for mouth in mouths:
        for other in merged:
            same_plane = (
                abs(float(np.dot(mouth["axis_in"], other["axis_in"]))) > 0.985
                and abs(float(np.dot(mouth["center"] - other["center"], other["axis_in"]))) < 2.0)
            near = np.linalg.norm(mouth["center"] - other["center"]) < max(
                mouth["outer_od"], other["outer_od"])
            if same_plane and (near or mouth["inner_id"] <= other["outer_od"] * 1.1
                               <= 2 * mouth["outer_od"]):
                other["outer_od"] = max(other["outer_od"], mouth["outer_od"])
                other["inner_id"] = min(other["inner_id"], mouth["inner_id"])
                other["triangles"] += mouth["triangles"]
                break
        else:
            merged.append(dict(mouth))
    return merged
def merge_mouths(mouths):
    """Spojí rozpůlená ústí téhož kruhu (stejná osa, blízké středy)."""
    merged = []
    for mouth in mouths:
        for group in merged:
            if (abs(float(np.dot(mouth["axis_in"], group["axis_in"]))) > 0.99
                    and np.linalg.norm(mouth["center"] - group["center"]) < 120.0):
                count = len(group["_members"])
                group["center"] = (group["center"] * count + mouth["center"]) / (count + 1)
                group["outer_od"] = max(group["outer_od"], mouth["outer_od"])
                group["_members"].append(mouth)
                break
        else:
            merged.append({**mouth, "_members": [mouth]})
    for group in merged:
        group.pop("_members", None)
    return merged
def _frame(wide, narrow, hint):
    """Pravotočivý rám: y k malému ústí, x = směr excentricity/odbočky."""
    y = wide["axis_in"]
    if np.dot(y, narrow["center"] - wide["center"]) < 0:
        y = -y
    x = hint - np.dot(hint, y) * y
    if np.linalg.norm(x) < 1e-6:
        x = np.array((1.0, 0.0, 0.0)) - y * y[0]
    if np.linalg.norm(x) < 1e-6:
        x = np.array((0.0, 0.0, 1.0)) - y * y[2]
    x /= np.linalg.norm(x)
    return np.column_stack((x, y, np.cross(x, y)))
def canonical_elbow_frame(vertices, faces=None, mouths=None, origin_mouth="socket"):
    """Kanonický rám kolena: hnízdo v počátku, osa +Y, ohyb do +X."""
    mouths = mouth_annuli(vertices, faces) if mouths is None else mouths
    if len(mouths) != 2:
        raise ValueError(f"očekávány 2 ústí, nalezeno {len(mouths)}")
    widest = max(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    narrowest = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    mouth_a, mouth_b = ((widest, narrowest) if origin_mouth == "socket"
                        else (narrowest, widest))
    center = mouth_a["center"]
    y = mouth_a["axis_in"] / np.linalg.norm(mouth_a["axis_in"])
    b_out = -mouth_b["axis_in"] / np.linalg.norm(mouth_b["axis_in"])
    x = b_out - np.dot(b_out, y) * y
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(y, (0.0, 0.0, 1.0))
    x /= np.linalg.norm(x)
    rotation = np.column_stack((x, y, np.cross(x, y)))
    return (vertices - center) @ rotation, mouth_a, mouth_b, rotation
def canonical_two_mouths(vertices, faces):
    """Kanonizace dvústí (redukce): osa podle většího hnízda, excentricita +X."""
    mouths = merge_mouths(mouth_annuli(vertices, faces))
    if len(mouths) != 2:
        raise ValueError(f"očekávány 2 ústí, nalezeno {len(mouths)}")
    wide, narrow = sorted(mouths, key=lambda m: -m["outer_od"])
    rotation = _frame(wide, narrow, narrow["center"] - wide["center"])
    return (vertices - wide["center"]) @ rotation
def align_by_mouths(vertices, faces, spigot_target):
    """Kanonizace odbočky přes ústí: hrot do `spigot_target`, osa +Y, větev +X."""
    mouths = merge_mouths(mouth_annuli(vertices, faces))
    spigot = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    axis = spigot["axis_in"] if spigot["axis_in"][1] > 0 else -spigot["axis_in"]
    rest = [m for m in mouths if m is not spigot]
    def distance(mouth):
        delta = mouth["center"] - spigot["center"]
        return float(np.linalg.norm(delta - np.dot(delta, axis) * axis))
    socket = max(rest, key=lambda m: -distance(m) - m["outer_od"])
    rest = [m for m in rest if m is not socket]
    far = max(distance(m) for m in rest)
    branch = [m for m in rest if distance(m) > 0.5 * far]
    branch_center = np.mean([m["center"] for m in branch], axis=0)
    direction = -np.mean([m["axis_in"] for m in branch], axis=0)
    direction /= np.linalg.norm(direction)
    x = direction - np.dot(direction, axis) * axis
    x /= np.linalg.norm(x)
    if np.dot(branch_center - spigot["center"], x) < 0:
        x = -x
    rotation = np.column_stack((x, axis, np.cross(x, axis)))
    return (vertices - spigot["center"]) @ rotation + np.asarray(spigot_target, float)
def align_cleanout(vertices, faces):
    """Kanonizace čistícího kusu: hlavní osa +Y, boční hrdlo +X."""
    mouths = merge_mouths(mouth_annuli(vertices, faces))
    if len(mouths) < 2:
        raise ValueError("málo ústí")
    a, b = max(itertools.combinations(mouths, 2),
               key=lambda pair: np.linalg.norm(pair[0]["center"] - pair[1]["center"]))
    wide = a if a["outer_od"] > b["outer_od"] else b
    narrow = b if wide is a else a
    stubs = [m for m in mouths if m is not wide and m is not narrow]
    hint = stubs[0]["center"] - wide["center"] if stubs else np.array((1.0, 0.0, 0.0))
    return (vertices - wide["center"]) @ _frame(wide, narrow, hint)
def tessellate(body):
    """Vrcholy (mm) a trojúhelníky geometry kernelu pro SweptBody."""
    file, _, context = new_file("t")
    entity = product(file, context, "t", "BEND", lathes_to_ifc(file, body), None)
    geometry = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), entity).geometry
    return (np.asarray(geometry.verts, float).reshape(-1, 3) * 1000.0,
            np.asarray(geometry.faces, int).reshape(-1, 3))
def _mask(points, triangles, low, high, pixels_per_mm=2.0):
    """Vyplněná silueta trojúhelníkové sítě (PIL-free)."""
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
        mask[ya:yb + 1, xa:xb + 1] |= ((w0 >= -1e-9) & (w1 >= -1e-9)
                                        & (1 - w0 - w1 >= -1e-9))
    return mask
def iou(model, reference, search_mm=10.0, pixels_per_mm=2.0):
    """IoU tří ortogonálních pohledů s registrací na středy bboxu + malý posun."""
    scores = {}
    for view, axes in {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}.items():
        mv, mt = model
        rv, rt = reference
        m, r = mv[:, axes], rv[:, axes]
        mc, rc = (m.min(0) + m.max(0)) / 2, (r.min(0) + r.max(0)) / 2
        extents = np.vstack((m - mc, r - rc))
        low, high = extents.min(0) - 3, extents.max(0) + 3
        a, b = _mask(m - mc, mt, low, high, pixels_per_mm), _mask(r - rc, rt, low, high, pixels_per_mm)
        area_a = int(np.count_nonzero(a))
        best = 0.0
        step, span = max(1, int(round(2 * pixels_per_mm))), int(search_mm * pixels_per_mm)
        for dy in range(-span, span + 1, step):
            for dx in range(-span, span + 1, step):
                shifted = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
                intersection = int(np.count_nonzero(a & shifted))
                union = area_a + int(np.count_nonzero(shifted)) - intersection
                if union:
                    best = max(best, intersection / union)
        scores[view] = best
    return scores
