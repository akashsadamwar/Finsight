from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .database import DEFAULT_DB_PATH, connect, initialize


MERCHANTS = [
    ("m_001", "Northstar Electronics", "electronics", "medium"),
    ("m_002", "Harbor Grocery", "grocery", "low"),
    ("m_003", "Atlas Travel", "travel", "high"),
    ("m_004", "Juniper Apparel", "retail", "low"),
    ("m_005", "Metro Fuel", "fuel", "medium"),
    ("m_006", "Ember Games", "digital_goods", "high"),
    ("m_007", "Cedar Pharmacy", "pharmacy", "low"),
    ("m_008", "Summit Fitness", "subscriptions", "medium"),
]


def seed_database(
    db_path: str | Path = DEFAULT_DB_PATH,
    rows: int = 25_000,
    seed: int = 42,
) -> int:
    if rows < 1:
        raise ValueError("rows must be positive")

    initialize(db_path)
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    with connect(db_path) as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO merchants (id, name, category, risk_level) VALUES (?, ?, ?, ?)",
            MERCHANTS,
        )
        if connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]:
            return 0

        transactions = []
        for index in range(rows):
            merchant_id = rng.choice(MERCHANTS)[0]
            age = rng.random() * 45
            created_at = now - timedelta(days=age)
            status = "declined" if rng.random() < 0.06 else "approved"

            chargeback_rate = 0.012
            if merchant_id in {"m_003", "m_006"}:
                chargeback_rate = 0.025
            # Deliberate recent spike so the anomaly tool has a useful demo result.
            if merchant_id == "m_006" and age <= 7:
                chargeback_rate = 0.16

            chargeback = int(status == "approved" and rng.random() < chargeback_rate)
            amount_cents = max(100, int(rng.lognormvariate(8.0, 0.9)))
            transactions.append(
                (
                    f"tx_{index + 1:08d}",
                    merchant_id,
                    amount_cents,
                    "USD",
                    status,
                    created_at.isoformat(),
                    chargeback,
                )
            )

        connection.executemany(
            """
            INSERT INTO transactions
                (id, merchant_id, amount_cents, currency, status, created_at, chargeback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            transactions,
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FinSight with synthetic payments")
    parser.add_argument("--rows", type=int, default=25_000)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    inserted = seed_database(args.db, args.rows)
    print(f"Inserted {inserted:,} transactions into {args.db}")


if __name__ == "__main__":
    main()

