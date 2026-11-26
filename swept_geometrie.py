"""Přesné parametrické tělesa: meridiánové profily revolucí podél přímky/oblouku.

Každý kus je IfcRevolvedAreaSolid (IFC4 SweptSolid): uzavřený profil v XY rovině
vlastního rámu, otočený kolem osy ležící v téže rovině. Žádné booleany, žádná
tessellace — tvar zůstává přesný při libovolném přiblížení.
"""
from dataclasses import dataclass
import numpy as np
from ifc_util import axis, direction, point
@dataclass(frozen=True)
class Lathe:
    profile: tuple  # ((radius_mm, axial_mm), ...) uzavřený řez, radius >= 0
    location: tuple  # počátek profilového rámu
    normal: tuple  # normála roviny profilu (rámu Z)
    x_axis: tuple  # rámu X
    axis_location: tuple  # osa revoluce v profilovém rámci
    axis_direction: tuple
    angle: float  # radiány
    void_profiles: tuple = ()
    circle: tuple = ()  # (outer_radius_mm, bore_radius_mm): dutý kruhový řez
@dataclass(frozen=True)
class SweptBody:
    lathes: tuple
@dataclass(frozen=True)
class Taper:
    """IfcExtrudedAreaSolidTapered: jeden loft mezi dvěma dutými kruhy.

    Kruhy mohou mít různé poloměry *i středy* — přesně to potřebuje excentrická
    redukce (bez schodů, bez naklápění). `bottom`/`top` = (r, tloušťka, x-offset).
    """
    bottom: tuple
    top: tuple
    location: tuple
    depth: float
def _unit(vector):
    vector = np.asarray(vector, float)
    return vector / np.linalg.norm(vector)
def straight_lathe(profile, start, direction):
    """Revolve meridiánového profilu podél přímky start -> direction."""
    direction = _unit(direction)
    reference = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.9 else (0.0, 1.0, 0.0)
    normal = _unit(np.cross(direction, reference))
    x_axis = np.cross(direction, normal)
    return Lathe(
        tuple(profile), tuple(map(float, start)), tuple(normal), tuple(x_axis),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 2.0 * np.pi,
    )
def arc_lathe(r_body, r_bore, start, tangent_in, tangent_out, radius):
    """Dutý kruhový řez revolucí kolem osy ohybu o úhel mezi tečnami."""
    d0, d1 = _unit(tangent_in), _unit(tangent_out)
    bend_axis = _unit(np.cross(d0, d1))
    to_centre = _unit(np.cross(bend_axis, d0))
    sign = -1.0 if np.dot(np.cross(bend_axis, -to_centre * radius), d1 - d0) < 0 else 1.0
    return Lathe(
        (), tuple(map(float, start)), tuple(d0), tuple(to_centre),
        (float(radius), 0.0, 0.0), (0.0, float(sign), 0.0),
        float(np.arccos(np.clip(np.dot(d0, d1), -1, 1))),
        (), (float(r_body), float(r_bore)),
    )
def socket_cup_profile(od_mm, wall_mm, socket_od_mm, bore_end_mm, cone_end_mm,
                       sleeve_len_mm=None):
    """Hnízdový profil měřený na KG OD110, škálovaný podle OD."""
    od = float(od_mm)
    scale = od / 110.4
    wall = 3.3 * scale if wall_mm is None else float(wall_mm)
    r_body, r_bore = od / 2, od / 2 - wall
    r_collar = float(socket_od_mm) / 2
    r_mouth, r_cup = r_body + 3.2 * scale, r_body + 0.3 * scale
    groove = r_collar - 3.0 * scale
    if (r_collar <= r_mouth + 0.5 * scale or groove <= r_mouth
            or r_bore + 1.7 * scale >= r_cup):
        raise ValueError("socket proportions do not fit the measured ring stack")
    tail = ((r_body, 21.0 * scale), (r_collar, 22.5 * scale),
            (r_collar, float(sleeve_len_mm))) if sleeve_len_mm else (
                (r_body, float(bore_end_mm)),)
    return (
        (r_cup, 0.0), (r_mouth, 0.0), (r_mouth, 3.0 * scale),
        (r_collar, 3.8 * scale), (r_collar, 5.0 * scale),
        (groove, 6.2 * scale), (groove, 15.8 * scale),
        (r_body + 0.3 * scale, 16.8 * scale), (r_collar, 17.8 * scale),
        (r_collar, 18.8 * scale), (r_body + 3.6 * scale, 19.2 * scale),
        *tail, (r_bore, float(bore_end_mm)),
        (r_bore + 1.7 * scale, float(cone_end_mm)),
    )
