"""Pipelife PP (EN 1451-1): SweptSolid z rozměrů aktuální příručky 2026."""

import json
import math
from pathlib import Path

import numpy as np

from definice import Fitting, Port
from generator import generate_catalogue_library
from swept_geometrie import (
    branch_lathes, cap_lathes, cleanout_lathes, elbow_lathes, reducer_lathes,
)

ROOT = Path(__file__).parent
TABLE = json.loads((ROOT / "data/pipelife_master3plus.json").read_text())
OD = {32: 33.0, 40: 41.1, 50: 51.0, 75: 76.1, 90: 91.2, 110: 111.3, 125: 126.3, 160: 161.5}
WALL = {32: 1.8, 40: 1.8, 50: 2.0, 75: 2.1, 90: 2.5, 110: 3.0, 125: 3.5, 160: 4.4}
LIBRARY_SIZES = {32, 40, 50, 75, 110, 125, 160}
SOCKET_T = {int(k): v for k, v in TABLE["dimension_status"]["socket"]["insertion_depth_t_mm"].items()}
SOCKET_OD = {int(k): v for k, v in TABLE["dimension_status"]["socket"]["collar_outer_diameter_mm"].items()}


def _bend_radii():
    """R z katalogového z1 = R*tan(alpha/2) + c (LSQ přes 5 úhlů na DN)."""
    result = {}
    for dn in LIBRARY_SIZES:
        rows = [r for r in TABLE["elbows"] if r["dn_od"] == dn]
        a = np.array([[math.tan(math.radians(r["angle_deg"]) / 2), 1.0] for r in rows])
        z = np.array([r["z1_mm"] for r in rows], float)
        (radius, _), *_ = np.linalg.lstsq(a, z, rcond=None)
        result[dn] = float(radius)
    return result


BEND_RADIUS = _bend_radii()


def _legacy_article(row, family):
    """Starý článek 3496… se stejnými rozměry (jen jako vlastnost typu)."""
    for legacy in TABLE["legacy_article_examples"].values():
        if (
            legacy.get("family") == family
            and legacy.get("dn_od") == row.get("dn_od")
            and legacy.get("branch_dn_od") == row.get("branch_dn_od")
            and legacy.get("angle_deg") == row.get("angle_deg")
        ):
            return next(iter(
                key for key, value in TABLE["legacy_article_examples"].items()
                if value is legacy
            ))
    return None


def _definition(row, family, main_dn, branch_dn=None, ports=(), status=""):
    title = (
        f"PP koleno {row['angle_deg']}° OD{main_dn}"
        if family == "BEND" else
        f"PP odbočka {row['angle_deg']}° OD{main_dn}/{branch_dn}" if family == "JUNCTION" else
        f"PP redukce OD{main_dn}/{branch_dn}" if family == "TRANSITION" else
        f"PP zátka OD{main_dn}" if family == "CAP" else
        f"PP čistící kus OD{main_dn}"
    )
    legacy = _legacy_article(row, {"CAP": "cap", "USERDEFINED": "cleanout"}.get(family, family.lower()))
    return Fitting(
        name=title, standard="EN 1451-1", article=row["article"],
        family="USERDEFINED" if family == "CAP" else family,
        od_mm=OD[main_dn], angle_deg=row.get("angle_deg", 0),
        length_mm=row["length_mm"], z1_mm=row.get("z1_mm", 0),
        z2_mm=row.get("z2_mm", 0),
        mesh_anchor_mm=(0, 0, 0), mesh_along=(0, 1, 0), mesh_side=(1, 0, 0),
        ports=ports, branch_od_mm=OD[branch_dn] if branch_dn else None,
        z3_mm=row.get("z3_mm"), geometry_status=status, legacy_article=legacy,
    )


