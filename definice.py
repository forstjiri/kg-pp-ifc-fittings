"""Ověřené definice výrobků pro IFC knihovnu."""

import math
from dataclasses import dataclass


KG_OD = (110, 125, 160)


@dataclass(frozen=True)
class Port:
    name: str
    position_mm: tuple[float, float, float]
    axis: tuple[float, float, float]
    flow: str
    od_mm: float
    end_type: str = "SOCKET"  # SOCKET | SPIGOT
    insertion_mm: float | None = None  # catalogue insertion depth t
    take_out_mm: float | None = None  # catalogue take-out (vertex -> face)


@dataclass(frozen=True)
class Fitting:
    name: str
    standard: str
    article: str
    family: str
    od_mm: float
    angle_deg: float
    length_mm: float
    z1_mm: float
    z2_mm: float
    mesh_anchor_mm: tuple[float, float, float]
    mesh_along: tuple[float, float, float]
    mesh_side: tuple[float, float, float]
    ports: tuple[Port, ...]
    branch_od_mm: float | None = None
    z3_mm: float | None = None
    geometry_status: str | None = None
    legacy_article: str | None = None


# Ostendorf KG 220220 (DN/OD 110, 45°); catalogue dimensions in mm.
KG_45_DN110 = Fitting(
    name="KG koleno 45° OD110",
    standard="ČSN EN 1401-1",
    article="220220",
    family="BEND",
    od_mm=110.0,
    angle_deg=45.0,
    length_mm=85.0,
    z1_mm=25.0,
    z2_mm=29.0,
    mesh_anchor_mm=(0.0, 87.1, 0.0),
    mesh_along=(-0.7071067811865476, -0.7071067811865476, 0.0),
    mesh_side=(0.7071067811865476, -0.7071067811865476, 0.0),
    ports=(
        Port(
            name="SINK OD 110",
            position_mm=(28.502580, 115.602580, 0.0),
            axis=(0.7071067811865475, 0.7071067811865475, 0.0),
            flow="SINK",
            od_mm=110.0,
        ),
        Port(
            name="SOURCE OD 110",
            position_mm=(0.0, 0.0, 0.0),
            axis=(0.0, -1.0, 0.0),
            flow="SOURCE",
            od_mm=110.0,
        ),
    ),
)


KG_15_DN110 = Fitting(
    name="KG koleno 15° OD110",
    standard="ČSN EN 1401-1",
    article="220200",
    family="BEND",
    od_mm=110.0,
    angle_deg=15.0,
    length_mm=69.0,
    z1_mm=9.0,
    z2_mm=14.0,
    mesh_anchor_mm=(0.0, 68.424, 0.0),
    mesh_along=(0.0, 1.0, 0.0),
    mesh_side=(1.0, 0.0, 0.0),
    ports=(
        Port("SOURCE OD 110", (0, 0, 0), (0, -1, 0), "SOURCE", 110),
        Port(
            "SINK OD 110",
            (6.326823, 92.036308, 0),
            (0.2588190451, 0.9659258263, 0),
            "SINK",
            110,
        ),
    ),
)

KG_30_DN110 = Fitting(
    name="KG koleno 30° OD110",
    standard="ČSN EN 1401-1",
    article="220210",
    family="BEND",
    od_mm=110.0,
    angle_deg=30.0,
    length_mm=77.0,
    z1_mm=17.0,
    z2_mm=21.0,
    mesh_anchor_mm=(0.0, -4.9034702214894, 0.0),
    mesh_along=(0.0, 1.0, 0.0),
    mesh_side=(1.0, 0.0, 0.0),
    ports=(
        Port(
            "SOURCE OD 110",
            (38.5, -71.5874263129, 0),
            (0.5, -0.8660254038, 0),
            "SOURCE",
            110,
        ),
        Port(
            "SINK OD 110",
            (0, 23.0965297785, 0),
            (0, 1, 0),
            "SINK",
            110,
        ),
    ),
)


# Ostendorf KGEA 45° 160/110 (article 222320); catalogue dimensions in mm.
KG_BRANCH_45_DN160_DN110 = Fitting(
    name="KG odbočka 45° OD160/110",
    standard="ČSN EN 1401-1",
    article="222320",
    family="JUNCTION",
    od_mm=160.0,
    angle_deg=45.0,
    length_mm=242.0,
    z1_mm=2.0,
    z2_mm=168.0,
    mesh_anchor_mm=(0.0, 0.0, 0.0),
    mesh_along=(0.0, 1.0, 0.0),
    mesh_side=(1.0, 0.0, 0.0),
    ports=(
        Port(
            name="SOURCE OD 160",
            position_mm=(0.0, -237.33878, 0.0),
            axis=(0.0, -1.0, 0.0),
            flow="SOURCE",
            od_mm=160.0,
        ),
        Port(
            name="SINK OD 160",
            position_mm=(0.0, 0.0, 0.0),
            axis=(0.0, 1.0, 0.0),
            flow="SINK",
            od_mm=160.0,
        ),
        Port(
            name="SINK OD 110",
            position_mm=(126.42334, -24.91544, 0.0),
            axis=(0.7071067811865475, 0.7071067811865475, 0.0),
            flow="SINK",
            od_mm=110.0,
        ),
    ),
    branch_od_mm=110.0,
    z3_mm=159.0,
)


