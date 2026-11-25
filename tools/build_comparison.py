#!/usr/bin/env python3
"""Srovnávací IFC: výrobní STEP (vlevo) vs aktuální SweptSolid (vpravo).

Stejná orientace podle hnízda, hrotu a roviny ohybu; stejné měřítko.
    python tools/build_comparison.py --output out/compare-kgb.ifc
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ifcopenshell.api
import numpy as np

import kg_generator
from swept_geometrie import lathes_to_ifc
from tools.measure_reference import canonical_elbow_frame, load_mesh, mouth_annuli

PAIRS = (("220200z", 15), ("220210z", 30), ("220220z", 45))


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


def build(output_path):
    table = kg_generator.load_table()
    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcProject", name="KGB STEP vs SweptSolid"
    )
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run(
        "context.add_context", file, context_type="Model", target_view="MODEL_VIEW"
    )
    context.Precision = 1e-5
    project.RepresentationContexts = [context]

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
            fitting = ifcopenshell.api.run(
                "root.create_entity", file, ifc_class="IfcPipeFitting",
                predefined_type="BEND", name=label,
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
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "out/compare-kgb.ifc"))
    args = parser.parse_args()
    print("Vytvořeno:", build(args.output))
