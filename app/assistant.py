from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .analytics import detect_anomalies, get_merchant_summary, query_transactions


def answer_question(question: str) -> dict[str, Any]:
    """Small deterministic baseline; an LLM orchestrator can replace only this function."""
    normalized = question.lower()
    today = datetime.now(timezone.utc).date()

    if "anomal" in normalized or "spike" in normalized or "chargeback" in normalized:
        rows = detect_anomalies()
        if rows:
            names = ", ".join(row["merchant_name"] for row in rows[:3])
            answer = f"Detected {len(rows)} merchant chargeback anomaly(s): {names}."
        else:
            answer = "No merchant chargeback anomalies crossed the configured threshold."
        return {"answer": answer, "tools_used": ["detect_anomalies"], "data": rows}

    if any(word in normalized for word in ("merchant", "volume", "summary", "top")):
        start = (today - timedelta(days=29)).isoformat()
        rows = get_merchant_summary(start_date=start, end_date=today.isoformat())
        top = rows[0] if rows else None
        answer = (
            f"{top['merchant_name']} had the highest 30-day volume at "
            f"${top['total_amount_cents'] / 100:,.2f}."
            if top
            else "No merchant activity was found."
        )
        return {"answer": answer, "tools_used": ["get_merchant_summary"], "data": rows}

    rows = query_transactions(limit=25)
    return {
        "answer": f"Returned the {len(rows)} most recent transactions.",
        "tools_used": ["query_transactions"],
        "data": rows,
    }

