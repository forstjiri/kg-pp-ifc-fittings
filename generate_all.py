"""Jediné CLI pro generování knihoven tvarovek (a volitelného náhledu)."""

import argparse, json, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
TITLES = {"kg": "KG (EN 1401-1) náhled", "pp": "PP (EN 1451-1) náhled"}


def build_preview(standard, path=None):
    """Mřížka vzorků knihovny do out/preview-<standard>.ifc pro Blender."""
    from ifc_util import new_file, placement, product
    from swept_geometrie import lathes_to_ifc

    module = __import__(f"{standard}_generator", fromlist=[f"{standard}_items"])
    file, _, context = new_file(TITLES[standard])
    for slot, (definition, body) in enumerate(module.__dict__[f"{standard}_items"]()):
        if isinstance(body, (str, Path)):
            body = json.loads(Path(body).read_text())
        if isinstance(body, tuple):
            verts, faces = (np.asarray(part) for part in body)
            items = [file.create_entity("IfcTriangulatedFaceSet",
                Coordinates=file.create_entity("IfcCartesianPointList3D",
                                               CoordList=np.round(verts, 7).tolist()),
                CoordIndex=(np.asarray(faces) + 1).tolist(), Closed=False)]
            rep_type = "Tessellation"
        else:
            items, rep_type = lathes_to_ifc(file, body), "SweptSolid"
        product(file, context, definition.name, definition.family, items,
                placement(file, (slot % 6 * 1000.0, slot // 6 * 1000.0, 0.0)), rep_type)
    path = Path(path or ROOT / f"out/preview-{standard}.ifc")
    path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(path))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standard", choices=("kg", "pp", "all"), default="all")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--grid", action="store_true")
    args = parser.parse_args()
    output = ROOT / "out"
    written = []
    if args.standard in ("kg", "all"):
        from kg_generator import generate_kg_library
        written.append(generate_kg_library(output / "tvarovky-EN1401-1.ifc"))
    if args.standard in ("pp", "all"):
        from pp_generator import generate_pp_library
        written.append(generate_pp_library(output / "tvarovky-EN1451-1.ifc"))
    selected = ("kg", "pp") if args.standard == "all" else (args.standard,)
    if args.preview:
        for standard in selected:
            written.append(build_preview(standard))
    if args.grid:
        from grid import build_grid, validate_grid
        for standard in selected:
            path, info = build_grid(standard, output / f"grid-{standard}.ifc")
            counts = validate_grid(path, info)
            print(f"Grid OK: {standard}, {counts[0]} tvarovek, {counts[1]} trubek, "
                  f"{counts[2]} typů, 0 EXPRESS chyb")
            written.append(path)
    print("Hotovo:\n  " + "\n  ".join(str(path) for path in written))


if __name__ == "__main__":
    main()
