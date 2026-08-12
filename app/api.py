from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from .analytics import detect_anomalies, get_merchant_summary, query_transactions
from .assistant import answer_question
from .database import initialize
from .mcp_server import mcp


mcp_app = mcp.streamable_http_app(streamable_http_path="/")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize()
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="FinSight",
    description="Auditable payments analytics exposed through REST and MCP tools.",
    version="0.1.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    return answer_question(request.question)


@app.get("/api/transactions")
def transactions(
    merchant_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chargeback_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    return query_transactions(merchant_id, start_date, end_date, chargeback_only, limit)


@app.get("/api/merchants/summary")
def merchant_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    merchant_id: str | None = None,
) -> list[dict]:
    return get_merchant_summary(start_date, end_date, merchant_id)


@app.get("/api/anomalies")
def anomalies(
    recent_days: int = Query(default=7, ge=1, le=30),
    baseline_days: int = Query(default=30, ge=7, le=365),
    z_threshold: float = Query(default=2.0, gt=0),
) -> list[dict]:
    return detect_anomalies(recent_days, baseline_days, z_threshold)


app.mount("/mcp", mcp_app)

