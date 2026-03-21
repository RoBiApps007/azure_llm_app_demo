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
WATCHLIST_CHOICES = tuple((item["ticker"], item["name"]) for item in DEFAULT_WATCHLIST)
WATCHLIST_LABEL_MAP = {f"{ticker} — {name}": (ticker, name) for ticker, name in WATCHLIST_CHOICES}
WATCHLIST_LABELS = list(WATCHLIST_LABEL_MAP.keys())
TIMEFRAME_WINDOWS = {"1M": 30, "3M": 90, "6M": 180}
TIMEFRAME_OPTIONS = ["1M", "3M", "6M"]
SAMPLE_FREQUENCIES = {"Weekly": "W", "Daily": "D"}

st.set_page_config(page_title="Bi-Lytix Assessment", layout="wide")

@st.cache_data(ttl=600, show_spinner="Loading live market data…")
def load_live_watchlist_snapshot(watchlist: tuple[tuple[str, str], ...]) -> tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    options = [{"ticker": ticker, "name": name} for ticker, name in watchlist]
    return download_watchlist_snapshot(options)


def resample_history(history: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "D":
        return history
    base = history.copy()
    if "Adj Close" not in base.columns and "Close" in base.columns:
        base["Adj Close"] = base["Close"]
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Adj Close": "last",
        "Volume": "sum",
    }
    resampled = base.resample(rule).agg(agg).dropna()
    return resampled


@st.cache_data(ttl=900)
def compute_cached_indicators(history: pd.DataFrame) -> pd.DataFrame:
    return compute_indicators(history)


def compute_barometer_signals(history: pd.DataFrame) -> list[dict[str, object]]:
    if history.empty or "Close" not in history:
        return []
    close_series = history["Close"]
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
    close_series = close_series.dropna()
    if len(close_series) < 6:
        return []
    enriched = compute_cached_indicators(history)
    latest_rsi = None
    latest_macd_hist = None
    if not enriched.empty:
        if "RSI" in enriched:
            latest_rsi = float(enriched["RSI"].iloc[-1])
        if "MACD_hist" in enriched:
            latest_macd_hist = float(enriched["MACD_hist"].iloc[-1])

    horizons = [
        ("Next day", 1),
        ("Next 3 days", 3),
        ("Next week", 5),
    ]
    cards: list[dict[str, object]] = []
    for label, days in horizons:
        if len(close_series) <= days:
            continue
        past_value = float(close_series.iloc[-(days + 1)])
        if past_value == 0:
            continue
        change = ((float(close_series.iloc[-1]) - past_value) / past_value) * 100
        if change > 1:
            bias = "Buy bias"
        elif change < -1:
            bias = "Sell bias"
        else:
            bias = "Hold"
        rationale = []
        if latest_rsi is not None:
            if latest_rsi < 30:
                rationale.append("RSI oversold")
            elif latest_rsi > 70:
                rationale.append("RSI overbought")
        if latest_macd_hist is not None:
            if latest_macd_hist > 0:
                rationale.append("MACD momentum up")
            elif latest_macd_hist < 0:
                rationale.append("MACD momentum down")
        if not rationale:
            rationale.append("Neutral momentum")
        cards.append(
            {
                "horizon": label,
                "bias": bias,
                "change": change,
                "rationale": ", ".join(rationale),
            }
        )
    return cards


