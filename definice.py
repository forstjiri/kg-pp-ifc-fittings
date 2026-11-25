"""Datové třídy portu a tvarovky; rozměry Žijí v data/*.json."""

from dataclasses import dataclass


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
