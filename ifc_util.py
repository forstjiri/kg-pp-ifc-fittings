"""Společné IFC4 entity helpery pro zápis knihoven, nástroje a testy (jednotka mm)."""

import ifcopenshell
import ifcopenshell.api
import numpy as np


def point(file, xyz):
    return file.create_entity("IfcCartesianPoint", Coordinates=tuple(float(v) for v in xyz))


def direction(file, xyz):
    return file.create_entity("IfcDirection", DirectionRatios=tuple(float(v) for v in xyz))


def axis(file, location, axis_dir=None, ref=None):
    fields = {"Location": point(file, location)}
    if axis_dir is not None:
        fields["Axis"] = direction(file, axis_dir)
    if ref is not None:
        fields["RefDirection"] = direction(file, ref)
    return file.create_entity("IfcAxis2Placement3D", **fields)


def placement(file, location, axis_dir=None, ref=None, rel=None):
    fields = {"RelativePlacement": axis(file, location, axis_dir, ref)}
    if rel is not None:
        fields["PlacementRelTo"] = rel
    return file.create_entity("IfcLocalPlacement", **fields)


def new_file(name):
    """(file, project, context) — IFC4, mm, MODEL_VIEW s přesností 1e-5."""
    file = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcProject", name=name
    )
    ifcopenshell.api.run("unit.assign_unit", file)
    context = ifcopenshell.api.run(
        "context.add_context", file, context_type="Model", target_view="MODEL_VIEW"
    )
    context.Precision = 1e-5
    project.RepresentationContexts = [context]
    return file, project, context


def shape(file, context, items, rep_type="SweptSolid"):
    return file.create_entity(
        "IfcShapeRepresentation", ContextOfItems=context,
        RepresentationIdentifier="Body", RepresentationType=rep_type, Items=items,
    )


def product(file, context, name, family, items, place, rep_type="SweptSolid"):
    entity = ifcopenshell.api.run(
        "root.create_entity", file, ifc_class="IfcPipeFitting",
        predefined_type=family, name=name,
    )
    if place is not None:
        entity.ObjectPlacement = place
    entity.Representation = file.create_entity(
        "IfcProductDefinitionShape", Representations=[shape(file, context, items, rep_type)]
    )
    return entity


def ref_direction(vector):
    """Stabilní RefDirection pro vnější osu portu/placementu."""
    v = np.asarray(vector, float)
    ref = np.cross(v, (0, 0, 1)) if abs(v[2]) < 0.9 else np.array((1.0, 0.0, 0.0))
    norm = np.linalg.norm(ref)
    return ref / norm if norm > 1e-8 else np.array((1.0, 0.0, 0.0))


def property(file, name, value):
    return file.create_entity(
        "IfcPropertySingleValue", Name=name,
        NominalValue=file.create_entity("IfcText", str(value)),
    )


def pset(file, target, name, values):
    entity = file.create_entity(
        "IfcPropertySet", GlobalId=ifcopenshell.guid.new(), Name=name,
        HasProperties=[property(file, key, value) for key, value in values.items()],
    )
    target.HasPropertySets = tuple(target.HasPropertySets or ()) + (entity,)
    return entity
