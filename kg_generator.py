"""KG (EN 1401-1, Ostendorf) sortiment knihovny tvarovek."""

import sys
from pathlib import Path

from definice import (
    KG_15_DN110,
    KG_30_DN110,
    KG_45_DN110,
    KG_BRANCH_45_DN160_DN110,
    KG_CAPS,
    KG_CAP_GEOMETRY,
    KG_CLEANOUTS,
    KG_REDUCER_160_110,
    kg_approximate_fittings,
)
from geometrie import kg_cap_mesh
from pp_geometrie import branch_mesh, elbow_mesh, inspection_piece_mesh, reducer_mesh

from generator import generate_catalogue_library

ROOT = Path(__file__).parent

CATALOGUE_KG = (
    KG_15_DN110,
    KG_30_DN110,
    KG_45_DN110,
    KG_BRANCH_45_DN160_DN110,
    KG_REDUCER_160_110,
)


def kg_items(mesh_dir=None):
    """(definice, mesh) položky KG: katalogové meshe + aproximované recepty."""
    mesh_dir = Path(mesh_dir or ROOT / "data/ostendorf")
    items = [
        (definition, mesh_dir / f"{definition.article}z.json")
        for definition in CATALOGUE_KG
    ]
    for definition in kg_approximate_fittings():
        wall = 3.2 if definition.od_mm <= 125 else 4.0
        if definition.family == "BEND":
            mesh = elbow_mesh(
                {"angle_deg": definition.angle_deg, "length_mm": definition.length_mm,
                 "od_mm": definition.od_mm, "socket_od_mm": definition.od_mm * 1.15},
                30.0,
                wall,
            )[:2]
        elif definition.family == "JUNCTION":
            mesh = branch_mesh(
                {"angle_deg": definition.angle_deg, "length_mm": definition.length_mm,
                 "z1_mm": definition.z1_mm, "z3_mm": definition.z3_mm},
                definition.od_mm,
                definition.branch_od_mm,
                30.0,
                wall,
            )[:2]
        else:
            small_od = definition.branch_od_mm
            mesh = reducer_mesh(
                definition.length_mm,
                definition.od_mm,
                small_od,
                definition.od_mm * 1.15,
                small_od * 1.15,
                wall,
                offset_mm=definition.z1_mm,
            )
        items.append((definition, mesh))
    items.extend(
        (
            definition,
            kg_cap_mesh(
                definition.od_mm,
                definition.length_mm,
                **KG_CAP_GEOMETRY[int(definition.od_mm)],
            ),
        )
        for definition in KG_CAPS
    )
    items.extend(
        (
            definition,
            inspection_piece_mesh(
                definition.length_mm,
                definition.od_mm,
                definition.od_mm * 1.15,
                30.0,
                3.2 if definition.od_mm <= 125 else 4.0,
                definition.od_mm * 0.65,
                definition.od_mm * 0.95,
                definition.length_mm * 0.62,
            ),
        )
        for definition in KG_CLEANOUTS
    )
    return items


def generate_kg_library(output_path, mesh_dir=None):
    return generate_catalogue_library(kg_items(mesh_dir), output_path, name="PVC-U KG")


if __name__ == "__main__":
    output = generate_kg_library(ROOT / "out/tvarovky-EN1401-1.ifc")
    print(f"Vytvořeno: {output}")
