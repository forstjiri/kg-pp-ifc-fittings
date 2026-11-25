"""Generate the approximate, dimension-driven Pipelife PP fitting library."""

import json
from pathlib import Path

import numpy as np

from definice import Fitting, Port
from generator import generate_catalogue_library
from swept_geometrie import branch_lathes, cleanout_lathes, elbow_lathes, reducer_lathes


ROOT = Path(__file__).parent
TABLE = json.loads((ROOT / "data/pipelife_master3plus.json").read_text())
OD = {32: 33.0, 40: 41.1, 50: 51.0, 75: 76.1, 90: 91.2, 110: 111.3, 125: 126.3, 160: 161.5}
WALL = {32: 1.8, 40: 1.8, 50: 2.0, 75: 2.1, 90: 2.5, 110: 3.0, 125: 3.5, 160: 4.4}
LIBRARY_SIZES = {32, 40, 50, 75, 110, 125, 160}
SOCKET_T = {int(k): v for k, v in TABLE["dimension_status"]["socket"]["insertion_depth_t_mm"].items()}
SOCKET_OD = {int(k): v for k, v in TABLE["dimension_status"]["socket"]["collar_outer_diameter_mm"].items()}


def _definition(row, family, main_od, branch_od=None, ports=()):
    title = (
        f"PP koleno {row['angle_deg']}° OD{main_od}"
        if family == "BEND"
        else f"PP odbočka {row['angle_deg']}° OD{main_od}/{branch_od}"
    )
    return Fitting(
        name=title,
        standard="EN 1451-1",
        article=row["article"],
        family=family,
        od_mm=OD[main_od],
        angle_deg=row["angle_deg"],
        length_mm=row["length_mm"],
        z1_mm=row["z1_mm"],
        z2_mm=row["z2_mm"],
        mesh_anchor_mm=(0, 0, 0),
        mesh_along=(0, 1, 0),
        mesh_side=(1, 0, 0),
        ports=ports,
        branch_od_mm=OD[branch_od] if branch_od else None,
        z3_mm=row.get("z3_mm"),
        geometry_status=(
            {
                "BEND": (
                    "Approximate SweptSolid from the measured KG 45 deg OD110 recipe, scaled by OD; "
                    "catalogue angle and OD retained. Socket section and bend radius approximate. "
                    "PP catalogue l1/l2/z semantics are ambiguous (see missing.md); KG recipe take-outs used."
                ),
                "JUNCTION": (
                    "Approximate SweptSolid: socketed main run plus angled branch tube, solid overlap "
                    "at the junction. Catalogue length/z1/z3/angle retained on ports; junction detail approximate."
                ),
            }.get(family, "Approximate SweptSolid.")
        ),
    )


def pp_items():
    items = []
    for row in TABLE["elbows"]:
        dn = row["dn_od"]
        if dn not in LIBRARY_SIZES:
            continue
        body, mouths = elbow_lathes(row["angle_deg"], OD[dn], SOCKET_OD[dn], WALL[dn])
        ports = tuple(
            Port(name, tuple(np.round(position, 6)), tuple(np.round(axis, 6)), name, OD[dn])
            for (name, flow), (position, axis) in zip(
                (("SOURCE", "SOURCE"), ("SINK", "SINK")), mouths
            )
        )
        definition = _definition(row, "BEND", dn, ports=ports)
        items.append((definition, body))

    for row in TABLE["simple_branches"]:
        main, branch = row["dn_od"], row["branch_dn_od"]
        if main not in LIBRARY_SIZES or branch not in LIBRARY_SIZES:
            continue
        angle = np.deg2rad(row["angle_deg"])
        junction = np.array([0.0, row["z1_mm"], 0.0])
        branch_end = junction + row["z3_mm"] * np.array([np.sin(angle), np.cos(angle), 0.0])
        ports = (
            Port("SOURCE", (0, -row["length_mm"] / 2, 0), (0, -1, 0), "SOURCE", OD[main]),
            Port("SINK", (0, row["length_mm"] / 2, 0), (0, 1, 0), "SINK", OD[main]),
            Port("SINK BRANCH", tuple(branch_end), (np.sin(angle), np.cos(angle), 0), "SINK", OD[branch]),
        )
        definition = _definition(row, "JUNCTION", main, branch, ports)
        body, _ = branch_lathes(
            row["length_mm"], OD[main], WALL[main], SOCKET_OD[main], SOCKET_T[main],
            OD[branch], WALL[branch], SOCKET_OD[branch], SOCKET_T[branch],
            row["z1_mm"], row["z3_mm"], row["angle_deg"],
        )
        items.append((definition, body))

    for row in TABLE["reducers"]:
        large, small = row["large_dn_od"], row["small_dn_od"]
        if large not in LIBRARY_SIZES or small not in LIBRARY_SIZES:
            continue
        definition = Fitting(
            name=f"PP redukce OD{large}/{small}",
            standard="EN 1451-1",
            article=row["article"],
            family="TRANSITION",
            od_mm=OD[large],
            angle_deg=0,
            length_mm=row["length_mm"],
            z1_mm=row["z1_mm"],
            z2_mm=0,
            mesh_anchor_mm=(0, 0, 0),
            mesh_along=(0, 1, 0),
            mesh_side=(1, 0, 0),
            ports=(
                Port("SOURCE", (0, 0, 0), (0, -1, 0), "SOURCE", OD[large]),
                Port("SINK", (0, row["length_mm"], 0), (0, 1, 0), "SINK", OD[small]),
            ),
            geometry_status=(
                "Approximate SweptSolid: conical wall tube with measured-section socket cups; "
                "catalogue length and end ODs retained. Taper and bore transition approximate."
            ),
        )
        body, _ = reducer_lathes(
            row["length_mm"], OD[large], OD[small], WALL[large], WALL[small],
            row["large_socket_od_mm"], row["small_socket_od_mm"],
            SOCKET_T[large], SOCKET_T[small],
        )
        items.append((definition, body))

    for row in TABLE["cleanouts"]:
        dn = row["dn_od"]
        if dn not in LIBRARY_SIZES:
            continue
        definition = Fitting(
            name=f"PP svislý čistící kus OD{dn}",
            standard="EN 1451-1",
            article=row["article"],
            family="USERDEFINED",
            od_mm=row["od_mm"],
            angle_deg=0,
            length_mm=row["length_mm"],
            z1_mm=row["z1_mm"],
            z2_mm=0,
            mesh_anchor_mm=(0, 0, 0),
            mesh_along=(0, 0, 1),
            mesh_side=(1, 0, 0),
            ports=(
                Port("SOURCE", (0, 0, 0), (0, 0, -1), "SOURCE", row["od_mm"]),
                Port("SINK", (0, 0, row["length_mm"]), (0, 0, 1), "SINK", row["od_mm"]),
            ),
            geometry_status=(
                "Approximate SweptSolid vertical cleanout; catalogue envelope retained. "
                f"Side cover dimensions: {row['service_dimensions_status']}; "
                "socket bore, side stub and flat cover approximate."
            ),
        )
        body, _ = cleanout_lathes(
            row["length_mm"], row["od_mm"], WALL[dn], row["socket_od_mm"], SOCKET_T[dn],
            row["z1_mm"], row["service_diameter_mm"],
        )
        items.append((definition, body))
    return items


def generate_pp_library(output_path):
    return generate_catalogue_library(
        pp_items(), output_path, name="PP MASTER 3 PLUS"
    )


if __name__ == "__main__":
    output = generate_pp_library(ROOT / "out/tvarovky-EN1451-1.ifc")
    print(f"Vytvořeno: {output}")
