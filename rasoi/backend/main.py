"""
RasOI Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import logging

from app.database import get_database
from app.routers import scan, pantry, recipes, substitutions

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite DB on startup."""
    logger.info("Initialising RasOI database…")
    await get_database()
    logger.info("Database ready.")
    yield


app = FastAPI(
    title="RasOI Kitchen Intelligence API",
    description="AI-powered kitchen intelligence — reducing food waste one meal at a time.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(scan.router)
app.include_router(pantry.router)
app.include_router(recipes.router)
app.include_router(substitutions.router)


# ── Base routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "RasOI Kitchen Intelligence API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {
        "status": "healthy",
        "services": {
            "database": "up",
            "claudeVision": "up" if anthropic_key else "missing_key",
            "claudeText": "up" if anthropic_key else "missing_key",
        },
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
