"""Tests for market_data helpers."""
from __future__ import annotations

import math
from typing import Any, List

import pandas as pd
import pytest

import market_data


def make_history(length: int = 80) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=length, freq="D")
    price = pd.Series(range(1, length + 1), index=dates)
    return pd.DataFrame(
        {
            "Open": price + 0.1,
            "High": price + 0.5,
            "Low": price - 0.3,
            "Close": price,
            "Adj Close": price,
            "Volume": 1_000,
        },
        index=dates,
    )


def test_format_helpers_handle_nan() -> None:
    assert market_data.format_pct(float("nan")) == "—"
    assert market_data.format_price(None) == "—"
    assert market_data.format_pct(1.2345) == "+1.23%"
    assert market_data.format_price(1234.5) == "€1,234.50"


def test_calculate_pct_changes_uses_default_windows() -> None:
    series = pd.Series(range(10, 40))
    pct = market_data.calculate_pct_changes(series)
    assert set(pct.keys()) == set(market_data.LOOKBACK_WINDOWS.keys())
    assert pytest.approx(pct["1D"], rel=1e-4) == (series.iloc[-1] - series.iloc[-2]) / series.iloc[-2] * 100


def test_compute_indicators_returns_expected_columns() -> None:
    history = make_history()
    enriched = market_data.compute_indicators(history)
    expected = {"SMA20", "SMA50", "MACD", "MACD_signal", "MACD_hist", "RSI"}
    assert expected.issubset(enriched.columns)
    assert 0 < len(enriched) < len(history)
    assert not enriched.isna().any().any()


def test_download_watchlist_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[str] = []

    def fake_download(ticker: str, *args: Any, **kwargs: Any) -> pd.DataFrame:
        calls.append(ticker)
        return make_history(30)

    monkeypatch.setattr(market_data.yf, "download", fake_download)

    watchlist = [
        {"ticker": "AAA", "name": "Alpha"},
        {"ticker": "BBB", "name": "Beta"},
    ]
    df, history = market_data.download_watchlist_snapshot(watchlist)
    assert calls == ["AAA", "BBB"]
    assert set(df["ticker"].tolist()) == {"AAA", "BBB"}
    assert "AAA" in history and "BBB" in history
    assert not df.empty


def test_download_watchlist_snapshot_handles_zero_lookback(monkeypatch: pytest.MonkeyPatch) -> None:
    history = make_history(10)
    history.iloc[-2, history.columns.get_loc("Close")] = 0
    history.iloc[-2, history.columns.get_loc("Adj Close")] = 0

    def fake_download(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return history

    monkeypatch.setattr(market_data.yf, "download", fake_download)
    df, _ = market_data.download_watchlist_snapshot([
        {"ticker": "AAA", "name": "Alpha"},
    ])
    assert math.isnan(df.iloc[0]["1D"])  # pct change should be NaN when prior value is zero
