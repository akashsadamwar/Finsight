from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from .database import DEFAULT_DB_PATH, connect


def _iso_date(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"{name} must use YYYY-MM-DD") from error


def query_transactions(
    merchant_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chargeback_only: bool = False,
    limit: int = 100,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    start_date = _iso_date(start_date, "start_date")
    end_date = _iso_date(end_date, "end_date")
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    conditions, parameters = [], []
    if merchant_id:
        conditions.append("t.merchant_id = ?")
        parameters.append(merchant_id)
    if start_date:
        conditions.append("date(t.created_at) >= date(?)")
        parameters.append(start_date)
    if end_date:
        conditions.append("date(t.created_at) <= date(?)")
        parameters.append(end_date)
    if chargeback_only:
        conditions.append("t.chargeback = 1")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    parameters.append(limit)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT t.id, t.merchant_id, m.name AS merchant_name, t.amount_cents,
                   t.currency, t.status, t.created_at, t.chargeback
            FROM transactions t
            JOIN merchants m ON m.id = t.merchant_id
            {where}
            ORDER BY t.created_at DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


def get_merchant_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    merchant_id: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    start_date = _iso_date(start_date, "start_date")
    end_date = _iso_date(end_date, "end_date")
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    conditions, parameters = [], []
    if start_date:
        conditions.append("date(t.created_at) >= date(?)")
        parameters.append(start_date)
    if end_date:
        conditions.append("date(t.created_at) <= date(?)")
        parameters.append(end_date)
    if merchant_id:
        conditions.append("m.id = ?")
        parameters.append(merchant_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT m.id AS merchant_id, m.name AS merchant_name, m.category,
                   COUNT(t.id) AS transaction_count,
                   COALESCE(SUM(t.amount_cents), 0) AS total_amount_cents,
                   COALESCE(SUM(t.chargeback), 0) AS chargeback_count,
                   CASE WHEN COUNT(t.id) = 0 THEN 0
                        ELSE ROUND(100.0 * SUM(t.chargeback) / COUNT(t.id), 2)
                   END AS chargeback_rate_pct
            FROM merchants m
            LEFT JOIN transactions t ON t.merchant_id = m.id
            {where}
            GROUP BY m.id, m.name, m.category
            ORDER BY total_amount_cents DESC
            """,
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


def detect_anomalies(
    recent_days: int = 7,
    baseline_days: int = 30,
    z_threshold: float = 2.0,
    db_path: str | Path = DEFAULT_DB_PATH,
    today: date | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= recent_days <= 30:
        raise ValueError("recent_days must be between 1 and 30")
    if baseline_days < 7:
        raise ValueError("baseline_days must be at least 7")
    if z_threshold <= 0:
        raise ValueError("z_threshold must be positive")

    today = today or datetime.now(timezone.utc).date()
    recent_start = today - timedelta(days=recent_days - 1)
    baseline_start = recent_start - timedelta(days=baseline_days)

    with connect(db_path) as connection:
        merchants = connection.execute("SELECT id, name FROM merchants").fetchall()
        daily_rows = connection.execute(
            """
            SELECT merchant_id, date(created_at) AS day, COUNT(*) AS transaction_count,
                   SUM(chargeback) AS chargeback_count
            FROM transactions
            WHERE date(created_at) >= date(?) AND date(created_at) <= date(?)
            GROUP BY merchant_id, date(created_at)
            """,
            (baseline_start.isoformat(), today.isoformat()),
        ).fetchall()

    daily: dict[str, dict[str, float]] = {}
    for row in daily_rows:
        daily.setdefault(row["merchant_id"], {})[row["day"]] = (
            row["chargeback_count"] / row["transaction_count"]
        )

    results = []
    for merchant in merchants:
        rates = daily.get(merchant["id"], {})
        baseline = [
            rates.get((baseline_start + timedelta(days=offset)).isoformat(), 0.0)
            for offset in range(baseline_days)
        ]
        recent = [
            rates.get((recent_start + timedelta(days=offset)).isoformat(), 0.0)
            for offset in range(recent_days)
        ]
        baseline_mean = mean(baseline)
        recent_mean = mean(recent)
        # ponytail: 0.5 percentage-point floor avoids unstable scores on sparse data;
        # replace with a volume-aware model when production data warrants it.
        deviation = max(pstdev(baseline), 0.005)
        z_score = (recent_mean - baseline_mean) / deviation
        if z_score >= z_threshold:
            results.append(
                {
                    "merchant_id": merchant["id"],
                    "merchant_name": merchant["name"],
                    "baseline_chargeback_rate_pct": round(baseline_mean * 100, 2),
                    "recent_chargeback_rate_pct": round(recent_mean * 100, 2),
                    "z_score": round(z_score, 2),
                }
            )
    return sorted(results, key=lambda row: row["z_score"], reverse=True)

