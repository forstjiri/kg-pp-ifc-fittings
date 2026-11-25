"""Zápis a validace katalogových IFC knihoven tvarovek (obě normy)."""

import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from geometrie import transform_catalogue_mesh, transform_catalogue_points
from swept_geometrie import SweptBody, lathes_to_ifc, swept_bounds


def _point(file, xyz):
    return file.create_entity("IfcCartesianPoint", Coordinates=tuple(float(v) for v in xyz))


def _direction(file, xyz):
    return file.create_entity("IfcDirection", DirectionRatios=tuple(float(v) for v in xyz))


def _property(file, name, value):
    nominal = file.create_entity("IfcText", str(value))
    return file.create_entity("IfcPropertySingleValue", Name=name, NominalValue=nominal)


def _add_properties(file, target, name, values):
    pset = file.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        HasProperties=[_property(file, key, value) for key, value in values.items()],
    )
    target.HasPropertySets = tuple(target.HasPropertySets or ()) + (pset,)
    return pset


def validate_source_ports(vertices_mm, definition):
    """Check each declared port plane intersects the source mesh at OD scale."""
    vertices = np.asarray(vertices_mm, dtype=float)
    sections = []
    for port in definition.ports:
        center = np.asarray(port.position_mm)
        axis = np.asarray(port.axis, dtype=float)
        axis /= np.linalg.norm(axis)
        delta = vertices - center
        axial = delta @ axis
        near_plane = np.abs(axial) <= 0.1
        radii = np.linalg.norm(delta[near_plane] - np.outer(axial[near_plane], axis), axis=1)
        if len(radii) < 20:
            raise RuntimeError(f"portová rovina neprotíná zdrojový mesh: {port.name}")
        expected_radius = port.od_mm / 2
        if not expected_radius - 4 <= np.median(radii) <= expected_radius + 2:
            raise RuntimeError(f"zdrojový mesh nepotvrzuje průměr portu: {port.name}")
        sections.append((len(radii), float(radii.min()), float(radii.max())))
    return sections


