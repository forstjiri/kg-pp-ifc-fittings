"""Katalogové IFC gridy pro Bonsai: sloupec = rozměr, řádek = varianta.

Každá tvarovka má vlastní typ, porty na typu i na výskytu; pro každý rozměr
je přidán IfcPipeSegmentType s dutým profilem a ukázkovou extruzí.
"""
import inspect
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.validate

from generator import LibraryBuilder, _prepare_record

SIZES = {"kg": (110, 125, 160), "pp": (32, 40, 50, 75, 90, 110)}
PIPE_LENGTH_MM = 1000.0
MARGIN_MM = 300.0
STANDARDS = {"kg": ("KG (EN 1401-1)", "EN 1401-1"),
             "pp": ("PP MASTER 3 PLUS", "EN 1451-1")}


def _category(definition):
    if definition.family == "BEND":
        return "BEND", (definition.angle_deg,)
    if definition.family == "JUNCTION":
        return "JUNCTION", (definition.angle_deg, definition.branch_dn_mm or 0)
    if definition.family == "TRANSITION":
        return "TRANSITION", (definition.branch_dn_mm or 0,)
    if len(definition.ports) == 1:
        return "CAP", ()
    return "CLEANOUT", ()


def _row_key(definition):
    order = {"BEND": 1, "JUNCTION": 2, "TRANSITION": 3, "CLEANOUT": 4, "CAP": 5}
    category, detail = _category(definition)
    return (order[category], *detail)


def _row_label(key):
    order, *detail = key
    if order == 1:
        return f"Koleno {detail[0]:g}°"
    if order == 2:
        return f"Odbočka {detail[0]:g}°/DN{detail[1]:g}"
    if order == 3:
        return f"Redukce na DN{detail[0]:g}"
    return "Čisticí kus" if order == 4 else "Zátka"


