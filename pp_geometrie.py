"""Approximate MASTER 3 PLUS mesh; catalogue dimensions remain in pp_data.py."""

import numpy as np


SIDES = 24


def _sweep_path(path, radius, depth, collar_radius, sides=SIDES, cap_start=True, cap_end=True):
    """Sweep a closed hollow tube along a polyline with socket collar radii."""
    path = np.asarray(path, float)
    lengths = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    if len(path) < 2 or lengths[-1] <= 0:
        raise ValueError("sweep path must have positive length")
    points, faces = [], []
    for i, center in enumerate(path):
        tangent = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        tangent /= np.linalg.norm(tangent)
        ref = np.array([0.0, 0.0, 1.0])
        u = np.cross(tangent, ref)
        if np.linalg.norm(u) < 1e-8:
            ref = np.array([0.0, 1.0, 0.0])
            u = np.cross(tangent, ref)
        u /= np.linalg.norm(u)
        v = np.cross(tangent, u)
        near_mouth = min(lengths[i], lengths[-1] - lengths[i])
        shoulder = np.clip(near_mouth / max(depth, 1), 0, 1)
        shoulder = shoulder * shoulder * (3 - 2 * shoulder)
        outer = radius + shoulder * (collar_radius - radius)
        for r in (outer, radius - 1.0):
            points.extend(
                center + r * (np.cos(a) * u + np.sin(a) * v)
                for a in np.linspace(0, 2 * np.pi, sides, endpoint=False)
            )
    for station in range(len(path) - 1):
        for side in range(2):
            a0, a1 = station * 2 * sides + side * sides, (station + 1) * 2 * sides + side * sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.extend(((a0 + i, a0 + j, a1 + j), (a0 + i, a1 + j, a1 + i)))
        outer0, inner0 = station * 2 * sides, station * 2 * sides + sides
        outer1, inner1 = (station + 1) * 2 * sides, (station + 1) * 2 * sides + sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend(
                (
                    (outer0 + i, outer1 + i, inner1 + i),
                    (outer0 + i, inner1 + i, inner0 + i),
                )
            )
    # Annular end faces close each socket mouth.
    for ring, enabled in ((0, cap_start), (len(path) - 1, cap_end)):
        if not enabled:
            continue
        outer, inner = ring * 2 * sides, ring * 2 * sides + sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend(
                ((outer + i, inner + i, inner + j), (outer + i, inner + j, outer + j))
            )
    return np.asarray(points), np.asarray(faces, dtype=int)


def _sweep(start, end, radius, length, depth, collar_radius):
    return _sweep_path(
        np.linspace(start, end, max(2, int(length / 4))),
        radius,
        depth,
        collar_radius,
    )


def elbow_mesh(row, socket_depth, wall):
    """Bezier elbow with catalogue chord, angle and endpoint sockets."""
    angle = np.deg2rad(row["angle_deg"])
    length = row["length_mm"]
    end = np.array([length * np.sin(angle), -length * np.cos(angle), 0.0])
    start = np.zeros(3)
    # Curvature and socket details are approximated; L and angle are catalogue values.
    control1 = start + np.array([0.0, length * 0.55, 0.0])
    control2 = end - np.array([np.sin(angle), -np.cos(angle), 0.0]) * length * 0.55
    t = np.linspace(0, 1, 48)[:, None]
    path = (1 - t) ** 3 * start + 3 * (1 - t) ** 2 * t * control1 + 3 * (1 - t) * t**2 * control2 + t**3 * end
    # A swept sequence of short hollow sections approximates the curved fitting.
    outer_r = row["od_mm"] / 2 + wall
    collar_r = row["socket_od_mm"] / 2
    vertices, faces = _sweep_path(path, outer_r, socket_depth, collar_r)
    return vertices, faces, (
        (start, np.array([0.0, -1.0, 0.0])),
        (end, np.array([-np.sin(angle), np.cos(angle), 0.0])),
    )