# Ostendorf KGR eccentric reducer 160/110; catalogue article 222700.
KG_REDUCER_160_110 = Fitting(
    name="KG excentrická redukce OD160/110",
    standard="ČSN EN 1401-1",
    article="222700",
    family="TRANSITION",
    od_mm=160.0,
    angle_deg=0.0,
    length_mm=115.0,
    z1_mm=34.0,
    z2_mm=0.0,
    mesh_anchor_mm=(0.0, 0.0, 0.0),
    mesh_along=(0.0, 1.0, 0.0),
    mesh_side=(1.0, 0.0, 0.0),
    ports=(
        Port(
            "SOURCE OD 160",
            (-23.05, -112.0, 0.0),
            (0.0, -1.0, 0.0),
            "SOURCE",
            160.0,
        ),
        Port(
            "SINK OD 110",
            (0.0, 64.0, 0.0),
            (0.0, 1.0, 0.0),
            "SINK",
            110.0,
        ),
    ),
    branch_od_mm=110.0,
)


KG_CAPS = tuple(
    Fitting(
        name=f"KG zátka OD{od}",
        standard="ČSN EN 1401-1",
        article=article,
        family="OBSTRUCTION",
        od_mm=float(od),
        angle_deg=0.0,
        length_mm=float(length),
        z1_mm=0.0,
        z2_mm=0.0,
        mesh_anchor_mm=(0.0, 0.0, 0.0),
        mesh_along=(0.0, 1.0, 0.0),
        mesh_side=(1.0, 0.0, 0.0),
        ports=(Port("SINK", (0, 0, 0), (0, -1, 0), "SINK", float(od)),),
        geometry_status=(
            "Approximate parametric cap; catalogue DN and length retained. "
            "Socket bore/collar dimensions are estimated."
        ),
    )
    for od, article, length in (
        (110, "220630", 41),
        (125, "221630", 45),
        (160, "222630", 53),
    )
)

# End-cap collar and body-wall dimensions not tabulated by this catalogue section.
# These are explicit geometry estimates (mm), not Ostendorf manufacturing values.
KG_CAP_GEOMETRY = {
    110: {"socket_od_mm": 126.9, "wall_mm": 3.2},
    125: {"socket_od_mm": 145.6, "wall_mm": 3.2},
    160: {"socket_od_mm": 183.4, "wall_mm": 4.0},
}


# Ostendorf KGRE purging/cleanout pieces; catalogue envelope lengths in mm.
# The cleanout body and removable-cover detail are not available as a local mesh.
KG_CLEANOUTS = tuple(
    Fitting(
        name=f"KG svislý čistící kus OD{od}",
        standard="ČSN EN 1401-1",
        article=article,
        family="USERDEFINED",
        od_mm=float(od),
        angle_deg=0.0,
        length_mm=float(length),
        z1_mm=0.0,
        z2_mm=0.0,
        mesh_anchor_mm=(0.0, 0.0, 0.0),
        mesh_along=(0.0, 0.0, 1.0),
        mesh_side=(1.0, 0.0, 0.0),
        ports=(
            Port("SOURCE", (0, 0, 0), (0, 0, -1), "SOURCE", float(od)),
            Port("SINK", (0, 0, length), (0, 0, 1), "SINK", float(od)),
        ),
        geometry_status=(
            "Approximate vertical KGRE cleanout envelope; catalogue article and "
            "overall length retained. Body, socket collars and cover details are "
            "coordination geometry, not manufacturing geometry."
        ),
    )
    for od, article, length in (
        (110, "220600", 359),
        (125, "221600", 365),
        (160, "222600", 394),
    )
)


