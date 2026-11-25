"""True parametric bodies: meridian profiles lathed along straight and arc centrelines.

Every piece is an IfcRevolvedAreaSolid (IFC4 SweptSolid): a closed profile in the
XY plane of its own frame, revolved about an axis lying in that plane.  The axis
is given in the profile frame, as IFC and IfcOpenShell expect.  No boolean, no
tessellation: the shape stays exact at any zoom and costs a few kB per fitting.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Lathe:
    profile: tuple  # ((radius_mm, axial_mm), ...) closed section, radius >= 0
    location: tuple  # profile frame origin, mm
    normal: tuple  # profile plane normal (frame Z)
    x_axis: tuple  # frame X
    axis_location: tuple  # revolution axis, in the profile frame
    axis_direction: tuple
    angle: float  # radians
    void_profiles: tuple = ()  # closed inner sections carved out of the revolve
    circle: tuple = ()  # (outer_radius_mm, bore_radius_mm): hollow circular section


@dataclass(frozen=True)
class SweptBody:
    lathes: tuple


def _unit(vector):
    vector = np.asarray(vector, float)
    return vector / np.linalg.norm(vector)


def straight_lathe(profile, start, direction):
    """Revolve a meridian profile about the straight centreline start -> direction.

    Profile axial coordinate runs along the centreline from `start`.
    """
    direction = _unit(direction)
    reference = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.9 else (0.0, 1.0, 0.0)
    normal = _unit(np.cross(direction, reference))
    x_axis = np.cross(direction, normal)
    return Lathe(
        tuple(profile), tuple(map(float, start)), tuple(normal), tuple(x_axis),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 2.0 * np.pi,
    )


def arc_lathe(r_body, r_bore, start, tangent_in, tangent_out, radius):
    """Revolve the hollow circular pipe section about the bend axis by the bend angle.

    `start` is the pipe-axis point where the bend begins; the section is the
    annulus (outer r_body, bore r_bore) in the plane perpendicular to `tangent_in`.
    """
    d0, d1 = _unit(tangent_in), _unit(tangent_out)
    bend_axis = _unit(np.cross(d0, d1))
    to_centre = _unit(np.cross(bend_axis, d0))
    x_axis = to_centre
    normal = d0
    # IfcOpenShell rotates clockwise about the declared axis for positive angles.
    sign = -1.0 if np.dot(np.cross(bend_axis, -to_centre * radius), d1 - d0) < 0 else 1.0
    return Lathe(
        (), tuple(map(float, start)), tuple(normal), tuple(x_axis),
        (float(radius), 0.0, 0.0), (0.0, float(sign), 0.0), float(np.arccos(np.clip(np.dot(d0, d1), -1, 1))),
        (), (float(r_body), float(r_bore)),
    )


def socket_cup_profile(od_mm, wall_mm, socket_od_mm, bore_end_mm, cone_end_mm):
    """Concentric socket cup, scaled from the measured KG OD110 reference.

    Closed meridian section: mouth lip, two retaining rings with grooves, taper to
    the body wall, straight bore to `bore_end_mm`, conical cup back to the lip.
    """
    od = float(od_mm)
    scale = od / 110.4
    wall = 3.3 * scale if wall_mm is None else float(wall_mm)
    r_body, r_bore = od / 2, od / 2 - wall
    r_collar = float(socket_od_mm) / 2
    r_mouth = r_body + 3.2 * scale
    r_cup = r_body + 0.3 * scale
    groove = r_collar - 3.0 * scale
    if r_collar <= r_mouth + 0.5 * scale or groove <= r_mouth or r_bore + 1.7 * scale >= r_cup:
        raise ValueError("socket proportions do not fit the measured ring stack")
    return (
        (r_cup, 0.0), (r_mouth, 0.0), (r_mouth, 3.0 * scale),
        (r_collar, 3.8 * scale), (r_collar, 5.0 * scale),
        (groove, 6.2 * scale), (groove, 15.8 * scale),
        (r_body + 0.3 * scale, 16.8 * scale), (r_collar, 17.8 * scale), (r_collar, 18.8 * scale),
        (r_body + 3.6 * scale, 19.2 * scale), (r_body, 21.0 * scale),
        (r_body, float(bore_end_mm)), (r_bore, float(bore_end_mm)),
        (r_bore + 1.7 * scale, float(cone_end_mm)),
    )


def tube_lathe(od_mm, wall_mm, length_mm, start=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0)):
    """Plain hollow tube: rectangular annulus section revolved about the centreline."""
    r_body, r_bore = float(od_mm) / 2, float(od_mm) / 2 - float(wall_mm)
    profile = ((r_bore, 0.0), (r_body, 0.0), (r_body, float(length_mm)), (r_bore, float(length_mm)))
    return straight_lathe(profile, start, direction)


def socket_run_lathes(length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm, sockets="both", start_mm=0.0, direction=(0.0, 1.0, 0.0)):
    """Straight run as overlapping lathes: through tube plus socket cup(s) at the ends.

    Returns (SweptBody, mouths) with mouth points on the centreline and outward axes.
    """
    od, wall = float(od_mm), float(wall_mm)
    length, cup_len, start = float(length_mm), float(cup_len_mm), float(start_mm)
    axis = _unit(direction)
    if length <= 2 * cup_len * 0.6:
        raise ValueError("run shorter than its sockets")
    tube = tube_lathe(od, wall, length, start=(tuple(start * axis)), direction=axis)
    cup = socket_cup_profile(od, wall, socket_od_mm, cup_len, cup_len * 0.956)
    lathes = [tube]
    mouths = []
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
):
    """Concentric reducer: conical wall tube with an overlapping socket cup at each end."""
    length = float(length_mm)
    body = Lathe(
        (
            (float(od_large) / 2 - float(wall_large), 0.0), (float(od_large) / 2, 0.0),
            (float(od_small) / 2, length), (float(od_small) / 2 - float(wall_small), length),
        ),
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 2.0 * np.pi,
    )
    cup_large = socket_cup_profile(od_large, wall_large, socket_od_large, cup_len_large, cup_len_large * 0.956)
    cup_small = socket_cup_profile(od_small, wall_small, socket_od_small, cup_len_small, cup_len_small * 0.956)
    lathes = (
        body,
        straight_lathe(cup_large, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        straight_lathe(cup_small, (0.0, length, 0.0), (0.0, -1.0, 0.0)),
    )
    mouths = (
        (np.zeros(3), np.array((0.0, -1.0, 0.0))),
        (np.array((0.0, length, 0.0)), np.array((0.0, 1.0, 0.0))),
    )
    return SweptBody(lathes), mouths


def branch_lathes(
    length_main_mm, od_main, wall_main, socket_od_main, cup_len_main,
    od_branch, wall_branch, socket_od_branch, cup_len_branch,
    z1_mm, z3_mm, angle_deg,
):
    """Junction as overlapping lathes: socketed main run plus an angled branch arm.

    The branch tube starts on the main axis and penetrates the main wall; the
    junction is a solid overlap, no boolean.
    """
    angle = np.deg2rad(float(angle_deg))
    main, mouths = socket_run_lathes(
        length_main_mm, od_main, wall_main, socket_od_main, cup_len_main,
        start_mm=-float(length_main_mm) / 2,
    )
    junction = np.array((0.0, float(z1_mm), 0.0))
    direction = np.array((np.sin(angle), np.cos(angle), 0.0))
    branch_len = float(z3_mm) + cup_len_branch * 0.6  # reach past the socket mouth plane
    branch = tube_lathe(od_branch, wall_branch, branch_len, start=junction, direction=direction)
    cup = socket_cup_profile(od_branch, wall_branch, socket_od_branch, cup_len_branch, cup_len_branch * 0.956)
    branch_cup = straight_lathe(cup, junction + float(z3_mm) * direction, -direction)
    lathes = main.lathes + (branch, branch_cup)
    mouths = mouths + ((junction + float(z3_mm) * direction, direction),)
    return SweptBody(lathes), mouths


def cleanout_lathes(
    length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm,
    z1_mm, cover_diameter_mm, cover_thickness_mm=None,
):
    """Vertical access piece: socketed run plus a side opening with a flat cover."""
    run, mouths = socket_run_lathes(
        length_mm, od_mm, wall_mm, socket_od_mm, cup_len_mm, direction=(0.0, 0.0, 1.0),
    )
    side_od = float(cover_diameter_mm)
    stub = tube_lathe(side_od, float(wall_mm), float(od_mm), start=(0.0, 0.0, float(z1_mm)), direction=(1.0, 0.0, 0.0))
    thickness = 0.35 * side_od if cover_thickness_mm is None else float(cover_thickness_mm)
    r_cover = side_od / 2
    cover = Lathe(
        ((0.0, 0.0), (r_cover, 0.0), (r_cover, thickness), (0.0, thickness)),
        (float(od_mm), 0.0, float(z1_mm)), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 2.0 * np.pi,
    )
    return SweptBody(run.lathes + (stub, cover)), mouths


def elbow_lathes(angle_deg, od_mm, socket_od_mm=None, wall_mm=None):
    """Elbow from the measured Ostendorf KG 45 deg OD110 reference (reference_canonical.json).

    Centreline: straight socket run, true circular arc, straight spigot run.
    All lengths scale with the body OD; the angle drives the bend.
    """
    angle = np.deg2rad(float(angle_deg))
    od = float(od_mm)
    if not 0 < angle < np.pi or od <= 0:
        raise ValueError("elbow needs a positive OD and an angle between 0 and 180 degrees")
    scale = od / 110.4
    radius, tangent_start, tangent_end = 56.5 * scale, 65.0 * scale, 64.0 * scale
    wall = 3.3 * scale if wall_mm is None else float(wall_mm)
    r_body, r_bore = od / 2, od / 2 - wall
    socket_len = 57.0 * scale
    r_collar = (126.9 * scale if socket_od_mm is None else float(socket_od_mm)) / 2
    r_cup = (110.99 * scale) / 2
    r_mouth = r_body + (58.4 - 55.2) * scale  # narrow face lip measured on the reference
    groove = r_collar - 3.0 * scale
    if r_cup <= r_body - wall or r_collar <= r_body + 3.0 * scale or tangent_start <= socket_len or tangent_end <= 30 * scale:
        raise ValueError("elbow dimensions do not leave a body between the ends")

    # outer skin measured on the reference: lip, two thin retaining rings, grooves between/behind
    socket_profile = (
        (r_cup, 0.0), (r_mouth, 0.0), (r_mouth, 3.0 * scale),
        (r_collar, 3.8 * scale), (r_collar, 5.0 * scale), (groove, 6.2 * scale), (groove, 15.8 * scale),
        (r_body + 0.3 * scale, 16.8 * scale), (r_collar, 17.8 * scale), (r_collar, 18.8 * scale),
        (r_body + 3.6 * scale, 19.2 * scale), (r_body, 21.0 * scale), (r_body, tangent_start),
        # back along the bore and the slightly conical cup wall (never outside the outer skin)
        (r_bore, tangent_start), (r_bore, 61.0 * scale),
        (r_bore + 1.7 * scale, 54.5 * scale), (r_cup, 0.0),
    )
    spigot_profile = (
        (r_bore, 0.0), (od / 2 - 0.1 * scale, 0.0), (od / 2 - 0.1 * scale, 30 * scale),
        (r_body, 30 * scale), (r_body, tangent_end), (r_bore, tangent_end),
    )
    d0 = np.array((0.0, 1.0, 0.0))
    d1 = np.array((np.sin(angle), np.cos(angle), 0.0))
    arc_start = np.array((0.0, tangent_start, 0.0))
    arc_end = arc_start + radius * np.array((1 - np.cos(angle), np.sin(angle), 0.0))
    lathes = (
        straight_lathe(socket_profile, (0, 0, 0), d0),
        arc_lathe(r_body, r_bore, arc_start, d0, d1, radius),
        straight_lathe(spigot_profile, arc_end, d1),
    )
    mouths = (
        (np.zeros(3), -d0),
        (arc_end + d1 * tangent_end, -d1),
    )
    return SweptBody(lathes), mouths


def swept_bounds(body, step_mm=1.0):
    """Near-exact bounding box (mm) of the tessellated-equivalent solids."""
    points = []
    for lathe in body.lathes:
        origin, normal, x_axis = (np.asarray(v, float) for v in (lathe.location, lathe.normal, lathe.x_axis))
        y_axis = np.cross(normal, x_axis)
        axis_point = origin + np.asarray(lathe.axis_location) @ np.vstack((x_axis, y_axis, normal))
        axis_dir = _unit(np.asarray(lathe.axis_direction) @ np.vstack((x_axis, y_axis, normal)))
        angles = np.arange(0.0, lathe.angle + 1e-9, np.deg2rad(1.0))
        if lathe.circle:
            samples = [
                (lathe.circle[0] * np.cos(phi), lathe.circle[0] * np.sin(phi))
                for phi in np.arange(0.0, 2.0 * np.pi, np.deg2rad(5.0))
            ]
        else:
            profile = np.asarray(lathe.profile, float)
            samples = []
            for (r0, s0), (r1, s1) in zip(profile, np.roll(profile, -1, axis=0)):
                for t in np.linspace(0.0, 1.0, max(2, int(np.hypot(r1 - r0, s1 - s0) / step_mm) + 1)):
                    samples.append((r0 + t * (r1 - r0), s0 + t * (s1 - s0)))
        for r, s in samples:
            base = origin + s * y_axis + r * x_axis
            rel = base - axis_point
            axial = (rel @ axis_dir) * axis_dir
            radial = rel - axial
            u, v = radial, np.cross(axis_dir, radial)
            for phi in angles:  # same sense as the geometry kernel
                points.append(axis_point + axial + np.cos(phi) * u - np.sin(phi) * v)
    points = np.asarray(points)
    return points.min(axis=0), points.max(axis=0)


def lathes_to_ifc(file, body):
    """IfcRevolvedAreaSolid items for a SweptBody (coordinates in mm, the file unit)."""
    items = []
    for lathe in body.lathes:
        def curve(points_2d):
            return file.create_entity(
                "IfcPolyline",
                Points=[
                    file.create_entity("IfcCartesianPoint", Coordinates=(float(r), float(s)))
                    for r, s in list(points_2d) + [points_2d[0]]
                ],
            )

        if lathe.circle:
            outer, bore = lathe.circle
            profile = file.create_entity(
                "IfcCircleHollowProfileDef",
                ProfileType="AREA",
                Radius=float(outer),
                WallThickness=float(outer - bore),
            )
        elif lathe.void_profiles:
            profile = file.create_entity(
                "IfcArbitraryProfileDefWithVoids",
                ProfileType="AREA",
                OuterCurve=curve(lathe.profile),
                InnerCurves=[curve(void) for void in lathe.void_profiles],
            )
        else:
            profile = file.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=curve(lathe.profile))
        items.append(
            file.create_entity(
                "IfcRevolvedAreaSolid",
                SweptArea=profile,
                Position=file.create_entity(
                    "IfcAxis2Placement3D",
                    Location=file.create_entity("IfcCartesianPoint", Coordinates=tuple(float(c) for c in lathe.location)),
                    Axis=file.create_entity("IfcDirection", DirectionRatios=tuple(float(c) for c in lathe.normal)),
                    RefDirection=file.create_entity("IfcDirection", DirectionRatios=tuple(float(c) for c in lathe.x_axis)),
                ),
                Axis=file.create_entity(
                    "IfcAxis1Placement",
                    Location=file.create_entity("IfcCartesianPoint", Coordinates=tuple(float(c) for c in lathe.axis_location)),
                    Axis=file.create_entity("IfcDirection", DirectionRatios=tuple(float(c) for c in lathe.axis_direction)),
                ),
                Angle=float(lathe.angle),
            )
        )
    return items
