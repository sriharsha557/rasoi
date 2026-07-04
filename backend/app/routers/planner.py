"""Planner, household, grocery, and cuisine profile endpoints."""

from fastapi import APIRouter, Query

from app.database import DEMO_USER_ID
from app.routers.pantry import get_session_pantry_items
from app.services.planner_service import (
    build_weekly_plan,
    get_cuisine_profiles,
    get_delivery_partners,
    get_household_profile,
)

router = APIRouter(prefix="/api", tags=["planner"])


@router.get("/planner/weekly")
async def weekly_planner(
    region: str = Query("south_indian"),
    household_size: int = Query(2, ge=1, le=12),
    days: int = Query(7, ge=1, le=14),
):
    pantry_items = await get_session_pantry_items(DEMO_USER_ID)
    return build_weekly_plan(pantry_items, region, household_size, days)


@router.get("/household/profile")
async def household_profile():
    return get_household_profile()


@router.get("/grocery/delivery-partners")
async def grocery_delivery_partners(items: str = Query("")):
    query_items = [item.strip() for item in items.split(",") if item.strip()]
    return {"partners": get_delivery_partners(query_items)}


@router.get("/cuisine-profiles")
async def cuisine_profiles():
    return {"profiles": get_cuisine_profiles()}