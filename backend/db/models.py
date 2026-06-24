"""
SQLAlchemy ORM models for persisting traces and evaluation scores.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Trace(Base):
    """Every LLM call is recorded as a Trace."""
    __tablename__ = "traces"

    id             = Column(Integer, primary_key=True, index=True)
    trace_id       = Column(String(64), unique=True, index=True, nullable=False)
    model          = Column(String(64), nullable=False)        # e.g. groq/llama-3.3-70b-versatile
    provider       = Column(String(32), nullable=False)        # groq | gemini | mistral
    prompt         = Column(Text, nullable=False)
    response       = Column(Text, nullable=False)
    context        = Column(Text, nullable=True)               # RAG context if any
    latency_ms     = Column(Float, nullable=False)
    prompt_tokens  = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens   = Column(Integer, nullable=True)
    cost_usd       = Column(Float, nullable=True)
    category       = Column(String(32), nullable=True)         # factual | rag | instruction
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)


class EvalResult(Base):
    """Evaluation scores tied to a Trace."""
    __tablename__ = "eval_results"

    id                  = Column(Integer, primary_key=True, index=True)
    trace_id            = Column(String(64), index=True, nullable=False)
    model               = Column(String(64), nullable=False)
    provider            = Column(String(32), nullable=False)
    hallucination_score = Column(Float, nullable=True)   # 0=bad 1=good (faithfulness proxy)
    relevance_score     = Column(Float, nullable=True)   # 0-1
    faithfulness_score  = Column(Float, nullable=True)   # 0-1 (RAG only)
    toxicity_score      = Column(Float, nullable=True)   # 0=clean 1=toxic
    overall_score       = Column(Float, nullable=True)   # weighted composite
    is_hallucinated     = Column(Boolean, default=False)
    is_toxic            = Column(Boolean, default=False)
    alert_triggered     = Column(Boolean, default=False)
    alert_reason        = Column(Text, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
