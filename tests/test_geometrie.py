import numpy as np
import pytest

from geometrie import transform_catalogue_mesh
from definice import KG_45_DN110, KG_BRANCH_45_DN160_DN110


def test_catalogue_mesh_anchor_and_frame():
    vertices = np.array([[0, 0, 0], [0, 1000, 0], [1000, 0, 0]], dtype=float)
    faces = np.array([[0, 1, 2]])

    world, actual_faces = transform_catalogue_mesh(
        vertices,
        faces,
        anchor_mm=(0, 0, 0),
        along=(0, 1, 0),
        side=(-1, 0, 0),
        origin=(2, 3, 4),
    )

    np.testing.assert_allclose(world, [[2, 3, 4], [2, 4, 4], [1, 3, 4]])
    np.testing.assert_array_equal(actual_faces, faces)


def test_catalogue_mesh_rejects_non_orthogonal_frame():
    with pytest.raises(ValueError, match="kolmé"):
        transform_catalogue_mesh(
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            [[0, 1, 2]],
            anchor_mm=(0, 0, 0),
            along=(1, 0, 0),
            side=(1, 1, 0),
            origin=(0, 0, 0),
        )


def test_first_catalogue_definition_is_a_two_port_kg_bend():
    fitting = KG_45_DN110
    assert (fitting.standard, fitting.article, fitting.family) == (
        "ČSN EN 1401-1",
        "220220",
        "BEND",
    )
    assert (fitting.od_mm, fitting.angle_deg, fitting.z1_mm, fitting.z2_mm) == (
        110.0,
        45.0,
        25.0,
        29.0,
    )
    assert {port.flow for port in fitting.ports} == {"SOURCE", "SINK"}
    assert all(np.isclose(np.linalg.norm(port.axis), 1.0) for port in fitting.ports)


def test_kg_branch_uses_a_sold_160_110_combination():
    fitting = KG_BRANCH_45_DN160_DN110
    assert (fitting.article, fitting.family, fitting.od_mm, fitting.branch_od_mm) == (
        "222320",
        "JUNCTION",
        160.0,
        110.0,
    )
    assert (fitting.z1_mm, fitting.z2_mm, fitting.z3_mm, fitting.length_mm) == (
        2.0,
        168.0,
        159.0,
        242.0,
    )
    assert [port.od_mm for port in fitting.ports] == [160.0, 160.0, 110.0]
