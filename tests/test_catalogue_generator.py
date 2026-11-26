import ifcopenshell
import ifcopenshell.util.unit
import pytest

from generator import generate_catalogue_library
from kg_generator import generate_kg_library, kg_items


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
    output = generate_kg_library(tmp_path / "kg.ifc")
    file = ifcopenshell.open(str(output))
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
    expected_branches = {(angle, main, branch)
                         for angle in (45, 87) for main, branch in combinations}
    expected_reducers = {(125, 110), (160, 110), (160, 125)}
    actual_bends = {(int(item.od_mm), int(item.angle_deg))
                    for item in definitions if item.family == "BEND"}
    actual_branches = {(int(item.angle_deg), int(item.od_mm), int(item.branch_od_mm))
                       for item in definitions if item.family == "JUNCTION"}
    actual_reducers = {(int(item.od_mm), int(item.branch_od_mm))
                       for item in definitions if item.family == "TRANSITION"}
    assert actual_bends == expected_bends
    assert actual_branches == expected_branches
    assert actual_reducers == expected_reducers
