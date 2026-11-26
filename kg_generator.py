"""KG (EN 1401-1, Ostendorf): SweptSolid z katalogu a STEP referencí."""
import json
import math
from pathlib import Path
import numpy as np
from definice import BRANCH_MEASURED as _MEASURED, Fitting, Port
from generator import generate_catalogue_library
from swept_geometrie import (
    branch_lathes, cap_lathes, cleanout_lathes, elbow_lathes, reducer_lathes,
)
ROOT = Path(__file__).parent
BEND_RADIUS_MM = {110: 60.0, 125: 69.0, 160: 88.0}
BRANCH_MEASURED = {article.rstrip("z"): value for article, value in _MEASURED.items()}
def load_table():
    return json.loads((ROOT / "data/kg_ostendorf.json").read_text())
def _socket(table, dn):
    return table["sockets"][str(int(dn))]
def _definition(name, article, family, od, angle, length, z1, z2, ports,
                branch_od=None, z3=None, status=""):
    return Fitting(
        name=name, standard="EN 1401-1", article=article, family=family,
        od_mm=float(od), angle_deg=float(angle), length_mm=float(length),
        z1_mm=float(z1), z2_mm=float(z2),
        mesh_anchor_mm=(0, 0, 0), mesh_along=(0, 1, 0), mesh_side=(1, 0, 0),
        ports=ports, branch_od_mm=branch_od, z3_mm=z3, geometry_status=status,
    )
def kg_elbow_lathes(row, table=None):
    """Koleno KGB přímo z katalogových kót (žádné škálování receptem)."""
    table = table or load_table()
    socket = _socket(table, row["dn_od"])
    od = float(row["dn_od"])
    radius = float(row.get("radius_mm") or BEND_RADIUS_MM[int(od)])
    straight = row["l1_mm"] - radius * math.tan(math.radians(row["angle_deg"]) / 2)
    return elbow_lathes(
        row["angle_deg"], od, socket_od_mm=socket["collar_diameter_mm"],
        wall_mm=socket["wall_mm"], socket_straight_mm=straight,
        spigot_straight_mm=straight, radius_mm=radius,
        socket_len_mm=min(57.0 * od / 110.4, 0.85 * straight),
        spigot_tip_mm=30.0 * od / 110.4,
        socket_on_spigot=bool(row.get("socket_on_spigot", False)),
    )
