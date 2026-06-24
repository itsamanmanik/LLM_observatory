"""
LLM Tracer — calls Groq, Gemini, Mistral via openai-compatible SDK.

"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI, APIConnectionError, APIStatusError

from backend.core.config import settings
from backend.core.grounding import fetch_grounding_context, needs_grounding
from backend.core.logger import log

# ── Provider registry ─────────────────────────────────────────────────────────

MODELS = {
    "groq": {
        "model_id":           "llama-3.3-70b-versatile",
        "display":            "Llama 3.3 70B (Groq)",
        "provider":           "groq",
        "base_url":           "https://api.groq.com/openai/v1",
        "api_key_attr":       "GROQ_API_KEY",
        "cost_input_per_1m":  0.0,
        "cost_output_per_1m": 0.0,
    },
    "gemini": {
        # gemini-1.5-flash is 404 on v1beta openai endpoint — use 2.0-flash
        "model_id":           "gemini-2.0-flash",
        "display":            "Gemini 2.0 Flash",
        "provider":           "gemini",
        "base_url":           "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_attr":       "GEMINI_API_KEY",
        "cost_input_per_1m":  0.10,
        "cost_output_per_1m": 0.40,
    },
    "mistral": {
        "model_id":           "mistral-small-latest",
        "display":            "Mistral Small",
        "provider":           "mistral",
        "base_url":           "https://api.mistral.ai/v1",
        "api_key_attr":       "MISTRAL_API_KEY",
        "cost_input_per_1m":  0.10,
        "cost_output_per_1m": 0.30,
    },
}

# ── TraceRecord ───────────────────────────────────────────────────────────────

@dataclass
class TraceRecord:
    trace_id:           str
    model:              str
    provider:           str
    prompt:             str
    response:           str
    context:            Optional[str]
    latency_ms:         float
    prompt_tokens:      int
    completion_tokens:  int
    total_tokens:       int
    cost_usd:           float
    category:           str
    error:              Optional[str] = field(default=None)


# ── Main entry ────────────────────────────────────────────────────────────────

def call_llm(
    provider: str,
    prompt:   str,
    context:  Optional[str] = None,
    category: str = "factual",
    system:   Optional[str] = None,
) -> TraceRecord:
    if provider not in MODELS:
        raise ValueError(f"Unknown provider '{provider}'. Choose: {list(MODELS.keys())}")

    cfg      = MODELS[provider]
    trace_id = str(uuid.uuid4())

    # ── Web grounding for factual queries ─────────────────────────────────────
    # If no RAG context was manually provided and the question looks like it
    # needs real-time data, auto-fetch Wikipedia context.
    effective_context = context
    if context is None and category == "factual" and needs_grounding(prompt):
        log.info(f"Real-time query detected — fetching web context")
        web_ctx = fetch_grounding_context(prompt)
        if web_ctx:
            effective_context = web_ctx

    messages = _build_messages(prompt, effective_context, system)

    # ── API key check ─────────────────────────────────────────────────────────
    api_key = getattr(settings, cfg["api_key_attr"], "").strip()
    if not api_key:
        err = f"Missing API key — set {cfg['api_key_attr']} in your .env file"
        log.error(err)
        return _error_trace(trace_id, cfg, prompt, effective_context, category, err)

    log.info(f"Calling {cfg['display']} | category={category}")
    start = time.perf_counter()

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=cfg["base_url"],
            timeout=30.0,
            max_retries=1,
        )

        resp = client.chat.completions.create(
            model=cfg["model_id"],
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

        latency_ms        = (time.perf_counter() - start) * 1000
        response_text     = resp.choices[0].message.content or ""
        prompt_tokens     = resp.usage.prompt_tokens     if resp.usage else 0
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0
        total_tokens      = resp.usage.total_tokens      if resp.usage else 0
        cost_usd          = _estimate_cost(cfg, prompt_tokens, completion_tokens)

        log.success(
            f"{cfg['display']} → {latency_ms:.0f}ms | "
            f"{total_tokens} tokens | ${cost_usd:.6f}"
        )

        return TraceRecord(
            trace_id=trace_id,
            model=cfg["model_id"],
            provider=provider,
            prompt=prompt,
            response=response_text,
            context=effective_context,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            category=category,
        )

    except APIStatusError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        err = f"API error {exc.status_code}: {exc.message}"
        log.error(f"{cfg['display']} — {err}")
        return _error_trace(trace_id, cfg, prompt, effective_context, category, err, latency_ms)

    except APIConnectionError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        err = f"Connection error — check internet / API key: {exc}"
        log.error(f"{cfg['display']} — {err}")
        return _error_trace(trace_id, cfg, prompt, effective_context, category, err, latency_ms)

    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        err = str(exc)
        log.error(f"{cfg['display']} failed: {err}")
        return _error_trace(trace_id, cfg, prompt, effective_context, category, err, latency_ms)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_messages(
    prompt:  str,
    context: Optional[str],
    system:  Optional[str],
) -> list[dict]:
    messages:  list[dict] = []
    sys_parts: list[str]  = []

    if system:
        sys_parts.append(system)
    if context:
        sys_parts.append(
            f"Use the following up-to-date context to answer accurately:\n\n{context}"
        )

    if sys_parts:
        messages.append({"role": "system", "content": "\n\n".join(sys_parts)})

    messages.append({"role": "user", "content": prompt})
    return messages


def _estimate_cost(cfg: dict, prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        (prompt_tokens     / 1_000_000) * cfg["cost_input_per_1m"] +
        (completion_tokens / 1_000_000) * cfg["cost_output_per_1m"],
        8,
    )


def _error_trace(
    trace_id:   str,
    cfg:        dict,
    prompt:     str,
    context:    Optional[str],
    category:   str,
    error:      str,
    latency_ms: float = 0.0,
) -> TraceRecord:
    return TraceRecord(
        trace_id=trace_id,
        model=cfg["model_id"],
        provider=cfg["provider"],
        prompt=prompt,
        response="",
        context=context,
        latency_ms=latency_ms,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
        category=category,
        error=error,
    )