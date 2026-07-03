"""
Recipes router

Endpoints:
  GET  /api/recipes                 — meal recommendations (full list)
  GET  /api/recommend               — alias with expiry/cuisine/count params
  GET  /api/recipe/provider-status  — which API tier is active
    GET  /api/recipe/{id}             — full recipe detail
  POST /api/pantry/cooked           — mark recipe cooked, remove used ingredients
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel
from app.services.recipe_service import (
    get_continental_recipe,
    get_provider_status,
    get_recipe,
    get_recipes,
    search_continental_recipe,
    search_recipes,
)
from app.services.planner_service import get_planner_recipe_by_name
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
    meal_type: str = Query(None),
    diet: str = Query(None),
    max_ready_time: int = Query(None, ge=1, le=240),
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
    
    # Attach expiry flags to items
    pantry = [_attach_expiry_flags(i) for i in raw_items]
    
    # Get recipe recommendations from Supabase for Indian/local recipes and
    # Spoonacular for continental cuisines.
    result = await get_recipes(
        pantry,
        prioritize_expiring,
        max_recipes,
        cuisine or "any",
        meal_type,
        diet,
        max_ready_time,
    )
    
    # Build response matching spec format
    if not result.get("success"):
        return {
            "success": True,
            "recipes": [],
            "provider": result.get("provider", "supabase"),
            "message": result.get("message", "No recipes found."),
        }
    
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
    meal_type: str = Query(None),
    diet: str = Query(None),
    max_ready_time: int = Query(None, ge=1, le=240),
    count: int = Query(5, ge=1, le=10),
    repo: PantryRepository = Depends(get_repository),
):
    """
    Alias of /api/recipes with expiry-first ordering and cuisine hint.
    """
    raw_items = await repo.get_all()
    pantry = [_attach_expiry_flags(i) for i in raw_items]
    result = await get_recipes(pantry, prioritize_expiry, count, cuisine, meal_type, diet, max_ready_time)
    return result


# NOTE: fixed paths must be registered before parameterised ones
@router.get("/recipe/provider-status")
async def provider_status():
    """Expose the current active recipe API provider (monitoring endpoint)."""
    return get_provider_status()


@router.get("/recipe/search")
async def search_recipe_detail(query: str = Query(..., min_length=2, max_length=120)):
    """
    Search Supabase recipes by meal name first, then Spoonacular for
    continental Italian/Mexican recipes.
    """
    recipes = []
    try:
        recipes = await search_recipes({"query": query}, [], 1)
    except Exception:
        recipes = []

    recipe = recipes[0] if recipes else await search_continental_recipe(query)
    if not recipe:
        recipe = get_planner_recipe_by_name(query)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found.")

    return {
        "success": True,
        "provider": recipe.get("source", "supabase"),
        "recipes": [recipe],
        "message": "Recipe loaded.",
    }


@router.get("/recipe/{recipe_id}")
async def get_recipe_detail(
    recipe_id: str,
    repo: PantryRepository = Depends(get_repository),
):
    """
    Fetch full recipe detail from Supabase first, then Spoonacular for
    continental recipe ids.
    """
    raw_items = await repo.get_all()
    pantry = [_attach_expiry_flags(i) for i in raw_items]
    recipe = None
    try:
        recipe = await get_recipe(recipe_id, pantry)
    except Exception:
        recipe = None
    if not recipe:
        recipe = await get_continental_recipe(recipe_id, pantry)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return recipe


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
