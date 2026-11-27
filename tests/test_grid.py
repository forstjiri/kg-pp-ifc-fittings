"""Katalogové gridy: rozvržení, unikátní typy, porty na typech, profily trubek."""

from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.system
import numpy as np
import pytest

from grid import PIPE_LENGTH_MM, SIZES, build_grid, validate_grid


@pytest.fixture(scope="module")
def kg_grid(tmp_path_factory):
    path, info = build_grid("kg", tmp_path_factory.mktemp("grid") / "grid-kg.ifc")
    return path, info, validate_grid(path, info)


@pytest.fixture(scope="module")
def pp_grid(tmp_path_factory):
    path, info = build_grid("pp", tmp_path_factory.mktemp("grid") / "grid-pp.ifc")
    return path, info, validate_grid(path, info)


def _ports(entity):
    return ifcopenshell.util.system.get_ports(entity)


def test_kg_grid_covers_all_catalogue_fittings_and_three_pipe_sizes(kg_grid):
    _, info, (fittings, pipes, total) = kg_grid
    assert (fittings, pipes, total) == (36, 3, 39)
    assert {row[2] for row in info["layout"] if row[2].startswith("PIPE-")} == {
        "PIPE-110", "PIPE-125", "PIPE-160"}


def test_pp_grid_includes_dn90_and_ends_at_dn110(pp_grid):
    _, info, (fittings, pipes, total) = pp_grid
    assert (fittings, pipes, total) == (85, 6, 91)  # vč. Ostendorf HT 113410
    assert info["sizes"] == (32, 40, 50, 75, 90, 110)
    articles = {row[2] for row in info["layout"]}
    assert any("B90" in article for article in articles)  # M3-B90/…
    assert "113410" in articles  # HT odbočka 75/50 87°
    assert not any("B150" in article for article in articles)


def test_every_cell_has_its_own_type_and_matching_ports(kg_grid, pp_grid):
    for path, info, _ in (kg_grid, pp_grid):
        file = ifcopenshell.open(str(path))
        entities = {e.GlobalId: e for e in file.by_type("IfcObjectDefinition")}
        typed = {o.GlobalId for o in file.by_type("IfcPipeFitting") + file.by_type("IfcPipeSegment")
                 if o.IsTypedBy}
        for row in info["layout"]:
            fitting_type, occurrence, ports = row[5], row[6], row[7]
            assert fitting_type is not occurrence
            assert occurrence.GlobalId in typed, "výskyt nemá přiřazený typ"
            type_ports = _ports(entities[fitting_type.GlobalId])
            file_ports = [entities[p.GlobalId] for p in ports]
            assert len(type_ports) == len(file_ports) > 0
            assert {(p.Name, p.FlowDirection) for p in type_ports} == {
                (p.Name, p.FlowDirection) for p in file_ports}
            for type_port, occurrence_port in zip(type_ports, file_ports):
                a = np.asarray(type_port.ObjectPlacement.RelativePlacement.Location.Coordinates)
                b = np.asarray(occurrence_port.ObjectPlacement.RelativePlacement.Location.Coordinates)
                assert np.allclose(a, b, atol=1e-6)


def test_pipe_segments_have_hollow_profiles_and_end_ports(pp_grid):
    path, info, _ = pp_grid
    file = ifcopenshell.open(str(path))
    entities = {e.GlobalId: e for e in file.by_type("IfcObjectDefinition")}
    specs = {dn: (od, wall, t) for dn, (od, wall, t, _) in
             __import__("pp_generator").pp_pipe_specs().items()}
    for dn, pipe_type in info["pipe_types"].items():
        pipe_type = entities[pipe_type.GlobalId]
        material = ifcopenshell.util.element.get_material(pipe_type)
        assert material.is_a("IfcMaterialProfileSet")
        profile = material.MaterialProfiles[0].Profile
        assert profile.is_a("IfcCircleHollowProfileDef")
        assert profile.Radius == pytest.approx(specs[dn][0] / 2000)  # grid v metrech
        assert profile.WallThickness == pytest.approx(specs[dn][1] / 1000)
        assert len(_ports(pipe_type)) == 2
        assert not pipe_type.RepresentationMaps, "typ nesmí mít mapu, jinak Bonsai neumí táhnout"
        sample = next(row[6] for row in info["layout"] if row[5].GlobalId == pipe_type.GlobalId)
        sample = entities[sample.GlobalId]
        solid = sample.Representation.Representations[0].Items[0]
        assert solid.is_a("IfcExtrudedAreaSolid")
        assert solid.Depth == pytest.approx(PIPE_LENGTH_MM / 1000)
    assert len(file.by_type("IfcPipeSegment")) == len(SIZES["pp"])