def pp_items():
    items = []
    for row in TABLE["elbows"]:
        dn = row["dn_od"]
        if dn not in LIBRARY_SIZES:
            continue
        angle = math.radians(row["angle_deg"])
        d1 = np.array((math.sin(angle), math.cos(angle), 0.0))
        t = SOCKET_T[dn]
        straight_socket = row["l2_mm"]
        straight_spigot = row["length_mm"] - row["z1_mm"]
        body, mouths = elbow_lathes(
            row["angle_deg"], OD[dn], SOCKET_OD[dn], WALL[dn],
            socket_straight_mm=straight_socket,
            spigot_straight_mm=straight_spigot,
            radius_mm=BEND_RADIUS[dn],
            socket_len_mm=min(t, 0.85 * straight_socket),
            spigot_tip_mm=row["l1_mm"],
        )
        ports = (
            Port("SOCKET", mouths[0][0], mouths[0][1], "SINK", SOCKET_OD[dn],
                 end_type="SOCKET", insertion_mm=t, take_out_mm=row["length_mm"]),
            Port("SPIGOT", mouths[1][0] - t * d1, tuple(d1), "SOURCE", OD[dn],
                 end_type="SPIGOT", insertion_mm=t, take_out_mm=row["length_mm"]),
        )
        items.append((_definition(row, "BEND", dn, ports=ports,
                     status="SweptSolid z příručky 2026: L, z1, l1, l2, Dmax, t; poloměr ohybu LSQ ze z1"), body))

    for row in TABLE["simple_branches"]:
        main, branch = row["dn_od"], row["branch_dn_od"]
        if main not in LIBRARY_SIZES or branch not in LIBRARY_SIZES:
            continue
        angle = math.radians(row["angle_deg"])
        length = row["length_mm"]
        # vrchol: z2 je vrchol -> horní hnízdo; kontrola proti z1 od spodního
        # čela nasazené trubky (spodek + t); neshoda znamená odhad
        t, tb = SOCKET_T[main], SOCKET_T[branch]
        vertex_from_socket = length / 2 - row["z2_mm"]
        vertex_from_spigot = -length / 2 + row["z1_mm"] + t
        estimated = abs(vertex_from_socket - vertex_from_spigot) > 8.0
        vertex_y = (vertex_from_socket + vertex_from_spigot) / 2.0
        direction = np.array((math.sin(angle), math.cos(angle), 0.0))
        ports = (
            Port("SPIGOT", (0, -length / 2 + t, 0), (0, -1, 0), "SOURCE", OD[main],
                 end_type="SPIGOT", insertion_mm=t),
            Port("SOCKET", (0, length / 2, 0), (0, 1, 0), "SINK", SOCKET_OD[main],
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET BRANCH",
                 (0, vertex_y, 0) + row["z3_mm"] * direction, tuple(direction),
                 "SINK", SOCKET_OD[branch], end_type="SOCKET", insertion_mm=tb),
        )
        body, _ = branch_lathes(
            length, OD[main], WALL[main], SOCKET_OD[main], t,
            OD[branch], WALL[branch], SOCKET_OD[branch], tb,
            vertex_y, row["z3_mm"], row["angle_deg"],
        )
        status = "SweptSolid: L, z2, z3 a úhel z příručky; průnik těl bez booleanu"
        if estimated:
            status = "estimated: vrchol z průměru z1/t a z2, řádky nesouhlasí o více než 8 mm"
        items.append((_definition(row, "JUNCTION", main, branch, ports, status=status), body))

    for row in TABLE["reducers"]:
        large, small = row["large_dn_od"], row["small_dn_od"]
        if large not in LIBRARY_SIZES or small not in LIBRARY_SIZES:
            continue
        t, tb = SOCKET_T[large], SOCKET_T[small]
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", row["large_socket_od_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET", (0, row["length_mm"], 0), (0, 1, 0), "SINK", row["small_socket_od_mm"],
                 end_type="SOCKET", insertion_mm=tb),
        )
        body, _ = reducer_lathes(
            row["length_mm"], OD[large], OD[small], WALL[large], WALL[small],
            row["large_socket_od_mm"], row["small_socket_od_mm"], t, tb,
            # Z1 se měří od malého ústí do konce kuželu; velké hnízdo zabírá L - Z1
            straight_large_mm=row["length_mm"] - row["z1_mm"],
        )
        items.append((_definition(row, "TRANSITION", large, small, ports,
                     status="SweptSolid kužel z katalogu L a Z1 (od malého ústí); rovný válec L-Z1 a malé hnízdo estimated"), body))

    for row in TABLE["cleanouts"]:
        dn = row["dn_od"]
        if dn not in LIBRARY_SIZES:
            continue
        t = SOCKET_T[dn]
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", row["socket_od_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SPIGOT", (0, row["length_mm"] - t, 0), (0, 1, 0), "SOURCE", OD[dn],
                 end_type="SPIGOT", insertion_mm=t),
        )
        body, _ = cleanout_lathes(
            row["length_mm"], row["od_mm"], WALL[dn], row["socket_od_mm"], t,
            row["z1_mm"], row["service_diameter_mm"], row["service_reach_mm"],
        )
        items.append((_definition(row, "USERDEFINED", dn, ports=ports,
                     status=f"SweptSolid z katalogu; {row['service_dimensions_status']}"), body))

    for row in TABLE["caps"]:
        dn = row["dn_od"]
        if dn not in LIBRARY_SIZES:
            continue
        t = SOCKET_T[dn]
        ports = (Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", SOCKET_OD[dn],
                      end_type="SOCKET", insertion_mm=t),)
        body, _ = cap_lathes(OD[dn], WALL[dn], SOCKET_OD[dn],
                             min(t, 0.8 * row["length_mm"]), row["length_mm"])
        items.append((_definition(row, "CAP", dn, ports=ports,
                     status="SweptSolid zátka: katalogová délka L, hnízdový profil approximated"), body))

    return items


def generate_pp_library(output_path):
    return generate_catalogue_library(pp_items(), output_path, name="PP MASTER 3 PLUS")


if __name__ == "__main__":
    output = generate_pp_library(ROOT / "out/tvarovky-EN1451-1.ifc")
    print(f"Vytvořeno: {output}")
