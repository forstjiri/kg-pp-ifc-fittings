"""Zápis a validace katalogových IFC knihoven tvarovek (obě normy)."""
from pathlib import Path
import ifcopenshell, ifcopenshell.api, ifcopenshell.geom
import ifcopenshell.util.element, ifcopenshell.util.placement, ifcopenshell.validate
import numpy as np
from ifc_util import axis, new_file, placement, point, pset, ref_direction, shape
from swept_geometrie import SweptBody, Taper, lathes_to_ifc, swept_bounds


def _check(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate_library(path, records, positions=None):
    """EXPRESS validace + kontrola typů, výskytů, těl, portů a obálky."""
    file = ifcopenshell.open(str(path))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(file, logger, express_rules=True)
    errors = [s for s in logger.statements if s.get("level") == "error"]
    _check(not errors, f"IFC EXPRESS validation errors: {errors[:3]}")
    types, occurrences = file.by_type("IfcPipeFittingType"), file.by_type("IfcPipeFitting")
    libraries = file.by_type("IfcProjectLibrary")
    _check(file.schema == "IFC4" and len(types) == len(records)
           and len(occurrences) == len(records) and len(libraries) == 1,
           "počet IFC typů/výskytů neodpovídá definicím")
    declarations = file.by_type("IfcRelDeclares")
    _check(any(libraries[0] in rel.RelatedDefinitions for rel in declarations),
           "IfcProjectLibrary není deklarovaná v projektu")
    _check(all(any(t in rel.RelatedDefinitions for rel in declarations) for t in types),
           "typ tvarovky není deklarovaný v knihovně")
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    positions = positions if positions is not None else [
        (index * 1000, 0, 0) for index in range(len(records))]
    for index, (record, fitting_type, occurrence) in enumerate(zip(records, types, occurrences)):
        definition = record["definition"]
        _check(fitting_type.Name == definition.name, f"typ v IFC neodpovídá: {definition.name}")
        items = fitting_type.RepresentationMaps[0].MappedRepresentation.Items
        _check(len(items) == len(record["swept"].lathes) and all(
            item.is_a("IfcRevolvedAreaSolid") or item.is_a("IfcExtrudedAreaSolidTapered")
            for item in items), f"IFC neobsahuje tažená tělesa: {definition.article}")
        geometric = ifcopenshell.geom.create_shape(settings, occurrence).geometry
        vertices = np.asarray(geometric.verts).reshape(-1, 3)
        faces = len(geometric.faces) // 3
        expected = record["vertices_mm"] + np.asarray(positions[index], float)
        _check(len(vertices) and faces, f"geometry kernel nevytvořil tvar: {definition.article}")
        _check(np.allclose(
            np.r_[vertices.min(axis=0), vertices.max(axis=0)],
            np.r_[expected.min(axis=0), expected.max(axis=0)], atol=0.5),
            f"IFC obálka se liší od zdroje: {definition.article}")
        ports = [p for rel in occurrence.IsNestedBy for p in rel.RelatedObjects]
        _check(len(ports) == len(definition.ports), f"nesprávný počet portů: {definition.article}")
        for port, position, axis_, port_def in zip(
            ports, record["port_positions"], record["port_axes"], definition.ports):
            matrix = ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)
            _check(np.allclose(matrix[:3, 3], position + np.asarray(positions[index], float), atol=5e-7),
                   f"poloha portu nesouhlasí: {port.Name}")
            _check(np.allclose(matrix[:3, 2], axis_, atol=5e-7),
                   f"osa portu nesouhlasí: {port.Name}")
            _check(port.FlowDirection == port_def.flow, f"směr toku portu nesouhlasí: {port.Name}")
            od = ifcopenshell.util.element.get_psets(port)["Pset_DistributionPortTypePipe"]["OuterDiameter"] * 1000
            _check(abs(od - port_def.od_mm) <= 0.05, f"OD portu nesouhlasí: {port.Name}")
        record["shape_counts"] = (len(vertices), faces, len(ports))


def _prepare_record(definition, body):
    if not isinstance(body, SweptBody):
        raise TypeError("knihovna přijímá jen SweptSolid (SweptBody)")
    low, high = swept_bounds(body)
    port_axes = np.asarray([p.axis for p in definition.ports], dtype=float)
    port_axes /= np.linalg.norm(port_axes, axis=1, keepdims=True)
    return {
        "definition": definition,
        "vertices_mm": np.vstack((low, high)),
        "swept": body,
        "port_positions": np.asarray([p.position_mm for p in definition.ports], dtype=float),
        "port_axes": port_axes,
        "source_sections": [("parametric swept solid", 0, 0)] * len(definition.ports),
    }


