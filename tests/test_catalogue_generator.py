from pathlib import Path

import ifcopenshell
import ifcopenshell.util.unit
import pytest

from definice import (
    KG_15_DN110,
    KG_30_DN110,
    KG_45_DN110,
    KG_OD,
    KG_BRANCH_45_DN160_DN110,
    KG_CAPS,
    KG_CLEANOUTS,
    KG_REDUCER_160_110,
    kg_approximate_fittings,
)
from kg_generator import CATALOGUE_KG, generate_kg_library
from generator import generate_catalogue_fitting


@pytest.mark.parametrize(
    "definition, mesh",
    [
        (KG_45_DN110, "220220z.json"),
        (KG_BRANCH_45_DN160_DN110, "222320z.json"),
    ],
)
def test_catalogue_product_generates_valid_library(tmp_path, definition, mesh):
    root = Path(__file__).parents[1]
    output = generate_catalogue_fitting(
        definition, root / "data/ostendorf" / mesh, tmp_path / f"{mesh}.ifc"
    )

    file = ifcopenshell.open(str(output))
    fitting_type = file.by_type("IfcPipeFittingType")[0]
    occurrence = file.by_type("IfcPipeFitting")[0]
    coordinates = fitting_type.RepresentationMaps[0].MappedRepresentation.Items[0].Coordinates.CoordList
    ports = [p for rel in occurrence.IsNestedBy for p in rel.RelatedObjects]
    assert file.schema == "IFC4"
    assert fitting_type.Name == definition.name
    assert ifcopenshell.util.unit.calculate_unit_scale(file) == pytest.approx(0.001)
    assert max(max(point) for point in coordinates) - min(
        min(point) for point in coordinates
    ) > 100
    assert len(ports) == len(definition.ports)


def test_kg_batch_contains_both_catalogue_families(tmp_path):
    root = Path(__file__).parents[1]
    output = generate_kg_library(tmp_path / "kg.ifc", root / "data/ostendorf")
    file = ifcopenshell.open(str(output))

    assert {t.Name for t in file.by_type("IfcPipeFittingType")} == {
        KG_15_DN110.name,
        KG_30_DN110.name,
        KG_45_DN110.name,
        KG_BRANCH_45_DN160_DN110.name,
        KG_REDUCER_160_110.name,
        *(fitting.name for fitting in KG_CAPS),
        *(fitting.name for fitting in KG_CLEANOUTS),
        *(fitting.name for fitting in kg_approximate_fittings()),
    }
    assert len(file.by_type("IfcPipeFitting")) == 36
    assert len(file.by_type("IfcDistributionPort")) == 81
    for definition in kg_approximate_fittings():
        fitting_type = next(
            item for item in file.by_type("IfcPipeFittingType")
            if item.Name == definition.name
        )
        assert ifcopenshell.util.element.get_psets(fitting_type)["Pset_Tvarovka"][
            "GeometryStatus"
        ].startswith("Approximate")


def test_kg_catalogue_covers_every_combination_in_planned_size_scope():
    definitions = (*CATALOGUE_KG, *kg_approximate_fittings())
    expected_bends = {(od, angle) for od in KG_OD for angle in (15, 30, 45, 67, 87)}
    expected_branches = {
        (45, main, branch)
        for main, branch in ((110, 110), (125, 110), (125, 125),
                             (160, 110), (160, 125), (160, 160))
    } | {
        (87, main, branch)
        for main, branch in ((110, 110), (125, 110), (125, 125),
                             (160, 110), (160, 125), (160, 160))
    }
    expected_reducers = {(125, 110), (160, 110), (160, 125)}
    actual_bends = {
        (int(item.od_mm), int(item.angle_deg))
        for item in definitions if item.family == "BEND"
    }
    actual_branches = {
        (int(item.angle_deg), int(item.od_mm), int(item.branch_od_mm))
        for item in definitions if item.family == "JUNCTION"
    }
    actual_reducers = {
        (int(item.od_mm), int(item.branch_od_mm))
        for item in definitions if item.family == "TRANSITION"
    }
    assert actual_bends == expected_bends
    assert actual_branches == expected_branches
    assert actual_reducers == expected_reducers
