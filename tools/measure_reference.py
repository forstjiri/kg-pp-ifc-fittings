#!/usr/bin/env python3
"""Measure a reference STEP mesh of a KG fitting (vertices mm, 0-based faces).

Finds the flat socket-mouth annuli from coplanar triangle groups, measures
OD/ID and axis of each mouth, and prints a summary. Used to derive catalogue
dimensions and canonical frames for the swept recipes and the IoU tests.

Usage:
    python tools/measure_reference.py data/ostendorf/220220z.json
    python tools/measure_reference.py ref.npz --json out.json
"""

import argparse
import json
from pathlib import Path

import numpy as np


def load_mesh(path):
    """Return (vertices, faces) from a .json [verts, faces] or .npz file."""
    path = Path(path)
    if path.suffix == ".npz":
        data = np.load(path)
        return np.asarray(data["vertices"], float), np.asarray(data["faces"], int)
    vertices, faces = json.loads(path.read_text())
    return np.asarray(vertices, float), np.asarray(faces, int)


def mouth_annuli(vertices, faces):
    """Find flat socket-mouth annuli via coplanar triangle groups.

    Returns one dict per mouth: center, axis_in (unit, into the solid),
    outer_od, inner_id. Coplanar groups are keyed by plane (normal + offset),
    so a rim ring split by vertex quantization merges back into one annulus;
    OD/ID then come from the vertex band in the mouth plane, never from an
    empty band (falls back to the group's own triangle vertices).
    """
    pts = vertices[faces]
    normals = np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    keep = lengths > 1e-9
    normals = normals[keep] / lengths[keep, None]
    tri_pts = pts[keep]
    centroids = tri_pts.mean(axis=1)
    offsets = np.einsum("ij,ij->i", normals, centroids)
    groups = {}
    for index in range(len(normals)):
        n = normals[index]
        if n[2] < 0:
            n = -n
        key = (
            round(float(n[0]) * 20), round(float(n[1]) * 20), round(float(n[2]) * 20),
            round(float(offsets[index])),
        )
        groups.setdefault(key, []).append(index)
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
        # a mouth is on an extreme plane of the solid
        if np.count_nonzero(side > 1.0) and np.count_nonzero(side < -1.0):
            continue
        # the flat annulus triangles span exactly ID..OD, unlike the vertex
        # band which may pick up unrelated vertices near the plane
        radial = np.linalg.norm(tri_pts[members].reshape(-1, 3) - center, axis=1)
        if not len(radial):
            continue
        if np.dot(n, vertices.mean(axis=0) - center) < 0:
            n = -n
        mouths.append(dict(
            center=center, axis_in=n,
            outer_od=2.0 * float(radial.max()),
            inner_id=2.0 * float(radial.min()),
            triangles=len(members),
        ))
    # Merge groups of one physical annulus (same plane, near centers).
    merged = []
    for mouth in mouths:
        for other in merged:
            same_plane = (
                abs(float(np.dot(mouth["axis_in"], other["axis_in"]))) > 0.985
                and abs(float(np.dot(mouth["center"] - other["center"], other["axis_in"]))) < 2.0
            )
            near = np.linalg.norm(mouth["center"] - other["center"]) < max(
                mouth["outer_od"], other["outer_od"]
            )
            if same_plane and (near or mouth["inner_id"] <= other["outer_od"] * 1.1 <= 2 * mouth["outer_od"]):
                other["outer_od"] = max(other["outer_od"], mouth["outer_od"])
                other["inner_id"] = min(other["inner_id"], mouth["inner_id"])
                other["triangles"] += mouth["triangles"]
                break
        else:
            merged.append(dict(mouth))
    return merged


def canonical_elbow_frame(vertices, faces=None, mouths=None, origin_mouth="socket"):
    """Canonical frame for a two-mouth elbow, derived from mouth AXES only.

    Mouth A centre at origin, inward axis A = +Y, bend in the XY plane with
    mouth B on +X. Flat-cap centre estimates can be off by several mm, so the
    centre A is reconstructed from centre B + catalogue take-out along both
    axes when `take_out_mm` is given. Returns (vertices, mouth_a, mouth_b, R).
    """
    if mouths is None:
        mouths = mouth_annuli(vertices, faces)
    if len(mouths) != 2:
        raise ValueError(f"očekávány 2 ústí, nalezeno {len(mouths)}")

    # Which physical end sits at the origin depends on the catalogue article:
    # some KGB pieces have the socket on the angled leg, others on the straight
    # one. The swept recipe uses the same flag, so the two frames meet.
    widest = max(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    narrowest = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    if origin_mouth == "socket":
        mouth_a, mouth_b = widest, narrowest
    else:
        mouth_a, mouth_b = narrowest, widest
    # Use the measured socket centre: reconstructing it from a catalogue
    # take-out shifts the ring by several mm and moves the visible collar.
    ca = mouth_a["center"]
    y_axis = mouth_a["axis_in"] / np.linalg.norm(mouth_a["axis_in"])
    b_out = -mouth_b["axis_in"] / np.linalg.norm(mouth_b["axis_in"])
    x_axis = b_out - np.dot(b_out, y_axis) * y_axis
    if np.linalg.norm(x_axis) < 1e-6:  # straight piece: any perpendicular axis
        x_axis = np.cross(y_axis, (0.0, 0.0, 1.0))
    x_axis /= np.linalg.norm(x_axis)
    rotation = np.column_stack((x_axis, y_axis, np.cross(x_axis, y_axis)))
    return (vertices - ca) @ rotation, mouth_a, mouth_b, rotation


def summarize(path):
    vertices, faces = load_mesh(path)
    mouths = mouth_annuli(vertices, faces)
    bbox = np.sort(vertices.max(axis=0) - vertices.min(axis=0))
    print(f"{path}: {len(vertices)} vrcholů, {len(faces)} trojúhelníků, bbox {np.round(bbox, 1).tolist()} mm")
    for index, mouth in enumerate(mouths):
        print(
            f"  ústí {index}: stred {np.round(mouth['center'], 1).tolist()} "
            f"osa_do {np.round(mouth['axis_in'], 4).tolist()} "
            f"OD {mouth['outer_od']:.1f} ID {mouth['inner_id']:.1f} "
            f"({mouth['triangles']} trojúhelníků)"
        )
    if len(mouths) == 2:
        canon, a, b, rotation = canonical_elbow_frame(vertices, mouths=mouths)
        angle = np.degrees(np.arccos(np.clip(a["axis_in"] @ (-b["axis_in"]), -1, 1)))
        delta = b["center"] - a["center"]
        print(f"  koleno: úhel {angle:.2f}°, tětiva {np.linalg.norm(delta):.1f} mm, "
              f"osa A protne osu B {float(delta @ a['axis_in']):.1f} mm od A, "
              f"{float(delta @ b['axis_in']):.1f} mm od B")
    return mouths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", help="reference: .json [vrcholy, faces] nebo .npz")
    parser.add_argument("--json", help="zapsat ústí jako JSON do souboru")
    args = parser.parse_args()
    mouths = summarize(args.mesh)
    if args.json:
        Path(args.json).write_text(json.dumps(
            [{k: np.asarray(v).tolist() if not isinstance(v, (int, float)) else v
              for k, v in mouth.items()} for mouth in mouths], indent=2,
        ))