def to_metres(file):
    """Gridy jsou pro Bonsai v metrech: přeškáluje délky a změní jednotku.

    Katalogové knihovny zůstávají v mm. Bonsai 5.3 totiž při vkládání z typu
    počítá kurzor v metrech; s milimetrovou jednotkou by porty nových segmentů
    dopadly 1000× mimo model.
    """
    for entity in file:
        if entity.is_a("IfcCartesianPoint"):
            entity.Coordinates = tuple(float(v) / 1000 for v in entity.Coordinates)
        elif entity.is_a("IfcCircleHollowProfileDef"):
            entity.Radius = float(entity.Radius) / 1000
            entity.WallThickness = float(entity.WallThickness) / 1000
        elif entity.is_a("IfcCircleProfileDef"):
            entity.Radius = float(entity.Radius) / 1000
        elif entity.is_a("IfcExtrudedAreaSolid") or entity.is_a("IfcExtrudedAreaSolidTapered"):
            entity.Depth = float(entity.Depth) / 1000
    assignment = file.by_type("IfcUnitAssignment")[0]
    units = [unit for unit in assignment.Units
             if not (unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT")]
    units.append(file.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE"))
    assignment.Units = units


def build_grid(standard, path=None, items=None, pipe_specs=None):
    """Vytvořit grid a vrátit (cesta, rozvržení pro testy)."""
    name, code = STANDARDS[standard]
    sizes = SIZES[standard]
    if items is None:
        module = __import__(f"{standard}_generator", fromlist=["items"])
        factory = module.__dict__[f"{standard}_items"]
        kwargs = {"sizes": sizes} if "sizes" in inspect.signature(factory).parameters else {}
        items = factory(**kwargs)
    if pipe_specs is None:
        module = __import__(f"{standard}_generator", fromlist=["pipe_specs"])
        pipe_specs = module.__dict__[f"{standard}_pipe_specs"]()
    records = [(item, _prepare_record(*item)) for item in items
               if int(item[0].dn_mm) in sizes]
    groups = {}
    for item, record in records:
        definition = item[0]
        key = _row_key(definition)
        groups.setdefault(key, {})[int(definition.dn_mm)] = (item, record)
    keys = sorted(groups)

    widths = np.array([record["vertices_mm"][1][0] - record["vertices_mm"][0][0]
                       for _, record in records])
    heights = np.array([record["vertices_mm"][1][1] - record["vertices_mm"][0][1]
                        for _, record in records])
    cell_w = float(max(widths.max(), max(sizes) * 2, PIPE_LENGTH_MM) + MARGIN_MM)
    cell_h = float(heights.max() + MARGIN_MM)
    grid = LibraryBuilder(name)
    layout = []  # (row, column, article, category, bbox, type, occurrence, ports)
    fitting_types = {}
    for key in keys:
        row = keys.index(key) + 1
        for column, dn in enumerate(sizes):
            entry = groups[key].get(dn)
            if entry is None:
                continue
            (definition, body), record = entry
            fitting_type, rep_map = grid.fitting_type(definition, record, type_ports=True)
            fitting_types[definition.article] = fitting_type
            low = record["vertices_mm"][0]
            position = (column * cell_w - low[0], -row * cell_h - low[1], 0.0)
            occurrence, ports = grid.fitting_occurrence(
                definition, fitting_type, rep_map, record, position)
            bbox = (np.array(position) + record["vertices_mm"]).tolist()
            layout.append((row, column, definition.article, _row_label(key), bbox,
                           fitting_type, occurrence, ports))

    grid.declare(code)
    pipe_types = {}
    for column, dn in enumerate(sizes):
        spec = pipe_specs[dn]
        pipe_type, profile = grid.pipe_type(dn, spec, f"{standard.upper()} trubka DN{dn}",
                                            code, PIPE_LENGTH_MM)
        pipe_types[dn] = pipe_type
        position = (column * cell_w, 0.0, 0.0)
        occurrence, ports = grid.pipe_occurrence(
            pipe_type, profile, dn, spec, position, PIPE_LENGTH_MM)
        bbox = [[position[0] - spec[0] / 2, position[1], -spec[0] / 2],
                [position[0] + spec[0] / 2, position[1] + PIPE_LENGTH_MM, spec[0] / 2]]
        layout.append((0, column, f"PIPE-{dn}", "Trubka", bbox, pipe_type, occurrence, ports))
    to_metres(grid.file)
    output = grid.write(path or f"out/grid-{standard}.ifc")
    return output, {"layout": layout, "cell": (cell_w, cell_h), "sizes": sizes,
                    "fitting_types": fitting_types, "pipe_types": pipe_types}


def validate_grid(path, info):
    """EXPRESS validace a kontrola typů, portů, profilů a rozvržení gridu."""
    file = ifcopenshell.open(str(path))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(file, logger, express_rules=True)
    errors = [s for s in logger.statements if s.get("level") == "error"]
    if errors:
        raise RuntimeError(f"IFC EXPRESS chyby: {errors[:3]}")
    layout = info["layout"]
    fittings = [row for row in layout if row[6].is_a("IfcPipeFitting")]
    pipes = [row for row in layout if row[6].is_a("IfcPipeSegment")]
    assert len(fittings) + len(pipes) == len(layout)
    assert len({row[5] for row in layout}) == len(layout), "typy musí být unikátní"
    assert len({row[5].Name for row in layout}) == len(layout), "názvy typů musí být unikátní"
    for row, column, article, category, bbox, fitting_type, occurrence, ports in layout:
        from ifcopenshell.util.system import get_ports
        type_ports = get_ports(fitting_type)
        assert len(type_ports) == len(ports), (article, "porty typu vs výskytu")
        assert sorted(p.Name for p in type_ports) == sorted(p.Name for p in ports)
        for tp, op in zip(type_ports, ports):
            t = tp.ObjectPlacement.RelativePlacement.Location.Coordinates
            o = op.ObjectPlacement.RelativePlacement.Location.Coordinates
            assert np.allclose(t, o, atol=1e-6), (article, tp.Name, t, o)
        if occurrence.is_a("IfcPipeSegment"):
            material = ifcopenshell.util.element.get_material(fitting_type)
            assert material.is_a("IfcMaterialProfileSet")
            profile = material.MaterialProfiles[0].Profile
            assert profile.is_a("IfcCircleHollowProfileDef")
            assert profile.Radius > profile.WallThickness > 0
    cell_w, cell_h = info["cell"]
    for i, a in enumerate(layout):
        for b in layout[i + 1:]:
            ax0, ay0, _ = a[4][0]
            ax1, ay1, _ = a[4][1]
            bx0, by0, _ = b[4][0]
            bx1, by1, _ = b[4][1]
            assert ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0, (
                a[2], b[2], "překrývání buněk")
    return len(fittings), len(pipes), len(layout)
