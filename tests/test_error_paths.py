import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

import main as app_module


@pytest.fixture(autouse=True)
def patch_lifespan(monkeypatch):
    """Replace lifespan so TestClient doesn't load real model files."""
    import numpy as np

    class DummyModel:
        def predict(self, x, verbose=0):
            return np.array([[10.0]])

    class DummyScaler:
        def transform(self, x):
            return x

    monkeypatch.setattr(app_module, "model", DummyModel())
    monkeypatch.setattr(app_module, "scaler", DummyScaler())

    @asynccontextmanager
    async def dummy_lifespan(app):
        yield

    monkeypatch.setattr(app_module, "lifespan", dummy_lifespan)


def test_predict_with_empty_username():
    client = TestClient(app_module.app)
    r = client.post("/api/predict", json={"username": "", "contests": []})
    assert r.status_code == 422


def test_predict_with_whitespace_username():
    client = TestClient(app_module.app)
    r = client.post("/api/predict", json={"username": "   ", "contests": []})
    assert r.status_code == 422


def test_predict_missing_body():
    client = TestClient(app_module.app)
    r = client.post("/api/predict")
    assert r.status_code == 422


def test_predict_invalid_json():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422


def test_predict_ssrf_contest_name():
    client = TestClient(app_module.app)
    r = client.post(
        "/api/predict",
        json={
            "username": "testuser",
            "contests": [{"name": "../../../etc/passwd", "rank": 100}],
        },
    )
    assert r.status_code == 422


def test_predict_contest_name_injection():
    client = TestClient(app_module.app)
    for bad_name in [
        "weekly-contest-377; DROP TABLE",
        "localhost:6379",
        "http://evil.com",
        "",
        "a" * 200,
    ]:
        r = client.post(
            "/api/predict",
            json={
                "username": "testuser",
                "contests": [{"name": bad_name, "rank": 100}],
            },
        )
        assert r.status_code == 422, f"Expected 422 for contest name: {bad_name}"


def test_fetch_user_data_http_error():
    from app.services.leetcode import fetch_user_data
    from app.utils.cache import TTLCache

    class DummyClient:
        async def post(self, *args, **kwargs):
            raise httpx.HTTPError("Connection failed")

    with pytest.raises(Exception):
        asyncio.run(
            fetch_user_data(DummyClient(), asyncio.Semaphore(5), TTLCache(), "nonexistent")
        )


def test_fetch_contest_data_invalid_name():
    from app.services.leetcode import fetch_contest_data
    from app.utils.cache import TTLCache

    class DummyClient:
        pass

    with pytest.raises(Exception):
        asyncio.run(
            fetch_contest_data(DummyClient(), asyncio.Semaphore(5), TTLCache(), "invalid-name")
        )


def test_nonexistent_endpoint():
    client = TestClient(app_module.app)
    r = client.get("/api/nonexistent")
    assert r.status_code == 404
