import numpy as np

import main as app_module


def test_make_prediction_with_dummy_model_and_scaler(monkeypatch):
    class DummyModel:
        def predict(self, x, verbose=0):
            # return shape (1,1)
            return np.array([[5.0]])

    class DummyScaler:
        def transform(self, x):
            # check that x arrives as 2D array
            assert x.ndim == 2
            return x

    monkeypatch.setattr(app_module, "model", DummyModel())
    monkeypatch.setattr(app_module, "scaler", DummyScaler())

    # create input with shape (1, features)
    arr = np.array([[1800, 500, 8000, 6.25, 45]])

    pred = app_module.make_prediction(arr)
    assert isinstance(pred, float)
    assert abs(pred - 5.0) < 1e-6