def test_pp_branch_socket_protrudes_and_port_sits_at_its_mouth(pp_grid):
    """Regrese: hrdlo odbočky nesmí být obrácené dovnitř hlavního těla."""
    import ifcopenshell.geom

    path, info, _ = pp_grid
    file = ifcopenshell.open(str(path))
    settings = ifcopenshell.geom.settings()
    for article in ("M3-EA70/50/87", "113410"):  # Pipelife i Ostendorf HT
        occurrence = file.by_id(next(row[6] for row in info["layout"]
                                     if row[2] == article).id())
        vertices = np.asarray(ifcopenshell.geom.create_shape(
            settings, occurrence).geometry.verts).reshape(-1, 3)
        assert (vertices[:, 0].max() - vertices[:, 0].min()) * 1000 > 120, article
        port = next(p for p in _ports(occurrence) if p.Name == "SOCKET BRANCH")
        local = (ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)[:3, 3]
                 - ifcopenshell.util.placement.get_local_placement(
                     occurrence.ObjectPlacement)[:3, 3])
        assert local[0] * 1000 > 60, article


def test_grid_cells_do_not_overlap(kg_grid, pp_grid):
    for _, info, _ in (kg_grid, pp_grid):
        cell_w, cell_h = info["cell"]
        for _, column, article, _, bbox, *_ in info["layout"]:
            x0, y0, _ = bbox[0]
            x1, y1, _ = bbox[1]
            assert 0 < x1 - x0 <= cell_w + 1e-6, article
            assert 0 < y1 - y0 <= max(cell_h, PIPE_LENGTH_MM) + 1e-6, article


def test_pipe_type_creates_editable_extrusion_and_connects(kg_grid, tmp_path):
    """Bez Blenderu: stejná cesta, jakou Bonsai použije při tažení sítě."""
    import ifcopenshell.api
    import ifcopenshell.util.representation
    import ifcopenshell.validate

    path, info, _ = kg_grid
    file = ifcopenshell.open(str(path))
    pipe_type = next(t for t in file.by_type("IfcPipeSegmentType") if t.Name.endswith("DN110"))
    profile = ifcopenshell.util.element.get_material(pipe_type).MaterialProfiles[0].Profile
    context = ifcopenshell.util.representation.get_context(file, "Model", "Body", "MODEL_VIEW")
    assert context is not None

    segment = ifcopenshell.api.run("root.create_entity", file, ifc_class="IfcPipeSegment",
                                   predefined_type="RIGIDSEGMENT", name="Nový tah")
    ifcopenshell.api.run("type.assign_type", file, related_objects=[segment], relating_type=pipe_type)
    from ifc_util import placement
    segment.ObjectPlacement = placement(file, (0, 0, 0))
    representation = ifcopenshell.api.run(
        "geometry.add_profile_representation", file, context=context, profile=profile, depth=0.5)
    segment.Representation = file.create_entity(
        "IfcProductDefinitionShape", Representations=[representation])
    extrusion = representation.Items[0]
    assert extrusion.is_a("IfcExtrudedAreaSolid")
    assert extrusion.Depth == pytest.approx(0.5)
    assert extrusion.SweptArea.is_a("IfcCircleHollowProfileDef")

    from ifc_util import placement, ref_direction

    fitting = file.by_type("IfcPipeFitting")[0]
    fitting_port = _ports(fitting)[0]
    matrix = ifcopenshell.util.placement.get_local_placement(fitting_port.ObjectPlacement)
    position, axis = matrix[:3, 3], matrix[:3, 2]
    new_port = ifcopenshell.api.run("system.add_port", file, element=segment)
    new_port.ObjectPlacement = placement(file, position, -axis, ref_direction(-axis))
    ifcopenshell.api.run("system.connect_port", file, port1=fitting_port,
                         port2=new_port, direction="SOURCE")
    output = tmp_path / "connected.ifc"
    file.write(str(output))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(file, logger, express_rules=True)
    assert not [s for s in logger.statements if s.get("level") == "error"]

    saved = ifcopenshell.open(str(output))
    relation = next(r for r in saved.by_type("IfcRelConnectsPorts")
                    if r.RelatingPort.GlobalId == fitting_port.GlobalId)
    a = ifcopenshell.util.placement.get_local_placement(relation.RelatingPort.ObjectPlacement)
    b = ifcopenshell.util.placement.get_local_placement(relation.RelatedPort.ObjectPlacement)
    assert np.linalg.norm(a[:3, 3] - b[:3, 3]) < 1e-6
    assert np.dot(a[:3, 2], b[:3, 2]) < -0.999999