def tube_lathe(od_mm, wall_mm, length_mm, start=(0.0, 0.0, 0.0),
               direction=(0.0, 1.0, 0.0)):
    """Prostá dutá trubka: prstencový řez revolucí podél osy."""
    outer, bore = float(od_mm) / 2, float(od_mm) / 2 - float(wall_mm)
    profile = ((bore, 0.0), (outer, 0.0), (outer, float(length_mm)),
               (bore, float(length_mm)))
    return straight_lathe(profile, start, direction)
def socket_run_lathes(length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm,
                      sockets="both", start_mm=0.0, direction=(0.0, 1.0, 0.0)):
    """Přímý úsek jako překrývající se lathe: trubka + hnízda na koncích."""
    length, cup_len, start = float(length_mm), float(cup_len_mm), float(start_mm)
    axis = _unit(direction)
    if length < cup_len:
        raise ValueError("run shorter than its sockets")
    tube = tube_lathe(od_mm, wall_mm, length, start=tuple(start * axis), direction=axis)
    cup = socket_cup_profile(od_mm, wall_mm, socket_od_mm, cup_len, cup_len * 0.956)
    lathes, mouths = [tube], []
    if sockets in ("both", "start"):
        lathes.append(straight_lathe(cup, tuple(start * axis), axis))
        mouths.append((start * axis, -axis))
    if sockets in ("both", "end"):
        end = start + length
        lathes.append(straight_lathe(cup, tuple(end * axis), -axis))
        mouths.append((end * axis, axis))
    return SweptBody(tuple(lathes)), tuple(mouths)
