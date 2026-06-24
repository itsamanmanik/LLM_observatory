"""
FastAPI router — all endpoints.

"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.tracer import call_llm, MODELS
from backend.db.crud import (
    get_alerts, get_cost_df, get_evals_df,
    get_latency_df, get_provider_summary, get_traces_df,
    save_eval, save_trace,
)
from backend.db.session import SessionLocal, get_db
from backend.evaluator.scorer import evaluate
from backend.models.schemas import HealthResponse, RunRequest, RunResponse, RunResult

router    = APIRouter()
_executor = ThreadPoolExecutor(max_workers=6)


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", db=db_status, models=list(MODELS.keys()))


# ── Run evaluation ─────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunResponse)
async def run_evaluation(req: RunRequest):
    """
    Call all requested providers in parallel.
    Each thread opens and closes its own DB session — never shared.
    """
    loop = asyncio.get_event_loop()

    def _run_one(provider: str) -> RunResult:
        # ✅ Own session per thread — fixes IllegalStateChangeError
        db = SessionLocal()
        try:
            trace = call_llm(
                provider=provider,
                prompt=req.prompt,
                context=req.context,
                category=req.category,
            )
            score = evaluate(trace)
            save_trace(db, trace)
            save_eval(db, score)

            return RunResult(
                trace_id=trace.trace_id,
                provider=provider,
                model=trace.model,
                response=trace.response,
                latency_ms=round(trace.latency_ms, 1),
                total_tokens=trace.total_tokens,
                cost_usd=round(trace.cost_usd, 6),
                hallucination_score=score.hallucination_score,
                relevance_score=score.relevance_score,
                faithfulness_score=score.faithfulness_score,
                toxicity_score=score.toxicity_score,
                overall_score=score.overall_score,
                is_hallucinated=score.is_hallucinated,
                alert_triggered=score.alert_triggered,
                alert_reason=score.alert_reason,
                error=trace.error,
            )
        finally:
            db.close()  # always released

    tasks = [
        loop.run_in_executor(_executor, _run_one, provider)
        for provider in req.providers
    ]
    results: list[RunResult] = await asyncio.gather(*tasks)

    valid = [r for r in results if not r.error]
    best  = max(valid, key=lambda r: r.overall_score).provider if valid else None

    return RunResponse(results=list(results), best_provider=best)


# ── Data endpoints ─────────────────────────────────────────────────────────────

@router.get("/traces")
def traces(limit: int = 200, db: Session = Depends(get_db)) -> Any:
    df = get_traces_df(db, limit=limit)
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/evals")
def evals(limit: int = 200, db: Session = Depends(get_db)) -> Any:
    df = get_evals_df(db, limit=limit)
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> Any:
    df = get_provider_summary(db)
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/latency")
def latency(db: Session = Depends(get_db)) -> Any:
    df = get_latency_df(db)
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/cost")
def cost(db: Session = Depends(get_db)) -> Any:
    df = get_cost_df(db)
    return df.to_dict(orient="records") if not df.empty else []


@router.get("/alerts")
def alerts(limit: int = 50, db: Session = Depends(get_db)) -> Any:
    df = get_alerts(db, limit=limit)
    return df.to_dict(orient="records") if not df.empty else []