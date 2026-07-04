"""
Preferences router — GET/PUT /api/preferences

Onboarding data for RasOI's single demo user (Rasoi Raja): cuisine picks,
diet type, height/weight (BMI computed server-side), family size, and a
weekly or monthly pantry budget.

Endpoints:
  GET /api/preferences — current preferences (onboardingCompleted: false if never saved)
  PUT /api/preferences — upsert preferences, returns the saved profile with computed BMI
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import json

from app.database import get_preferences_repository, PreferencesRepository, DEMO_USER_ID
from app.services.brand_preferences_service import rebuild_brand_preferences

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

DietType = Literal["vegetarian", "non_vegetarian", "eggetarian", "vegan"]
BudgetPeriod = Literal["weekly", "monthly"]


class PreferencesUpdateRequest(BaseModel):
    cuisines: List[str] = Field(default_factory=list)
    dietType: DietType = "vegetarian"
    heightCm: float = Field(gt=0, le=300)
    weightKg: float = Field(gt=0, le=400)
    familySize: int = Field(ge=1, le=20)
    budgetAmount: float = Field(ge=0)
    budgetPeriod: BudgetPeriod = "monthly"


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


def _to_response(row: Optional[dict]) -> dict:
    if not row:
        return {
            "cuisines": [],
            "dietType": "vegetarian",
            "heightCm": None,
            "weightKg": None,
            "bmi": None,
            "bmiCategory": None,
            "familySize": 1,
            "budgetAmount": None,
            "budgetPeriod": "monthly",
            "onboardingCompleted": False,
        }

    height_cm = row.get("height_cm")
    weight_kg = row.get("weight_kg")
    bmi = None
    if height_cm and weight_kg:
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 1)

    try:
        cuisines = json.loads(row.get("cuisines") or "[]")
    except (json.JSONDecodeError, TypeError):
        cuisines = []

    return {
        "cuisines": cuisines,
        "dietType": row.get("diet_type"),
        "heightCm": height_cm,
        "weightKg": weight_kg,
        "bmi": bmi,
        "bmiCategory": _bmi_category(bmi) if bmi is not None else None,
        "familySize": row.get("family_size"),
        "budgetAmount": row.get("budget_amount"),
        "budgetPeriod": row.get("budget_period"),
        "onboardingCompleted": bool(row.get("onboarding_completed")),
    }


@router.get("")
async def get_preferences(repo: PreferencesRepository = Depends(get_preferences_repository)):
    """Return the demo user's saved preferences (onboardingCompleted: false if none saved yet)."""
    row = await repo.get(DEMO_USER_ID)
    return {"preferences": _to_response(row)}


@router.put("")
async def save_preferences(
    body: PreferencesUpdateRequest,
    repo: PreferencesRepository = Depends(get_preferences_repository),
):
    """Create or update the demo user's onboarding preferences."""
    row = await repo.upsert(DEMO_USER_ID, {
        "cuisines": body.cuisines,
        "diet_type": body.dietType,
        "height_cm": body.heightCm,
        "weight_kg": body.weightKg,
        "family_size": body.familySize,
        "budget_amount": body.budgetAmount,
        "budget_period": body.budgetPeriod,
    })
    return {"success": True, "preferences": _to_response(row)}


@router.post("/rebuild")
async def rebuild_preferences(userId: str = DEMO_USER_ID):
    """
    Manually rebuild brand preferences (user_brand_preferences) from the
    user's full receipt_items history. Same aggregation the automatic
    post-scan background task runs — useful for backfills or debugging.
    """
    result = await rebuild_brand_preferences(userId)
    return {"success": True, **result}
