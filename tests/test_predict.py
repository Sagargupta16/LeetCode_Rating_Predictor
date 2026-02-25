import numpy as np
import pytest
from fastapi import HTTPException

from app.services.prediction import make_prediction


def test_make_prediction_with_dummy_model_and_scaler():
    class DummyModel:
        input_shape = (None, 7)  # Dense model: 2D input

        def predict(self, x, verbose=0):
            return np.array([[5.0]])

    class DummyScaler:
        def transform(self, x):
            assert x.ndim == 2
            return x

    arr = np.array([[1800, 500, 8000, 6.25, 45, 6.2, 160.0]])
    pred = make_prediction(DummyModel(), DummyScaler(), arr)
    assert isinstance(pred, float)
    assert abs(pred - 5.0) < 1e-6


def test_make_prediction_returns_float():
    class DummyModel:
        input_shape = (None, 7)

        def predict(self, x, verbose=0):
            return np.array([[-12.5]])

    class DummyScaler:
        def transform(self, x):
            return x

    arr = np.array([[1500, 1000, 5000, 20.0, 10, 6.9, 150.0]])
    pred = make_prediction(DummyModel(), DummyScaler(), arr)
    assert isinstance(pred, float)
    assert abs(pred - (-12.5)) < 1e-6


def test_make_prediction_model_not_loaded():
    with pytest.raises(HTTPException) as exc_info:
        make_prediction(None, None, np.array([[1800, 500, 8000, 6.25, 45, 6.2, 160.0]]))
    assert exc_info.value.status_code == 500


def test_make_prediction_scaler_error():
    class BadScaler:
        def transform(self, x):
            raise ValueError("Bad scaler")

    class DummyModel:
        input_shape = (None, 7)

        def predict(self, x, verbose=0):
            return np.array([[0.0]])

    with pytest.raises(HTTPException) as exc_info:
        make_prediction(DummyModel(), BadScaler(), np.array([[1800, 500, 8000, 6.25, 45, 6.2, 160.0]]))
    assert exc_info.value.status_code == 500


def test_make_prediction_dense_no_reshape():
    """Dense model (2D input_shape) should NOT reshape to 3D."""
    received_shapes = {}

    class TrackingScaler:
        def transform(self, x):
            received_shapes["scaler_input"] = x.shape
            return x

    class TrackingModel:
        input_shape = (None, 7)

        def predict(self, x, verbose=0):
            received_shapes["model_input"] = x.shape
            return np.array([[1.0]])

    arr = np.array([[1800, 500, 8000, 6.25, 45, 6.2, 160.0]])
    make_prediction(TrackingModel(), TrackingScaler(), arr)

    assert received_shapes["scaler_input"] == (1, 7)
    assert received_shapes["model_input"] == (1, 7)  # Dense: stays 2D


def test_make_prediction_lstm_reshapes():
    """Legacy LSTM model (3D input_shape) should reshape to 3D."""
    received_shapes = {}

    class TrackingScaler:
        def transform(self, x):
            received_shapes["scaler_input"] = x.shape
            return x

    class TrackingModel:
        input_shape = (None, 1, 7)  # LSTM: expects 3D

        def predict(self, x, verbose=0):
            received_shapes["model_input"] = x.shape
            return np.array([[1.0]])

    arr = np.array([[1800, 500, 8000, 6.25, 45, 6.2, 160.0]])
    make_prediction(TrackingModel(), TrackingScaler(), arr)

    assert received_shapes["scaler_input"] == (1, 7)
    assert received_shapes["model_input"] == (1, 1, 7)  # LSTM: reshaped to 3D
