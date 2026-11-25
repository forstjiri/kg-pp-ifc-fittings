#!/usr/bin/env python3
"""Mřížka vzorků knihovny do out/preview-<standard>.ifc pro Blender.

Každá položka knihovny (definice, tělo) je jedna instance IfcPipeFitting
na mřížce s 1000 mm roztečí, aby se vzorky daly prohlédnout a vyfotit
v get_viewport_screenshot. Nekontroluje porty ani Psety — na to je
validate_library v generator.py.

    python tools/build_preview.py --standard kg|pp|all
"""

import argparse
from pathlib import Path

import ifcopenshell.api
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPACING = 1000.0


def _items(standard):
    if standard == "kg":
        from kg_generator import kg_items

        return kg_items(), "KG (EN 1401-1) náhled"
    from pp_generator import pp_items

    return pp_items(), "PP (EN 1451-1) náhled"


def _body_items(file, context, body):
    from swept_geometrie import lathes_to_ifc

    if isinstance(body, (str, Path)):  # katalogový mesh JSON [vrcholy, faces]
        import json

        vertices, faces = (np.asarray(part) for part in json.loads(Path(body).read_text()))
        body = (vertices, faces)
    if isinstance(body, tuple):  # (vertices, faces) tessellation
        vertices, faces = (np.asarray(part) for part in body)
        return [
            file.create_entity(
                "IfcTriangulatedFaceSet",
                Coordinates=file.create_entity(
                    "IfcCartesianPointList3D", CoordList=np.round(vertices, 7).tolist()
                ),
                CoordIndex=(faces + 1).tolist(),
                Closed=False,
            )
        ], "Tessellation"
    return lathes_to_ifc(file, body), "SweptSolid"


def build_preview(standard, output_path=None):
    items, title = _items(standard)
    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcProject", name=title
    )
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run(
        "context.add_context", file, context_type="Model", target_view="MODEL_VIEW"
    )
    context.Precision = 1e-5
    project.RepresentationContexts = [context]

    for slot, (definition, body) in enumerate(items):
        representation_items, representation_type = _body_items(file, context, body)
        fitting = ifcopenshell.api.run(
            "root.create_entity", file, ifc_class="IfcPipeFitting",
            predefined_type=definition.family, name=definition.name,
        )
        fitting.ObjectPlacement = file.create_entity(
            "IfcLocalPlacement",
            RelativePlacement=file.create_entity(
                "IfcAxis2Placement3D",
                Location=file.create_entity(
                    "IfcCartesianPoint",
                    Coordinates=(
                        float(slot % 6 * SPACING), float(slot // 6 * SPACING), 0.0
                    ),
                ),
            ),
        )
        fitting.Representation = file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[file.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=context,
                RepresentationIdentifier="Body",
                RepresentationType=representation_type,
                Items=representation_items,
            )],
        )

    output_path = Path(output_path or ROOT / f"out/preview-{standard}.ifc")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standard", choices=("kg", "pp", "all"), default="all")
    args = parser.parse_args()
    for name in ("kg", "pp") if args.standard == "all" else (args.standard,):
        print(f"Vytvořeno: {build_preview(name)}")
