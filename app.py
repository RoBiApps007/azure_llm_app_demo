from datetime import datetime

import streamlit as st

from signal_engine import (  # type: ignore
    DEFAULT_TIMEOUT,
    DEFAULT_WATCHLIST,
    MAX_RETRIES,
    AZURE_MODEL,
    AZURE_VERSION,
    generate_signal,
)

st.set_page_config(page_title="BiBroker Signals", layout="wide")
st.title("BiBroker – Default Watchlist Signal (preview)")
st.caption("Backend-first workflow: MACD + RSI combo, daily 06:00 assessments")

with st.sidebar:
    st.subheader("LLM Runtime")
    st.text_input("Model", AZURE_MODEL, disabled=True)
    st.text_input("API version", AZURE_VERSION, disabled=True)
    timeout = st.slider("LLM timeout (seconds)", min_value=5.0, max_value=60.0, value=DEFAULT_TIMEOUT)
    retries = st.number_input("Max retries", min_value=1, max_value=5, value=MAX_RETRIES, key="retries")

st.write("### Default watchlist")
st.table(DEFAULT_WATCHLIST)

notes = st.text_area("Optional analyst notes / overrides")


def render_signal(block):
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
    st.write("**Suggested stop-loss**:", stop_loss)


if st.button("Generate signal", type="primary"):
    try:
        result = generate_signal(
            tickers=[item["ticker"] for item in DEFAULT_WATCHLIST],
            notes=notes,
            timeout=timeout,
            retries=int(retries),
        )
        st.success(f"Signal generated at {datetime.now().isoformat(timespec='seconds')}")
        render_signal(result)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to generate signal: {exc}")
else:
    st.info("Set notes (optional) and click *Generate signal* to run the MACD+RSI assessment.")
