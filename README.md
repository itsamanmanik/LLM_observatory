# 🔭 LLM Observatory

> **Real-time LLM Observability & Evaluation Dashboard**  
> Compare Groq (Llama 3.3), Gemini 1.5 Flash, and Mistral Small across hallucination, relevance, latency, and cost — in one unified dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)
![LiteLLM](https://img.shields.io/badge/LiteLLM-unified-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📸 Features

| Feature | Description |
|---|---|
| **Multi-Model Evaluation** | Run prompts against Groq, Gemini, Mistral in parallel |
| **Hallucination Scoring** | Automatic faithfulness & grounding detection |
| **Relevance Scoring** | Measures if response actually answers the question |
| **Toxicity Detection** | Local Detoxify model — no API cost |
| **Latency Tracking** | p50/p95/p99 latency per provider |
| **Cost Tracking** | USD cost per query and cumulative cost |
| **Alert System** | In-dashboard alerts when metrics breach thresholds |
| **Model Leaderboard** | Radar chart comparison across all metrics |
| **Batch Runner** | Pre-built test suite across 3 categories |
| **Export** | Download traces and scores as CSV |

---

## 🏗 Architecture

```
User Prompt
    │
    ▼
FastAPI Backend (Python)
    │
    ├── LiteLLM Wrapper ──► Groq / Gemini / Mistral  (parallel)
    │                              │
    │                         Response + Latency + Tokens
    │
    ├── Evaluator Engine
    │       ├── Relevance Score     (keyword overlap heuristic)
    │       ├── Hallucination Score (faithfulness proxy)
    │       ├── Faithfulness Score  (RAG: bigram overlap)
    │       └── Toxicity Score      (Detoxify, local)
    │
    ├── SQLite DB  (traces + eval_results tables)
    │
    └── REST API ──► Streamlit Dashboard
                          ├── Run Evaluation page
                          ├── Live Dashboard
                          ├── Model Leaderboard
                          ├── Alert Feed
                          └── Raw Trace Logs
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/llm-observatory.git
cd llm-observatory
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your API keys:

```env
GROQ_API_KEY=your_groq_key        # free at console.groq.com
GEMINI_API_KEY=your_gemini_key    # free at aistudio.google.com
MISTRAL_API_KEY=your_mistral_key  # free trial at console.mistral.ai
```

### 5. Create data folder

```bash
mkdir -p data
```

### 6. Start the FastAPI backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) — you should see the Swagger UI.

### 7. Start the Streamlit dashboard (new terminal)

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501) — your dashboard is live!

### 8. (Optional) Run batch evaluation to populate data

```bash
python scripts/batch_run.py
```

---

## 🔑 Getting Free API Keys

| Provider | URL | Notes |
|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com) | Completely free, very fast |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com) | Free tier: 1500 req/day |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) | Free trial credits on signup |

---

## 📁 Project Structure

```
llm-observatory/
├── backend/
│   ├── api/
│   │   └── routes.py          # All FastAPI endpoints
│   ├── core/
│   │   ├── config.py          # Settings (pydantic-settings)
│   │   ├── logger.py          # Loguru logger
│   │   └── tracer.py          # LiteLLM wrapper + TraceRecord
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── session.py         # DB session factory
│   │   └── crud.py            # All DB read/write operations
│   ├── evaluator/
│   │   └── scorer.py          # Hallucination, relevance, toxicity scoring
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response schemas
│   └── main.py                # FastAPI app entrypoint
├── dashboard/
│   └── app.py                 # Streamlit dashboard (5 pages)
├── data/
│   └── test_prompts.json      # Pre-built evaluation dataset
├── scripts/
│   └── batch_run.py           # Batch evaluation runner
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.dashboard
├── .github/
│   └── workflows/ci.yml       # GitHub Actions CI
├── .streamlit/
│   └── config.toml            # Streamlit dark theme config
├── render.yaml                # Render deployment config
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📊 Evaluation Metrics Explained

| Metric | Range | Description |
|---|---|---|
| **Hallucination Score** | 0–1 (higher = grounded) | Did model stick to facts/context? |
| **Relevance Score** | 0–1 (higher = relevant) | Did response actually answer the question? |
| **Faithfulness Score** | 0–1 (higher = faithful) | RAG only: did model use the provided context? |
| **Toxicity Score** | 0–1 (lower = cleaner) | Detoxify model prediction |
| **Overall Score** | 0–1 (higher = better) | Weighted composite of all above |

---

## 🌐 Deployment on Render (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render reads `render.yaml` and auto-creates both services
5. Add env variables (API keys) in the Render dashboard
6. Done — your app is live!

---

## 🛠 Tech Stack

- **Backend:** FastAPI + Uvicorn
- **LLM Routing:** LiteLLM (unified API for all providers)
- **Evaluation:** Custom scorer + Detoxify
- **Database:** SQLite (zero setup) → swap to PostgreSQL for prod
- **Dashboard:** Streamlit + Plotly
- **Deployment:** Render (free tier)

---

## 👤 Author

**Aman Manikpuri**  
AI/LLM Engineer | GenAI Developer  
[LinkedIn](https://linkedin.com/in/aman-manikpuri/) | [GitHub](https://github.com/itsamanmanik)

---

## 📄 License

MIT — free to use, modify, and distribute.