class LibraryBuilder:
    """Společný zápis IFC4 knihovny a katalogového gridu."""

    def __init__(self, name):
        self.file, self.project, self.context = new_file(f"Tvarovky {name}")
        self.guid = ifcopenshell.guid.new
        self.name = name
        self.library = self.file.create_entity(
            "IfcProjectLibrary", GlobalId=self.guid(), Name=f"{name} | katalog")
        self.material = self.file.create_entity("IfcMaterial", Name=name)
        self.types = []

    def declare(self, standard):
        self.library.Name = f"{self.name} | {standard}"
        self.file.create_entity("IfcRelDeclares", GlobalId=self.guid(),
                                RelatingContext=self.project, RelatedDefinitions=[self.library])
        self.file.create_entity("IfcRelDeclares", GlobalId=self.guid(),
                                RelatingContext=self.library, RelatedDefinitions=self.types)
        self.file.create_entity("IfcRelAssociatesMaterial", GlobalId=self.guid(),
                                RelatedObjects=self.types, RelatingMaterial=self.material)

    def port(self, port_def, position, axis_, parent=None, name=None):
        """IfcDistributionPort s Psetem; `parent` = relativní umístění výskytu."""
        axis_ = np.asarray(axis_, float)
        axis_ /= np.linalg.norm(axis_)
        entity = self.file.create_entity(
            "IfcDistributionPort", GlobalId=self.guid(), Name=name or port_def.name,
            ObjectPlacement=placement(self.file, position, axis_, ref_direction(axis_), rel=parent),
            FlowDirection=port_def.flow, PredefinedType="PIPE", SystemType="NOTDEFINED")
        pset_entity = ifcopenshell.api.run("pset.add_pset", self.file, product=entity,
                                           name="Pset_DistributionPortTypePipe")
        ifcopenshell.api.run("pset.edit_pset", self.file, pset=pset_entity,
                             properties={"OuterDiameter": port_def.od_mm / 1000})
        return entity

    def nest(self, parent, ports):
        if ports:
            self.file.create_entity("IfcRelNests", GlobalId=self.guid(),
                                    RelatingObject=parent, RelatedObjects=ports)

    def fitting_type(self, definition, record, type_ports=False):
        body = record["swept"]
        rep_type = "SolidModel" if any(isinstance(l, Taper) for l in body.lathes) else "SweptSolid"
        rep_map = self.file.create_entity(
            "IfcRepresentationMap", MappingOrigin=axis(self.file, (0, 0, 0)),
            MappedRepresentation=shape(self.file, self.context,
                                       lathes_to_ifc(self.file, body), rep_type))
        attrs = {"ElementType": definition.article} if definition.family == "USERDEFINED" else {}
        fitting_type = self.file.create_entity(
            "IfcPipeFittingType", GlobalId=self.guid(), Name=definition.name,
            PredefinedType=definition.family, RepresentationMaps=[rep_map], **attrs)
        self.types.append(fitting_type)
        properties = {
            "Standard": definition.standard, "CatalogArticle": definition.article,
            "NominalDiameter": definition.od_mm, "BendAngle": definition.angle_deg,
            "Length": definition.length_mm, "Z1": definition.z1_mm, "Z2": definition.z2_mm,
        }
        if definition.branch_od_mm is not None:
            properties["BranchOD"] = definition.branch_od_mm
            if definition.z3_mm is not None:
                properties["Z3"] = definition.z3_mm
        for key, value in (("GeometryStatus", getattr(definition, "geometry_status", None)),
                           ("LegacyArticle", getattr(definition, "legacy_article", None))):
            if value:
                properties[key] = value
        pset(self.file, fitting_type, "Pset_Tvarovka", properties)
        for index, (port, position, axis_) in enumerate(zip(
            definition.ports, record["port_positions"], record["port_axes"]), start=1):
            pset(self.file, fitting_type, f"Pset_TvarovkaPort{index}", {
                "Name": port.name,
                "Position": ", ".join(f"{v:.3f}" for v in position),
                "Axis": ", ".join(f"{v:.6f}" for v in axis_),
                "FlowDirection": port.flow, "OuterDiameter": port.od_mm,
                "EndType": port.end_type,
                "InsertionDepth": "" if port.insertion_mm is None else port.insertion_mm,
                "TakeOut": "" if port.take_out_mm is None else port.take_out_mm,
            })
        if type_ports:
            self.nest(fitting_type, [
                self.port(port, position, axis_) for port, position, axis_ in zip(
                    definition.ports, record["port_positions"], record["port_axes"])])
        return fitting_type, rep_map

    def fitting_occurrence(self, definition, fitting_type, rep_map, record, position):
        occurrence = ifcopenshell.api.run(
            "root.create_entity", self.file, ifc_class="IfcPipeFitting",
            predefined_type=definition.family, name=definition.name)
        if definition.family == "USERDEFINED":
            occurrence.ObjectType = definition.article
        occurrence.ObjectPlacement = placement(self.file, position)
        self.file.create_entity("IfcRelDefinesByType", GlobalId=self.guid(),
                                RelatedObjects=[occurrence], RelatingType=fitting_type)
        mapped = self.file.create_entity(
            "IfcMappedItem", MappingSource=rep_map,
            MappingTarget=self.file.create_entity(
                "IfcCartesianTransformationOperator3D",
                LocalOrigin=point(self.file, (0, 0, 0)), Scale=1.0))
        occurrence.Representation = self.file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape(self.file, self.context, [mapped], "MappedRepresentation")])
        ports = [self.port(port, pos, axis_, parent=occurrence.ObjectPlacement) for port, pos, axis_ in
                 zip(definition.ports, record["port_positions"], record["port_axes"])]
        self.nest(occurrence, ports)
        return occurrence, ports

    def pipe_type(self, dn, spec, name, standard, length_mm):
        """IfcPipeSegmentType s dutým profilem. Bez RepresentationMaps, aby Bonsai
        z typu vytvořil novou extruzi, kterou lze protáhnout po trase."""
        od, wall, t, collar = map(float, spec)
        file = self.file
        profile = file.create_entity(
            "IfcCircleHollowProfileDef", ProfileName=name, ProfileType="AREA",
            Radius=od / 2, WallThickness=wall)
        pipe_type = file.create_entity(
            "IfcPipeSegmentType", GlobalId=self.guid(), Name=name,
            PredefinedType="RIGIDSEGMENT")
        self.types.append(pipe_type)
        pset(file, pipe_type, "Pset_Tvarovka", {
            "Standard": standard, "NominalDiameter": dn, "OuterDiameter": od,
            "WallThickness": wall, "SocketDepth": t, "SocketOuterDiameter": collar})
        association = ifcopenshell.api.run("material.assign_material", file,
                                           products=[pipe_type], type="IfcMaterialProfileSet")
        ifcopenshell.api.run("material.add_profile", file,
                             profile_set=association.RelatingMaterial,
                             material=self.material, profile=profile)
        self.nest(pipe_type, [
            self.port(_pipe_port(label, position, axis_, od, collar, t), position, axis_)
            for label, position, axis_ in (
                ("SPIGOT", (0, t, 0), (0, -1, 0)),
                ("SOCKET", (0, length_mm, 0), (0, 1, 0)))])
        return pipe_type, profile

    def pipe_occurrence(self, pipe_type, profile, dn, spec, position, length_mm):
        file = self.file
        od, wall, t, collar = map(float, spec)
        occurrence = ifcopenshell.api.run(
            "root.create_entity", file, ifc_class="IfcPipeSegment",
            predefined_type="RIGIDSEGMENT", name=f"Trubka DN{dn}")
        occurrence.ObjectPlacement = placement(file, position)
        file.create_entity("IfcRelDefinesByType", GlobalId=self.guid(),
                           RelatedObjects=[occurrence], RelatingType=pipe_type)
        solid = file.create_entity(
            "IfcExtrudedAreaSolid", SweptArea=profile,
            Position=axis(file, (0, 0, 0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
            ExtrudedDirection=file.create_entity(
                "IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)), Depth=float(length_mm))
        occurrence.Representation = file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape(file, self.context, [solid], "SweptSolid")])
        ports = [self.port(_pipe_port(name, pos, axis_, od, collar, t), pos, axis_,
                           parent=occurrence.ObjectPlacement)
                 for name, pos, axis_ in (
                     ("SPIGOT", (0, t, 0), (0, -1, 0)),
                     ("SOCKET", (0, length_mm, 0), (0, 1, 0)))]
        self.nest(occurrence, ports)
        return occurrence, ports

    def write(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file.write(str(path))
        return path


def _pipe_port(name, position, axis_, od, collar_od, t):
    """Port trubky; SPIGOT má OD trubky, SOCKET průměr hrdla."""
    from definice import Port
    return Port(name, position, axis_, "SOURCE" if name == "SPIGOT" else "SINK",
                od if name == "SPIGOT" else collar_od, end_type=name,
                insertion_mm=t)


def generate_catalogue_library(items, output_path, name="PVC-U KG"):
    """IFC4 Project Library z položek (definice, SweptBody)."""
    records = [_prepare_record(definition, body) for definition, body in items]
    if not records:
        raise ValueError("knihovna nemůže být prázdná")
    standards = {record["definition"].standard for record in records}
    if len(standards) != 1:
        raise ValueError("jedna IFC knihovna smí obsahovat jen jednu normu")
    library = LibraryBuilder(name)
    types = [library.fitting_type(record["definition"], record) for record in records]
    library.declare(next(iter(standards)))
    ports_total = 0
    for index, (record, (fitting_type, rep_map)) in enumerate(zip(records, types)):
        _, ports = library.fitting_occurrence(
            record["definition"], fitting_type, rep_map, record, (index * 1000, 0, 0))
        ports_total += len(ports)
    output = library.write(output_path)
    validate_library(output, records)
    print(f"Validace OK: IFC4, 0 EXPRESS chyb, {len(records)} typů, {ports_total} portů")
    return output


def generate_catalogue_fitting(definition, mesh_path, output_path):
    """Zpětně kompatibilní jednopoložkový generátor pro testy."""
    return generate_catalogue_library([(definition, mesh_path)], output_path)
