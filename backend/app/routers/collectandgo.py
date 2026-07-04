"""
Collect&Go router — GET /api/collectandgo/suggest

Missing-ingredient product suggestions from Colruyt Group's Collect&Go
assortment (synthetic catalog until the real API is wired — see
app/services/collectandgo/collect_and_go.py). Decision order:
  1. Explicit onboarding preference (stated pantry budget)
  2. Fallback: purchase-history brand-tier pattern (classify_customer)
"""

from fastapi import APIRouter, HTTPException, Query

from app.database import get_preferences_repository, DEMO_USER_ID
from app.services.collectandgo.product_suggestion_service import (
    suggest_for_missing_ingredient,
    DEFAULT_CUSTOMER_ID,
)
from app import guardrails

router = APIRouter(prefix="/api/collectandgo", tags=["collectandgo"])


@router.get("/suggest")
async def suggest(
    ingredient: str = Query(..., description="Missing ingredient name, e.g. 'melk'"),
    customerId: str = Query(DEFAULT_CUSTOMER_ID, description="Synthetic Collect&Go customer id (CUST001-CUST010)"),
):
    """Suggest Collect&Go products for a missing ingredient, tiered by brand."""
    try:
        ingredient = guardrails.sanitise_text_field(ingredient, max_len=100, field_name="ingredient")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    prefs_repo = await get_preferences_repository()
    prefs_row = await prefs_repo.get(DEMO_USER_ID)
    preferences = None
    if prefs_row:
        preferences = {
            "onboardingCompleted": bool(prefs_row.get("onboarding_completed")),
            "budgetAmount": prefs_row.get("budget_amount"),
            "budgetPeriod": prefs_row.get("budget_period"),
            "familySize": prefs_row.get("family_size"),
        }

    try:
        result = suggest_for_missing_ingredient(ingredient, preferences, customerId)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Collect&Go suggestion failed: {e}")

    return result
