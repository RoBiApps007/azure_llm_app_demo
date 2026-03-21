from datetime import datetime
from pathlib import Path
from typing import Dict
import pandas as pd
import platform
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from market_data import (  # type: ignore
    compute_indicators,
    download_watchlist_snapshot,
    format_pct,
    format_price,
)
from signal_engine import (  # type: ignore
    DEFAULT_TIMEOUT,
    DEFAULT_WATCHLIST,
    MAX_RETRIES,
    AZURE_MODEL,
    AZURE_VERSION,
    generate_signal,
)

APP_VERSION = "2026.03.21"
SOURCE_REPO = "https://github.com/RoBiApps007/azure_llm_app_demo"
BUILD_TIMESTAMP = datetime.fromtimestamp(Path(__file__).stat().st_mtime).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
BUILD_METADATA = [
    ("App version", APP_VERSION),
    ("Last updated", BUILD_TIMESTAMP),
    ("Python", platform.python_version()),
    ("Streamlit", st.__version__),
    ("Data source", "Live yfinance OHLC (6M • 1D interval)"),
    ("Repository", SOURCE_REPO),
]
RELEASE_NOTES = [
    {
        "version": "2026.03.21",
        "date": "2026-03-21",
        "changes": [
            "Added navigation panel with Monitoring and About views",
            "Removed database dependency in favor of on-demand live snapshots",
            "Expanded CI coverage (Ruff + pytest) and added regression tests for live refresh",
            "Introduced About page with build metadata and release history",
        ],
    },
    {
        "version": "2026.03.18",
        "date": "2026-03-18",
        "changes": [
            "Initial MACD + RSI monitoring dashboard",
            "FastAPI signal endpoint for automated clients",
        ],
    },
]

st.set_page_config(page_title="Bi-Lytix Assessment", layout="wide")

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


def render_about():
    st.title("About BiBroker Monitoring")
    st.caption("Build + delivery overview")
    st.write("This view summarizes the current build, toolchain, and release cadence for the live monitoring workspace.")

    st.write("### Build metadata")
    for label, value in BUILD_METADATA:
        st.markdown(f"**{label}:** {value}")

    st.write("### Release notes")
    for entry in RELEASE_NOTES:
        expanded = entry is RELEASE_NOTES[0]
        with st.expander(f"{entry['version']} — {entry['date']}", expanded=expanded):
            for change in entry["changes"]:
                st.markdown(f"- {change}")
    st.write("")
    st.markdown(f"Source repo: [{SOURCE_REPO}]({SOURCE_REPO})")

with st.sidebar:
    st.subheader("Navigation")
    current_view = st.radio("View", ["Monitoring", "About"], index=0, key="nav_view")
    if current_view == "Monitoring":
        st.subheader("LLM Runtime")
        st.text_input("Model", AZURE_MODEL, disabled=True)
        st.text_input("API version", AZURE_VERSION, disabled=True)
        timeout = st.slider("LLM timeout (seconds)", min_value=5.0, max_value=60.0, value=DEFAULT_TIMEOUT)
        retries = st.number_input("Max retries", min_value=1, max_value=5, value=MAX_RETRIES, key="retries")
    else:
        st.info("Viewing build & release notes. Switch back to Monitoring to run signals.")

if current_view == "Monitoring":
    st.title("Bi-Lytix Assessment")
    st.caption("Backend-first workflow: MACD + RSI combo, daily 06:00 assessments")

    st.write("### Default watchlist")
    st.table(DEFAULT_WATCHLIST)

    st.write("### Watchlist performance snapshot")
    st.caption("Live yfinance snapshot (no database dependency).")

    live_clicked = st.button("Load live market data", type="primary")
    if live_clicked:
        load_live_watchlist_snapshot.clear()
        with st.spinner("Fetching latest OHLC data from yfinance…"):
            snapshot = load_live_watchlist_snapshot()
        st.session_state["watchlist_snapshot"] = snapshot
        df_preview = snapshot[0]
        if not df_preview.empty:
            tickers = df_preview["ticker"].dropna().tolist()
            if tickers:
                st.session_state["selected_ticker"] = tickers[0]

    snapshot = st.session_state.get("watchlist_snapshot")
    if snapshot:
        watchlist_df, history_map = snapshot
    else:
        watchlist_df = pd.DataFrame()
        history_map = {}

    if watchlist_df.empty:
        st.warning("No market data yet. Click **Load live market data** above to fetch the latest snapshot.")
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
else:
    render_about()


