"""
CRUD helpers — all DB reads/writes go through here.
Compatible with pandas 3.x (stricter groupby, copy-on-write enabled by default).
"""

import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models import EvalResult, Trace
from backend.core.tracer import TraceRecord
from backend.evaluator.scorer import EvalScore


# ── Write ─────────────────────────────────────────────────────────────────────

def save_trace(db: Session, trace: TraceRecord) -> Trace:
    row = Trace(
        trace_id=trace.trace_id,
        model=trace.model,
        provider=trace.provider,
        prompt=trace.prompt,
        response=trace.response,
        context=trace.context,
        latency_ms=trace.latency_ms,
        prompt_tokens=trace.prompt_tokens,
        completion_tokens=trace.completion_tokens,
        total_tokens=trace.total_tokens,
        cost_usd=trace.cost_usd,
        category=trace.category,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_eval(db: Session, score: EvalScore) -> EvalResult:
    row = EvalResult(
        trace_id=score.trace_id,
        model=score.model,
        provider=score.provider,
        hallucination_score=score.hallucination_score,
        relevance_score=score.relevance_score,
        faithfulness_score=score.faithfulness_score,
        toxicity_score=score.toxicity_score,
        overall_score=score.overall_score,
        is_hallucinated=score.is_hallucinated,
        is_toxic=score.is_toxic,
        alert_triggered=score.alert_triggered,
        alert_reason=score.alert_reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Read ──────────────────────────────────────────────────────────────────────

def _rows_to_df(rows: list) -> pd.DataFrame:
    """Convert SQLAlchemy ORM rows to DataFrame safely."""
    if not rows:
        return pd.DataFrame()
    records = []
    for r in rows:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        records.append(d)
    return pd.DataFrame(records)


def get_traces_df(db: Session, limit: int = 500) -> pd.DataFrame:
    rows = db.query(Trace).order_by(Trace.created_at.desc()).limit(limit).all()
    return _rows_to_df(rows)


def get_evals_df(db: Session, limit: int = 500) -> pd.DataFrame:
    rows = db.query(EvalResult).order_by(EvalResult.created_at.desc()).limit(limit).all()
    return _rows_to_df(rows)


def get_alerts(db: Session, limit: int = 50) -> pd.DataFrame:
    rows = (
        db.query(EvalResult)
        .filter(EvalResult.alert_triggered == True)  # noqa: E712
        .order_by(EvalResult.created_at.desc())
        .limit(limit)
        .all()
    )
    return _rows_to_df(rows)


def get_provider_summary(db: Session) -> pd.DataFrame:
    """Aggregate avg scores per provider for leaderboard."""
    evals = get_evals_df(db, limit=1000)
    if evals.empty:
        return pd.DataFrame()
    summary = (
        evals.groupby("provider", as_index=False)
        .agg(
            avg_overall=("overall_score", "mean"),
            avg_hallucination=("hallucination_score", "mean"),
            avg_relevance=("relevance_score", "mean"),
            avg_toxicity=("toxicity_score", "mean"),
            total_runs=("trace_id", "count"),
            alerts=("alert_triggered", "sum"),
        )
        .sort_values("avg_overall", ascending=False)
        .reset_index(drop=True)
    )
    return summary


def get_latency_df(db: Session) -> pd.DataFrame:
    traces = get_traces_df(db)
    if traces.empty:
        return pd.DataFrame()
    latency = (
        traces.groupby("provider", as_index=False)["latency_ms"]
        .describe(percentiles=[0.5, 0.95, 0.99])
    )
    return latency


def get_cost_df(db: Session) -> pd.DataFrame:
    traces = get_traces_df(db)
    if traces.empty:
        return pd.DataFrame()
    cost = (
        traces.groupby("provider", as_index=False)
        .agg(
            total_cost=("cost_usd", "sum"),
            avg_cost=("cost_usd", "mean"),
            runs=("trace_id", "count"),
        )
    )
    return cost
