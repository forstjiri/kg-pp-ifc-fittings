"""Pipelife PP (EN 1451-1): SweptSolid z rozměrů příručky 2026."""
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
OD = {32: 33.0, 40: 41.1, 50: 51.0, 75: 76.1, 90: 91.2,
      110: 111.3, 125: 126.3, 160: 161.5}
WALL = {32: 1.8, 40: 1.8, 50: 2.0, 75: 2.1, 90: 2.5,
        110: 3.0, 125: 3.5, 160: 4.4}
DN_BY_SIZE = {32: 30, 40: 40, 50: 50, 75: 70, 90: 90,
              110: 100, 125: 125, 160: 150}
LIBRARY_SIZES = {32, 40, 50, 75, 110, 125, 160}
_RAW = json.loads((ROOT / "data/pipelife_master3plus.json").read_text())
SOCKET_T = {int(k): v for k, v in _RAW["dimension_status"]["socket"]["insertion_depth_t_mm"].items()}
SOCKET_OD = {int(k): v for k, v in _RAW["dimension_status"]["socket"]["collar_outer_diameter_mm"].items()}


def _expand(table):
    """VRACÍ původní podobu řádků: hodnoty sdílené na rozměr se jen rozvinou."""
    for row in table["elbows"] + table["cleanouts"]:
        dn = row["dn_od"]
        row.update(DN=DN_BY_SIZE[dn], od_mm=OD[dn], socket_od_mm=SOCKET_OD[dn])
    for row in table["reducers"]:
        row.update(DN=DN_BY_SIZE[row["large_dn_od"]],
                   large_socket_od_mm=SOCKET_OD[row["large_dn_od"]],
                   small_socket_od_mm=SOCKET_OD[row["small_dn_od"]])
    for row in table["simple_branches"]:
        row["DN"] = DN_BY_SIZE[row["dn_od"]]
        # D/D1/D2/Dmax se ve zdroji vyskytovaly právě u řádků 87,5°.
        if row["angle_deg"] == 87.5:
            row.update(D_mm=OD[row["dn_od"]], D1_mm=OD[row["branch_dn_od"]],
                       D2_mm=SOCKET_OD[row["branch_dn_od"]],
                       Dmax_mm=SOCKET_OD[row["dn_od"]])
    for row in table["caps"]:
        row["DN"] = DN_BY_SIZE[row["dn_od"]]
    return table


TABLE = _expand(_RAW)
# Další výrobní série (Ostendorf HT) má vlastní OD/stěny/hrdla; řádky nesou překrytí.
_HT = json.loads((ROOT / "data/ostendorf_ht.json").read_text())
TABLE["simple_branches"].extend(_HT["simple_branches"])
def _bend_radii():
    """R z katalogového z1 = R·tan(α/2) + c (LSQ přes úhly na DN)."""
    result = {}
    for dn in OD:
        rows = [r for r in TABLE["elbows"] if r["dn_od"] == dn]
        design = np.array([[math.tan(math.radians(r["angle_deg"]) / 2), 1.0]
                           for r in rows])
        z = np.array([r["z1_mm"] for r in rows], float)
        (radius, _), *_ = np.linalg.lstsq(design, z, rcond=None)
        result[dn] = float(radius)
    return result
BEND_RADIUS = _bend_radii()
TITLES = {
    "BEND": lambda r, main, _: f"PP koleno {r['angle_deg']}° OD{main}",
    "JUNCTION": lambda r, main, small: f"PP odbočka {r['angle_deg']}° OD{main}/{small}",
    "TRANSITION": lambda r, main, small: f"PP redukce OD{main}/{small}",
    "CAP": lambda r, main, _: f"PP zátka OD{main}",
    "USERDEFINED": lambda r, main, _: f"PP čistící kus OD{main}",
}
def _legacy_article(row, family):
    """Starý článek 3496… se stejnými rozměry (jen jako vlastnost typu)."""
    for key, legacy in TABLE["legacy_article_examples"].items():
        if all(legacy.get(field) == row.get(field) for field in
               ("family", "dn_od", "branch_dn_od", "angle_deg")):
            return key
    return None
