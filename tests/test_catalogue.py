"""IFC knihovna: typy, výskyty, porty, reprezentace a orientace."""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import numpy as np
import pytest

from generator import generate_catalogue_library
from kg_generator import generate_kg_library, kg_items
from pp_generator import pp_items


def test_kg_product_generates_valid_swept_library(tmp_path):
    item = next(i for i in kg_items() if i[0].article == "220220")
    output = generate_catalogue_library([item], tmp_path / "kg-elbow.ifc")
    file = ifcopenshell.open(str(output))
    fitting_type = file.by_type("IfcPipeFittingType")[0]
    occurrence = file.by_type("IfcPipeFitting")[0]
    items = fitting_type.RepresentationMaps[0].MappedRepresentation.Items
    ports = [p for rel in occurrence.IsNestedBy for p in rel.RelatedObjects]
    assert file.schema == "IFC4"
    assert all(item.is_a("IfcRevolvedAreaSolid") for item in items)
    assert ifcopenshell.util.unit.calculate_unit_scale(file) == pytest.approx(0.001)
    assert len(ports) == len(item[0].ports)


def test_kg_batch_is_pure_swept_solid_and_complete(tmp_path):
    file = ifcopenshell.open(str(generate_kg_library(tmp_path / "kg.ifc")))
    items = kg_items()
    assert {t.Name for t in file.by_type("IfcPipeFittingType")} == {
        definition.name for definition, _ in items
    }
    assert len(file.by_type("IfcPipeFitting")) == 36
    assert len(file.by_type("IfcDistributionPort")) == sum(
        len(definition.ports) for definition, _ in items
    )
    assert not file.by_type("IfcTriangulatedFaceSet")
    assert all(
        item.is_a("IfcRevolvedAreaSolid") or item.is_a("IfcExtrudedAreaSolidTapered")
        for representation in file.by_type("IfcShapeRepresentation")
        for item in representation.Items
        if item.is_a("IfcRevolvedAreaSolid") or item.is_a("IfcExtrudedAreaSolidTapered")
    )


def test_kg_catalogue_covers_every_combination_in_planned_size_scope():
    definitions = [definition for definition, _ in kg_items()]
    expected_bends = {(od, angle) for od in (110, 125, 160)
                      for angle in (15, 30, 45, 67, 87)}
    combinations = ((110, 110), (125, 110), (125, 125),
                    (160, 110), (160, 125), (160, 160))
    expected_branches = {(angle, main, small) for angle in (45, 87)
                         for main, small in combinations}
    expected_reducers = {(125, 110), (160, 110), (160, 125)}
    assert {(int(i.od_mm), int(i.angle_deg)) for i in definitions
            if i.family == "BEND"} == expected_bends
    assert {(int(i.angle_deg), int(i.od_mm), int(i.branch_od_mm)) for i in definitions
            if i.family == "JUNCTION"} == expected_branches
    assert {(int(i.od_mm), int(i.branch_od_mm)) for i in definitions
            if i.family == "TRANSITION"} == expected_reducers


def test_pp_occurrence_passes_ifc4_and_orientation_validation(tmp_path):
    items = pp_items()
    sample = (
        items[0],
        next(i for i in items if i[0].family == "JUNCTION"),
        next(i for i in items if i[0].family == "TRANSITION"),
        next(i for i in items if i[0].family == "USERDEFINED"),
    )
    output = generate_catalogue_library(list(sample), tmp_path / "pp-sample.ifc",
                                        name="PP MASTER 3 PLUS")
    model = ifcopenshell.open(str(output))
    assert model.schema == "IFC4"
    assert len(model.by_type("IfcPipeFittingType")) == 4
    assert len(model.by_type("IfcDistributionPort")) == 9
    for occurrence in model.by_type("IfcPipeFitting"):
        for relation in occurrence.IsNestedBy:
            for port in relation.RelatedObjects:
                placement = ifcopenshell.util.placement.get_local_placement(
                    port.ObjectPlacement)
                assert np.isclose(np.linalg.norm(placement[:3, 2]), 1.0)
                assert ifcopenshell.util.element.get_psets(port)[
                    "Pset_DistributionPortTypePipe"]["OuterDiameter"] > 0
                if port.Name == "SINK" and occurrence.Name.startswith("PP svislý čistící"):
                    assert np.allclose(placement[:3, 2], [0, 0, 1])
