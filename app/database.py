from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = Path(
    os.getenv(
        "FINSIGHT_DB_PATH",
        Path(__file__).resolve().parents[1] / "data" / "finsight.db",
    )
)


@contextmanager
def connect(db_path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS merchants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL REFERENCES merchants(id),
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL CHECK (status IN ('approved', 'declined')),
                created_at TEXT NOT NULL,
                chargeback INTEGER NOT NULL DEFAULT 0 CHECK (chargeback IN (0, 1))
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_merchant_created
                ON transactions (merchant_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_transactions_created
                ON transactions (created_at);
            """
        )
