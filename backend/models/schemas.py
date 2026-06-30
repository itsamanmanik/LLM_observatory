"""Pydantic request/response schemas for the FastAPI layer."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    prompt:   str = Field(..., min_length=1, max_length=4000, description="User prompt to evaluate")
    context:  Optional[str] = Field(None, max_length=8000, description="RAG context (optional)")
    category: Literal["factual", "rag", "instruction"] = "factual"
    providers: list[Literal["groq", "cerebras", "mistral"]] = ["groq", "cerebras", "mistral"]


class RunResult(BaseModel):
    trace_id:           str
    provider:           str
    model:              str
    response:           str
    latency_ms:         float
    total_tokens:       int
    cost_usd:           float
    hallucination_score: float
    relevance_score:    float
    faithfulness_score: Optional[float]
    toxicity_score:     float
    overall_score:      float
    is_hallucinated:    bool
    alert_triggered:    bool
    alert_reason:       Optional[str]
    error:              Optional[str] = None


class RunResponse(BaseModel):
    results: list[RunResult]
    best_provider: Optional[str]


class HealthResponse(BaseModel):
    status: str
    db:     str
    models: list[str]