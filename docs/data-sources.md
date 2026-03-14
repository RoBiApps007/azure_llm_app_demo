# Data Sources & Inputs (Draft)

## 1. Holdings Snapshot (March 1, 2026)

| Symbol  | Name                        | Quantity | Notes |
| ------- | --------------------------- | -------- | ----- |
| BROA.VI | Broadcom Inc. (Vienna cert) | 3        | Vienna preferred listing |
| INL.DE  | Intel Corporation (Vienna)  | 20       | Xetra feed |
| NVTS    | Navitas Semiconductor       | 80       | NASDAQ |
| NVD.DE  | NVIDIA Corporation (Vienna) | 2        | Xetra feed |
| PLTR    | Palantir Technologies       | 8        | NYSE |
| Cash    | EUR liquidity               | €1,000   | Available for new allocations |

_Source:_ Roger’s latest update (Mar 13, 2026) + `bilytics-avl-playbook/bibroker/docs/current-investments.md`

## 2. Default Watchlist
A curated starter list drawn from Apple Stocks links (Vienna emphasis). Reference: `bilytics-avl-playbook/bibroker/docs/default-watchlist.md`.

## 3. Anticipated Additional Inputs
- **Brokerage statements:** PDF/CSV exports from primary brokers (need list + cadence).
- **Market data feeds:** Price, FX, fundamentals (provider TBD — e.g., Xetra, Polygon, Alphavantage).
- **Manual overrides:** Ability for Roger to edit holdings/watchlist inline.
- **LLM context:** Prior insights/recommendations to maintain continuity.

## 4. Constraints & Questions
1. Do we handle PII or account numbers? (Impacts storage + encryption requirements.)
2. Should ingestion be manual (file drop) or automated API polling in v0?
3. Required history depth (intra-day vs daily closes) for analytics/forecasting?
4. Need for compliance-grade audit logs?

Update this document as soon as real data samples and technical constraints are confirmed.
