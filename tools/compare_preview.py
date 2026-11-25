"""Srovnání KG odbočky: STEP reference vs generátor, jeden IFC na iteraci.

Usage: python tools/compare_preview.py 222320z [out.ifc]

Vytvoří IFC4 se dvěma tělesy vedle sebe (reference vlevo v X, model vpravo),
plus vypíše radiální profily podél hlavní osy a osy odbočky. Slouží k živé
iteraci v Blenderu (scéna "Porovnani"); do knihoven se neshipuje.
"""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))

from swept_geometrie import branch_lathes
from tests.silhouette import pca_register, tessellate
from tests.test_kg_other_geometry import BRANCH_MEASURED
from tools.measure_reference import load_mesh

ROOT = Path(__file__).parents[1]


def build_body(article):
    """Stejný recept jako IoU test odboček; vrací (SweptBody, úhel, vertex_y, délka)."""
    length, vertex, branch_len, angle, dn, branch_dn = BRANCH_MEASURED[article]
    table = __import__("kg_generator").load_table()["sockets"]
    sock, bsock = table[str(dn)], table[str(branch_dn)]
    wall = 3.2 if dn <= 125 else 4.0
    bwall = 3.2 if branch_dn <= 125 else 4.0
    body, _ = branch_lathes(
        length, dn, wall, sock["collar_diameter_mm"], sock["insertion_depth_t_mm"],
        branch_dn, bwall, bsock["collar_diameter_mm"], bsock["insertion_depth_t_mm"],
        vertex - length / 2, branch_len, angle,
    )
    return body, angle, vertex - length / 2, length


def profile(vertices, origin, direction, bins_mm=5.0, exclude=None):
    """Radiální poloměr (max/median) po 5 mm podél osy `direction` od `origin`."""
    d = np.asarray(direction, dtype=float)
    d /= np.linalg.norm(d)
    t = (vertices - origin) @ d
    radial = vertices - origin - np.outer(t, d)
    r = np.linalg.norm(radial, axis=1)
    mask = np.ones(len(t), dtype=bool)
    if exclude is not None:
        oe, od_ = exclude
        oe, od_ = np.asarray(oe, float), np.asarray(od_, float)
        od_ = od_ / np.linalg.norm(od_)
        te = (vertices - oe) @ od_
        re = np.linalg.norm(vertices - oe - np.outer(te, od_), axis=1)
        mask = re > 70.0  # body blízko hlavní osy nejsou odbočka
    rows = []
    lo, hi = t[mask].min(), t[mask].max()
    edges = np.arange(np.floor(lo / bins_mm) * bins_mm, hi + bins_mm, bins_mm)
    for a, b in zip(edges[:-1], edges[1:]):
        m = mask & (t >= a) & (t < b)
        if m.sum() < 5:
            continue
        rows.append((float(a), float(r[m].max()), float(np.median(r[m])), int(m.sum())))
    return rows


def print_profiles(mv, rv, angle, vertex_y, length):
    """Tabulka profilů model vs reference (registrovaná) podél obou os."""
    d_main = np.array((0.0, 1.0, 0.0))
    d_branch = np.array((np.sin(angle), np.cos(angle), 0.0))
    origin = np.array((0.0, vertex_y, 0.0))
    for name, axis, org, excl in (
        ("hlavní osa", d_main, origin, None),
        ("osa odbočky", d_branch, origin, (origin, d_main)),
    ):
        print(f"--- profil: {name} (vzdálenost od vrcholu, mm) ---")
        pm = profile(mv, org, axis, exclude=excl)
        pr = profile(rv, org, axis, exclude=excl)
        print(f"{'od':>6} {'mod_max':>8} {'mod_med':>8} | {'ref_max':>8} {'ref_med':>8}")
        for (a, mmx, mme, _), row in zip(pm, pr):
            print(f"{a:6.0f} {mmx:8.1f} {mme:8.1f} | {row[1]:8.1f} {row[2]:8.1f}")


def write_ifc(model, reference, path):
    """Dvě IfcTriangulatedFaceSet tělesa: reference při x = -400, model při x = +400."""
    import ifcopenshell

    f = ifcopenshell.file(schema="IFC4")
    owner = None
    ctx = f.createIfcGeometricRepresentationContext(
        "Model", "Model", 3, 1e-5,
        f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
        f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
    )
    project = f.createIfcProject(ifcopenshell.guid.new(), owner, "Porovnani odbocek")
    project.RepresentationContexts = [ctx]

    def body(name, verts, faces, offset_x):
        place = f.createIfcLocalPlacement()
        place.RelativePlacement = f.createIfcAxis2Placement3D(
            f.createIfcCartesianPoint((float(offset_x), 0.0, 0.0)), None, None)
        coords = f.createIfcCartesianPointList3D([tuple(map(float, v)) for v in verts])
        shape = f.createIfcTriangulatedFaceSet()
        shape.Coordinates = coords
        shape.Closed = True
        shape.CoordIndex = [[int(i) + 1 for i in tri] for tri in faces]
        rep = f.createIfcShapeRepresentation(ctx, "Body", "Tessellation", [shape])
        product = f.createIfcBuildingElementProxy()
        product.GlobalId = ifcopenshell.guid.new()
        product.OwnerHistory = owner
        product.Name = name
        product.ObjectPlacement = place
        product.Representation = rep
        rel = f.createIfcRelContainedInSpatialStructure()
        rel.GlobalId = ifcopenshell.guid.new()
        rel.RelatedElements = [product]
        rel.RelatingStructure = _storey(f, owner, place)
        return product

    def _storey(f, owner, place):
        if f.by_type("IfcBuildingStorey"):
            return f.by_type("IfcBuildingStorey")[0]
        site_place = f.createIfcLocalPlacement()
        site_place.RelativePlacement = f.createIfcAxis2Placement3D(
            f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None)
        site = f.createIfcSite()
        site.GlobalId = ifcopenshell.guid.new()
        site.OwnerHistory = owner
        site.Name = "Porovnani"
        site.ObjectPlacement = site_place
        storey = f.createIfcBuildingStorey()
        storey.GlobalId = ifcopenshell.guid.new()
        storey.OwnerHistory = owner
        storey.Name = "Iterace"
        storey.ObjectPlacement = site_place
        f.createIfcRelAggregates(ifcopenshell.guid.new(), owner, None, None, site, [storey])
        return storey

    rv, rf = reference
    mv, mf = model
    body("REF " + sys.argv[1], rv, rf, -400.0)
    body("MODEL " + sys.argv[1], mv, mf, 400.0)
    f.write(str(path))
    return path


def main():
    article = sys.argv[1] if len(sys.argv) > 1 else "222320z"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / f"compare-{article}.ifc"
    model = tessellate(build_body(article)[0])
    ref_v, ref_f = load_mesh(ROOT / f"data/ostendorf/{article}.json")
    rotation = pca_register(model, (ref_v, ref_f))
    ref = (ref_v @ rotation, ref_f)
    out.parent.mkdir(exist_ok=True)
    write_ifc(model, ref, out)
    print("IFC:", out)
    mv, mf = model
    _, vertex, branch_len, angle, dn, _ = BRANCH_MEASURED[article]
    print_profiles(mv, ref[0], np.deg2rad(BRANCH_MEASURED[article][3]),
                   BRANCH_MEASURED[article][1] - BRANCH_MEASURED[article][0] / 2,
                   BRANCH_MEASURED[article][0])


if __name__ == "__main__":
    main()
