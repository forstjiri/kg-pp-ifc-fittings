#!/usr/bin/env python3
"""Srovnávací IFC: výrobní STEP (vlevo) vs aktuální SweptSolid (vpravo).

Stejná orientace podle hnízda, hrotu a roviny ohybu; stejné měřítko.
    python tools/build_comparison.py --output out/compare-kgb.ifc           # kolena
    python tools/build_comparison.py --branches --output out/compare-branches.ifc
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ifcopenshell.api
import numpy as np

import kg_generator
from swept_geometrie import lathes_to_ifc
from tests.silhouette import tessellate
from tools.measure_reference import canonical_elbow_frame, load_mesh, mouth_annuli

ALIGN_JSON = ROOT / "data/ostendorf/align.json"

PAIRS = (("220200z", 15), ("220210z", 30), ("220220z", 45))
# KG odbočky k živému srovnání (recept je stejný jako v IoU testu)
BRANCH_ARTICLES = ("222320z", "222420z", "220400z", "220300z")


def _manual_correction(article):
    """Ruční korekce z align.json: (rx_deg, rz_deg) nebo None."""
    if not ALIGN_JSON.exists():
        return None
    entry = json.loads(ALIGN_JSON.read_text()).get("manual", {}).get(article)
    if not entry:
        return None
    return float(entry.get("rx_deg", 0.0)), float(entry.get("rz_deg", 0.0))


def _apply_manual(coords, article):
    """Otočí kanonizovanou referenci o ruční korekci kolem středu tělesa."""
    correction = _manual_correction(article)
    if correction is None:
        return coords
    rx, rz = np.radians(correction)
    ca, sa = np.cos(rx), np.sin(rx)
    cb, sb = np.cos(rz), np.sin(rz)
    Rx = np.array(((1, 0, 0), (0, ca, -sa), (0, sa, ca)))
    Rz = np.array(((cb, -sb, 0), (sb, cb, 0), (0, 0, 1)))
    center = (coords.min(axis=0) + coords.max(axis=0)) / 2
    return (coords - center) @ (Rz @ Rx) + center


def _branch_model_body(article):
    """Stejný recept jako test_kg_other_geometry; vrací (body, úhel, vertex_y, délka)."""
    from tools.compare_preview import build_body
    return build_body(article)


def _merge_mouths(mouths):
    """Spojí rozpůlené ústí (tolikže osa, středy blízko sebe)."""
    merged = []
    for m in mouths:
        for g in merged:
            dot = float(np.dot(m["axis_in"], g["axis_in"]))
            near = np.linalg.norm(m["center"] - g["center"]) < 120.0
            if dot > 0.99 and near:
                n = len(g["_members"])
                g["center"] = (g["center"] * n + m["center"]) / (n + 1)
                g["outer_od"] = max(g["outer_od"], m["outer_od"])
                g["_members"].append(m)
                break
        else:
            merged.append({**m, "_members": [m]})
    for g in merged:
        g.pop("_members", None)
    return merged


def _align_by_mouths(vertices, faces, spigot_target):
    """Deterministická kanonizace odbočky přes ústí (bez PCA, bez ICP).

    Hrot = ústí s nejmenším rozdílem OD−ID (prostý konec trubky), hnízdo =
    ústí na ose hrotu s největším OD, odbočka = zbytek. Osa hlavního běhu
    jde do +Y, osa odbočky do (+X, +Y). Posun: čelo hrotu na `spigot_target`.
    """
    mouths = _merge_mouths(mouth_annuli(vertices, faces))
    spigot = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    axis = spigot["axis_in"] if spigot["axis_in"][1] > 0 else -spigot["axis_in"]
    rest = [m for m in mouths if m is not spigot]
    # hnízdo: nejbližší ose hrotu, největší OD
    def dist_to_axis(m):
        delta = m["center"] - spigot["center"]
        return float(np.linalg.norm(delta - np.dot(delta, axis) * axis))
    socket = max(rest, key=lambda m: -dist_to_axis(m) - m["outer_od"])
    rest = [m for m in rest if m is not socket]
    # odbočka: jen ústí daleko od osy (kruh šikmého čela bývá rozpůlený)
    far = max(dist_to_axis(m) for m in rest)
    branch = [m for m in rest if dist_to_axis(m) > 0.5 * far]
    branch_c = np.mean([m["center"] for m in branch], axis=0)
    d_branch = -np.mean([m["axis_in"] for m in branch], axis=0)
    d_branch /= np.linalg.norm(d_branch)

    y = (socket["center"] - spigot["center"])
    y /= np.linalg.norm(y)
    if np.dot(y, axis) < 0:  # osa hrotu míří do tělesa k hnízdu
        y = -y
    # branch do +X poloviny
    x = d_branch - np.dot(d_branch, y) * y
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    rotation = np.column_stack((x, y, z))  # modelové osy ve sloupcích

    delta = branch_c - spigot["center"]
    if np.dot(delta, x) < 0:
        x = -x
        z = np.cross(x, y)
        rotation = np.column_stack((x, y, z))
    coords = (vertices - spigot["center"]) @ rotation + np.asarray(spigot_target, float)
    return coords


def _branch_reference_items(file, article, spigot_target):
    """Referenční mesh z STEP, kanonizovaná přes ústí + ruční korekce."""
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    coords = _align_by_mouths(vertices, faces, spigot_target)
    coords = _apply_manual(coords, article)
    return [
        file.create_entity(
            "IfcTriangulatedFaceSet",
            Coordinates=file.create_entity(
                "IfcCartesianPointList3D", CoordList=np.round(coords, 4).tolist()
            ),
            CoordIndex=(np.asarray(faces) + 1).tolist(),
            Closed=False,
        )
    ], "Tessellation"


def _reference_items(file, article, row):
    vertices, faces = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    mouths = mouth_annuli(vertices, faces)
    socket = max(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    spigot = min(mouths, key=lambda m: m["outer_od"] - m["inner_id"])
    canon, _, _, _ = canonical_elbow_frame(
        vertices, mouths=[socket, spigot],
        origin_mouth=row.get("reference_origin", "socket"),
    )
    coords = np.asarray(canon, float)  # lokální souřadnice; posici nese IfcLocalPlacement
    return [
        file.create_entity(
            "IfcTriangulatedFaceSet",
            Coordinates=file.create_entity(
                "IfcCartesianPointList3D", CoordList=np.round(coords, 4).tolist()
            ),
            CoordIndex=(faces + 1).tolist(),
            Closed=False,
        )
    ], "Tessellation"


def _new_file(name):
    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcProject", name=name
    )
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run(
        "context.add_context", file, context_type="Model", target_view="MODEL_VIEW"
    )
    context.Precision = 1e-5
    project.RepresentationContexts = [context]
    return file, context


def _place(file, context, label, ifc_class, position, items, representation_type):
    fitting = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcPipeFitting",
        predefined_type=ifc_class, name=label,
    )
    fitting.ObjectPlacement = file.create_entity(
        "IfcLocalPlacement",
        RelativePlacement=file.create_entity(
            "IfcAxis2Placement3D",
            Location=file.create_entity("IfcCartesianPoint", Coordinates=position),
        ),
    )
    fitting.Representation = file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[file.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=context, RepresentationIdentifier="Body",
            RepresentationType=representation_type, Items=items,
        )],
    )


def build_elbows(output_path):
    table = kg_generator.load_table()
    file, context = _new_file("KGB STEP vs SweptSolid")
    for index, (article, angle) in enumerate(PAIRS):
        row = next(r for r in table["elbows"] if r["article"] == article[:-1])
        base_y = index * 500.0
        for label, offset_x in (("STEP " + article, 0.0), ("SWEPT " + article, 350.0)):
            position = (offset_x, base_y, 0.0)
            if label.startswith("STEP"):
                items, representation_type = _reference_items(file, article, row)
            else:
                body, _ = kg_generator.kg_elbow_lathes(row, table)
                items, representation_type = lathes_to_ifc(file, body), "SweptSolid"
            _place(file, context, label, "BEND", position, items, representation_type)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))
    return output_path


def build_branches(output_path, articles=BRANCH_ARTICLES):
    file, context = _new_file("KG branches STEP vs SweptSolid")
    for index, article in enumerate(articles):
        base_y = index * 500.0
        body, angle, vertex_y, length = _branch_model_body(article)
        spigot_target = (0.0, -length / 2, 0.0)
        for label, offset_x in (("STEP " + article, 0.0), ("SWEPT " + article, 350.0)):
            position = (offset_x, base_y, 0.0)
            if label.startswith("STEP"):
                items, representation_type = _branch_reference_items(file, article, spigot_target)
            else:
                items, representation_type = lathes_to_ifc(file, body), "SweptSolid"
            _place(file, context, label, "JUNCTION", position, items, representation_type)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "out/compare-kgb.ifc"))
    parser.add_argument("--branches", nargs="*", default=None,
                        help="články odboček; bez hodnoty použije výchozí seznam")
    args = parser.parse_args()
    if args.branches is not None:
        print("Vytvořeno:", build_branches(args.output, args.branches or BRANCH_ARTICLES))
    else:
        print("Vytvořeno:", build_elbows(args.output))