def kg_items():
    """(definice, SweptBody) pro celý KG sortiment bez jediného mesh-e."""
    table = load_table()
    items = []
    for row in table["elbows"]:  # 15 kolen, ověřených IoU proti 5 STEP referencím
        dn, socket = row["dn_od"], _socket(table, row["dn_od"])
        body, mouths = kg_elbow_lathes(row, table)
        angle = math.radians(row["angle_deg"])
        d1 = np.array((math.sin(angle), math.cos(angle), 0.0))
        t, tip, take_out = socket["insertion_depth_t_mm"], mouths[1][0], row["l1_mm"]
        if row.get("socket_on_spigot"):
            ports = (
                Port("SPIGOT", tuple(t * np.array((0.0, 1.0, 0.0))),
                     (0.0, -1.0, 0.0), "SOURCE", float(dn),
                     end_type="SPIGOT", insertion_mm=t, take_out_mm=take_out),
                Port("SOCKET", tip, tuple(d1), "SINK", socket["collar_diameter_mm"],
                     end_type="SOCKET", insertion_mm=t, take_out_mm=take_out),
            )
        else:
            ports = (
                Port("SOCKET", mouths[0][0], mouths[0][1], "SINK",
                     socket["collar_diameter_mm"], end_type="SOCKET",
                     insertion_mm=t, take_out_mm=take_out),
                Port("SPIGOT", tip - t * d1, tuple(d1), "SOURCE", float(dn),
                     end_type="SPIGOT", insertion_mm=t, take_out_mm=take_out),
            )
        items.append((_definition(
            f"KG koleno {row['angle_deg']}° OD{dn}", row["article"], "BEND",
            dn, row["angle_deg"], row["l1_mm"], row["z1_mm"], row["z2_mm"], ports,
            status="SweptSolid z katalogu; hnízdový profil approximated z 220220z",
        ), body))
    for row in table["branches"]:  # 12 odboček: 4 ze STEP, 8 škálovaných
        dn, small = row["dn_od"], row["branch_dn_od"]
        sock, bsock = _socket(table, dn), _socket(table, small)
        article = row["article"]
        if article in BRANCH_MEASURED:
            length, vertex, branch_len, angle, _, _ = BRANCH_MEASURED[article]
            status = f"SweptSolid z rozměrů STEP {article}z; hnízda approximated"
        else:
            scale = dn / (110 if dn <= 125 else 160)
            ref = BRANCH_MEASURED["220300" if row["angle_deg"] == 45 else "220400"]
            length, vertex, branch_len = (ref[0] * scale, ref[1] * scale, ref[2] * scale)
            angle = row["angle_deg"]
            reference = "220300z" if angle == 45 else "220400z"
            status = (f"estimated: odvozeno škálováním ze STEP {reference}; "
                      "katalog L/z jen jako vlastnosti")
        rad = math.radians(angle)
        direction = np.array((math.sin(rad), math.cos(rad), 0.0))
        junction = np.array((0.0, vertex - length / 2, 0.0))
        t, tb = sock["insertion_depth_t_mm"], bsock["insertion_depth_t_mm"]
        ports = (
            Port("SPIGOT", (0, -length / 2 + t, 0), (0, -1, 0), "SOURCE", float(dn),
                 end_type="SPIGOT", insertion_mm=t),
            Port("SOCKET", (0, length / 2, 0), (0, 1, 0), "SINK",
                 sock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=t),
            Port("SOCKET BRANCH", junction + branch_len * direction, tuple(direction),
                 "SINK", bsock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=tb),
        )
        body, _ = branch_lathes(
            length, float(dn), sock["wall_mm"], sock["collar_diameter_mm"], t,
            float(small), bsock["wall_mm"], bsock["collar_diameter_mm"], tb,
            junction[1], branch_len, angle,
        )
        items.append((_definition(
            f"KG odbočka {row['angle_deg']}° OD{dn}/{small}", article, "JUNCTION",
            dn, row["angle_deg"], length, row["z1_mm"], row["z2_mm"], ports,
            branch_od=small, z3=row["z3_mm"], status=status,
        ), body))
    for row in table["reducers"]:  # 3 excentrické redukce
        dn, small = row["dn_od"], row["branch_dn_od"]
        sock, bsock = _socket(table, dn), _socket(table, small)
        length = 176.5 if row["article"] == "222700" else row["L_mm"] * 1.5
        t, tb = sock["insertion_depth_t_mm"], bsock["insertion_depth_t_mm"]
        offset = 23.1 * dn / 160.0  # z STEP 222700z, katalog z1 neodpovídá
        ports = (
            Port("SPIGOT", (-offset, t, 0), (0, -1, 0), "SOURCE", float(dn),
                 end_type="SPIGOT", insertion_mm=t),
            Port("SOCKET", (0, length, 0), (0, 1, 0), "SINK",
                 bsock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=tb),
        )
        body, _ = reducer_lathes(
            length, float(dn), float(small), sock["wall_mm"], bsock["wall_mm"],
            float(sock["collar_diameter_mm"]) + 12.0 * dn / 160.0,
            bsock["collar_diameter_mm"], t, tb, offset_mm=offset,
            straight_large_mm=88.0 * dn / 160.0, cone_len_mm=29.0 * dn / 160.0,
            plain_large_end=True,
        )
        items.append((_definition(
            f"KG redukce OD{dn}/{small}", row["article"], "TRANSITION",
            dn, 0, length, offset, 0, ports, branch_od=small,
            status="estimated: holý široký konec, kužel s excentricitou 23,1×DN/160 ze STEP "
                   "222700z, samice jen nahoře; hrdlo boss OD194×88, kužel 29 mm",
        ), body))
    for row in table["caps"]:  # 3 zátky
        dn = row["dn_od"]
        sock = _socket(table, dn)
        t, length = sock["insertion_depth_t_mm"], row["length_mm"]
        ports = (Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK",
                      sock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=t),)
        body, _ = cap_lathes(float(dn), sock["wall_mm"], sock["collar_diameter_mm"],
                             min(57.0 * dn / 110.4, 0.8 * length), float(length))
        items.append((_definition(
            f"KG zátka OD{dn}", row["article"], "USERDEFINED", dn, 0, length, 0, 0,
            ports, status="estimated: hnízdový profil a čelo zátky approximated",
        ), body))
    for row in table["cleanouts"]:  # 3 čistící kusy; víčko a krk ze STEP 175600z
        dn = row["dn_od"]
        sock = _socket(table, dn)
        t, length = sock["insertion_depth_t_mm"], row["length_mm"]
        scale = dn / 110.0
        z1, cover_d, cover_reach = 120.0 * scale, 111.5 * scale, 86.5 * scale
        cover_t, neck_d = 17.0 * scale, 98.0 * scale
        status = ("SweptSolid: víčko a krk ze STEP 175600z, délka z katalogu"
                  if row["article"] == "220600" else
                  "estimated: víčko a krk ze STEP 175600z škálované DN/110, délka z katalogu")
        ports = (
            Port("SOCKET", (0, 0, 0), (0, -1, 0), "SINK",
                 sock["collar_diameter_mm"], end_type="SOCKET", insertion_mm=t),
            Port("SPIGOT", (0, length - t, 0), (0, 1, 0), "SOURCE", float(dn),
                 end_type="SPIGOT", insertion_mm=t),
        )
        body, _ = cleanout_lathes(
            float(length), float(dn), sock["wall_mm"], sock["collar_diameter_mm"], t,
            z1, cover_d, cover_reach,
            cover_thickness_mm=cover_t, neck_diameter_mm=neck_d,
        )
        items.append((_definition(
            f"KG čistící kus OD{dn}", row["article"], "USERDEFINED", dn, 0, length,
            z1, 0, ports, status=status,
        ), body))
    return items
def generate_kg_library(output_path):
    return generate_catalogue_library(kg_items(), output_path, name="PVC-U KG")
if __name__ == "__main__":
    print(f"Vytvořeno: {generate_kg_library(ROOT / 'out/tvarovky-EN1401-1.ifc')}")
