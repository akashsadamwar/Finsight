from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from .analytics import (
    detect_anomalies as run_detect_anomalies,
    get_merchant_summary as run_get_merchant_summary,
    query_transactions as run_query_transactions,
)


mcp = MCPServer("FinSight Payments Analytics")


@mcp.tool()
def query_transactions(
    merchant_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chargeback_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query payments through bounded filters; never accepts raw SQL."""
    return run_query_transactions(merchant_id, start_date, end_date, chargeback_only, limit)


@mcp.tool()
def get_merchant_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    merchant_id: str | None = None,
) -> list[dict[str, Any]]:
    """Aggregate transaction volume and chargebacks by merchant."""
    return run_get_merchant_summary(start_date, end_date, merchant_id)


@mcp.tool()
def detect_anomalies(
    recent_days: int = 7,
    baseline_days: int = 30,
    z_threshold: float = 2.0,
) -> list[dict[str, Any]]:
    """Find merchants whose recent chargeback rate is unusually high."""
    return run_detect_anomalies(recent_days, baseline_days, z_threshold)


if __name__ == "__main__":
    mcp.run()

