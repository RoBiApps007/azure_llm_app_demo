"""Shared helpers for BiBroker signal generation."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_WATCHLIST = [
    {"ticker": "ACAG.VI", "name": "Accelleron (Vienna)"},
    {"ticker": "GOOG", "name": "Alphabet"},
    {"ticker": "PF8.F", "name": "Porsche Automobil Holding (Frankfurt)"},
    {"ticker": "INL.DE", "name": "Intel (Xetra)"},
    {"ticker": "MSFT", "name": "Microsoft"},
    {"ticker": "FACC.VI", "name": "FACC (Vienna)"},
    {"ticker": "CRM.VI", "name": "Salesforce CD (Vienna)"},
    {"ticker": "PLTR", "name": "Palantir"},
    {"ticker": "NVD.DE", "name": "NVIDIA (Xetra)"},
    {"ticker": "NVTS", "name": "Navitas Semiconductor"},
    {"ticker": "MU.VI", "name": "Micron CD (Vienna)"},
    {"ticker": "IFX.VI", "name": "Infineon (Vienna)"},
    {"ticker": "BROA.VI", "name": "Broadcom (Vienna cert)"},
    {"ticker": "AMD.VI", "name": "AMD CD (Vienna)"},
]

AZURE_URL = os.getenv("LYTIX_JUNIOR_FOUNDRY_URL")
AZURE_MODEL = os.getenv("LYTIX_JUNIOR_FOUNDRY_MODEL", "gpt-5-nano")
AZURE_VERSION = os.getenv("LYTIX_JUNIOR_FOUNDRY_MODEL_VERSION", "2024-02-15-preview")
API_KEY = os.getenv("LYTIX_JUNIOR_FOUNDRY_API_KEY")
USER_AGENT = os.getenv("USER_AGENT", "demo_user")
DEFAULT_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))


class SignalEngineError(RuntimeError):
    """Raised when the signal engine cannot return a result."""


def request_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY or "",
    }
    if USER_AGENT:
        headers["User-Agent"] = USER_AGENT
    return headers


def azure_chat_completions_url() -> str:
    if not AZURE_URL:
        raise SignalEngineError("Missing LYTIX_JUNIOR_FOUNDRY_URL in environment")
    return f"{AZURE_URL}/openai/deployments/{AZURE_MODEL}/chat/completions?api-version={AZURE_VERSION}"


def build_prompt(watchlist: List[str], notes: str = "") -> str:
    tickers = ", ".join(watchlist)
    extra = f"Additional notes: {notes}\n" if notes else ""
    return (
        "You are BiBroker Junior, an analyst producing a single buy/sell/hold call for"
        " Roger's default watchlist. Combine MACD(12,26,9) + RSI(14,30/70) logic,"
        " mention divergence if present, and include stop-loss guidance (~5%).\n"
        f"Watchlist tickers: {tickers}.\n"
        f"{extra}Return JSON with fields action, confidence, rationale, stop_loss."
    )


def call_llm(prompt: str, timeout: float | None = None, retries: int | None = None) -> Dict[str, Any]:
    if not API_KEY:
        raise SignalEngineError("LYTIX_JUNIOR_FOUNDRY_API_KEY is not set")

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a precise trading assistant who outputs valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }

    url = azure_chat_completions_url()
    max_retries = retries or MAX_RETRIES
    timeout_seconds = timeout or DEFAULT_TIMEOUT
    last_error: Exception | None = None

    for _attempt in range(max_retries):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_seconds)) as client:
                response = client.post(url, headers=request_headers(), json=payload)
                response.raise_for_status()
            raw = response.json()
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except (httpx.TimeoutException, httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
    raise SignalEngineError(f"LLM call failed after {max_retries} attempts: {last_error}")


def generate_signal(
    tickers: List[str] | None = None,
    notes: str | None = None,
    timeout: float | None = None,
    retries: int | None = None,
) -> Dict[str, Any]:
    watchlist = tickers or [item["ticker"] for item in DEFAULT_WATCHLIST]
    prompt = build_prompt(watchlist, notes or "")
    return call_llm(prompt, timeout=timeout, retries=retries)
