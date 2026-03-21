"""Data helpers for the BiBroker dashboard and APIs."""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

import pandas as pd
import yfinance as yf

from signal_engine import DEFAULT_WATCHLIST  # type: ignore

LOOKBACK_WINDOWS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
}


def format_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:+.2f}%"


def format_price(value: float | None, currency_symbol: str = "€") -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{currency_symbol}{value:,.2f}"


def calculate_pct_changes(price_series: pd.Series, windows: Dict[str, int] | None = None) -> Dict[str, float]:
    windows = windows or LOOKBACK_WINDOWS
    latest_price = price_series.iloc[-1]
    pct_changes: Dict[str, float] = {}
    for label, steps in windows.items():
        if len(price_series) <= steps:
            pct_changes[label] = float("nan")
            continue
        past_value = price_series.iloc[-(steps + 1)]
        pct_changes[label] = ((latest_price - past_value) / past_value) * 100 if past_value else float("nan")
    return pct_changes


def compute_indicators(history: pd.DataFrame) -> pd.DataFrame:
    df = history.copy()
    price = df["Close"]
    df["SMA20"] = price.rolling(20).mean()
    df["SMA50"] = price.rolling(50).mean()

    ema12 = price.ewm(span=12, adjust=False).mean()
    ema26 = price.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    delta = price.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df.dropna()


def download_watchlist_snapshot(
    watchlist: Sequence[Dict[str, str]] | None = None,
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    rows = []
    history_map: Dict[str, pd.DataFrame] = {}
    watchlist = watchlist or DEFAULT_WATCHLIST
    for item in watchlist:
        ticker = item["ticker"]
        name = item["name"]
        try:
            df = yf.download(
                ticker,
                period="6mo",
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
        except Exception:  # noqa: BLE001
            continue
        if df.empty:
            continue
        df.index = pd.to_datetime(df.index)
        history_map[ticker] = df
        price_series = df["Close"].dropna()
        if price_series.empty:
            continue
        latest_price = price_series.iloc[-1]
        pct_changes = calculate_pct_changes(price_series)

        rows.append(
            {
                "ticker": ticker,
                "name": name,
                "price": latest_price,
                "1D": pct_changes["1D"],
                "1W": pct_changes["1W"],
                "1M": pct_changes["1M"],
            }
        )

    df_rows = pd.DataFrame(rows)
    return df_rows, history_map
