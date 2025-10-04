import os
import pytest
from fastapi.testclient import TestClient

import main as app_module


@pytest.fixture(autouse=True)
def patch_model_and_scaler(monkeypatch):
    # Patch model and scaler so the app doesn't try to load large artifacts during tests
    class DummyModel:
        def predict(self, x, verbose=0):
            import numpy as np

            return np.array([[10.0]])

    class DummyScaler:
        def transform(self, x):
            return x

    monkeypatch.setattr(app_module, "model", DummyModel())
    monkeypatch.setattr(app_module, "scaler", DummyScaler())

    # Provide a dummy async_client so fetch calls fail quickly if used
    class DummyClient:
        async def aclose(self):
            return

    monkeypatch.setattr(app_module, "async_client", DummyClient())

    # Replace lifespan with a no-op so TestClient doesn't attempt to load real model files
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def dummy_lifespan(app):
        yield

    monkeypatch.setattr(app_module, "lifespan", dummy_lifespan)


def test_health_endpoint():
    client = TestClient(app_module.app)
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data and data["status"] == "healthy"


def test_root_endpoint():
    client = TestClient(app_module.app)
    r = client.get("/api")
    assert r.status_code == 200
    assert "LeetCode Rating Predictor API is running" in r.json().get("message", "")
