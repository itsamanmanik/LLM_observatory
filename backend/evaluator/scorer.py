"""
Evaluation Engine — scores every TraceRecord on:
  1. Relevance Score     — is the answer on-topic?
  2. Hallucination Score — did the model stick to the context / truth?
  3. Faithfulness Score  — RAG-only: did it answer from provided context?
  4. Toxicity Score      — is the response harmful?
  5. Overall Score       — weighted composite

Uses lightweight heuristics + Detoxify (local model, no API cost).
For RAG traces, also runs a simple faithfulness check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from backend.core.config import settings
from backend.core.logger import log
from backend.core.tracer import TraceRecord

# Lazy-load detoxify to avoid slow startup when not needed
_detoxify_model = None


def _get_detoxify():
    global _detoxify_model
    if _detoxify_model is None:
        try:
            from detoxify import Detoxify
            _detoxify_model = Detoxify("original")
            log.info("Detoxify model loaded.")
        except Exception as e:
            log.warning(f"Detoxify unavailable: {e}. Toxicity will be skipped.")
    return _detoxify_model


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class EvalScore:
    trace_id:           str
    model:              str
    provider:           str
    hallucination_score: float        # 0=likely hallucinated, 1=grounded
    relevance_score:    float         # 0-1
    faithfulness_score: Optional[float]  # None if no context
    toxicity_score:     float         # 0=clean, 1=very toxic
    overall_score:      float         # weighted composite
    is_hallucinated:    bool
    is_toxic:           bool
    alert_triggered:    bool
    alert_reason:       Optional[str]


# ── Main scorer ──────────────────────────────────────────────────────────────

def evaluate(trace: TraceRecord) -> EvalScore:
    """Score a completed TraceRecord and return an EvalScore."""
    log.info(f"Evaluating trace {trace.trace_id[:8]}… [{trace.provider}]")

    if trace.error or not trace.response.strip():
        return _error_score(trace)

    relevance    = _score_relevance(trace.prompt, trace.response)
    hallucination= _score_hallucination(trace.prompt, trace.response, trace.context)
    faithfulness = _score_faithfulness(trace.response, trace.context) if trace.context else None
    toxicity     = _score_toxicity(trace.response)

    overall = _composite(relevance, hallucination, faithfulness, toxicity)

    is_hallucinated = hallucination < settings.HALLUCINATION_ALERT_THRESHOLD
    is_toxic        = toxicity > 0.6

    alert_triggered, alert_reason = _check_alerts(
        hallucination, trace.latency_ms, is_toxic
    )

    score = EvalScore(
        trace_id=trace.trace_id,
        model=trace.model,
        provider=trace.provider,
        hallucination_score=round(hallucination, 4),
        relevance_score=round(relevance, 4),
        faithfulness_score=round(faithfulness, 4) if faithfulness is not None else None,
        toxicity_score=round(toxicity, 4),
        overall_score=round(overall, 4),
        is_hallucinated=is_hallucinated,
        is_toxic=is_toxic,
        alert_triggered=alert_triggered,
        alert_reason=alert_reason,
    )

    log.info(
        f"Scores → relevance={score.relevance_score} | "
        f"hallucination={score.hallucination_score} | "
        f"toxicity={score.toxicity_score} | overall={score.overall_score}"
    )
    return score


# ── Individual scorers ───────────────────────────────────────────────────────

def _score_relevance(prompt: str, response: str) -> float:
    """
    Heuristic relevance: keyword overlap between prompt and response.
    0 = no overlap (irrelevant), 1 = high overlap (relevant).
    """
    prompt_words   = set(_tokenise(prompt))
    response_words = set(_tokenise(response))
    if not prompt_words:
        return 0.5
    overlap = prompt_words & response_words
    score   = min(len(overlap) / max(len(prompt_words) * 0.3, 1), 1.0)
    return float(score)


def _score_hallucination(prompt: str, response: str, context: Optional[str]) -> float:
    """
    Hallucination proxy:
    - With context  → faithfulness (fraction of response sentences grounded in context)
    - Without context → length + hedging heuristics (longer coherent answers = more trustworthy)

    Returns 0 (likely hallucinated) → 1 (likely grounded).
    """
    if context:
        return _score_faithfulness(response, context)

    # Heuristic: very short responses or uncertainty phrases lower trust
    uncertainty_phrases = [
        "i'm not sure", "i don't know", "i cannot", "i'm unable",
        "as an ai", "i apologize", "i do not have",
    ]
    lower = response.lower()
    penalty = sum(0.1 for ph in uncertainty_phrases if ph in lower)

    length_bonus = min(len(response.split()) / 50, 0.3)
    base = 0.7
    return max(0.0, min(1.0, base + length_bonus - penalty))


def _score_faithfulness(response: str, context: str) -> float:
    """
    Sentence-level faithfulness: what fraction of response sentences
    contain at least one multi-word phrase from the context?
    """
    if not context:
        return 1.0

    context_lower   = context.lower()
    resp_sentences  = [s.strip() for s in re.split(r'[.!?]', response) if len(s.strip()) > 10]

    if not resp_sentences:
        return 0.5

    grounded = 0
    for sent in resp_sentences:
        words  = _tokenise(sent)
        bigrams= [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        if any(bg in context_lower for bg in bigrams):
            grounded += 1

    return grounded / len(resp_sentences)


def _score_toxicity(response: str) -> float:
    """
    Run Detoxify. Returns 0 (clean) → 1 (toxic).
    Falls back to 0.0 if model unavailable.
    """
    model = _get_detoxify()
    if model is None:
        return 0.0
    try:
        results = model.predict(response)
        return float(results.get("toxicity", 0.0))
    except Exception as e:
        log.warning(f"Toxicity scoring failed: {e}")
        return 0.0


def _composite(
    relevance:    float,
    hallucination:float,
    faithfulness: Optional[float],
    toxicity:     float,
) -> float:
    """Weighted composite score (higher = better)."""
    weights = {"hallucination": 0.40, "relevance": 0.35, "faithfulness": 0.15, "toxicity": 0.10}

    faith_val = faithfulness if faithfulness is not None else hallucination
    score = (
        weights["hallucination"] * hallucination +
        weights["relevance"]     * relevance      +
        weights["faithfulness"]  * faith_val       +
        weights["toxicity"]      * (1 - toxicity)  # invert: lower toxicity = better
    )
    return min(max(score, 0.0), 1.0)


def _check_alerts(
    hallucination: float,
    latency_ms:    float,
    is_toxic:      bool,
) -> tuple[bool, Optional[str]]:
    reasons = []
    if hallucination < settings.HALLUCINATION_ALERT_THRESHOLD:
        reasons.append(f"Hallucination score {hallucination:.2f} below threshold {settings.HALLUCINATION_ALERT_THRESHOLD}")
    if latency_ms > settings.LATENCY_ALERT_THRESHOLD_MS:
        reasons.append(f"Latency {latency_ms:.0f}ms exceeds {settings.LATENCY_ALERT_THRESHOLD_MS:.0f}ms threshold")
    if is_toxic:
        reasons.append("Response flagged as toxic")

    if reasons:
        return True, " | ".join(reasons)
    return False, None


def _error_score(trace: TraceRecord) -> EvalScore:
    return EvalScore(
        trace_id=trace.trace_id,
        model=trace.model,
        provider=trace.provider,
        hallucination_score=0.0,
        relevance_score=0.0,
        faithfulness_score=None,
        toxicity_score=0.0,
        overall_score=0.0,
        is_hallucinated=True,
        is_toxic=False,
        alert_triggered=True,
        alert_reason=f"LLM call failed: {trace.error}",
    )


def _tokenise(text: str) -> list[str]:
    return re.findall(r'\b[a-z]{3,}\b', text.lower())
