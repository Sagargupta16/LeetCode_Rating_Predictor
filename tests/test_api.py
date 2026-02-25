from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

import main as app_module


@pytest.fixture(autouse=True)
def patch_model_and_scaler(monkeypatch):
    """Patch model/scaler/client so tests don't need real ML artifacts."""
    import numpy as np

    class DummyModel:
        def predict(self, x, verbose=0):
            return np.array([[10.0]])

    class DummyScaler:
        def transform(self, x):
            return x

    monkeypatch.setattr(app_module, "model", DummyModel())
    monkeypatch.setattr(app_module, "scaler", DummyScaler())

    class DummyClient:
        async def aclose(self):
            return

    monkeypatch.setattr(app_module, "async_client", DummyClient())

    @asynccontextmanager
    async def dummy_lifespan(app):
        yield

    monkeypatch.setattr(app_module, "lifespan", dummy_lifespan)


def test_health_endpoint():
    client = TestClient(app_module.app)
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data
    assert "scaler_loaded" in data
    assert "client_ready" in data


def test_root_endpoint():
    client = TestClient(app_module.app)
    r = client.get("/api")
    assert r.status_code == 200
    assert "LeetCode Rating Predictor API is running" in r.json()["message"]


def test_predict_empty_username():
    """Empty username should return 422 (pydantic validation)."""
    client = TestClient(app_module.app)
    r = client.post("/api/predict", json={"username": "", "contests": []})
    assert r.status_code == 422


def test_predict_empty_contests():
    """Valid username with empty contests still tries to fetch user data.
    With the dummy client that has no .post, it returns 503."""
    client = TestClient(app_module.app)
    r = client.post("/api/predict", json={"username": "testuser", "contests": []})
    assert r.status_code == 503


def test_predict_invalid_contest_name():
    """Contest name not matching expected pattern should return 422."""
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "../../etc/passwd", "rank": 100}],
        },
    )
    assert r.status_code == 422


def test_predict_negative_rank():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "weekly-contest-377", "rank": -1}],
        },
    )
    assert r.status_code == 422


def test_predict_zero_rank():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "weekly-contest-377", "rank": 0}],
        },
    )
    assert r.status_code == 422


def test_predict_rank_exceeds_max():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "weekly-contest-377", "rank": 2000000}],
        },
    )
    assert r.status_code == 422


def test_predict_username_invalid_chars():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "user<script>alert(1)</script>",
            "contests": [{"name": "weekly-contest-377", "rank": 100}],
        },
    )
    assert r.status_code == 422


def test_predict_username_too_long():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "a" * 51,
            "contests": [{"name": "weekly-contest-377", "rank": 100}],
        },
    )
    assert r.status_code == 422


def test_predict_biweekly_contest_name_valid():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "biweekly-contest-120", "rank": 100}],
        },
    )
    assert r.status_code in (503, 500)


def test_cors_headers():
    client = TestClient(app_module.app)
    r = client.options(
        "/api",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
