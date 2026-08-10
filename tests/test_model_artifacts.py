"""Regression tests against the real exported model artifacts.

Every other backend test uses dummy models, so nothing else would notice if a
dependency bump, a re-export, or a refactor silently changed what the API
predicts. These tests pin the actual numbers.

If a legitimate retrain changes the model, update GOLDEN_PREDICTION in the same
commit as the new artifacts.
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi import HTTPException

from app.model_loader import DenseNetwork, load_model, load_scaler
from app.services.prediction import make_prediction

REPO_ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_PATH = REPO_ROOT / "models" / "weights.npz"
SCALER_PATH = REPO_ROOT / "models" / "scaler.json"

NUM_FEATURES = 15

# A fixed, representative feature vector: ~1800 rated user placing 500th in an
# 8000-player contest. Feature order matches main.py.
GOLDEN_FEATURES = np.array(
    [
        [
            1800.0,  # current_rating
            500.0,  # rank
            8000.0,  # total_participants
            6.25,  # rank_percentage
            45.0,  # attended_contests
            0.75,  # avg_solve_rate
            3000.0,  # avg_finish_time
            0.8,  # recent_solve_rate
            2800.0,  # recent_finish_time
            5.0,  # rating_trend
            1850.0,  # max_rating
            6.2,  # log_rank
            112.5,  # rating_x_pct
            1350.0,  # avg_solve_rate * current_rating
            0.55,  # avg_finish_time / 5400
        ]
    ]
)

# Produced by the numpy inference path. The TensorFlow path returns
# 57.28030014038086; the two agree to ~2.3e-05, which is far below the two
# decimal places the UI renders.
GOLDEN_PREDICTION = 57.2802848815918
TOLERANCE = 1e-4


@pytest.fixture(scope="module")
def model():
    return load_model(WEIGHTS_PATH)


@pytest.fixture(scope="module")
def scaler():
    return load_scaler(SCALER_PATH)


def test_artifacts_are_committed():
    assert WEIGHTS_PATH.is_file(), f"missing {WEIGHTS_PATH}"
    assert SCALER_PATH.is_file(), f"missing {SCALER_PATH}"


def test_model_and_scaler_agree_on_feature_count(model, scaler):
    assert model.input_shape == (None, NUM_FEATURES)
    assert scaler.n_features_in_ == NUM_FEATURES


def test_golden_prediction_is_stable(model, scaler):
    """The whole point: a fixed input must keep producing a fixed output."""
    result = make_prediction(model, scaler, GOLDEN_FEATURES)
    assert result == pytest.approx(GOLDEN_PREDICTION, abs=TOLERANCE)


def test_prediction_is_finite_and_plausible(model, scaler):
    result = make_prediction(model, scaler, GOLDEN_FEATURES)
    assert math.isfinite(result)
    assert abs(result) < 500


def test_scaler_transform_matches_exported_vectors(scaler):
    payload = json.loads(SCALER_PATH.read_text(encoding="utf-8"))
    expected = GOLDEN_FEATURES * np.asarray(payload["scale"]) + np.asarray(
        payload["min"]
    )
    np.testing.assert_allclose(scaler.transform(GOLDEN_FEATURES), expected)


def test_better_rank_predicts_larger_gain(model, scaler):
    """Sanity check on learned behaviour, not just plumbing."""
    strong = GOLDEN_FEATURES.copy()
    strong[0][1] = 100.0  # much better rank
    strong[0][3] = (100.0 * 100) / 8000.0
    strong[0][11] = float(np.log1p(100.0))
    strong[0][12] = 1800.0 * (100.0 / 8000.0)

    weak = GOLDEN_FEATURES.copy()
    weak[0][1] = 6000.0
    weak[0][3] = (6000.0 * 100) / 8000.0
    weak[0][11] = float(np.log1p(6000.0))
    weak[0][12] = 1800.0 * (6000.0 / 8000.0)

    assert make_prediction(model, scaler, strong) > make_prediction(model, scaler, weak)


def test_rejects_wrong_feature_count(model, scaler):
    bad = np.ones((1, NUM_FEATURES - 1))
    with pytest.raises(HTTPException) as exc_info:
        make_prediction(model, scaler, bad)
    assert exc_info.value.status_code == 500


def test_rejects_implausible_output(scaler):
    """A model returning a huge value must be refused, not passed through."""

    class RunawayModel:
        input_shape = (None, NUM_FEATURES)

        def predict(self, x, verbose=0):
            return np.array([[9999.0]])

    runaway = RunawayModel()
    with pytest.raises(HTTPException) as exc_info:
        make_prediction(runaway, scaler, GOLDEN_FEATURES)
    assert exc_info.value.status_code == 500


def test_dropout_free_network_is_pure_matmul():
    """Two identical calls must agree exactly; no dropout at inference."""
    net = DenseNetwork(
        [(np.eye(2, dtype=np.float32), np.zeros(2, dtype=np.float32))],
        ["linear"],
        2,
    )
    x = np.array([[1.5, -2.5]])
    np.testing.assert_array_equal(net.predict(x), net.predict(x))
    np.testing.assert_allclose(net.predict(x), x)
