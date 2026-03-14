# BiBroker Requirements (Working Draft)

_Last updated: March 13, 2026_

## 1. Vision & Problem Statement

BiBroker aims to become Roger’s brokerage analytics co-pilot that:
- Normalizes holdings from multiple exchanges/certificates (with Vienna tickers preferred).
- Surfaces allocation insights (sector/geo splits, liquidity runway, tax lots).
- Generates daily, watchlist-specific buy/sell recommendations (with probability/conviction scores) and delivers them via message—no frontend required initially.

**Clarified scope:** prioritize backend intelligence + automated brief delivery first; UI/dashboard work can wait until the recommendation loop is solid.

## 2. Target Outcomes

| Outcome | KPI / Evidence |
| --- | --- |
| Faster portfolio reviews | Reduce manual spreadsheet prep time by ≥70% |
| Actionable insights | At least 3 prioritized recommendations per review cycle |
| Morning trade guidance | Daily buy/sell signal for the **default watchlist** (test & tryouts) with probability/confidence score >= 0.7 |
| Frictionless exports (later) | One-click PDF/DOCX briefs with localized tickers |

## 3. Personas & Workflows

See `personas.md` for detailed archetypes. Primary persona today is **Roger (Founder/PM)** who wants a morning digest and deep-dive workspace. Secondary personas (e.g., advisor, finance ops) TBD.

**Initial workflows to validate:**
1. Import/refresh holdings (CSV, brokerage PDF, manual form).
2. Run allocation health check (diversification, cash buffer, watchlist deltas).
3. Generate automated morning trade brief (per watchlist) with buy/sell suggestion + probability/confidence + rationale.
4. Deliver the brief via WhatsApp/email/API—no UI required yet.
5. Ask ad-hoc questions via chatbot/API ("How exposed am I to semiconductors?").

## 4. Data Inputs & Constraints

Reference `data-sources.md` for the detailed inventory.
- Holdings table from March 1, 2026 (BROA.VI, INL.DE, NVTS, NVD.DE, PLTR + €1k cash).
- Watchlist fixture with Apple Stocks links for Vienna + US tickers.
- User-defined share lists: each list must store **current possible budget**, **currently deployed budget**, and **per-share allocation split** so we can show headroom vs utilization at a glance.
- Canonical tickers should default to Vienna listings when available (e.g., INL.DE for Intel), with alternates for other exchanges as fallbacks.
- Include a broad coverage of Austrian-listed equities so Roger can pivot to lower-cost local shares when budget is constrained.
- Need clarification on additional brokers, live APIs, and PII handling requirements.

## 5. Analytics & Signal Engine Tasks

| Task | Mode | Notes |
| --- | --- | --- |
| Holdings summarization | batch + on-demand | highlight allocation shifts & concentration |
| Recommendation engine | batch (daily 06:00) | focus on the **default watchlist** first; combine MACD(12,26,9) + RSI(14, 30/70) signals (with divergence check + stop-loss guidance) to produce buy/sell suggestion with probability/confidence and rationale |
| Divergence detection | batch | Identify bullish/bearish divergence between price and RSI to boost/decrease confidence scores |
| Risk controls | batch | Attach suggested stop-loss (e.g., ~5% below entry) and note upcoming events (earnings/news) |
| Narrative generation | on-demand | Optional PDF/DOCX brief text once backend signals are validated |
| Q&A co-pilot | interactive | likely via MCP endpoint reusing Nives infra |

_Open questions:_ Do we require forecasting, scenario modeling, or compliance narrative explainability in v0?

## 6. Integrations

Prioritized assumptions (awaiting confirmation):
1. **Brokerage CSV/PDF ingest** – manual drop for now, automation later.
2. **Market data API** – price history, FX, fundamentals (Alphavantage/Xetra feed?).
3. **Document export** – same engine as Nives (DOCX/PDF pipeline) or a leaner alternative.
4. **Notification channel** – WhatsApp (primary) + email fallback for automated morning suggestions; no frontend needed initially.

## 7. Deliverables & Artifacts

- **Backend service** that ingests holdings/watchlists and emits daily buy/sell suggestions with probability/confidence (initially scoped to the default watchlist).
- **Delivery pipeline** (WhatsApp/email/API) for 06:00 messages; replaceable with other channels later.
- **REST + MCP endpoints** for programmatic access and assistant integration.
- **Seed dataset** for demos/tests (holdings + watchlist + sample insights).
- **Dashboard / export artifacts** are deferred until backend guidance is proven valuable.

## 8. Roadmap Overview

Refer to `roadmap.md` for milestone-level planning. Tentative phases:
1. Requirements lock + dataset prep
2. Backend prototype (ingest + analytics + narrative)
3. Frontend dashboard + export integration
4. Copilot/API features + automation

## 9. Open Decisions

1. Finalize problem statement wording + scope boundaries.
2. Confirm data ingestion pipeline (manual vs automated connectors).
3. Pick market data provider and caching strategy.
4. Decide if compliance/reporting features are in v0 or deferred.
5. Determine notification cadence + format (e.g., probability threshold, multi-watchlist rotation).

---
**Action:** Work with Roger to answer the open questions; update this doc as canonical reference before implementation begins.
