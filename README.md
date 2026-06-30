# 🔭 LLM Observatory

> **Real-time LLM Observability & Evaluation Dashboard**  
> Compare **Groq (Llama 3.3 70B)**, **Cerebras (GPT-OSS 120B)**, and **Mistral Small** across hallucination, relevance, latency, and cost — side by side, in real time.

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.138-green?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red?logo=streamlit)
![OpenAI SDK](https://img.shields.io/badge/OpenAI_SDK-1.82-black?logo=openai)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📸 Demo

> Dashboard running locally with all 3 models evaluated side by side

| Run Evaluation | Model Leaderboard |
|---|---|
| Send any prompt → get scores from 3 LLMs instantly | Radar chart + ranked cards across all metrics |

---

## 🧠 The Problem This Solves

Most teams building with LLMs are **flying blind**. They deploy a model and have no idea if it's:
- Hallucinating 30% of the time
- Degrading in quality week over week  
- Costing 3x more per query than it should

**LLM Observatory gives you full visibility** — every call traced, every output scored, every anomaly alerted.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Multi-Model Parallel Evaluation** | Send one prompt → all 3 LLMs respond simultaneously |
| **Hallucination Scoring** | Automatic faithfulness & grounding detection per response |
| **Relevance Scoring** | Measures if the response actually answers the question |
| **Faithfulness Score** | RAG-only: did the model stick to provided context? |
| **Toxicity Detection** | Local heuristic check — no extra API needed |
| **Web Grounding** | Auto-fetches Wikipedia context for real-time/factual queries |
| **Latency Tracking** | Per-provider response time on every call |
| **Cost Tracking** | USD cost per query + cumulative total |
| **Alert System** | In-dashboard alerts when metrics breach thresholds |
| **Model Leaderboard** | Radar chart + ranked cards across all metrics |
| **Batch Runner** | Pre-built test suite: factual, RAG, instruction categories |
| **CSV Export** | Download all traces and scores for offline analysis |

---

## 🏗 Architecture

```
User Prompt
    │
    ▼
FastAPI Backend  ──────────────────────────────────────────
    │                                                      │
    ├── OpenAI SDK → Groq (Llama 3.3 70B)                 │
    ├── OpenAI SDK → Cerebras (GPT-OSS 120B)   (parallel)  │
    └── OpenAI SDK → Mistral Small                        │
              │                                            │
              ▼                                            │
    Web Grounding Layer                                    │
    (Wikipedia REST API — auto-injects                     │
     real-time context for factual queries)                │
              │                                            │
              ▼                                            │
    Evaluation Engine                                      │
    ├── Relevance Score  (keyword overlap)                 │
    ├── Hallucination Score (faithfulness proxy)           │
    ├── Faithfulness Score (RAG: bigram overlap)           │
    └── Toxicity Score  (local heuristic)                  │
              │                                            │
              ▼                                            │
    SQLite DB  (traces + eval_results)  ───────────────────
              │
              ▼
    Streamlit Dashboard (5 pages)
    ├── 🚀 Run Evaluation
    ├── 📊 Live Dashboard
    ├── ⚖️  Model Leaderboard
    ├── 🚨 Alert Feed
    └── 📋 Raw Trace Logs
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/itsamanmanik/LLL_Observatory.git
cd LLL_Observatory
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your free API keys:

```env
GROQ_API_KEY=your_groq_key
CEREBRAS_API_KEY=your_cerebras_key
MISTRAL_API_KEY=your_mistral_key
```

### 5. Start the backend

```bash
mkdir -p data
uvicorn backend.main:app --reload --port 8000
```

Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Start the dashboard (new terminal)

```bash
streamlit run dashboard/app.py
```

Dashboard → [http://localhost:8501](http://localhost:8501)

### 7. Populate with test data (optional)

```bash
python scripts/batch_run.py
```

---

## 🔑 Getting Free API Keys

| Provider | Link | Free Tier |
|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com) | Unlimited (rate limited) |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) | Generous free tier, no card needed |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) | Free trial credits |

> All three providers expose an **OpenAI-compatible REST API** — this project uses one unified SDK for all of them.

---

## 📁 Project Structure

```
LLL_Observatory/
├── backend/
│   ├── api/
│   │   └── routes.py          # All FastAPI endpoints
│   ├── core/
│   │   ├── config.py          # Settings via pydantic-settings
│   │   ├── logger.py          # Loguru logger
│   │   ├── tracer.py          # OpenAI SDK wrapper + TraceRecord
│   │   └── grounding.py       # Wikipedia-based real-time grounding
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM (Trace, EvalResult)
│   │   ├── session.py         # DB session factory
│   │   └── crud.py            # All DB read/write operations
│   ├── evaluator/
│   │   └── scorer.py          # Hallucination, relevance, toxicity
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response schemas
│   └── main.py                # FastAPI app + lifespan
├── dashboard/
│   └── app.py                 # Streamlit UI (5 pages)
├── data/
│   └── test_prompts.json      # Pre-built eval dataset (factual/RAG/instruction)
├── scripts/
│   └── batch_run.py           # Batch evaluation runner
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.dashboard
├── .github/
│   └── workflows/ci.yml       # GitHub Actions CI
├── .streamlit/
│   └── config.toml            # Dark theme config
├── render.yaml                # One-click Render deployment
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📊 Evaluation Metrics

| Metric | Range | What it measures |
|---|---|---|
| **Hallucination Score** | 0–1 ↑ | Did the model stick to facts / provided context? |
| **Relevance Score** | 0–1 ↑ | Did the response actually answer the question? |
| **Faithfulness Score** | 0–1 ↑ | RAG: did the model use only the provided context? |
| **Toxicity Score** | 0–1 ↓ | Lower = cleaner output |
| **Overall Score** | 0–1 ↑ | Weighted composite of all above |

---

## 🌐 Web Grounding

One of the unique features of this project is **automatic web grounding** for real-time queries.

When you ask something like _"How many goals has Ronaldo scored in the World Cup?"_, the system:
1. Detects it's a real-time/factual query (keywords: goals, current, 2026, score, etc.)
2. Fetches a Wikipedia summary for the topic **before** calling the LLMs
3. Injects it as system context so all 3 models answer from **current facts**, not stale training data

Uses **Wikipedia REST API** — completely free, no API key needed.

---

## 🌐 Deploy on Render (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically
4. Add your 3 API keys in the Render environment settings
5. Deploy — live in ~3 minutes

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| LLM Routing | OpenAI SDK (Groq / Cerebras / Mistral) |
| Evaluation | Custom scorer (heuristic + rule-based) |
| Web Grounding | Wikipedia REST API |
| Database | SQLite via SQLAlchemy 2.0 |
| Dashboard | Streamlit + Plotly |
| Deployment | Render (free tier) |
| Python | 3.14 compatible |

---

## 🗺 Roadmap

- [ ] Add OpenAI GPT-4o as optional provider
- [ ] Persistent PostgreSQL support for production deployments
- [ ] LangSmith integration for deeper tracing
- [ ] Ragas-based evaluation for structured RAG pipelines
- [ ] User authentication for multi-user deployments
- [ ] Export evaluation reports as PDF

---

## 👤 Author

**Aman Manikpuri**  
AI/LLM Engineer · GenAI Developer  
📧 amanmanikpuri04@gmail.com  
🔗 [LinkedIn](https://linkedin.com/in/aman-manikpuri) · [GitHub](https://github.com/itsamanmanik)

---

## 📄 License

MIT — free to use, modify, and distribute.