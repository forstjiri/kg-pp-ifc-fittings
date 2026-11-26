"""Datové třídy portu a tvarovky; rozměry žijí v data/*.json."""

from dataclasses import dataclass

# Ze STEP naměřené rozměry odboček KG:
# (délka hrot→hnízdo, vrchol od hrotu, délka odbočky, úhel, DN, DN odbočky)
BRANCH_MEASURED = {
    "220300z": (277.0, 90.65, 187.3, 45, 110, 110),
    "220400z": (240.5, 122.3, 118.9, 87, 110, 110),
    "222320z": (317.5, 86.0, 227.4, 45, 160, 110),
    "222420z": (273.5, 143.7, 143.0, 87, 160, 110),
}


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
    dn_mm: float | None = None  # katalogový rozměr (ne skutečný OD)
    branch_dn_mm: float | None = None
