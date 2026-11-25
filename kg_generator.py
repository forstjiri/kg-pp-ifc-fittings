"""KG (EN 1401-1, Ostendorf) sortiment — výhradně IFC SweptSolid.

Rozměry pocházejí z data/kg_ostendorf.json (katalogové) a ze STEP referencí
(data/ostendorf, označeno measured). Co katalog neudává, je estimated.
"""

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

# poloměr ohybu per DN; katalogové z1 ≈ R·tan(α/2) + 1 mm (viz docs/plán)
BEND_RADIUS_MM = {110: 60.0, 125: 69.0, 160: 88.0}

# Naměřeno ze STEP (ústí z mouth_annuli): (délka hrot→hnízdo, průsečík od hrotu, odbočka, úhel, DN, DN odbočky)
# 220300z: spigot −215,7 → hnízdo +61,3; čelo odbočky (129,1; 10,8) = 187,5 od vrcholu
# 220400z: spigot −179,0 → hnízdo +61,5; čelo odbočky (118,7; −50,5) ⇒ vrchol 122,3 od hrotu, odbočka 118,9
BRANCH_MEASURED = {
    "220300": (277.0, 90.65, 187.3, 45, 110, 110),
    "220400": (240.5, 122.3, 118.9, 87, 110, 110),
    "222320": (317.5, 86.0, 227.4, 45, 160, 110),
    "222420": (273.5, 143.7, 143.0, 87, 160, 110),
}


def load_table():
    return json.loads((ROOT / "data/kg_ostendorf.json").read_text())


def _socket(table, dn):
    return table["sockets"][str(int(dn))]


def _ports_socket_spigot(socket_od, spigot_od, length, t, spigot_axis=(0.0, -1.0, 0.0)):
    """Port hnízda na ústí, port hrotu o t uvnitř těla; osy ven."""
    axis = np.asarray(spigot_axis, float)
    axis /= np.linalg.norm(axis)
    return (
        Port("SOCKET", (0, 0, 0), (0, 1, 0), "SINK", socket_od,
             end_type="SOCKET", insertion_mm=t),
        Port("SPIGOT", tuple(-t * axis), tuple(-axis), "SOURCE", spigot_od,
             end_type="SPIGOT", insertion_mm=t),
    )


def kg_elbow_lathes(row, table=None):
    """Koleno KGB přímo z katalogových hodnot (žádné škálování receptem)."""
    table = table or load_table()
    socket = _socket(table, row["dn_od"])
    od = float(row["dn_od"])
    radius = float(row.get("radius_mm") or BEND_RADIUS_MM[int(od)])
    straight = row["l1_mm"] - radius * math.tan(math.radians(row["angle_deg"]) / 2)
    return elbow_lathes(
        row["angle_deg"], od,
        socket_od_mm=socket["collar_diameter_mm"],
        wall_mm=socket["wall_mm"],
        socket_straight_mm=straight,
        spigot_straight_mm=straight,
        radius_mm=radius,
        # hnízdo z měření 220220z, škálované; nesmí překročit rovný úsek
        socket_len_mm=min(57.0 * od / 110.4, 0.85 * straight),
        spigot_tip_mm=30.0 * od / 110.4,
        socket_on_spigot=bool(row.get("socket_on_spigot", False)),
    )


def _definition(name, article, family, od, angle, length, z1, z2, ports,
                branch_od=None, z3=None, status=""):
    return Fitting(
        name=name, standard="EN 1401-1", article=article, family=family,
        od_mm=float(od), angle_deg=float(angle), length_mm=float(length),
        z1_mm=float(z1), z2_mm=float(z2),
        mesh_anchor_mm=(0, 0, 0), mesh_along=(0, 1, 0), mesh_side=(1, 0, 0),
        ports=ports, branch_od_mm=branch_od, z3_mm=z3, geometry_status=status,
    )


