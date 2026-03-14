# BiBroker Requirements Repository

_Repurposed from the previous `azure_llm_app_demo` skeleton; this repo now tracks discovery artifacts for BiBroker._

This repository captures the product requirements, research inputs, and delivery plan for the **BiBroker** initiative. It is intentionally separate from prior experimental work so we can document the problem space cleanly before scaffolding code.

## Repository layout

```
bibroker-requirements/
├── README.md              # This file: overview + navigation
├── docs/
│   ├── requirements.md    # Core specification (personas, workflows, KPIs)
│   ├── personas.md        # Target-user archetypes and journeys
│   ├── data-sources.md    # Ingestion/catalog of broker files + constraints
│   ├── trading-strategy.md# MACD+RSI blueprint for daily signals
│   └── roadmap.md         # Milestones, releases, and dependency mapping
└── notes/                 # (optional) Scratchpad for interviews or research
```

> Feel free to add more folders (e.g., `/references`, `/ux`, `/experiments`) as the discovery work evolves.

## How to use this repo

1. **Capture discovery inputs** – Meeting notes, broker file samples, regulatory constraints.
2. **Iterate on requirements** – Keep `docs/requirements.md` as the single source of truth; link out to supporting docs.
3. **Track decisions** – Any major assumption or scope decision should be summarized here before being mirrored into implementation backlogs.
4. **Hand off to delivery** – Once requirements stabilize, we’ll copy the relevant specs into the implementation repo (backend/frontend) and treat this repo as the authoritative reference.

## Outstanding needs

- Flesh out problem statement and success metrics.
- Confirm data ingestion scope (file types, APIs, privacy constraints).
- Decide on v0 deliverables (daily signal delivery, exports, etc.).
- Define integration targets and sequencing.

See `docs/requirements.md` for the current working draft.
