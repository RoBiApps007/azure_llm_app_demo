"""Unit tests for signal_engine helpers."""
from __future__ import annotations

import importlib
import sys
from typing import Any, Dict

import pytest


MODULE_NAME = "signal_engine"
ENV_KEYS = {
    "LYTIX_JUNIOR_FOUNDRY_URL",
    "LYTIX_JUNIOR_FOUNDRY_MODEL",
    "LYTIX_JUNIOR_FOUNDRY_MODEL_VERSION",
    "LYTIX_JUNIOR_FOUNDRY_API_KEY",
    "USER_AGENT",
}


def load_module(monkeypatch: pytest.MonkeyPatch, **env: str) -> Any:
    """Reload signal_engine with a clean environment."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def test_build_prompt_includes_watchlist_and_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(monkeypatch)
    prompt = module.build_prompt(["AAPL", "MSFT"], notes="watch RSI closely")
    assert "AAPL" in prompt
    assert "MSFT" in prompt
    assert "watch RSI closely" in prompt


def test_request_headers_include_api_key_and_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(monkeypatch)
    module.API_KEY = "secret"
    module.USER_AGENT = "pytest-agent/1.0"
    headers = module.request_headers()
    assert headers["api-key"] == "secret"
    assert headers["User-Agent"] == "pytest-agent/1.0"


def test_azure_chat_completions_url_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(monkeypatch)
    module.AZURE_URL = "https://example.openai.azure.com"
    module.AZURE_MODEL = "demo"
    module.AZURE_VERSION = "2025-01-01-preview"
    url = module.azure_chat_completions_url()
    assert url == "https://example.openai.azure.com/openai/deployments/demo/chat/completions?api-version=2025-01-01-preview"


def test_azure_chat_completions_url_missing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(monkeypatch)
    module.AZURE_URL = None
    with pytest.raises(module.SignalEngineError):
        module.azure_chat_completions_url()


def test_call_llm_returns_parsed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"action": "buy", "confidence": 0.74, "rationale": "MACD crossover", "stop_loss": "5%"}

    class DummyResponse:
        def __init__(self, content: Dict[str, Any]) -> None:
            self._content = content

        def raise_for_status(self) -> None:
            return None

        def json(self) -> Dict[str, Any]:
            return self._content

    captured: Dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            """Mimic httpx.Client signature."""
            captured["timeout"] = kwargs.get("timeout")

        def __enter__(self) -> "DummyClient":  # noqa: D401
            return self

        def __exit__(self, *exc: Any) -> None:  # noqa: D401
            return None

        def post(self, url: str, headers: Dict[str, str], json: Dict[str, Any]) -> DummyResponse:  # noqa: D401
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return DummyResponse({"choices": [{"message": {"content": module.json.dumps(payload)}}]})

    module = load_module(monkeypatch)
    module.AZURE_URL = "https://example.openai.azure.com"
    module.AZURE_MODEL = "demo"
    module.AZURE_VERSION = "2025-01-01-preview"
    module.API_KEY = "super-secret"

    monkeypatch.setattr(module.httpx, "Client", DummyClient)

    result = module.call_llm("test prompt", timeout=5, retries=1)
    assert result == payload
    assert captured["headers"]["api-key"] == "super-secret"
    assert "messages" in captured["payload"]
    assert captured["url"].endswith("chat/completions?api-version=2025-01-01-preview")
