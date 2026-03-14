# MACD + RSI Strategy Blueprint

This document captures the baseline technical strategy used for the initial BiBroker guidance loop. It combines MACD and RSI indicators so that momentum and overbought/oversold conditions confirm each other.

## 1. Indicator Settings
- **Timeframes:**
  - Default: Daily (1D) for swing trades holding days/weeks.
  - Optional: 15m or 1h for intraday loops (future scope).
- **RSI:** Length 14, lower bound 30 (oversold), upper bound 70 (overbought).
- **MACD:** Fast 12, Slow 26, Signal 9.

## 2. Buy Signal Logic
1. **Setup (RSI):** RSI drops near/at/below 30 → asset is oversold.
2. **Trigger (MACD):** MACD line crosses above signal line.
3. **Action:** When trigger follows a recent oversold RSI, mark a BUY suggestion with probability/confidence score.

### Enhancers
- Bullish divergence: price making lower lows while RSI prints higher lows → increase confidence.
- Optional filters: volume expansion or proximity to key support levels.

## 3. Sell Signal Logic
1. **Setup (RSI):** RSI approaches/exceeds 70 → asset overbought.
2. **Trigger (MACD):** MACD line crosses below signal line.
3. **Action:** When trigger follows recent overbought RSI, mark a SELL (profit take) signal.

### Enhancers
- Bearish divergence: price making higher highs but RSI lower highs → increase urgency/confidence.
- Consider partial exits if signal occurs during strong uptrend.

## 4. Risk Controls
- **Stop-loss:** Default 5% below buy price (tunable per asset).
- **News filter:** Flag upcoming earnings/releases; reduce confidence if uncertainty is high.
- **Position sizing:** Respect list-level budget limits (possible vs deployed budget fields).

## 5. Implementation Notes
- Run indicator calculations per ticker, per watchlist, at 06:00 local time using latest available close.
- Output includes: action (buy/sell/hold), probability/confidence (0-1), rationale text (RSI/MACD, divergence, contextual notes), recommended stop-loss.
- Future: Add signal aggregation (e.g., trending score, multi-timeframe confirmation).

Use this document as the canonical reference when building or tuning the signal engine.
