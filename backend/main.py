"""
LLM Observatory — FastAPI application entrypoint.

FastAPI >= 0.115 deprecates @app.on_event("startup").
We use the modern `lifespan` context manager instead.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.db.session import init_db
from backend.core.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup → yield → shutdown."""
    init_db()
    log.info("✅ LLM Observatory started — DB initialised.")
    yield
    log.info("🛑 LLM Observatory shutting down.")


app = FastAPI(
    title="LLM Observatory",
    description="Real-time LLM Observability & Evaluation Dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "LLM Observatory API is running.",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
