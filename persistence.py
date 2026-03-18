"""Persistence helpers for Bi-Lytix Assessment."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Dict, List, Sequence, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from signal_engine import DEFAULT_WATCHLIST  # type: ignore

SYSTEM_ACTOR = os.getenv("BIBROKER_SYSTEM_ACTOR", "system")
DEFAULT_USER_NAME = os.getenv("BIBROKER_DEFAULT_USER_NAME", "Roger Binder")
DEFAULT_WATCHLIST_NAME = os.getenv("BIBROKER_DEFAULT_WATCHLIST_NAME", "Default Watchlist")
DEFAULT_WATCHLIST_DESC = os.getenv(
    "BIBROKER_DEFAULT_WATCHLIST_DESCRIPTION",
    "Primary Bi-Lytix assessment universe",
)

LOOKBACK_WINDOWS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
}

INDICATOR_TYPES = [
    ("SMA20", "20-day simple moving average"),
    ("SMA50", "50-day simple moving average"),
    ("MACD", "MACD line (12,26)",),
    ("MACD_SIGNAL", "MACD signal line (9)",),
    ("MACD_HIST", "MACD histogram",),
    ("RSI", "Relative Strength Index (14)",),
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_user (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    email VARCHAR(120)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS watchlist (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    base_currency VARCHAR(16) DEFAULT 'EUR',
    UNIQUE KEY watchlist_user_name_idx (user_id, name),
    CONSTRAINT fk_watchlist_user FOREIGN KEY (user_id) REFERENCES app_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS share (
    id CHAR(36) PRIMARY KEY,
    watchlist_id CHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    ticker VARCHAR(32) NOT NULL,
    currency VARCHAR(12) DEFAULT 'EUR',
    exchange VARCHAR(32),
    last_price DECIMAL(18,4),
    last_price_at DATETIME(6),
    change_1d DECIMAL(9,4),
    change_1w DECIMAL(9,4),
    change_1m DECIMAL(9,4),
    UNIQUE KEY share_watchlist_ticker_idx (watchlist_id, ticker),
    CONSTRAINT fk_share_watchlist FOREIGN KEY (watchlist_id) REFERENCES watchlist(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS share_historical (
    id CHAR(36) PRIMARY KEY,
    share_id CHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    historical_blob JSON NOT NULL,
    as_of DATETIME(6) NOT NULL,
    UNIQUE KEY share_historical_share_id_uq (share_id),
    CONSTRAINT fk_share_historical_share FOREIGN KEY (share_id) REFERENCES share(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS indicator_type (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS share_indicator (
    id CHAR(36) PRIMARY KEY,
    share_id CHAR(36) NOT NULL,
    indicator_type_id CHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(250) DEFAULT '',
    created DATETIME(6) NOT NULL,
    modified_last DATETIME(6) NOT NULL,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    modified_by VARCHAR(50) NOT NULL,
    indicator_payload JSON,
    timeframe VARCHAR(32) DEFAULT 'daily',
    UNIQUE KEY share_indicator_unique_idx (share_id, indicator_type_id),
    CONSTRAINT fk_share_indicator_share FOREIGN KEY (share_id) REFERENCES share(id),
    CONSTRAINT fk_share_indicator_indicator FOREIGN KEY (indicator_type_id) REFERENCES indicator_type(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _now() -> datetime:
    return datetime.utcnow()


def _uuid() -> str:
    return str(uuid.uuid4())


def _audit_defaults(name: str, actor: str = SYSTEM_ACTOR) -> Dict[str, object]:
    now = _now()
    return {
        "name": name[:50],
        "description": "",
        "created": now,
        "modified_last": now,
        "is_deleted": False,
        "created_by": actor,
        "modified_by": actor,
    }


@dataclass(frozen=True)
class RepositoryContext:
    user_id: str
    watchlist_id: str


class WatchlistRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            buffer: List[str] = []
            for line in SCHEMA_SQL.strip().splitlines():
                if line.strip().startswith("--"):
                    continue
                buffer.append(line)
            statements = "\n".join(buffer).split(";")
            for statement in statements:
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))

    def ensure_indicator_types(self) -> None:
        with self.engine.begin() as conn:
            for code, desc in INDICATOR_TYPES:
                existing = conn.execute(
                    text("SELECT id FROM indicator_type WHERE code = :code AND is_deleted = 0"),
                    {"code": code},
                ).fetchone()
                if existing:
                    continue
                payload = {
                    **_audit_defaults(code),
                    "id": _uuid(),
                    "description": desc[:250],
                    "code": code,
                }
                conn.execute(
                    text(
                        """
                        INSERT INTO indicator_type (
                            id, name, description, created, modified_last,
                            is_deleted, created_by, modified_by, code
                        ) VALUES (
                            :id, :name, :description, :created, :modified_last,
                            :is_deleted, :created_by, :modified_by, :code
                        )
                        """
                    ),
                    payload,
                )

    def ensure_default_state(self, watchlist_seed: Sequence[Dict[str, str]]) -> RepositoryContext:
        with self.engine.begin() as conn:
            user_row = conn.execute(
                text("SELECT id FROM app_user WHERE name = :name AND is_deleted = 0"),
                {"name": DEFAULT_USER_NAME},
            ).fetchone()
            if user_row:
                user_id = user_row[0]
            else:
                user_id = _uuid()
                payload = {
                    **_audit_defaults(DEFAULT_USER_NAME),
                    "id": user_id,
                    "description": DEFAULT_WATCHLIST_DESC[:250],
                    "email": None,
                }
                conn.execute(
                    text(
                        """
                        INSERT INTO app_user (
                            id, name, description, created, modified_last,
                            is_deleted, created_by, modified_by, email
                        ) VALUES (
                            :id, :name, :description, :created, :modified_last,
                            :is_deleted, :created_by, :modified_by, :email
                        )
                        """
                    ),
                    payload,
                )

            watchlist_row = conn.execute(
                text(
                    """
                    SELECT id FROM watchlist
                    WHERE user_id = :user_id AND name = :name AND is_deleted = 0
                    """
                ),
                {"user_id": user_id, "name": DEFAULT_WATCHLIST_NAME},
            ).fetchone()
            if watchlist_row:
                watchlist_id = watchlist_row[0]
            else:
                watchlist_id = _uuid()
                payload = {
                    **_audit_defaults(DEFAULT_WATCHLIST_NAME),
                    "id": watchlist_id,
                    "description": DEFAULT_WATCHLIST_DESC[:250],
                    "user_id": str(user_id),
                    "base_currency": "EUR",
                }
                conn.execute(
                    text(
                        """
                        INSERT INTO watchlist (
                            id, user_id, name, description, created, modified_last,
                            is_deleted, created_by, modified_by, base_currency
                        ) VALUES (
                            :id, :user_id, :name, :description, :created, :modified_last,
                            :is_deleted, :created_by, :modified_by, :base_currency
                        )
                        """
                    ),
                    payload,
                )

            for item in watchlist_seed:
                ticker = item["ticker"].upper()
                share_row = conn.execute(
                    text(
                        """
                        SELECT id FROM share
                        WHERE watchlist_id = :watchlist_id AND ticker = :ticker AND is_deleted = 0
                        """
                    ),
                    {"watchlist_id": watchlist_id, "ticker": ticker},
                ).fetchone()
                if share_row:
                    continue
                share_id = _uuid()
                payload = {
                    **_audit_defaults(item.get("name", ticker)),
                    "id": share_id,
                    "watchlist_id": str(watchlist_id),
                    "ticker": ticker,
                    "currency": item.get("currency", "EUR"),
                    "exchange": item.get("exchange", ""),
                }
                conn.execute(
                    text(
                        """
                        INSERT INTO share (
                            id, watchlist_id, name, description, created, modified_last,
                            is_deleted, created_by, modified_by, ticker, currency, exchange
                        ) VALUES (
                            :id, :watchlist_id, :name, :description, :created, :modified_last,
                            :is_deleted, :created_by, :modified_by, :ticker, :currency, :exchange
                        )
                        """
                    ),
                    payload,
                )
        return RepositoryContext(user_id=user_id, watchlist_id=watchlist_id)

    def list_shares(self, watchlist_id: str) -> List[Dict[str, object]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, ticker, name
                    FROM share
                    WHERE watchlist_id = :watchlist_id AND is_deleted = 0
                    ORDER BY name
                    """
                ),
                {"watchlist_id": watchlist_id},
            ).fetchall()
        return [
            {
                "id": row[0],
                "ticker": row[1],
                "name": row[2],
            }
            for row in rows
        ]

    def refresh_watchlist_history(self, watchlist_id: str, watchlist_seed: Sequence[Dict[str, str]]) -> Dict[str, str]:
        shares = self.list_shares(watchlist_id)
        ticker_to_name = {item["ticker"].upper(): item["name"] for item in watchlist_seed}
        updated: Dict[str, str] = {}
        with self.engine.begin() as conn:
            for share in shares:
                ticker = share["ticker"]
                df = yf.download(
                    ticker,
                    period="6mo",
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                )
                if df.empty:
                    continue
                df.index = pd.to_datetime(df.index)
                df = df.dropna(subset=["Close"])
                latest_price = float(df["Close"].iloc[-1])
                pct_changes = {}
                price_series = df["Close"].reset_index(drop=True)
                for label, steps in LOOKBACK_WINDOWS.items():
                    if len(price_series) <= steps:
                        pct_changes[label] = None
                        continue
                    past_value = float(price_series.iloc[-(steps + 1)])
                    pct_changes[label] = ((latest_price - past_value) / past_value) * 100 if past_value else None

                history_reset = df.reset_index().rename(columns={"index": "Date"})
                history_reset["Date"] = history_reset["Date"].dt.strftime("%Y-%m-%d")
                history_payload = history_reset[
                    ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
                ].rename(columns={"Adj Close": "AdjClose"}).to_dict(orient="records")

                last_price_at = df.index[-1].to_pydatetime()
                if last_price_at.tzinfo:
                    last_price_at = last_price_at.replace(tzinfo=None)

                timestamp = _now()
                params = {
                    "last_price": latest_price,
                    "last_price_at": last_price_at,
                    "change_1d": pct_changes["1D"],
                    "change_1w": pct_changes["1W"],
                    "change_1m": pct_changes["1M"],
                    "id": share["id"],
                    "now": timestamp,
                }
                conn.execute(
                    text(
                        """
                        UPDATE share
                        SET last_price = :last_price,
                            last_price_at = :last_price_at,
                            change_1d = :change_1d,
                            change_1w = :change_1w,
                            change_1m = :change_1m,
                            modified_last = :now,
                            modified_by = :actor
                        WHERE id = :id
                        """
                    ),
                    {**params, "actor": SYSTEM_ACTOR},
                )

                historical_id = _uuid()
                as_of = last_price_at
                payload_created = timestamp
                conn.execute(
                    text(
                        """
                        INSERT INTO share_historical (
                            id, share_id, name, description, created, modified_last,
                            is_deleted, created_by, modified_by, historical_blob, as_of
                        ) VALUES (
                            :hid, :share_id, :name, :description, :created, :modified_last,
                            :is_deleted, :created_by, :modified_by, :historical_blob, :as_of
                        )
                        ON DUPLICATE KEY UPDATE
                            historical_blob = VALUES(historical_blob),
                            modified_last = VALUES(modified_last),
                            modified_by = VALUES(modified_by),
                            as_of = VALUES(as_of)
                        """
                    ),
                    {
                        "hid": historical_id,
                        "share_id": share["id"],
                        "name": f"{ticker} history"[:50],
                        "description": f"Daily OHLC for {ticker_to_name.get(ticker, ticker)}"[:250],
                        "created": payload_created,
                        "modified_last": payload_created,
                        "is_deleted": 0,
                        "created_by": SYSTEM_ACTOR,
                        "modified_by": SYSTEM_ACTOR,
                        "historical_blob": json.dumps(history_payload),
                        "as_of": as_of,
                    },
                )
                updated[ticker] = f"{len(history_payload)} pts"
        return updated

    def fetch_watchlist_snapshot(self, watchlist_id: str) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT s.id, s.ticker, s.name, s.last_price, s.change_1d, s.change_1w, s.change_1m,
                           h.historical_blob
                    FROM share s
                    LEFT JOIN share_historical h ON h.share_id = s.id AND h.is_deleted = 0
                    WHERE s.watchlist_id = :watchlist_id AND s.is_deleted = 0
                    ORDER BY s.name
                    """
                ),
                {"watchlist_id": watchlist_id},
            ).fetchall()

        data = []
        history_map: Dict[str, pd.DataFrame] = {}
        for row in rows:
            ticker = row[1]
            history_blob = row[7]
            if history_blob:
                if isinstance(history_blob, str):
                    try:
                        history_blob = json.loads(history_blob)
                    except json.JSONDecodeError:
                        history_blob = []
                df = pd.DataFrame(history_blob)
                if not df.empty:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)
                    history_map[ticker] = df
            data.append(
                {
                    "ticker": ticker,
                    "name": row[2],
                    "price": float(row[3]) if row[3] is not None else None,
                    "1D": float(row[4]) if row[4] is not None else None,
                    "1W": float(row[5]) if row[5] is not None else None,
                    "1M": float(row[6]) if row[6] is not None else None,
                }
            )

        df_rows = pd.DataFrame(data)
        return df_rows, history_map


def build_repository(database_url: str | None = None) -> Tuple[WatchlistRepository, RepositoryContext]:
    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    repo = WatchlistRepository(engine)
    repo.ensure_schema()
    repo.ensure_indicator_types()
    ctx = repo.ensure_default_state(DEFAULT_WATCHLIST)
    return repo, ctx