def _pipe_type_by_dn(file, dn):
    for pipe_type in file.by_type("IfcPipeSegmentType"):
        props = ifcopenshell.util.element.get_psets(pipe_type)["Pset_Tvarovka"]
        if float(props["NominalDiameter"]) == dn:
            return pipe_type
    raise AssertionError(f"v gridu není trubka DN{dn}")


def _fitting_type(file, family, **props):
    for fitting_type in file.by_type("IfcPipeFittingType"):
        if fitting_type.PredefinedType != family:
            continue
        values = ifcopenshell.util.element.get_psets(fitting_type)["Pset_Tvarovka"]
        if all(float(values[key]) == pytest.approx(value, abs=0.05)
               for key, value in props.items()):
            return fitting_type
    raise AssertionError(f"v gridu není typ {family} {props}")


def _port_od_mm(port):
    return ifcopenshell.util.element.get_psets(
        port)["Pset_DistributionPortTypePipe"]["OuterDiameter"] * 1000


def _add_connected_segment(file, socket, pipe_type):
    """Segment z profilu typu, prodloužený a připojený k hnízdu (cesta Bonsai/IFC API)."""
    import ifcopenshell.api
    import ifcopenshell.util.representation
    from ifc_util import placement, ref_direction

    profile = ifcopenshell.util.element.get_material(pipe_type).MaterialProfiles[0].Profile
    context = ifcopenshell.util.representation.get_context(file, "Model", "Body", "MODEL_VIEW")
    segment = ifcopenshell.api.run("root.create_entity", file, ifc_class="IfcPipeSegment",
                                   predefined_type="RIGIDSEGMENT", name="Nový tah")
    ifcopenshell.api.run("type.assign_type", file, related_objects=[segment], relating_type=pipe_type)
    matrix = ifcopenshell.util.placement.get_local_placement(socket.ObjectPlacement)
    position, axis = matrix[:3, 3], matrix[:3, 2]
    outward = -axis
    segment.ObjectPlacement = placement(file, position, outward, ref_direction(outward))
    representation = ifcopenshell.api.run(
        "geometry.add_profile_representation", file, context=context, profile=profile, depth=0.5)
    segment.Representation = file.create_entity(
        "IfcProductDefinitionShape", Representations=[representation])
    port = ifcopenshell.api.run("system.add_port", file, element=segment)
    port.ObjectPlacement = placement(file, position, outward, ref_direction(outward))
    ifcopenshell.api.run("system.connect_port", file, port1=socket, port2=port, direction="SOURCE")
    assert representation.Items[0].Depth == pytest.approx(0.5)
    return segment, port


def _assert_connected(file, pairs):
    for socket, port in pairs:
        relation = next((r for r in file.by_type("IfcRelConnectsPorts")
                         if {r.RelatingPort.GlobalId, r.RelatedPort.GlobalId} ==
                         {socket.GlobalId, port.GlobalId}), None)
        assert relation is not None
        a = ifcopenshell.util.placement.get_local_placement(relation.RelatingPort.ObjectPlacement)
        b = ifcopenshell.util.placement.get_local_placement(relation.RelatedPort.ObjectPlacement)
        assert np.linalg.norm(a[:3, 3] - b[:3, 3]) < 1e-6
        assert np.dot(a[:3, 2], b[:3, 2]) < -0.999999