def reducer_lathes(
    length_mm, od_large, od_small, wall_large, wall_small,
    socket_od_large, socket_od_small, cup_len_large, cup_len_small,
    offset_mm=0.0, straight_large_mm=0.0, cone_len_mm=None, plain_large_end=False,
):
    """Redukce podél +Y: hnízdo/široký konec, kužel, malé hnízdo.

    `plain_large_end` = dole holý válec se středem -offset, nahoře samice na ose,
    mezi nimi jeden kužel se dvěma kruhy různého poloměru i středu (STEP 222700z).
    """
    length = float(length_mm)
    straight = min(float(straight_large_mm), length - 5.0)
    cone_end = length if cone_len_mm is None else min(straight + float(cone_len_mm), length)
    r_large, r_small = float(od_large) / 2, float(od_small) / 2
    bore_large = r_large - float(wall_large)
    offset = float(offset_mm)
    if plain_large_end:
        axis_start = (-offset, 0.0, 0.0)
        barrel = tube_lathe(od_large, wall_large, straight, start=axis_start)
        cone = Taper((r_large, float(wall_large), 0.0),
                     (r_small, float(wall_small), offset),
                     (-offset, straight, 0.0), cone_end - straight)
        socket_len = length - cone_end
        cup = socket_cup_profile(od_small, wall_small, socket_od_small,
                                 socket_len, socket_len * 0.956)
        socket = straight_lathe(cup, (0.0, length, 0.0), (0.0, -1.0, 0.0))
        mouths = ((np.array(axis_start), np.array((0.0, -1.0, 0.0))),
                  (np.array((0.0, length, 0.0)), np.array((0.0, 1.0, 0.0))))
        return SweptBody((barrel, cone, socket)), mouths
    profile = (
        (bore_large, 0.0), (r_large, 0.0), (r_large, straight),
        (r_small, cone_end), (r_small, length),
        (r_small - float(wall_small), length), (bore_large, straight),
    )
    large_end = straight_lathe(
        socket_cup_profile(od_large, wall_large, socket_od_large, cup_len_large,
                           cup_len_large * 0.956, sleeve_len_mm=cup_len_large),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    cup_small = socket_cup_profile(od_small, wall_small, socket_od_small,
                                   cup_len_small, cup_len_small * 0.956)
    lathes = (straight_lathe(profile, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
              large_end,
              straight_lathe(cup_small, (offset, length, 0.0), (0.0, -1.0, 0.0)))
    mouths = ((np.zeros(3), np.array((0.0, -1.0, 0.0))),
              (np.array((offset, length, 0.0)), np.array((0.0, 1.0, 0.0))))
    return SweptBody(lathes), mouths
def branch_lathes(
    length_main_mm, od_main, wall_main, socket_od_main, cup_len_main,
    od_branch, wall_branch, socket_od_branch, cup_len_branch,
    vertex_y_mm, z3_mm, angle_deg,
):
    """Odbočka jako překrývající se lathe: hnízdovaný hlavní běh + šikmá větev."""
    angle = np.deg2rad(float(angle_deg))
    main, mouths = socket_run_lathes(
        length_main_mm, od_main, wall_main, socket_od_main, cup_len_main,
        sockets="end", start_mm=-float(length_main_mm) / 2)
    junction = np.array((0.0, float(vertex_y_mm), 0.0))
    direction = np.array((np.sin(angle), np.cos(angle), 0.0))
    branch = tube_lathe(od_branch, wall_branch, float(z3_mm),
                        start=junction, direction=direction)
    cup = socket_cup_profile(od_branch, wall_branch, socket_od_branch,
                             cup_len_branch, cup_len_branch * 0.956)
    branch_cup = straight_lathe(cup, junction + float(z3_mm) * direction, -direction)
    return (SweptBody(main.lathes + (branch, branch_cup)),
            mouths + ((junction + float(z3_mm) * direction, direction),))
def cleanout_lathes(
    length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm,
    z1_mm, cover_diameter_mm, cover_reach_mm,
    cover_thickness_mm=None, neck_diameter_mm=None,
):
    """Čistící kus podél +Y: hnízdo u počátku, boční hrdlo víčkem."""
    run, mouths = socket_run_lathes(
        length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm,
        sockets="start", start_mm=0.0, direction=(0.0, 1.0, 0.0))
    side_od, reach = float(cover_diameter_mm), float(cover_reach_mm)
    thickness = 0.15 * side_od if cover_thickness_mm is None else float(cover_thickness_mm)
    neck = side_od - 13.0 if neck_diameter_mm is None else float(neck_diameter_mm)
    stub = tube_lathe(neck, float(wall_mm), reach - thickness,
                      start=(0.0, float(z1_mm), 0.0), direction=(1.0, 0.0, 0.0))
    radius = side_od / 2
    cover = straight_lathe(
        ((0.0, 0.0), (radius, 0.0), (radius, thickness), (0.0, thickness)),
        (reach, float(z1_mm), 0.0), (-1.0, 0.0, 0.0))
    return SweptBody(run.lathes + (stub, cover)), mouths
def cap_lathes(od_mm, wall_mm, socket_od_mm, cup_len_mm, length_mm):
    """Zátka: hnízdo na ústí a plná záslepka za ním."""
    od, wall = float(od_mm), float(wall_mm)
    outer, bore = od / 2, od / 2 - wall
    cup = socket_cup_profile(od, wall, socket_od_mm, float(cup_len_mm),
                             float(cup_len_mm) * 0.956)
    plug = (
        (bore, float(cup_len_mm)), (outer, float(cup_len_mm)),
        (outer, float(length_mm)), (0.0, float(length_mm)), (0.0, float(cup_len_mm)),
    )
    lathes = (straight_lathe(cup, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
              straight_lathe(plug, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
    return SweptBody(lathes), ((np.zeros(3), np.array((0.0, -1.0, 0.0))),)
def elbow_lathes(
    angle_deg, od_mm, socket_od_mm=None, wall_mm=None,
    socket_straight_mm=None, spigot_straight_mm=None, radius_mm=None,
    socket_len_mm=None, spigot_tip_mm=None, socket_on_spigot=False,
):
    """Koleno z rozměrů (mm); None = měřený KG 45° OD110 (220220z) škálovaný."""
    angle = np.deg2rad(float(angle_deg))
    od = float(od_mm)
    if not 0 < angle < np.pi or od <= 0:
        raise ValueError("elbow needs a positive OD and an angle between 0 and 180 degrees")
    scale = od / 110.4
    wall = 3.3 * scale if wall_mm is None else float(wall_mm)
    outer, bore = od / 2, od / 2 - wall
    # OCCT/Revit tiše zahodí oblouk s příliš malým vnitřním poloměrem (PP DN125)
    radius = max(56.5 * scale if radius_mm is None else float(radius_mm), bore + 4.0)
    tangent_start = 65.0 * scale if socket_straight_mm is None else float(socket_straight_mm)
    tangent_end = 64.0 * scale if spigot_straight_mm is None else float(spigot_straight_mm)
    socket_len = 57.0 * scale if socket_len_mm is None else float(socket_len_mm)
    tip = 30.0 * scale if spigot_tip_mm is None else float(spigot_tip_mm)
    r_collar = (126.9 * scale if socket_od_mm is None else float(socket_od_mm)) / 2
    r_cup, r_mouth = 110.99 * scale / 2, outer + 3.2 * scale
    groove = r_collar - 3.0 * scale
    if (r_cup <= outer - wall or r_collar <= outer + 3.0 * scale
            or tangent_start <= socket_len or tangent_end <= tip):
        raise ValueError("elbow dimensions do not leave a body between the ends")
    socket_profile = (
        (r_cup, 0.0), (r_mouth, 0.0), (r_mouth, 3.0 * scale),
        (r_collar, 3.8 * scale), (r_collar, 5.0 * scale),
        (groove, 6.2 * scale), (groove, 15.8 * scale),
        (outer + 0.3 * scale, 16.8 * scale), (r_collar, 17.8 * scale),
        (r_collar, 18.8 * scale), (outer + 3.6 * scale, 19.2 * scale),
        (outer, 21.0 * scale), (outer, tangent_start),
        (bore, tangent_start), (bore, socket_len + 4.0 * scale),
        (bore + 1.7 * scale, socket_len * 0.956), (r_cup, 0.0),
    )
    spigot_profile = (
        (bore, 0.0), (outer - 0.1 * scale, 0.0), (outer - 0.1 * scale, tip),
        (outer, tip), (outer, tangent_end), (bore, tangent_end),
    )
    d0 = np.array((0.0, 1.0, 0.0))
    d1 = np.array((np.sin(angle), np.cos(angle), 0.0))
    arc_start = np.array((0.0, tangent_start, 0.0))
    arc_end = arc_start + radius * np.array((1 - np.cos(angle), np.sin(angle), 0.0))
    first = spigot_profile if socket_on_spigot else socket_profile
    last = socket_profile if socket_on_spigot else spigot_profile
    last_start = arc_end + d1 * tangent_end if socket_on_spigot else arc_end
    last_direction = -d1 if socket_on_spigot else d1
    lathes = (
        straight_lathe(first, (0.0, 0.0, 0.0), d0),
        arc_lathe(outer, bore, arc_start, d0, d1, radius),
        straight_lathe(last, last_start, last_direction),
    )
    return SweptBody(lathes), ((np.zeros(3), -d0), (arc_end + d1 * tangent_end, d1))
def swept_bounds(body, step_mm=1.0):
    """Vektorizovaná obálka (mm) revolucí: vzorkování profilu a úhlů."""
    points = []
    for lathe in body.lathes:
        if isinstance(lathe, Taper):
            origin = np.asarray(lathe.location, float)
            phi = np.arange(0.0, 2 * np.pi, np.deg2rad(5.0))
            for spec, height in ((lathe.bottom, 0.0), (lathe.top, float(lathe.depth))):
                r, _, cx = spec
                points.append(np.column_stack((
                    np.full_like(phi, origin[0] + cx) + r * np.cos(phi),
                    np.full_like(phi, origin[1] + height), -r * np.sin(phi))))
            continue
        origin, normal, x_axis = (np.asarray(v, float) for v in
                                  (lathe.location, lathe.normal, lathe.x_axis))
        basis = np.vstack((x_axis, np.cross(normal, x_axis), normal))
        axis_point = origin + np.asarray(lathe.axis_location) @ basis
        axis_dir = _unit(np.asarray(lathe.axis_direction) @ basis)
        if lathe.circle:
            phi = np.arange(0.0, 2 * np.pi, np.deg2rad(5.0))
            profile = np.column_stack((lathe.circle[0] * np.cos(phi),
                                       lathe.circle[0] * np.sin(phi)))
        else:
            raw = np.asarray(lathe.profile, float)
            profile = np.vstack([
                np.linspace(a, b, max(2, int(np.hypot(*(b - a)) / step_mm) + 1))
                for a, b in zip(raw, np.roll(raw, -1, axis=0))
            ])
        base = origin + profile[:, 1:2] * basis[1] + profile[:, 0:1] * basis[0]
        rel = base - axis_point
        axial = (rel @ axis_dir)[:, None] * axis_dir
        radial = rel - axial
        u, v = radial, np.cross(axis_dir, radial)
        angles = np.arange(0.0, lathe.angle + 1e-9, np.deg2rad(1.0))
        points.append((axis_point + axial[:, None, :]
                       + np.cos(angles)[None, :, None] * u[:, None, :]
                       - np.sin(angles)[None, :, None] * v[:, None, :]).reshape(-1, 3))
    bounds = np.vstack(points)
    return bounds.min(axis=0), bounds.max(axis=0)
def lathes_to_ifc(file, body):
    """IfcRevolvedAreaSolid / IfcExtrudedAreaSolidTapered (souřadnice v mm)."""
    def hollow(spec):
        r, wall, cx = spec
        return file.create_entity(
            "IfcCircleHollowProfileDef", ProfileType="AREA", Radius=float(r),
            WallThickness=float(wall),
            Position=file.create_entity("IfcAxis2Placement2D", Location=point(file, (cx, 0.0))),
        )
    def curve(profile):
        return file.create_entity(
            "IfcPolyline", Points=[point(file, (r, s)) for r, s in list(profile) + [profile[0]]]
        )
    items = []
    for lathe in body.lathes:
        if isinstance(lathe, Taper):
            items.append(file.create_entity(
                "IfcExtrudedAreaSolidTapered",
                SweptArea=hollow(lathe.bottom), EndSweptArea=hollow(lathe.top),
                Position=axis(file, lathe.location, (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
                ExtrudedDirection=direction(file, (0.0, 0.0, 1.0)), Depth=float(lathe.depth),
            ))
            continue
        if lathe.circle:
            outer, bore = lathe.circle
            profile = file.create_entity(
                "IfcCircleHollowProfileDef", ProfileType="AREA", Radius=float(outer),
                WallThickness=float(outer - bore))
        elif lathe.void_profiles:
            profile = file.create_entity(
                "IfcArbitraryProfileDefWithVoids", ProfileType="AREA",
                OuterCurve=curve(lathe.profile),
                InnerCurves=[curve(void) for void in lathe.void_profiles])
        else:
            profile = file.create_entity(
                "IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=curve(lathe.profile))
        items.append(file.create_entity(
            "IfcRevolvedAreaSolid", SweptArea=profile,
            Position=axis(file, lathe.location, lathe.normal, lathe.x_axis),
            Axis=file.create_entity(
                "IfcAxis1Placement", Location=point(file, lathe.axis_location),
                Axis=direction(file, lathe.axis_direction)),
            Angle=float(lathe.angle)))
    return items
