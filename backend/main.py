"""
RasOI Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio
import os
import logging
import json
from datetime import datetime

from app.database import get_database
from app.routers import scan, pantry, recipes, substitutions
from app.routers.chammach import router as chammach_router, run_agent_loop
from app.guardrails import demo_preflight_check

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _expiry_check_loop():
    """Every hour, check if any pantry items are expiring and trigger Chammach."""
    while True:
        await asyncio.sleep(3600)
        try:
            from app.database import get_repository
            repo = await get_repository()
            all_items = await repo.get_all()
            # Check for any expiring/expired items
            from datetime import date
            expiring = [
                i for i in all_items
                if i.get("expiration_date") and
                   (date.fromisoformat(i["expiration_date"]) - date.today()).days <= 2
            ]
            if expiring:
                logger.info("[expiry_loop] %d expiring item(s) — triggering Chammach", len(expiring))
                await run_agent_loop("expiry_threshold_crossed")
            # PRD §8b.4 — pantry drops below 5 items triggers low_stock alert
            elif len(all_items) < 5 and len(all_items) > 0:
                logger.info("[expiry_loop] Pantry below 5 items (%d) — triggering low_stock", len(all_items))
                await run_agent_loop("pantry_low_stock")
        except Exception as exc:
            logger.warning("[expiry_loop] Error during check: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite DB on startup; start hourly expiry checker."""
    logger.info("Initialising RasOI database…")
    await get_database()
    logger.info("Database ready.")
    expiry_task = asyncio.create_task(_expiry_check_loop())
    yield
    expiry_task.cancel()


app = FastAPI(
    title="RasOI Kitchen Intelligence API",
    description="AI-powered kitchen intelligence — reducing food waste one meal at a time.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,https://rasoi.vercel.app",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error Handlers ───────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422).
    
    Returns detailed validation error information for client debugging.
    """
    logger.warning(
        "[error_handler] Validation error for %s %s: %s",
        request.method,
        request.url.path,
        str(exc.errors())
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "code": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected server errors (500).
    
    Logs the full error traceback and returns a generic error response.
    """
    logger.error(
        "[error_handler] Unhandled exception for %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle ValueError as 400 Bad Request.
    
    Indicates client provided invalid data that doesn't match validation.
    """
    logger.warning(
        "[error_handler] Value error for %s %s: %s",
        request.method,
        request.url.path,
        str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "code": "bad_request",
            "message": str(exc) or "Invalid request parameters",
        },
    )

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(scan.router)
app.include_router(pantry.router)
app.include_router(recipes.router)
app.include_router(substitutions.router)
app.include_router(chammach_router)


# ── Base routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "app": "RasOI",
        "version": "1.0.0",
        "tagline": "Powered by Organic Intelligence",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    spoonacular_key = bool(os.getenv("SPOONACULAR_API_KEY"))
    edamam_configured = bool(os.getenv("EDAMAM_APP_ID") and os.getenv("EDAMAM_APP_KEY"))
    return {
        "status": "healthy",
        "services": {
            "database": "up",
            "claudeVision": "up" if anthropic_key else "missing_key",
            "claudeText": "up" if anthropic_key else "missing_key",
            "spoonacular": "configured" if spoonacular_key else "not_configured",
            "edamam": "configured" if edamam_configured else "not_configured",
        },
    }


@app.get("/api/safety/demo-check")
async def demo_safety_check():
    """
    PRD §14.4 — Demo Day Safety pre-flight check.
    Run this before going on stage to verify all 5 failure scenarios are covered.

    Returns overall: 'ok' | 'warn' | 'fail' and per-check details.
    """
    return await demo_preflight_check()


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
