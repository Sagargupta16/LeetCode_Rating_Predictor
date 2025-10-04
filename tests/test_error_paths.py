import pytest
from fastapi.testclient import TestClient

import main as app_module


def test_predict_with_missing_username(monkeypatch):
    client = TestClient(app_module.app)
    r = client.post("/api/predict", json={"username": "", "contests": []})
    assert r.status_code == 400


def test_fetch_user_data_http_error(monkeypatch):
    # simulate httpx HTTP error when fetching user data
    class DummyClient:
        async def post(self, *args, **kwargs):
            raise Exception("HTTP error simulated")

    monkeypatch.setattr(app_module, "async_client", DummyClient())

    with pytest.raises(Exception):
        # call internal function directly; ensure exception mapping
        import asyncio

        asyncio.run(app_module.fetch_user_data("nonexistent_user"))
