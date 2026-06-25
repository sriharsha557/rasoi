"""
Recipes router — GET /api/recipes, GET /api/recipe/provider-status
"""

from fastapi import APIRouter, Query, Depends
from app.services.recipe_service import get_recipes, get_provider_status
from app.routers.pantry import _attach_expiry_flags
from app.database import get_repository, PantryRepository

router = APIRouter(prefix="/api", tags=["recipes"])


@router.get("/recipes")
async def recipes(
    prioritize_expiring: bool = Query(True, alias="prioritize_expiring"),
    max_recipes: int = Query(5, ge=1, le=10),
    repo: PantryRepository = Depends(get_repository),
):
    """
    Return AI-ranked meal recommendations from the current pantry.
    Uses 3-tier failover: Spoonacular → Edamam → Claude.
    """
    raw_items = await repo.get_all()
    pantry = [_attach_expiry_flags(i) for i in raw_items]

    result = await get_recipes(pantry, prioritize_expiring, max_recipes)
    return result


@router.get("/recipe/provider-status")
async def provider_status():
    """Expose the current active recipe API provider (monitoring endpoint)."""
    return get_provider_status()
