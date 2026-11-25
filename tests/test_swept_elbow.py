"""Swept (lathe) elbows: exact solids, measured against the KG reference shape."""

from pathlib import Path

import numpy as np
import pytest

from swept_geometrie import elbow_lathes, swept_bounds
from tests.silhouette import iou, tessellate

REFERENCE = Path(__file__).parent.parent / "tmp/agent_NEW/reference_canonical.npz"


@pytest.mark.parametrize("angle", [15, 30, 45, 67.5, 87.5])
@pytest.mark.parametrize("od", [110.4, 126.3, 161.5])
def test_swept_elbow_matches_analytic_bounds(angle, od):
    body, mouths = elbow_lathes(angle, od)
    low, high = swept_bounds(body)
    vertices, triangles = tessellate(body)
    assert len(triangles) > 100
    assert np.allclose(np.r_[vertices.min(0), vertices.max(0)], np.r_[low, high], atol=0.6)
    # both mouths lie on the tessellated envelope
    for position, axis in mouths:
        assert np.linalg.norm(vertices - position, axis=1).min() < 60 * od / 110.4


def test_swept_elbow_matches_the_measured_reference():
    if not REFERENCE.exists():
        pytest.skip("reference mesh not available")
    data = np.load(REFERENCE)
    body, _ = elbow_lathes(45.0, 110.4)
    scores = iou(tessellate(body), (np.asarray(data["vertices"], float), np.asarray(data["faces"], int)))
    assert all(score >= 0.85 for score in scores.values()), scores