def validate_library(path, records):
    file = ifcopenshell.open(str(path))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(file, logger, express_rules=True)
    errors = [s for s in logger.statements if s.get("level") == "error"]
    if errors:
        raise RuntimeError(f"IFC EXPRESS validation errors: {errors[:3]}")
    types = file.by_type("IfcPipeFittingType")
    occurrences = file.by_type("IfcPipeFitting")
    libraries = file.by_type("IfcProjectLibrary")
    if (
        file.schema != "IFC4"
        or len(types) != len(records)
        or len(occurrences) != len(records)
        or len(libraries) != 1
    ):
        raise RuntimeError("počet IFC typů/výskytů neodpovídá definicím")
    declarations = file.by_type("IfcRelDeclares")
    if not any(libraries[0] in rel.RelatedDefinitions for rel in declarations):
        raise RuntimeError("IfcProjectLibrary není deklarovaná v projektu")
    if not all(
        any(t in rel.RelatedDefinitions for rel in declarations) for t in types
    ):
        raise RuntimeError("typ tvarovky není deklarovaný v knihovně")
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    for index, (record, fitting_type, occurrence) in enumerate(
        zip(records, types, occurrences)
    ):
        definition = record["definition"]
        if fitting_type.Name != definition.name:
            raise RuntimeError(f"typ v IFC neodpovídá: {definition.name}")
        mapped_mesh = fitting_type.RepresentationMaps[0].MappedRepresentation.Items[0]
        swept = record["swept"]
        if swept:
            items = fitting_type.RepresentationMaps[0].MappedRepresentation.Items
            if len(items) != len(swept.lathes) or not all(
                item.is_a("IfcRevolvedAreaSolid") for item in items
            ):
                raise RuntimeError(f"IFC neobsahuje tažená tělesa: {definition.article}")
        elif not np.allclose(
            np.asarray(mapped_mesh.Coordinates.CoordList),
            np.round(record["vertices_mm"], 7),
            atol=1e-9,
        ):
            raise RuntimeError(f"IFC neobsahuje zdrojové vrcholy: {definition.article}")
        if not swept and not np.array_equal(
            np.asarray(mapped_mesh.CoordIndex), record["faces"] + 1
        ):
            raise RuntimeError(f"IFC neobsahuje zdrojovou topologii: {definition.article}")

        shape = ifcopenshell.geom.create_shape(settings, occurrence)
        actual_vertices = np.asarray(shape.geometry.verts).reshape(-1, 3)
        actual_faces = len(shape.geometry.faces) // 3
        expected_vertices = record["vertices_mm"] + (index * 1000, 0, 0)
        # OCCT may weld coincident/near-coincident stations in procedural meshes.
        if record["has_source_mesh"] and len(actual_vertices) < 0.99 * len(expected_vertices):
            raise RuntimeError(f"geometry kernel ztratil vrcholy: {definition.article}")
        if record["has_source_mesh"] and actual_faces < 0.99 * len(record["faces"]):
            raise RuntimeError(f"geometry kernel ztratil trojúhelníky: {definition.article}")
        if not len(actual_vertices) or not actual_faces:
            raise RuntimeError(f"geometry kernel nevytvořil tvar: {definition.article}")
        if not np.allclose(
            np.r_[actual_vertices.min(axis=0), actual_vertices.max(axis=0)],
            np.r_[expected_vertices.min(axis=0), expected_vertices.max(axis=0)],
            atol=0.5 if swept else 5e-7,
        ):
            raise RuntimeError(f"IFC obálka se liší od zdroje: {definition.article}")

        ports = [p for rel in occurrence.IsNestedBy for p in rel.RelatedObjects]
        if len(ports) != len(definition.ports):
            raise RuntimeError(f"nesprávný počet portů: {definition.article}")
        for port, position, axis, port_definition in zip(
            ports, record["port_positions"], record["port_axes"], definition.ports
        ):
            matrix = ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)
            expected_position = position + (index * 1000, 0, 0)
            if not np.allclose(matrix[:3, 3], expected_position, atol=5e-7):
                raise RuntimeError(f"poloha portu nesouhlasí: {port.Name}")
            if not np.allclose(matrix[:3, 2], axis, atol=5e-7):
                raise RuntimeError(f"osa portu nesouhlasí: {port.Name}")
            if port.FlowDirection != port_definition.flow:
                raise RuntimeError(f"směr toku portu nesouhlasí: {port.Name}")
            props = ifcopenshell.util.element.get_psets(port)
            od = props["Pset_DistributionPortTypePipe"]["OuterDiameter"] * 1000
            if abs(od - port_definition.od_mm) > 0.05:
                raise RuntimeError(f"OD portu nesouhlasí: {port.Name}")
        record["shape_counts"] = (len(actual_vertices), actual_faces, len(ports))


def _prepare_record(definition, mesh_path):
    if isinstance(mesh_path, SweptBody):
        low, high = swept_bounds(mesh_path)
        port_axes = np.asarray([p.axis for p in definition.ports], dtype=float)
        port_axes /= np.linalg.norm(port_axes, axis=1, keepdims=True)
        return {
            "definition": definition,
            "vertices_mm": np.vstack((low, high)),
            "faces": np.zeros((0, 3), dtype=int),
            "has_source_mesh": False,
            "swept": mesh_path,
            "port_positions": np.asarray([p.position_mm for p in definition.ports], dtype=float),
            "port_axes": port_axes,
            "source_sections": [("parametric swept solid", 0, 0)] * len(definition.ports),
        }
    record = _prepare_mesh_record(definition, mesh_path)
    record["swept"] = None
    return record


def _prepare_mesh_record(definition, mesh_path):
    if isinstance(mesh_path, tuple):
        vertices_mm, faces = mesh_path
        has_source_mesh = False
        vertices_mm, faces = np.asarray(vertices_mm, dtype=float), np.asarray(faces, dtype=int)
        port_positions = np.asarray([p.position_mm for p in definition.ports], dtype=float)
        port_axes = np.asarray([p.axis for p in definition.ports], dtype=float)
        port_axes /= np.linalg.norm(port_axes, axis=1, keepdims=True)
    else:
        vertices_mm, faces = json.loads(Path(mesh_path).read_text())
        source_vertices_mm = vertices_mm
        has_source_mesh = True
        vertices_si, faces = transform_catalogue_mesh(
            vertices_mm,
            faces,
            anchor_mm=definition.mesh_anchor_mm,
            along=definition.mesh_along,
            side=definition.mesh_side,
        )
        vertices_mm = vertices_si * 1000
        port_positions = transform_catalogue_points(
            [p.position_mm for p in definition.ports],
            anchor_mm=definition.mesh_anchor_mm,
            along=definition.mesh_along,
            side=definition.mesh_side,
        ) * 1000
        port_axes = transform_catalogue_points(
            [p.axis for p in definition.ports],
            anchor_mm=(0, 0, 0),
            along=definition.mesh_along,
            side=definition.mesh_side,
        )
        port_axes /= np.linalg.norm(port_axes, axis=1, keepdims=True)
    return {
        "definition": definition,
        "vertices_mm": vertices_mm,
        "faces": faces,
        "has_source_mesh": has_source_mesh,
        "port_positions": port_positions,
        "port_axes": port_axes,
        "source_sections": (
            validate_source_ports(source_vertices_mm, definition)
            if has_source_mesh
            else [("approximate geometry", 0, 0)] * len(definition.ports)
        ),
    }