def kg_items():
    """(definice, SweptBody) pro celý KG sortiment bez jediného mesh-e."""
    table = load_table()
    items = []

    # 15 kolen KGB — katalogové kóty, ověřené IoU proti 5 STEP referencím
    for row in table["elbows"]:
        dn = row["dn_od"]
        socket = _socket(table, dn)
        body, mouths = kg_elbow_lathes(row, table)
        angle = math.radians(row["angle_deg"])
        d1 = np.array((math.sin(angle), math.cos(angle), 0.0))
        tip = mouths[1][0]
        t = socket["insertion_depth_t_mm"]
        if row.get("socket_on_spigot"):
            ports = (
                Port("SPIGOT", tuple(t * np.array((0.0, 1.0, 0.0))),
                     (0.0, -1.0, 0.0), "SOURCE", float(dn),
                     end_type="SPIGOT", insertion_mm=t, take_out_mm=row["l1_mm"]),
                Port("SOCKET", mouths[1][0], tuple(d1), "SINK", socket["collar_diameter_mm"],
                     end_type="SOCKET", insertion_mm=t, take_out_mm=row["l1_mm"]),
            )
        else:
            ports = (
                Port("SOCKET", mouths[0][0], mouths[0][1], "SINK", socket["collar_diameter_mm"],
                     end_type="SOCKET", insertion_mm=t, take_out_mm=row["l1_mm"]),
                Port("SPIGOT", tip - t * d1, tuple(d1), "SOURCE", float(dn),
                     end_type="SPIGOT", insertion_mm=t, take_out_mm=row["l1_mm"]),
            )
        definition = _definition(
            f"KG koleno {row['angle_deg']}° OD{dn}", row["article"], "BEND",
            dn, row["angle_deg"], row["l1_mm"], row["z1_mm"], row["z2_mm"], ports,
            status="SweptSolid z katalogu; hnízdový profil approximated z 220220z",
        )
        items.append((definition, body))

    # 12 odboček KGEA — 4 ze STEP, 8 škálovaných (estimated)
    for row in table["branches"]:
        dn, small = row["dn_od"], row["branch_dn_od"]
        sock, bsock = _socket(table, dn), _socket(table, small)
        article = row["article"]
        if article in BRANCH_MEASURED:
            length, vertex, branch_len, angle, _, _ = BRANCH_MEASURED[article]
            status = "SweptSolid z rozměrů STEP " + article + "z; hnízda approximated"
        else:
            scale = dn / (110 if dn <= 125 else 160)
            ref = BRANCH_MEASURED["220300" if row["angle_deg"] == 45 else "220400"]
            length, vertex, branch_len = (ref[0] * scale, ref[1] * scale, ref[2] * scale)
            angle = row["angle_deg"]
            status = "estimated: odvozeno škálováním ze STEP " + ref_key(article, row) + "; katalog L/z jen jako vlastnosti"
        rad = math.radians(angle)
        direction = np.array((math.sin(rad), math.cos(rad), 0.0))
        junction = np.array((0.0, vertex - length / 2, 0.0))
        t, tb = sock["insertion_depth_t_mm"], bsock["insertion_depth_t_mm"]
        ports = (
            Port("SPIGOT", (0, -length / 2 + t, 0), (0, -1, 0), "SOURCE", float(dn),
                 end_type="SPIGOT", insertion_mm=t),
            Port("SOCKET", (0, length / 2, 0), (0, 1, 0), "SINK", sock["collar_diameter_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET BRANCH", junction + branch_len * direction, tuple(direction),
                 "SINK", bsock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=tb),
        )
        definition = _definition(
            f"KG odbočka {row['angle_deg']}° OD{dn}/{small}", article, "JUNCTION",
            dn, row["angle_deg"], length, row["z1_mm"], row["z2_mm"], ports,
            branch_od=small, z3=row["z3_mm"], status=status,
        )
        body, _ = branch_lathes(
            length, float(dn), sock["wall_mm"], sock["collar_diameter_mm"], t,
            float(small), bsock["wall_mm"], bsock["collar_diameter_mm"], tb,
            junction[1], branch_len, angle,
        )
        items.append((definition, body))

    # 3 excentrické redukce KGR
    for row in table["reducers"]:
        dn, small = row["dn_od"], row["branch_dn_od"]
        sock, bsock = _socket(table, dn), _socket(table, small)
        length = 176.5 if row["article"] == "222700" else row["L_mm"] * 1.5
        t, tb = sock["insertion_depth_t_mm"], bsock["insertion_depth_t_mm"]
        offset = row["z1_mm"]
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", sock["collar_diameter_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SOCKET", (offset, length, 0), (0, 1, 0), "SINK", bsock["collar_diameter_mm"],
                 end_type="SOCKET", insertion_mm=tb),
        )
        definition = _definition(
            f"KG redukce OD{dn}/{small}", row["article"], "TRANSITION",
            dn, 0, length, row["z1_mm"], 0, ports, branch_od=small,
            status="estimated: souosý kužel s rovným válcem, excentricita na malém hnízdu; oba konce hnízda; tvar hrdla ze STEP 222700z (plný boss OD194×88, kužel 29 mm)",
        )
        body, _ = reducer_lathes(
            length, float(dn), float(small), sock["wall_mm"], bsock["wall_mm"],
            float(sock["collar_diameter_mm"]) + 12.0 * dn / 160.0, bsock["collar_diameter_mm"],
            t, tb, offset_mm=offset,
            straight_large_mm=88.0 * dn / 160.0, cone_len_mm=29.0 * dn / 160.0,
        )
        items.append((definition, body))

    # 3 zátky KGK
    for row in table["caps"]:
        dn = row["dn_od"]
        sock = _socket(table, dn)
        t = sock["insertion_depth_t_mm"]
        length = row["length_mm"]
        ports = (Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK",
                      sock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=t),)
        definition = _definition(
            f"KG zátka OD{dn}", row["article"], "USERDEFINED", dn, 0, length, 0, 0,
            ports, status="estimated: hnízdový profil a čelo zátky approximated",
        )
        body, _ = cap_lathes(float(dn), sock["wall_mm"], sock["collar_diameter_mm"],
                             min(57.0 * dn / 110.4, 0.8 * length), float(length))
        items.append((definition, body))

    # 3 čistící kusy KGRE (svislý typ jako 175600)
    for row in table["cleanouts"]:
        dn = row["dn_od"]
        sock = _socket(table, dn)
        t = sock["insertion_depth_t_mm"]
        length = row["length_mm"]
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK", sock["collar_diameter_mm"],
                 end_type="SOCKET", insertion_mm=t),
            Port("SPIGOT", (0, length - t, 0), (0, 1, 0), "SOURCE", float(dn),
                 end_type="SPIGOT", insertion_mm=t),
        )
        definition = _definition(
            f"KG čistící kus OD{dn}", row["article"], "USERDEFINED", dn, 0, length,
            length * 0.6, 0, ports,
            status="estimated: boční víčko a hrdlo z katalogu nejsou rozměrována",
        )
        body, _ = cleanout_lathes(
            float(length), float(dn), sock["wall_mm"], sock["collar_diameter_mm"], t,
            length * 0.6, float(dn) * 0.65,
        )
        items.append((definition, body))

    return items


def ref_key(article, row):
    return "220300z" if row["angle_deg"] == 45 else "220400z"


def generate_kg_library(output_path):
    return generate_catalogue_library(kg_items(), output_path, name="PVC-U KG")


if __name__ == "__main__":
    output = generate_kg_library(ROOT / "out/tvarovky-EN1401-1.ifc")
    print(f"Vytvořeno: {output}")
