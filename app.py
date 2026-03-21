import os
from datetime import datetime
from typing import Dict
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from market_data import (  # type: ignore
    compute_indicators,
    download_watchlist_snapshot,
    format_pct,
    format_price,
)
from persistence import build_repository  # type: ignore
from signal_engine import (  # type: ignore
    DEFAULT_TIMEOUT,
    DEFAULT_WATCHLIST,
    MAX_RETRIES,
    AZURE_MODEL,
    AZURE_VERSION,
    generate_signal,
)

st.set_page_config(page_title="Bi-Lytix Assessment", layout="wide")
st.title("Bi-Lytix Assessment")
st.caption("Backend-first workflow: MACD + RSI combo, daily 06:00 assessments")

DATABASE_URL = os.getenv("DATABASE_URL")


@st.cache_resource
def bootstrap_repository(database_url: str):
    return build_repository(database_url)


REPO = None
REPO_CTX = None
PERSISTENCE_ERROR: str | None = None
if DATABASE_URL:
    try:
        REPO, REPO_CTX = bootstrap_repository(DATABASE_URL)
    except Exception as exc:  # noqa: BLE001
        PERSISTENCE_ERROR = str(exc)


def set_selected_ticker(ticker: str) -> None:
    st.session_state["selected_ticker"] = ticker


@st.cache_data(ttl=600, show_spinner="Loading live market data…")
def load_live_watchlist_snapshot() -> tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    return download_watchlist_snapshot(DEFAULT_WATCHLIST)


@st.cache_data(ttl=900)
def compute_cached_indicators(history: pd.DataFrame) -> pd.DataFrame:
    return compute_indicators(history)


def build_plotly_dash_chart(ticker: str, history: pd.DataFrame) -> go.Figure:
    enriched = compute_cached_indicators(history)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=(
            f"{ticker} Price & SMAs",
            "MACD",
            "RSI",
        ),
    )

    fig.add_trace(
        go.Candlestick(
            x=enriched.index,
            open=enriched["Open"],
            high=enriched["High"],
            low=enriched["Low"],
            close=enriched["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=enriched.index, y=enriched["SMA20"], name="SMA20", line=dict(color="#1f77b4")),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=enriched.index, y=enriched["SMA50"], name="SMA50", line=dict(color="#ff7f0e")),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(x=enriched.index, y=enriched["MACD_hist"], name="MACD hist", marker_color="#8c564b"),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=enriched.index, y=enriched["MACD"], name="MACD", line=dict(color="#2ca02c")),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=enriched.index, y=enriched["MACD_signal"], name="Signal", line=dict(color="#d62728")),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=enriched.index, y=enriched["RSI"], name="RSI", line=dict(color="#9467bd")),
        row=3,
        col=1,
    )
    fig.add_hrect(y0=30, y1=70, line_width=0, fillcolor="rgba(200,200,200,0.2)", row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    fig.update_layout(
        height=800,
        showlegend=True,
        template="plotly_white",
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


with st.sidebar:
    st.subheader("LLM Runtime")
    st.text_input("Model", AZURE_MODEL, disabled=True)
    st.text_input("API version", AZURE_VERSION, disabled=True)
    timeout = st.slider("LLM timeout (seconds)", min_value=5.0, max_value=60.0, value=DEFAULT_TIMEOUT)
    retries = st.number_input("Max retries", min_value=1, max_value=5, value=MAX_RETRIES, key="retries")

st.write("### Default watchlist")
st.table(DEFAULT_WATCHLIST)

st.write("### Watchlist performance snapshot")
persistence_enabled = REPO is not None
if persistence_enabled:
    if st.button("Refresh market data from source", type="secondary"):
        with st.spinner("Fetching latest OHLC data and persisting to MySQL…"):
            updates = REPO.refresh_watchlist_history(REPO_CTX.watchlist_id, DEFAULT_WATCHLIST)
        st.session_state["refresh_message"] = f"Updated {len(updates)} tickers from yfinance."
        st.experimental_rerun()

    if message := st.session_state.pop("refresh_message", None):
        st.success(message)

    watchlist_df, history_map = REPO.fetch_watchlist_snapshot(REPO_CTX.watchlist_id)
else:
    if not DATABASE_URL:
        st.info("DATABASE_URL not set – falling back to live yfinance data (no persistence).")
    elif PERSISTENCE_ERROR:
        st.warning(f"Database unavailable (`{PERSISTENCE_ERROR}`). Using live yfinance data only.")
    if st.button("Refresh live market data", type="secondary"):
        load_live_watchlist_snapshot.clear()
        st.experimental_rerun()
    watchlist_df, history_map = load_live_watchlist_snapshot()

if watchlist_df.empty:
    st.warning("No market data yet. Use the refresh button above to load the latest snapshot.")
else:
    header_cols = st.columns([0.4, 1.1, 2.2, 1, 1, 1, 1])
    for col, label in zip(header_cols, ["", "Ticker", "Name", "Last", "1D", "1W", "1M"]):
        col.markdown(f"**{label}**")

    for _, row in watchlist_df.iterrows():
        row_cols = st.columns([0.4, 1.1, 2.2, 1, 1, 1, 1])
        with row_cols[0]:
            st.button("⋮", key=f"chart-{row['ticker']}", on_click=set_selected_ticker, args=(row["ticker"],))
        row_cols[1].markdown(f"**{row['ticker']}**")
        row_cols[2].markdown(row["name"])
        row_cols[3].markdown(format_price(row["price"]))
        row_cols[4].markdown(format_pct(row["1D"]))
        row_cols[5].markdown(format_pct(row["1W"]))
        row_cols[6].markdown(format_pct(row["1M"]))

    st.caption("Click the three-dot button to open the Plotly Dash chart with MACD + RSI for that ticker.")

if "selected_ticker" not in st.session_state and not watchlist_df.empty:
    available = watchlist_df["ticker"].dropna().tolist()
    if available:
        st.session_state["selected_ticker"] = available[0]

selected_ticker = st.session_state.get("selected_ticker")
if selected_ticker and selected_ticker in history_map:
    st.write(f"### Plotly Dash view – {selected_ticker}")
    selected_history = history_map[selected_ticker]
    chart = build_plotly_dash_chart(selected_ticker, selected_history)
    st.plotly_chart(chart, use_container_width=True)
elif not watchlist_df.empty:
    st.info("Select a ticker with available history to render the chart.")

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
