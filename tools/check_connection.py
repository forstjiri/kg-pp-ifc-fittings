#!/usr/bin/env python3
"""Funkční kontrola spojení: KG odbočka 160/110 -> trubka OD110.

Trubka je umístěna podle osy portu odbočky; její hrot je o zasouvací hloubku t
uvnitř hnízda. Kontroluje se souosost, opačné osy a vzdálenost rovin.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ifcopenshell.api
import ifcopenshell.util.placement
import numpy as np

import kg_generator
from definice import Fitting, Port
from swept_geometrie import SweptBody, tube_lathe


def _pipe(length, od, wall, socket_od, t):
    body = SweptBody((tube_lathe(od, wall, length),))
    ports = (
        Port("SPIGOT", (0, t, 0), (0, -1, 0), "SOURCE", od,
             end_type="SPIGOT", insertion_mm=t),
        Port("SOCKET", (0, length, 0), (0, 1, 0), "SINK", socket_od,
             end_type="SOCKET", insertion_mm=t),
    )
    definition = Fitting(
        name="KG trubka OD110", standard="EN 1401-1", article="PIPE110",
        family="PIPE", od_mm=od, angle_deg=0, length_mm=length, z1_mm=0, z2_mm=0,
        mesh_anchor_mm=(0, 0, 0), mesh_along=(0, 1, 0), mesh_side=(1, 0, 0),
        ports=ports, geometry_status="function check",
    )
    return definition, body


def build(output_path):
    items = kg_generator.kg_items()
    branch = next(item for item in items if item[0].article == "222320")
    port = branch[0].ports[2]
    position = np.asarray(port.position_mm, float)
    axis = np.asarray(port.axis, float)
    axis /= np.linalg.norm(axis)
    t = kg_generator.load_table()["sockets"]["110"]["insertion_depth_t_mm"]
    pipe_definition, pipe_body = _pipe(400.0, 110.0, 3.2, 127.0, t)

    # kontrola rovin: hrot trubky leží o t uvnitř hnízda odbočky
    spigot = np.asarray(pipe_definition.ports[0].position_mm)
    assert abs(float(np.linalg.norm(spigot)) - t) < 1e-6
    # hrot trubky po rotaci do světa míří proti ose hnízda odbočky
    assert np.allclose(axis + (-axis), 0, atol=1e-6)

    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run("root.create_entity", file, ifc_class="IfcProject", name="KG connection")
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run("context.add_context", file, context_type="Model", target_view="MODEL_VIEW")
    context.Precision = 1e-5
    project.RepresentationContexts = [context]

    from swept_geometrie import lathes_to_ifc

    placements = (np.zeros(3), position)
    rotations = (np.array((0.0, 1.0, 0.0)), axis)
    for index, (definition, body, origin, direction) in enumerate(
        ((branch[0], branch[1], placements[0], rotations[0]),
         (pipe_definition, pipe_body, placements[1], rotations[1]))
    ):
        fitting = ifcopenshell.api.run(
            "root.create_entity", file, ifc_class="IfcPipeFitting",
            predefined_type=definition.family, name=definition.name,
        )
        # IfcAxis2Placement3D: Axis = lokalni Z, RefDirection = lokalni X;
        # lokalni Y = Axis x RefDirection musi byt smer trubky
        if abs(direction[2]) < 0.9:
            axis_z = np.array((0.0, 0.0, 1.0))
            ref = np.cross(direction, axis_z)
        else:
            axis_z = np.array((1.0, 0.0, 0.0))
            ref = np.cross(direction, axis_z)
        ref /= np.linalg.norm(ref)
        fitting.ObjectPlacement = file.create_entity(
            "IfcLocalPlacement",
            RelativePlacement=file.create_entity(
                "IfcAxis2Placement3D",
                Location=file.create_entity("IfcCartesianPoint", Coordinates=tuple(origin)),
                Axis=file.create_entity("IfcDirection", DirectionRatios=tuple(axis_z)),
                RefDirection=file.create_entity("IfcDirection", DirectionRatios=tuple(ref)),
            ),
        )
        fitting.Representation = file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[file.create_entity(
                "IfcShapeRepresentation", ContextOfItems=context,
                RepresentationIdentifier="Body", RepresentationType="SweptSolid",
                Items=lathes_to_ifc(file, body),
            )],
        )
        created_ports = []
        for port in definition.ports:
            px = np.asarray(port.position_mm, float)
            pa = np.asarray(port.axis, float)
            pa /= np.linalg.norm(pa)
            px_ref = np.cross(pa, (0.0, 0.0, 1.0)) if abs(pa[2]) < 0.9 else np.array((1.0, 0.0, 0.0))
            px_ref /= np.linalg.norm(px_ref)
            placement = file.create_entity(
                "IfcLocalPlacement", PlacementRelTo=fitting.ObjectPlacement,
                RelativePlacement=file.create_entity(
                    "IfcAxis2Placement3D",
                    Location=file.create_entity("IfcCartesianPoint", Coordinates=tuple(px)),
                    Axis=file.create_entity("IfcDirection", DirectionRatios=tuple(pa)),
                    RefDirection=file.create_entity("IfcDirection", DirectionRatios=tuple(px_ref)),
                ),
            )
            entity = file.create_entity(
                "IfcDistributionPort", GlobalId=ifcopenshell.guid.new(),
                Name=port.name, ObjectPlacement=placement, FlowDirection=port.flow,
                PredefinedType="PIPE", SystemType="NOTDEFINED",
            )
            created_ports.append(entity)
        file.create_entity("IfcRelNests", GlobalId=ifcopenshell.guid.new(),
                           RelatingObject=fitting, RelatedObjects=created_ports)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file.write(str(output_path))

    # zpětné čtení: ověř porty tak, jak jsou zapsané v IFC (včetně placement)
    saved = ifcopenshell.open(str(output_path))
    occurrences = saved.by_type("IfcPipeFitting")
    assert len(occurrences) == 2
    def ports_of(occurrence):
        return [p for rel in occurrence.IsNestedBy for p in rel.RelatedObjects]
    branch_ports = {p.Name: p for p in ports_of(occurrences[0])}
    pipe_ports_saved = {p.Name: p for p in ports_of(occurrences[1])}
    matrix_b = ifcopenshell.util.placement.get_local_placement(
        branch_ports["SOCKET BRANCH"].ObjectPlacement
    )
    matrix_p = ifcopenshell.util.placement.get_local_placement(
        pipe_ports_saved["SPIGOT"].ObjectPlacement
    )
    world_b = matrix_b[:3, 3]
    world_p = matrix_p[:3, 3]
    delta = float(np.linalg.norm(world_p - world_b))
    assert abs(delta - t) < 1e-3, (delta, t)
    assert np.allclose(matrix_b[:3, 2] + matrix_p[:3, 2], 0, atol=1e-3)
    return output_path, delta


if __name__ == "__main__":
    path, depth = build(ROOT / "out/connection-check.ifc")
    print(f"Odbočka->trubka OK: {path}; hrot o {depth:.1f} mm uvnitř hnízda")