def kg_approximate_fittings():
    """Catalogued KG combinations without a locally available source mesh."""
    fittings = []
    elbows = {
        110: (
            (67, "220230", 100, 40, 44),
            (87, "220240", 117, 57, 61),
        ),
        125: (
            (15, "221200", 77, 10, 15),
            (30, "221210", 86, 19, 23),
            (45, "221220", 95, 28, 33),
            (67, "221230", 113, 46, 50),
            (87, "221240", 132, 65, 70),
        ),
        160: (
            (15, "222200", 94, 13, 19),
            (30, "222210", 105, 24, 30),
            (45, "222220", 117, 36, 42),
            (67, "222230", 139, 58, 64),
            (87, "222240", 164, 83, 89),
        ),
    }
    for od, rows in elbows.items():
        for angle, article, length, z1, z2 in rows:
            radians = math.radians(angle)
            fittings.append(
                Fitting(
                    name=f"KG koleno {angle}° OD{od}",
                    standard="ČSN EN 1401-1",
                    article=article,
                    family="BEND",
                    od_mm=float(od),
                    angle_deg=float(angle),
                    length_mm=float(length),
                    z1_mm=float(z1),
                    z2_mm=float(z2),
                    mesh_anchor_mm=(0, 0, 0),
                    mesh_along=(0, 1, 0),
                    mesh_side=(1, 0, 0),
                    ports=(
                        Port("SOURCE", (0, 0, 0), (0, -1, 0), "SOURCE", float(od)),
                        Port(
                            "SINK",
                            (length * math.sin(radians),
                             -length * math.cos(radians), 0),
                            (-math.sin(radians), math.cos(radians), 0),
                            "SINK",
                            float(od),
                        ),
                    ),
                    geometry_status=(
                        "Approximate parametric KG elbow; Ostendorf article, OD, "
                        "angle and catalogue dimensions retained. Socket details "
                        "and bend-body profile are not manufacturer geometry."
                    ),
                )
            )

    branches = (
        (45, 110, 110, "220300", 25, 134, 134, 219),
        (45, 125, 110, "221310", 18, 144, 141, 226),
        (45, 125, 125, "221300", 28, 152, 152, 247),
        (45, 160, 125, "222310", 12, 176, 169, 262),
        (45, 160, 160, "222300", 36, 194, 194, 311),
        (87, 110, 110, "220400", 59, 62, 62, 197),
        (87, 125, 110, "221410", 59, 70, 63, 204),
        (87, 125, 125, "221400", 66, 70, 70, 218),
        (87, 160, 110, "222420", 60, 87, 65, 225),
        (87, 160, 125, "222410", 67, 87, 72, 239),
        (87, 160, 160, "222400", 84, 89, 89, 273),
    )
    for angle, main_od, branch_od, article, z1, z2, z3, length in branches:
        radians = math.radians(angle)
        fittings.append(
            Fitting(
                name=f"KG odbočka {angle}° OD{main_od}/{branch_od}",
                standard="ČSN EN 1401-1",
                article=article,
                family="JUNCTION",
                od_mm=float(main_od),
                angle_deg=float(angle),
                length_mm=float(length),
                z1_mm=float(z1),
                z2_mm=float(z2),
                mesh_anchor_mm=(0, 0, 0),
                mesh_along=(0, 1, 0),
                mesh_side=(1, 0, 0),
                ports=(
                    Port("SOURCE", (0, -length / 2, 0), (0, -1, 0), "SOURCE", float(main_od)),
                    Port("SINK", (0, length / 2, 0), (0, 1, 0), "SINK", float(main_od)),
                    Port(
                        "SINK branch",
                        (z3 * math.sin(radians), z1 + z3 * math.cos(radians), 0),
                        (math.sin(radians), math.cos(radians), 0),
                        "SINK",
                        float(branch_od),
                    ),
                ),
                branch_od_mm=float(branch_od),
                z3_mm=float(z3),
                geometry_status=(
                    "Approximate parametric KG branch; Ostendorf article, nominal "
                    "sizes, angle and catalogue dimensions retained. Junction and "
                    "socket details are not manufacturer geometry."
                ),
            )
        )

    for large_od, small_od, article, length, offset in (
        (125, 110, "221700", 82, 15),
        (160, 125, "222710", 108, 27),
    ):
        fittings.append(
            Fitting(
                name=f"KG excentrická redukce OD{large_od}/{small_od}",
                standard="ČSN EN 1401-1",
                article=article,
                family="TRANSITION",
                od_mm=float(large_od),
                angle_deg=0,
                length_mm=float(length),
                z1_mm=float(offset),
                z2_mm=0,
                mesh_anchor_mm=(0, 0, 0),
                mesh_along=(0, 1, 0),
                mesh_side=(1, 0, 0),
                ports=(
                    Port("SOURCE", (0, 0, 0), (0, -1, 0), "SOURCE", float(large_od)),
                    Port("SINK", (offset, length, 0), (0, 1, 0), "SINK", float(small_od)),
                ),
                branch_od_mm=float(small_od),
                geometry_status=(
                    "Approximate parametric eccentric KG reducer; Ostendorf "
                    "article, nominal sizes, offset and length retained. "
                    "Socket details are not manufacturer geometry."
                ),
            )
        )
    return tuple(fittings)
