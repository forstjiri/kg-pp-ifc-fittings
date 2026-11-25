import numpy as np

import pp_generator
from generator import generate_catalogue_library
from pp_generator import pp_items


def test_parametric_pp_meshes_provide_ports_and_nonempty_triangles():
    items = pp_items()
    # catalog rows restricted to the approved sizes (32-160, no 90)
    sizes = pp_generator.LIBRARY_SIZES
    table = pp_generator.TABLE
    assert len(items) == len(
        [r for r in table["elbows"] if r["dn_od"] in sizes]
    ) + len(
        [r for r in table["simple_branches"] if r["dn_od"] in sizes and r["branch_dn_od"] in sizes]
    ) + len([r for r in table["reducers"] if r["large_dn_od"] in sizes and r["small_dn_od"] in sizes]) + len(
        [r for r in table["cleanouts"] if r["dn_od"] in sizes]
    ) + len([r for r in table["caps"] if r["dn_od"] in sizes])
    swept = 0
    for definition, body in items:
        # swept solid: exact lathes, no triangle meshes in this library
        assert all(np.isfinite(np.asarray(lathe.profile)).all() for lathe in body.lathes)
        assert len(body.lathes) >= 1  # tube/arc plus socket cups and stubs
        swept += 1
        expected_ports = (
            1 if definition.article.startswith("M3-M")
            else 3 if definition.family == "JUNCTION" else 2
        )
        assert len(definition.ports) == expected_ports
        assert len(definition.geometry_status) > 20  # původ rozměrů/odhadů v Psetu
    assert swept == len(items)  # every PP item is an exact swept solid; no triangle meshes left


def test_parametric_pp_occurrence_passes_ifc4_and_orientation_validation(tmp_path):
    items = pp_items()
    elbow = items[0]
    branch = next(item for item in items if item[0].family == "JUNCTION")
    reducer = next(item for item in items if item[0].family == "TRANSITION")
    cleanout = next(item for item in items if item[0].family == "USERDEFINED")
    output = generate_catalogue_library(
        [elbow, branch, reducer, cleanout],
        tmp_path / "pp-sample.ifc",
        name="PP MASTER 3 PLUS",
    )
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.placement

    model = ifcopenshell.open(str(output))
    assert model.schema == "IFC4"
    assert len(model.by_type("IfcPipeFittingType")) == 4
    assert len(model.by_type("IfcDistributionPort")) == 9
    for occurrence in model.by_type("IfcPipeFitting"):
        for relation in occurrence.IsNestedBy:
            for port in relation.RelatedObjects:
                placement = ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)
                assert np.isclose(np.linalg.norm(placement[:3, 2]), 1.0)
                assert ifcopenshell.util.element.get_psets(port)[
                    "Pset_DistributionPortTypePipe"
                ]["OuterDiameter"] > 0
                if port.Name == "SINK" and occurrence.Name.startswith("PP svislý čistící"):
                    assert np.allclose(placement[:3, 2], [0, 0, 1])
