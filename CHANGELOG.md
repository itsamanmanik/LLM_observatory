# Changelog

## [1.1.0] — 2026-06-30

### Changed
- Replaced Gemini provider with **Cerebras (GPT-OSS 120B)** — Gemini's free-tier
  quota was unreliable (returned `limit: 0` even on fresh API keys/projects);
  Cerebras offers a stable, generous free tier with no card required
- Updated `tracer.py`, `config.py`, `schemas.py`, `dashboard/app.py`, and
  `scripts/batch_run.py` to reflect the new provider across the full stack

### Fixed
- **Thread-safe DB sessions** — `/run` endpoint previously shared a single
  SQLAlchemy session across parallel LLM call threads, causing
  `IllegalStateChangeError` on concurrent commits. Each thread now opens
  and closes its own session.
- **Markdown rendering** — model responses containing `**bold**`, headers,
  or `===` underlines were printing as raw symbols inside the HTML preview
  card. Added a `strip_markdown()` helper for previews and switched the
  "Full Response" expander to `st.markdown()` for proper rendering.
- **Provider/schema mismatch (422 error)** — `RunRequest.providers` Literal
  type still referenced the old `gemini` value after the Cerebras migration,
  causing FastAPI to reject valid requests. Synced across all files.
- **Stale Cerebras model ID (404 error)** — `llama-3.3-70b` was deprecated
  by Cerebras in Feb 2026; switched to `gpt-oss-120b`, their current
  fastest and free-tier-friendly model.
- Removed legacy raw `requests`-based Gemini `:generate` endpoint call
  (deprecated PaLM-era API) in favour of the unified OpenAI SDK path used
  for all three providers.

---

## [1.0.0] — 2026-06-24

### Initial Release

**Core Features**
- Multi-model parallel evaluation: Groq (Llama 3.3 70B), Gemini 2.0 Flash, Mistral Small
- Automatic evaluation scoring: hallucination, relevance, faithfulness, toxicity
- Web grounding layer: auto-fetches Wikipedia context for real-time queries
- Per-call tracing: latency, token usage, USD cost
- In-dashboard alert system for quality and latency threshold breaches
- 5-page Streamlit dashboard: Run Evaluation, Dashboard, Leaderboard, Alerts, Raw Traces
- Batch evaluation runner with pre-built factual/RAG/instruction test suite
- CSV export for traces and evaluation scores
- Docker + Render deployment support

**Technical**
- FastAPI backend with async parallel LLM calls via ThreadPoolExecutor
- OpenAI SDK used for all providers (unified API, no litellm dependency)
- Python 3.14 compatible
- SQLite database (zero setup, swappable to PostgreSQL)