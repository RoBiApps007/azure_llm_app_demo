#!/usr/bin/env python
"""CLI helper to refresh Bi-Lytix watchlist data on a schedule."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from persistence import build_repository  # type: ignore
from signal_engine import DEFAULT_WATCHLIST  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("refresh_watchlist")


def main() -> int:
    try:
        repo, ctx = build_repository()
    except RuntimeError as exc:
        LOGGER.error("Database unavailable: %s", exc)
        return 1

    LOGGER.info("Refreshing watchlist %s", ctx.watchlist_id)
    updates = repo.refresh_watchlist_history(ctx.watchlist_id, DEFAULT_WATCHLIST)
    LOGGER.info("Updated %s tickers", len(updates))
    LOGGER.debug("Details: %s", json.dumps(updates, indent=2))
    LOGGER.info("Completed refresh at %s", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