def branch_mesh(row, main_od, branch_od, socket_depth, wall):
    """Three overlapping hollow arms; socketed ends and junction are approximate."""
    length = float(row["length_mm"])
    angle = np.deg2rad(row["angle_deg"])
    main_start = np.array([0.0, -length / 2, 0.0])
    main_end = np.array([0.0, length / 2, 0.0])
    junction = np.array([0.0, float(row["z1_mm"]), 0.0])
    branch_end = junction + float(row["z3_mm"]) * np.array(
        [np.sin(angle), np.cos(angle), 0.0]
    )
    main_vertices, main_faces = _sweep(
        main_start, main_end, main_od / 2 + wall, length,
        socket_depth, main_od * 1.15 / 2,
    )
    branch_vertices, branch_faces = _sweep_path(
        np.linspace(junction, branch_end, max(2, int(np.linalg.norm(branch_end - junction) / 4))),
        branch_od / 2 + wall,
        socket_depth,
        branch_od * 1.15 / 2,
        cap_start=False,
    )
    vertices = np.vstack((main_vertices, branch_vertices))
    faces = np.vstack((main_faces, branch_faces + len(main_vertices)))
    ports = (
        (main_start, np.array([0.0, -1.0, 0.0]), main_od),
        (main_end, np.array([0.0, 1.0, 0.0]), main_od),
        (branch_end, np.array([np.sin(angle), np.cos(angle), 0.0]), branch_od),
    )
    return vertices, faces, ports


def reducer_mesh(length, large_od, small_od, large_socket_od, small_socket_od, wall, offset_mm=0):
    """Conical reducer; both socket collars and internal profile are approximate."""
    stations, sides = 24, SIDES
    vertices, faces = [], []
    for t in np.linspace(0, 1, stations):
        center = np.array([t * offset_mm, t * length, 0.0])
        smooth = t * t * (3 - 2 * t)
        outer_body = (large_od / 2 + wall) * (1 - smooth) + (small_od / 2 + wall) * smooth
        collar = large_socket_od / 2 * (1 - smooth) + small_socket_od / 2 * smooth
        end_factor = max(np.clip(1 - t * length / 12, 0, 1),
                         np.clip(1 - (1 - t) * length / 12, 0, 1))
        outer = outer_body + end_factor * max(0, collar - outer_body)
        inner = (large_od / 2 - 0.8) * (1 - smooth) + (small_od / 2 - 0.8) * smooth
        for radius in (outer, inner):
            vertices.extend(
                center + radius * np.array([np.cos(a), 0, np.sin(a)])
                for a in np.linspace(0, 2 * np.pi, sides, endpoint=False)
            )
    for k in range(stations - 1):
        for shell in range(2):
            a0, a1 = k * 2 * sides + shell * sides, (k + 1) * 2 * sides + shell * sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.extend(((a0 + i, a0 + j, a1 + j), (a0 + i, a1 + j, a1 + i)))
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend(((k * 2 * sides + i, (k + 1) * 2 * sides + i,
                           (k + 1) * 2 * sides + sides + i),
                          (k * 2 * sides + i, (k + 1) * 2 * sides + sides + i,
                           k * 2 * sides + sides + i)))
    for k in (0, stations - 1):
        outer, inner = k * 2 * sides, k * 2 * sides + sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend(((outer + i, inner + i, inner + j), (outer + i, inner + j, outer + j)))
    return np.asarray(vertices), np.asarray(faces, dtype=int)


def inspection_piece_mesh(
    length, od, socket_od, socket_depth, wall, side_diameter, side_projection, side_center
):
    """Vertical access piece; side cover dimensions and seal detail are approximate."""
    body_v, body_f = _sweep(
        (0, 0, 0), (0, 0, length), od / 2 + wall,
        length, socket_depth, socket_od / 2,
    )
    boss_radius = side_diameter / 2 + wall
    boss_length = side_projection - od / 2
    if boss_length <= 0 or not 0 < side_center < length:
        raise ValueError("inspection side-port dimensions are outside the fitting envelope")
    boss_start = np.array([od / 2, 0.0, side_center])
    boss_end = boss_start + np.array([boss_length, 0.0, 0.0])
    boss_v, boss_f = _sweep_path(
        np.linspace(boss_start, boss_end, 8),
        boss_radius,
        max(1, boss_length),
        boss_radius + wall,
        cap_start=False,
        cap_end=False,
    )
    # A flat circular lid closes the access boss (seal/screw detail omitted).
    center = boss_end + np.array([0.2, 0.0, 0.0])
    lid_start = len(body_v) + len(boss_v)
    lid_vertices = np.vstack((center, boss_end + boss_radius * np.column_stack((
        np.zeros(SIDES), np.cos(np.linspace(0, 2*np.pi, SIDES, endpoint=False)),
        np.sin(np.linspace(0, 2*np.pi, SIDES, endpoint=False)),
    ))))
    lid_faces = np.asarray(
        [(0, i + 1, (i + 1) % SIDES + 1) for i in range(SIDES)], dtype=int
    ) + lid_start
    return (
        np.vstack((body_v, boss_v, lid_vertices)),
        np.vstack((body_f, boss_f + len(body_v), lid_faces)),
    )
