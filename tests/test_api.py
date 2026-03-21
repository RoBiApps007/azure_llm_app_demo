"""Tests for FastAPI surface."""
from __future__ import annotations

from fastapi.testclient import TestClient

import api


client = TestClient(api.app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "default_watchlist_count" in payload


def test_signal_endpoint_success(monkeypatch) -> None:
    stub = {"action": "buy", "confidence": 0.8, "rationale": "test", "stop_loss": "5%"}

    def fake_generate_signal(**kwargs):  # noqa: ANN001
        return stub

    monkeypatch.setattr(api, "generate_signal", fake_generate_signal)

    response = client.post("/signal", json={"tickers": ["AAA"], "notes": "demo"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "buy"
    assert data["raw"] == stub


def test_signal_endpoint_handles_engine_error(monkeypatch) -> None:
    def boom(**kwargs):  # noqa: ANN001
        raise api.SignalEngineError("model down")

    monkeypatch.setattr(api, "generate_signal", boom)
    response = client.post("/signal", json={})
    assert response.status_code == 502
    assert response.json()["detail"] == "model down"


def test_signal_endpoint_handles_generic_error(monkeypatch) -> None:
    def explode(**kwargs):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "generate_signal", explode)
    response = client.post("/signal", json={})
    assert response.status_code == 500
    assert "boom" in response.json()["detail"]