def test_pp_dn90_elbow_and_pipe_connect_after_reopen(pp_grid, tmp_path):
    """PP 90 (mimo standardní knihovnu) musí být v gridu plně použitelný."""
    import ifcopenshell.validate

    path, _, _ = pp_grid
    file = ifcopenshell.open(str(path))
    bend = _fitting_type(file, "BEND", NominalDiameter=91.2)  # OD DN90
    socket = next(p for p in _ports(bend) if p.Name == "SOCKET")
    _, port = _add_connected_segment(file, socket, _pipe_type_by_dn(file, 90))
    output = tmp_path / "pp90-connected.ifc"
    file.write(str(output))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(file, logger, express_rules=True)
    assert not [s for s in logger.statements if s.get("level") == "error"]
    saved = ifcopenshell.open(str(output))
    _assert_connected(saved, [(saved.by_id(socket.id()), saved.by_id(port.id()))])


def test_junction_and_unequal_reducer_connect_correct_ends(pp_grid):
    """Odbočka má tři porty, redukce velký/malý konec; oba se dají napojit."""
    path, _, _ = pp_grid
    file = ifcopenshell.open(str(path))
    junction = next(t for t in file.by_type("IfcPipeFittingType")
                    if t.PredefinedType == "JUNCTION"
                    and float(ifcopenshell.util.element.get_psets(t)["Pset_Tvarovka"]["BranchOD"])
                    < float(ifcopenshell.util.element.get_psets(t)["Pset_Tvarovka"]["NominalDiameter"]))
    ods = {32: 33.0, 40: 41.1, 50: 51.0, 75: 76.1, 90: 91.2, 110: 111.3}
    props = ifcopenshell.util.element.get_psets(junction)["Pset_Tvarovka"]
    main_od, branch_od = float(props["NominalDiameter"]), float(props["BranchOD"])
    ports = {p.Name: p for p in _ports(junction)}
    assert set(ports) == {"SPIGOT", "SOCKET", "SOCKET BRANCH"}
    assert _port_od_mm(ports["SPIGOT"]) == pytest.approx(main_od, abs=0.05)
    assert _port_od_mm(ports["SOCKET"]) > _port_od_mm(ports["SOCKET BRANCH"])
    main_dn = next(dn for dn, od in ods.items() if od == pytest.approx(main_od, abs=0.05))
    branch_dn = next(dn for dn, od in ods.items() if od == pytest.approx(branch_od, abs=0.05))
    assert main_dn > branch_dn
    main_type = _pipe_type_by_dn(file, main_dn)
    pairs = []
    for name, pipe_type in (("SPIGOT", main_type), ("SOCKET", main_type),
                            ("SOCKET BRANCH", _pipe_type_by_dn(file, branch_dn))):
        pairs.append((ports[name], _add_connected_segment(file, ports[name], pipe_type)[1]))
    assert len(file.by_type("IfcRelConnectsPorts")) == 3

    reducer = _fitting_type(file, "TRANSITION")
    rp = _ports(reducer)
    assert len(rp) == 2
    large, small = (rp if _port_od_mm(rp[0]) > _port_od_mm(rp[1]) else rp[::-1])
    socket_ods = {dn: float(ifcopenshell.util.element.get_psets(t)["Pset_Tvarovka"]["SocketOuterDiameter"])
                  for dn, t in ((dn, _pipe_type_by_dn(file, dn)) for dn in (32, 40, 50, 75, 90, 110))}
    large_dn = next(dn for dn, od in socket_ods.items() if od == pytest.approx(_port_od_mm(large), abs=0.05))
    small_dn = next(dn for dn, od in socket_ods.items() if od == pytest.approx(_port_od_mm(small), abs=0.05))
    assert large_dn > small_dn
    large_y = large.ObjectPlacement.RelativePlacement.Location.Coordinates[1]
    small_y = small.ObjectPlacement.RelativePlacement.Location.Coordinates[1]
    assert large_y < small_y  # velké hnízdo je u počátku, malé na konci redukce
    reducer_pairs = [(port, _add_connected_segment(file, port, _pipe_type_by_dn(file, dn))[1])
                     for port, dn in ((large, large_dn), (small, small_dn))]
    _assert_connected(file, pairs + reducer_pairs)


def test_missing_sized_pp_rows_are_documented(tmp_path):
    missing = Path(__file__).resolve().parents[1] / "missing.md"
    text = missing.read_text()
    assert "DN20" in text and "DN25" in text
    assert "data/pipelife_master3plus.json" in text