def _definition(row, family, main_dn, branch_dn=None, ports=(), status="",
                name=None, od=None, branch_od=None):
    return Fitting(
        name=name or TITLES[family](row, main_dn, branch_dn), standard="EN 1451-1",
        article=row["article"], family="USERDEFINED" if family == "CAP" else family,
        od_mm=float(od) if od is not None else OD[main_dn], angle_deg=row.get("angle_deg", 0),
        length_mm=row["length_mm"], z1_mm=row.get("z1_mm", 0),
        z2_mm=row.get("z2_mm", 0),
        mesh_anchor_mm=(0, 0, 0), mesh_along=(0, 1, 0), mesh_side=(1, 0, 0),
        ports=ports, branch_od_mm=(float(branch_od) if branch_od is not None
                                   else OD[branch_dn] if branch_dn else None),
        z3_mm=row.get("z3_mm"), geometry_status=status,
        dn_mm=float(main_dn), branch_dn_mm=float(branch_dn) if branch_dn else None,
        legacy_article=_legacy_article(
            row, {"CAP": "cap", "USERDEFINED": "cleanout"}.get(family, family.lower())),
    )
def pp_items(sizes=None):
    """Volitelně omezit rozsah DN; výchozí knihovna vynechává 90."""
    sizes = LIBRARY_SIZES if sizes is None else set(sizes)
    items = []
    for row in TABLE["elbows"]:
        dn = row["dn_od"]
        if dn not in sizes:
            continue
        angle = math.radians(row["angle_deg"])
        d1 = np.array((math.sin(angle), math.cos(angle), 0.0))
        t = SOCKET_T[dn]
        straight = row["l2_mm"]
        body, mouths = elbow_lathes(
            row["angle_deg"], OD[dn], SOCKET_OD[dn], WALL[dn],
            socket_straight_mm=straight,
            spigot_straight_mm=row["length_mm"] - row["z1_mm"],
            radius_mm=BEND_RADIUS[dn], socket_len_mm=min(t, 0.85 * straight),
            spigot_tip_mm=row["l1_mm"],
        )
        ports = (
            Port("SOCKET", mouths[0][0], mouths[0][1], "SINK", SOCKET_OD[dn],
                 end_type="SOCKET", insertion_mm=t, take_out_mm=row["length_mm"]),
            Port("SPIGOT", mouths[1][0] - t * d1, tuple(d1), "SOURCE", OD[dn],
                 end_type="SPIGOT", insertion_mm=t, take_out_mm=row["length_mm"]),
        )
        items.append((_definition(row, "BEND", dn, ports=ports,
                      status="SweptSolid z příručky 2026: L, z1, l1, l2, Dmax, t; "
                             "poloměr ohybu LSQ ze z1"), body))
    for row in TABLE["simple_branches"]:
        main, small = row["dn_od"], row["branch_dn_od"]
        if main not in sizes or small not in sizes:
            continue
        angle = math.radians(row["angle_deg"])
        length = row["length_mm"]
        od_main = float(row.get("od_mm", OD[main]))
        od_small = float(row.get("branch_od_mm", OD[small]))
        sock_main = float(row.get("socket_od_mm", SOCKET_OD[main]))
        sock_small = float(row.get("branch_socket_od_mm", SOCKET_OD[small]))
        t = float(row.get("insertion_t_mm", SOCKET_T[main]))
        tb = float(row.get("branch_insertion_t_mm", SOCKET_T[small]))
        from_socket, from_spigot = length / 2 - row["z2_mm"], -length / 2 + row["z1_mm"] + t
        estimated = abs(from_socket - from_spigot) > 8.0
        vertex_y = (from_socket + from_spigot) / 2
        direction = np.array((math.sin(angle), math.cos(angle), 0.0))
        body, mouths = branch_lathes(
            length, od_main, float(row.get("wall_mm", WALL[main])), sock_main, t,
            od_small, float(row.get("branch_wall_mm", WALL[small])), sock_small, tb,
            vertex_y, row["z3_mm"], row["angle_deg"], cup_outward=True,
        )
        branch_mouth, branch_axis = mouths[-1]
        ports = (
            Port("SPIGOT", (0, -length / 2 + t, 0), (0, -1, 0), "SOURCE", od_main,
                 end_type="SPIGOT", insertion_mm=t),
            Port("SOCKET", (0, length / 2, 0), (0, 1, 0), "SINK", sock_main,
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET BRANCH", tuple(branch_mouth), tuple(branch_axis),
                 "SINK", sock_small, end_type="SOCKET", insertion_mm=tb),
        )
        status = row.get("geometry_status") or (
            "estimated: vrchol z průměru z1/t a z2, řádky nesouhlasí o více než 8 mm"
            if estimated else
            "SweptSolid: L, z2, z3 a úhel z příručky; průnik těl bez booleanu")
        items.append((_definition(row, "JUNCTION", main, small, ports, status,
                                  name=row.get("display_name"), od=od_main,
                                  branch_od=od_small), body))
    for row in TABLE["reducers"]:
        large, small = row["large_dn_od"], row["small_dn_od"]
        if large not in sizes or small not in sizes:
            continue
        t, tb = SOCKET_T[large], SOCKET_T[small]
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", row["large_socket_od_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET", (0, row["length_mm"], 0), (0, 1, 0), "SINK",
                 row["small_socket_od_mm"], end_type="SOCKET", insertion_mm=tb),
        )
        body, _ = reducer_lathes(
            row["length_mm"], OD[large], OD[small], WALL[large], WALL[small],
            row["large_socket_od_mm"], row["small_socket_od_mm"], t, tb,
            # Z1 se měří od malého ústí do konce kuželu; velké hnízdo = L − Z1
            straight_large_mm=row["length_mm"] - row["z1_mm"],
        )
        items.append((_definition(
            row, "TRANSITION", large, small, ports,
            status="SweptSolid kužel z katalogu L a Z1 (od malého ústí); rovný válec "
                   "L−Z1 a malé hnízdo estimated",
        ), body))
    for row in TABLE["cleanouts"]:
        dn = row["dn_od"]
        if dn not in sizes:
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
        items.append((_definition(
            row, "USERDEFINED", dn, ports=ports,
            status=f"SweptSolid z katalogu; {row['service_dimensions_status']}",
        ), body))
    for row in TABLE["caps"]:
        dn = row["dn_od"]
        if dn not in sizes:
            continue
        t = SOCKET_T[dn]
        ports = (Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", SOCKET_OD[dn],
                      end_type="SOCKET", insertion_mm=t),)
        body, _ = cap_lathes(OD[dn], WALL[dn], SOCKET_OD[dn],
                             min(t, 0.8 * row["length_mm"]), row["length_mm"])
        items.append((_definition(
            row, "CAP", dn, ports=ports,
            status="SweptSolid zátka: katalogová délka L, hnízdový profil approximated",
        ), body))
    return items
def pp_pipe_specs():
    """Katalogové trubky pro tažení: DN -> (OD, stěna, t hnízda, OD hrdla)."""
    return {dn: (OD[dn], WALL[dn], SOCKET_T[dn], SOCKET_OD[dn])
            for dn in sorted(OD)}


def generate_pp_library(output_path):
    return generate_catalogue_library(pp_items(), output_path, name="PP MASTER 3 PLUS")
if __name__ == "__main__":
    print(f"Vytvořeno: {generate_pp_library(ROOT / 'out/tvarovky-EN1451-1.ifc')}")
