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
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel
from app.services.recipe_service import get_recipes, get_provider_status
from app.routers.pantry import _attach_expiry_flags
from app.database import get_repository, PantryRepository

router = APIRouter(prefix="/api", tags=["recipes"])


class CookedRequest(BaseModel):
    items_used: list[str]   # ingredient names (not IDs) to remove from pantry
    recipe_title: str = "Unknown Recipe"  # for cook history log


@router.get("/recipes")
async def recipes(
    prioritize_expiring: bool = Query(True, alias="prioritize_expiring"),
    max_recipes: int = Query(5, ge=1, le=20),
    cuisine: str = Query(None),
    repo: PantryRepository = Depends(get_repository),
):
    """
    Get meal recommendations based on available pantry ingredients.
    
    Query Parameters:
    - prioritize_expiring (bool, default: true) - Prioritize recipes using expiring items
    - max_recipes (int, 1-20, default: 5) - Maximum number of recipes to return
    - cuisine (str, optional) - Cuisine filter hint
    
    Returns success response with recipes sorted by:
    1. usesExpiringItems (true first)
    2. matchPercentage (highest first)
    
    Returns 400 if pantry is empty.
    Validates query parameters (max_recipes 1-20).
    
    Validates: Requirements 4.1, 4.2, 4.3, 9.4
    """
    # Validate max_recipes parameter
    if max_recipes < 1 or max_recipes > 20:
        raise HTTPException(
            status_code=422,
            detail="max_recipes must be between 1 and 20"
        )
    
    # Fetch pantry items
    raw_items = await repo.get_all()
    
    # Handle empty pantry
    if not raw_items:
        raise HTTPException(
            status_code=400,
            detail="Your pantry is empty. Scan some ingredients first!"
        )
    
    # Attach expiry flags to items
    pantry = [_attach_expiry_flags(i) for i in raw_items]
    
    # Get recipe recommendations with 3-tier failover
    result = await get_recipes(pantry, prioritize_expiring, max_recipes, cuisine or "any")
    
    # Build response matching spec format
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Could not generate recipes")
        )
    
    return {
        "success": True,
        "recipes": result.get("recipes", []),
        "provider": result.get("provider", "claude"),
        "message": result.get("message", f"Found {len(result.get('recipes', []))} recipes for your pantry."),
    }


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


@router.get("/recipe/search")
async def search_recipe_detail(query: str = Query(..., min_length=2, max_length=120)):
    """
    Search Spoonacular by meal name and return the first full recipe detail.
    Used by planner cards so a planned meal opens a real recipe from the API.
    """
    spoonacular_key = os.getenv("SPOONACULAR_API_KEY")
    if not spoonacular_key:
        raise HTTPException(status_code=404, detail="Spoonacular recipe search is not configured.")

    async with httpx.AsyncClient(timeout=10) as client:
        search_resp = await client.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params={
                "apiKey": spoonacular_key,
                "query": query,
                "number": 1,
                "addRecipeInformation": False,
            },
        )

        if search_resp.status_code == 402:
            raise HTTPException(status_code=502, detail="Spoonacular quota exhausted.")
        if search_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Spoonacular search error {search_resp.status_code}.")

        results = search_resp.json().get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Recipe not found.")

        recipe_id = results[0]["id"]
        detail_resp = await client.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/information",
            params={"apiKey": spoonacular_key, "includeNutrition": False},
        )

    if detail_resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    if detail_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Spoonacular error {detail_resp.status_code}.")

    data = detail_resp.json()
    steps = [
        step["step"]
        for inst in data.get("analyzedInstructions", [])
        for step in inst.get("steps", [])
    ]
    ingredients = [
        {"name": i.get("name", ""), "quantity": i.get("amount", 1), "unit": i.get("unit", "pcs"), "available": True}
        for i in data.get("extendedIngredients", [])
    ]
    return {
        "success": True,
        "provider": "spoonacular",
        "recipes": [
            {
                "id": str(data["id"]),
                "name": data["title"],
                "cuisine": (data.get("cuisines") or [""])[0],
                "difficulty": "Medium",
                "prepTimeMinutes": data.get("readyInMinutes", 30),
                "matchPercentage": 100,
                "usesExpiringItems": False,
                "ingredients": ingredients,
                "missingIngredients": [],
                "steps": steps or ["Open the source recipe for detailed cooking steps."],
            }
        ],
        "message": "Recipe loaded from Spoonacular.",
    }


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
    background_tasks: BackgroundTasks,
    repo: PantryRepository = Depends(get_repository),
):
    """
    Called when the user finishes cooking a recipe.
    Removes the used ingredients from the pantry, saves cook history,
    and triggers the Chammach agentic loop (PRD §8b.4).
    """
    removed = await repo.delete_by_names(body.items_used)
    # Save to cook_history for Chammach memory (PRD §6b.1)
    await repo.save_cook_history(body.recipe_title, body.items_used)
    all_items = await repo.get_all()
    remaining = len(all_items)
    # Trigger Chammach agent loop in background (PRD §8b.4)
    from app.routers.chammach import run_agent_loop
    background_tasks.add_task(run_agent_loop, "recipe_cooked")
    return {
        "removed": removed,
        "remaining": remaining,
        "message": f"Removed {removed} ingredient(s). {remaining} item(s) left in pantry.",
    }
