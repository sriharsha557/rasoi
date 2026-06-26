"""
Recipes router

Endpoints:
  GET  /api/recipes                 — meal recommendations (full list)
  GET  /api/recommend               — alias with expiry/cuisine/count params
  GET  /api/recipe/provider-status  — which API tier is active
  GET  /api/recipe/{id}             — full recipe detail (Spoonacular)
  POST /api/pantry/cooked           — mark recipe cooked, remove used ingredients
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.services.recipe_service import get_recipes, get_provider_status
from app.routers.pantry import _attach_expiry_flags
from app.database import get_repository, PantryRepository

router = APIRouter(prefix="/api", tags=["recipes"])


class CookedRequest(BaseModel):
    items_used: list[str]   # ingredient names (not IDs) to remove from pantry


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


@router.get("/recommend")
async def recommend(
    prioritize_expiry: bool = Query(True),
    cuisine: str = Query("any"),
    count: int = Query(5, ge=1, le=10),
    repo: PantryRepository = Depends(get_repository),
):
    """
    Alias of /api/recipes with expiry-first ordering and cuisine hint.
    Cuisine filtering is applied as a best-effort hint to Claude fallback.
    """
    raw_items = await repo.get_all()
    if not raw_items:
        raise HTTPException(status_code=400, detail="Pantry is empty. Scan your fridge first.")
    pantry = [_attach_expiry_flags(i) for i in raw_items]
    result = await get_recipes(pantry, prioritize_expiry, count)
    return result


# NOTE: fixed paths must be registered before parameterised ones
@router.get("/recipe/provider-status")
async def provider_status():
    """Expose the current active recipe API provider (monitoring endpoint)."""
    return get_provider_status()


@router.get("/recipe/{recipe_id}")
async def get_recipe_detail(recipe_id: str):
    """
    Fetch full recipe detail from Spoonacular by numeric ID.
    Returns 404 if Spoonacular is not configured or the recipe is not found.
    """
    spoonacular_key = os.getenv("SPOONACULAR_API_KEY")
    if not spoonacular_key or recipe_id.startswith("claude_"):
        raise HTTPException(status_code=404, detail="Recipe detail not available.")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/information",
            params={"apiKey": spoonacular_key, "includeNutrition": False},
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Spoonacular error {resp.status_code}.")

    data = resp.json()
    steps = [
        step["step"]
        for inst in data.get("analyzedInstructions", [])
        for step in inst.get("steps", [])
    ]
    return {
        "id": str(data["id"]),
        "name": data["title"],
        "image": data.get("image", ""),
        "source": "spoonacular",
        "prepTimeMinutes": data.get("readyInMinutes", 30),
        "servings": data.get("servings", 2),
        "ingredients": [
            {"name": i.get("name", ""), "quantity": i.get("amount", 1), "unit": i.get("unit", "pcs"), "available": True}
            for i in data.get("extendedIngredients", [])
        ],
        "steps": steps,
        "url": data.get("sourceUrl", ""),
    }


@router.post("/pantry/cooked")
async def mark_cooked(
    body: CookedRequest,
    repo: PantryRepository = Depends(get_repository),
):
    """
    Called when the user finishes cooking a recipe.
    Removes the used ingredients from the pantry by name.
    """
    removed = await repo.delete_by_names(body.items_used)
    all_items = await repo.get_all()
    remaining = len(all_items)
    return {
        "removed": removed,
        "remaining": remaining,
        "message": f"Removed {removed} ingredient(s). {remaining} item(s) left in pantry.",
    }