def generate_catalogue_library(items, output_path, name="PVC-U KG"):
    """Vytvoří dávkovou IFC4 Project Library z (definice, mesh-json) položek."""
    records = [_prepare_record(definition, mesh) for definition, mesh in items]
    if not records:
        raise ValueError("knihovna nemůže být prázdná")
    standards = {record["definition"].standard for record in records}
    if len(standards) != 1:
        raise ValueError("jedna IFC knihovna smí obsahovat jen jednu normu")

    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcProject", name=f"Tvarovky {name}"
    )
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run(
        "context.add_context", file, context_type="Model", target_view="MODEL_VIEW"
    )
    context.Precision = 1e-5
    project.RepresentationContexts = [context]

    library = file.create_entity(
        "IfcProjectLibrary",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"{name} | {next(iter(standards))}",
    )
    file.create_entity(
        "IfcRelDeclares",
        GlobalId=ifcopenshell.guid.new(),
        RelatingContext=project,
        RelatedDefinitions=[library],
    )

    fitting_types, representation_maps = [], []
    material = file.create_entity("IfcMaterial", Name=name)
    for record in records:
        definition = record["definition"]
        if record["swept"]:
            representation = file.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=context,
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=lathes_to_ifc(file, record["swept"]),
            )
        else:
            representation = file.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=context,
                RepresentationIdentifier="Body",
                RepresentationType="Tessellation",
                Items=[
                    file.create_entity(
                        "IfcTriangulatedFaceSet",
                        Coordinates=file.create_entity(
                            "IfcCartesianPointList3D",
                            CoordList=np.round(record["vertices_mm"], 7).tolist(),
                        ),
                        CoordIndex=(record["faces"] + 1).tolist(),
                        Closed=False,
                    )
                ],
            )
        representation_map = file.create_entity(
            "IfcRepresentationMap",
            MappingOrigin=file.create_entity(
                "IfcAxis2Placement3D", Location=_point(file, (0, 0, 0))
            ),
            MappedRepresentation=representation,
        )
        representation_maps.append(representation_map)
        type_attributes = {}
        if definition.family == "USERDEFINED":
            type_attributes["ElementType"] = definition.article
        fitting_type = file.create_entity(
            "IfcPipeFittingType",
            GlobalId=ifcopenshell.guid.new(),
            Name=definition.name,
            PredefinedType=definition.family,
            RepresentationMaps=[representation_map],
            **type_attributes,
        )
        fitting_types.append(fitting_type)
        properties = {
            "Standard": definition.standard,
            "CatalogArticle": definition.article,
            "NominalDiameter": definition.od_mm,
            "BendAngle": definition.angle_deg,
            "Length": definition.length_mm,
            "Z1": definition.z1_mm,
            "Z2": definition.z2_mm,
        }
        if definition.branch_od_mm is not None:
            properties["BranchOD"] = definition.branch_od_mm
            if definition.z3_mm is not None:
                properties["Z3"] = definition.z3_mm
        if getattr(definition, "geometry_status", None):
            properties["GeometryStatus"] = definition.geometry_status
        _add_properties(file, fitting_type, "Pset_Tvarovka", properties)
        for index, (port, position, axis) in enumerate(
            zip(definition.ports, record["port_positions"], record["port_axes"]), start=1
        ):
            _add_properties(
                file,
                fitting_type,
                f"Pset_TvarovkaPort{index}",
                {
                    "Name": port.name,
                    "Position": ", ".join(f"{v:.3f}" for v in position),
                    "Axis": ", ".join(f"{v:.6f}" for v in axis),
                    "FlowDirection": port.flow,
                    "OuterDiameter": port.od_mm,
                },
            )

    file.create_entity(
        "IfcRelDeclares",
        GlobalId=ifcopenshell.guid.new(),
        RelatingContext=library,
        RelatedDefinitions=fitting_types,
    )
    file.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=fitting_types,
        RelatingMaterial=material,
    )

    for index, (record, fitting_type, representation_map) in enumerate(
        zip(records, fitting_types, representation_maps)
    ):
        definition = record["definition"]
        occurrence = ifcopenshell.api.run(
            "root.create_entity",
            file,
            ifc_class="IfcPipeFitting",
            predefined_type=definition.family,
            name=definition.name,
        )
        if definition.family == "USERDEFINED":
            occurrence.ObjectType = definition.article
        occurrence.ObjectPlacement = file.create_entity(
            "IfcLocalPlacement",
            RelativePlacement=file.create_entity(
                "IfcAxis2Placement3D", Location=_point(file, (float(index * 1000), 0, 0))
            ),
        )
        file.create_entity(
            "IfcRelDefinesByType",
            GlobalId=ifcopenshell.guid.new(),
            RelatedObjects=[occurrence],
            RelatingType=fitting_type,
        )
        occurrence.Representation = file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[
                file.create_entity(
                    "IfcShapeRepresentation",
                    ContextOfItems=context,
                    RepresentationIdentifier="Body",
                    RepresentationType="MappedRepresentation",
                    Items=[
                        file.create_entity(
                            "IfcMappedItem",
                            MappingSource=representation_map,
                            MappingTarget=file.create_entity(
                                "IfcCartesianTransformationOperator3D",
                                LocalOrigin=_point(file, (0, 0, 0)),
                                Scale=1.0,
                            ),
                        )
                    ],
                )
            ],
        )
        ports = []
        for port, position, axis in zip(
            definition.ports, record["port_positions"], record["port_axes"]
        ):
            axis_x = np.cross(axis, (0, 0, 1))
            if np.linalg.norm(axis_x) < 1e-8:
                axis_x = np.array((1.0, 0.0, 0.0))
            axis_x /= np.linalg.norm(axis_x)
            port_placement = file.create_entity(
                "IfcLocalPlacement",
                PlacementRelTo=occurrence.ObjectPlacement,
                RelativePlacement=file.create_entity(
                    "IfcAxis2Placement3D",
                    Location=_point(file, position),
                    Axis=_direction(file, axis),
                    RefDirection=_direction(file, axis_x),
                ),
            )
            port_entity = file.create_entity(
                "IfcDistributionPort",
                GlobalId=ifcopenshell.guid.new(),
                Name=port.name,
                ObjectPlacement=port_placement,
                FlowDirection=port.flow,
                PredefinedType="PIPE",
                SystemType="NOTDEFINED",
            )
            pset = ifcopenshell.api.run(
                "pset.add_pset",
                file,
                product=port_entity,
                name="Pset_DistributionPortTypePipe",
            )
            ifcopenshell.api.run(
                "pset.edit_pset",
                file,
                pset=pset,
                properties={"OuterDiameter": port.od_mm / 1000},
            )
            ports.append(port_entity)
        file.create_entity(
            "IfcRelNests",
            GlobalId=ifcopenshell.guid.new(),
            RelatingObject=occurrence,
            RelatedObjects=ports,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))
    validate_library(output_path, records)
    for record in records:
        definition = record["definition"]
        vertices, triangles, port_count = record["shape_counts"]
        print(
            f"{definition.article} {definition.name}: {vertices} vrcholů, "
            f"{triangles} trojúhelníků, {port_count} porty"
        )
        for port, position, axis, section in zip(
            definition.ports,
            record["port_positions"],
            record["port_axes"],
            record["source_sections"],
        ):
            print(
                f"  {port.name}: xyz={np.round(position, 3).tolist()} mm, "
                f"osa={np.round(axis, 6).tolist()}, flow={port.flow}, OD={port.od_mm:g}; "
                f"zdrojový řez {section[0]} bodů, r={section[1]:.2f}–{section[2]:.2f} mm"
            )
    print(f"Validace OK: IFC4, 0 EXPRESS chyb, {len(records)} typů a výskytů")
    return output_path


def generate_catalogue_fitting(definition, mesh_path, output_path):
    """Zpětně kompatibilní jednopoložkový generátor pro testy."""
    return generate_catalogue_library([(definition, mesh_path)], output_path)