def build_plotly_dash_chart(
    ticker: str,
    history: pd.DataFrame,
    window_days: int,
    *,
    show_sma20: bool,
    show_sma50: bool,
    show_macd: bool,
    show_rsi: bool,
    show_bbands: bool,
    price_scale: str,
) -> go.Figure:
    enriched = compute_cached_indicators(history)
    if enriched.empty:
        enriched = history.copy()
    history_window = enriched.tail(window_days)
    if history_window.empty:
        history_window = enriched
    if history_window.empty:
        return go.Figure()
    enriched = history_window

    rows = [("Price & Trend", "price"), ("Volume", "volume")]
    if show_macd:
        rows.append(("MACD", "macd"))
    if show_rsi:
        rows.append(("RSI", "rsi"))

    fig = make_subplots(
        rows=len(rows),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.45 if label == "price" else 0.2 for _, label in rows],
        subplot_titles=[title for title, _ in rows],
    )
    row_index = {label: idx + 1 for idx, (_, label) in enumerate(rows)}

    fig.add_trace(
        go.Candlestick(
            x=enriched.index,
            open=enriched["Open"],
            high=enriched["High"],
            low=enriched["Low"],
            close=enriched["Close"],
            name="Price",
            increasing_line_color="#2ca02c",
            decreasing_line_color="#d62728",
        ),
        row=row_index["price"],
        col=1,
    )
    if show_sma20 and "SMA20" in enriched:
        fig.add_trace(
            go.Scatter(x=enriched.index, y=enriched["SMA20"], name="SMA20", line=dict(color="#1f77b4")),
            row=row_index["price"],
            col=1,
        )
    if show_sma50 and "SMA50" in enriched:
        fig.add_trace(
            go.Scatter(x=enriched.index, y=enriched["SMA50"], name="SMA50", line=dict(color="#ff7f0e")),
            row=row_index["price"],
            col=1,
        )
    if show_bbands:
        close = enriched["Close"].astype(float)
        basis = close.rolling(window=20).mean()
        dev = close.rolling(window=20).std()
        upper = basis + 2 * dev
        lower = basis - 2 * dev
        fig.add_trace(
            go.Scatter(x=enriched.index, y=upper, name="BB Upper", line=dict(color="#8c564b", dash="dot")),
            row=row_index["price"],
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=enriched.index, y=lower, name="BB Lower", line=dict(color="#8c564b", dash="dot")),
            row=row_index["price"],
            col=1,
        )

    volume_row = row_index["volume"]
    fig.add_trace(
        go.Bar(x=enriched.index, y=enriched["Volume"], name="Volume", marker_color="#7f7f7f"),
        row=volume_row,
        col=1,
    )

    if show_macd and "macd" in row_index:
        row = row_index["macd"]
        fig.add_trace(
            go.Bar(x=enriched.index, y=enriched["MACD_hist"], name="MACD hist", marker_color="#8c564b"),
            row=row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=enriched.index, y=enriched["MACD"], name="MACD", line=dict(color="#2ca02c")),
            row=row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=enriched.index, y=enriched["MACD_signal"], name="Signal", line=dict(color="#d62728")),
            row=row,
            col=1,
        )

    if show_rsi and "rsi" in row_index:
        row = row_index["rsi"]
        fig.add_trace(
            go.Scatter(x=enriched.index, y=enriched["RSI"], name="RSI", line=dict(color="#9467bd")),
            row=row,
            col=1,
        )
        fig.add_hrect(y0=30, y1=70, line_width=0, fillcolor="rgba(200,200,200,0.2)", row=row, col=1)
        fig.update_yaxes(range=[0, 100], row=row, col=1)

    fig.update_layout(
        height=850,
        showlegend=True,
        template="plotly_white",
        margin=dict(l=40, r=20, t=60, b=40),
    )
    price_row = row_index["price"]
    fig.update_yaxes(type=price_scale, row=price_row, col=1)
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all"),
            ]
        ),
        rangeslider=dict(visible=True),
        type="date",
        row=price_row,
        col=1,
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

    st.write("### Watchlist selection")
    selection_col, indicator_col = st.columns([3, 1])
    with selection_col:
        ticker_label = st.selectbox("Choose a ticker to analyze", WATCHLIST_LABELS, key="watchlist_selector")
        timeframe_label = st.selectbox("Timeframe", TIMEFRAME_OPTIONS, index=1, key="timeframe_select")
        freq_label = st.selectbox("Sampling", list(SAMPLE_FREQUENCIES.keys()), index=0, key="freq_select")
        scale_label = st.selectbox("Price scale", ["Linear", "Log"], index=0, key="scale_select")
        window_days = TIMEFRAME_WINDOWS[timeframe_label]
    with indicator_col:
        st.write("### Indicators")
        show_sma20 = st.checkbox("SMA 20", value=True)
        show_sma50 = st.checkbox("SMA 50", value=True)
        show_bbands = st.checkbox("Bollinger Bands", value=False)
        show_macd = st.checkbox("MACD", value=True)
        show_rsi = st.checkbox("RSI", value=True)

    selected_ticker, selected_name = WATCHLIST_LABEL_MAP[ticker_label]
    price_scale = "log" if scale_label == "Log" else "linear"
    sampling_rule = SAMPLE_FREQUENCIES[freq_label]
    st.caption("Selection pulls the latest OHLC snapshot and indicators directly from yfinance.")

    try:
        watchlist_df, history_map = load_live_watchlist_snapshot(((selected_ticker, selected_name),))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load live data: {exc}")
        watchlist_df = pd.DataFrame()
        history_map = {}
    if watchlist_df.empty:
        st.warning("No live data returned for the selected ticker.")
    else:
        row = watchlist_df.iloc[0]
        metric_cols = st.columns([1, 1, 1, 1])
        metric_cols[0].metric("Last", format_price(row["price"]))
        metric_cols[1].metric("1D", format_pct(row["1D"]))
        metric_cols[2].metric("1W", format_pct(row["1W"]))
        metric_cols[3].metric("1M", format_pct(row["1M"]))

    barometer_cards = compute_barometer_signals(history_map.get(selected_ticker, pd.DataFrame()))
    if barometer_cards:
        st.write("### Short-term barometer")
        card_cols = st.columns(len(barometer_cards))
        for col, card in zip(card_cols, barometer_cards):
            with col:
                st.markdown(f"**{card['horizon']}**")
                st.metric(card["bias"], f"{card['change']:+.2f}%")
                st.caption(card["rationale"])

    if selected_ticker in history_map:
        st.write(f"### Plotly Dash view – {selected_ticker} ({selected_name})")
        selected_history = history_map[selected_ticker]
        resampled_history = resample_history(selected_history, sampling_rule)
        chart = build_plotly_dash_chart(
            selected_ticker,
            resampled_history,
            window_days,
            show_sma20=show_sma20,
            show_sma50=show_sma50,
            show_macd=show_macd,
            show_rsi=show_rsi,
            show_bbands=show_bbands,
            price_scale=price_scale,
        )
        if chart.data:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("Not enough data to render the requested timeframe.")
    elif not watchlist_df.empty:
        st.info("Select a ticker with available history to render the chart.")

    st.write("### Signal generation")
    note_mode = st.radio("Mode", ("Auto", "Add analyst notes"), horizontal=True, key="note_mode")
    trigger_signal = st.button("Generate signal", type="primary")
    notes = ""
    if note_mode == "Add analyst notes":
        notes = st.text_area(
            "Analyst notes",
            help="These notes are appended to the MACD+RSI prompt before the LLM generates a signal.",
        )

    if trigger_signal:
        try:
            result = generate_signal(
                tickers=[item["ticker"] for item in DEFAULT_WATCHLIST],
                notes=notes or None,
                timeout=timeout,
                retries=int(retries),
            )
            st.success(f"Signal generated at {datetime.now().isoformat(timespec='seconds')}")
            render_signal(result)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to generate signal: {exc}")
    else:
        st.info("Choose Auto for a vanilla MACD+RSI run or add notes to guide the signal before hitting *Generate*. ")
else:
    render_about()


