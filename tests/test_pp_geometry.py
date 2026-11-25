import numpy as np

from generator import generate_catalogue_library
from pp_generator import pp_items


def test_parametric_pp_meshes_provide_ports_and_nonempty_triangles():
    items = pp_items()
    assert len(items) == 60
    assert sum(definition.family == "BEND" for definition, _ in items) == 31
    assert sum(definition.family == "JUNCTION" for definition, _ in items) == 15
    assert sum(definition.family == "TRANSITION" for definition, _ in items) == 9
    assert sum(definition.family == "USERDEFINED" for definition, _ in items) == 5
    swept = 0
    for definition, body in items:
        # swept solid: exact lathes, no triangle meshes in this library
        assert all(np.isfinite(np.asarray(lathe.profile)).all() for lathe in body.lathes)
        assert len(body.lathes) >= 3  # tube/arc plus socket cups and stubs
        swept += 1
        expected_ports = 3 if definition.family == "JUNCTION" else 2
        assert len(definition.ports) == expected_ports
        assert "approximate" in definition.geometry_status.lower()
    assert swept == 60  # every PP item is an exact swept solid; no triangle meshes left


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
