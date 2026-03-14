import os
import json
from datetime import datetime
from typing import List, Dict, Any

import httpx
import streamlit as st
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
        raise ValueError("Missing LYTIX_JUNIOR_FOUNDRY_URL in environment")
    return f"{AZURE_URL}/openai/deployments/{AZURE_MODEL}/chat/completions?api-version={AZURE_VERSION}"


def build_prompt(watchlist: List[str], notes: str) -> str:
    tickers = ", ".join(watchlist)
    extra = f"Additional notes: {notes}\n" if notes else ""
    return (
        "You are BiBroker Junior, an analyst producing a single buy/sell/hold call for"
        " Roger's default watchlist. Combine MACD(12,26,9) + RSI(14,30/70) logic,"
        " mention divergence if present, and include stop-loss guidance (~5%).\n"
        f"Watchlist tickers: {tickers}.\n"
        f"{extra}Return JSON with fields action, confidence, rationale."
    )


def call_llm(prompt: str, timeout: float) -> Dict[str, Any]:
    if not API_KEY:
        raise RuntimeError("LYTIX_JUNIOR_FOUNDRY_API_KEY is not set")

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
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                response = client.post(url, headers=request_headers(), json=payload)
                response.raise_for_status()
            raw = response.json()
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except (httpx.TimeoutException, httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")


def render_signal(block: Dict[str, Any]):
    action = block.get("action", "unknown").upper()
    confidence = block.get("confidence", "?")
    rationale = block.get("rationale", "No rationale returned")
    stop_loss = block.get("stop_loss", "N/A")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Suggested action", action)
    with col2:
        st.metric("Confidence", confidence)

    st.write("**Rationale**")
    st.info(rationale)
    st.write("**Suggested stop-loss**: ", stop_loss)


st.set_page_config(page_title="BiBroker Signals", layout="wide")
st.title("BiBroker – Default Watchlist Signal (preview)")
st.caption("Backend-first workflow: MACD + RSI combo, daily 06:00 assessments")

with st.sidebar:
    st.subheader("LLM Runtime")
    st.text_input("Model", AZURE_MODEL, disabled=True)
    st.text_input("API version", AZURE_VERSION, disabled=True)
    timeout = st.slider("LLM timeout (seconds)", min_value=5.0, max_value=60.0, value=DEFAULT_TIMEOUT)
    st.number_input("Max retries", min_value=1, max_value=5, value=MAX_RETRIES, key="retries")
    st.write("API key configured:" if API_KEY else "⚠️ Set LYTIX_JUNIOR_FOUNDRY_API_KEY")

st.write("### Default watchlist")
st.table(DEFAULT_WATCHLIST)

notes = st.text_area("Optional analyst notes / overrides")

if st.button("Generate signal", type="primary"):
    prompt = build_prompt([item["ticker"] for item in DEFAULT_WATCHLIST], notes)
    try:
        result = call_llm(prompt, timeout=timeout)
        st.success(f"Signal generated at {datetime.now().isoformat(timespec='seconds')}")
        render_signal(result)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to generate signal: {exc}")
        st.stop()
else:
    st.info("Set notes (optional) and click *Generate signal* to run the MACD+RSI assessment.")
