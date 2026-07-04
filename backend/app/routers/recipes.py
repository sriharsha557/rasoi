"""
Recipes router

Endpoints:
  GET  /api/recipes                 — meal recommendations (full list)
  GET  /api/recommend               — alias with expiry/cuisine/count params
  GET  /api/recipe/provider-status  — which API tier is active
    GET  /api/recipe/{id}             — full recipe detail
  POST /api/pantry/cooked           — mark recipe cooked, remove used ingredients
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
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
from app.routers.pantry import get_session_pantry_items, remove_session_items
from app.database import DEMO_USER_ID, get_cook_history_repository, get_preferences_repository


async def _health_profile() -> tuple[list[str], str]:
    """Read the demo user's onboarding health conditions/goal (defaults if unset)."""
    repo = await get_preferences_repository()
    row = await repo.get(DEMO_USER_ID)
    if not row:
        return [], "maintenance"
    import json
    try:
        conditions = json.loads(row.get("health_conditions") or "[]")
    except (json.JSONDecodeError, TypeError):
        conditions = []
    return conditions, row.get("health_goal") or "maintenance"

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
):
    """
    Get meal recommendations based on the session pantry (last scan).

    Query Parameters:
    - prioritize_expiring (bool, default: true) - kept for API compatibility; the
      session pantry has no live expiry tracking, so this has no effect
    - max_recipes (int, 1-20, default: 5) - Maximum number of recipes to return
    - cuisine (str, optional) - Cuisine filter hint

    Returns success response with recipes sorted by matchPercentage (highest first).
    Validates query parameters (max_recipes 1-20).

    Validates: Requirements 4.1, 4.2, 4.3, 9.4
    """
    # Validate max_recipes parameter
    if max_recipes < 1 or max_recipes > 20:
        raise HTTPException(
            status_code=422,
            detail="max_recipes must be between 1 and 20"
        )

    pantry = await get_session_pantry_items(DEMO_USER_ID)
    health_conditions, health_goal = await _health_profile()

    # Get recipe recommendations from the local Supabase catalogue, falling
    # back to Spoonacular for cuisines not owned locally.
    result = await get_recipes(
        pantry,
        prioritize_expiring,
        max_recipes,
        cuisine or "any",
        meal_type,
        diet,
        max_ready_time,
        health_conditions,
        health_goal,
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
):
    """
    Alias of /api/recipes with expiry-first ordering and cuisine hint.
    """
    pantry = await get_session_pantry_items(DEMO_USER_ID)
    health_conditions, health_goal = await _health_profile()
    result = await get_recipes(
        pantry, prioritize_expiry, count, cuisine, meal_type, diet, max_ready_time,
        health_conditions, health_goal,
    )
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
async def get_recipe_detail(recipe_id: str):
    """
    Fetch full recipe detail from Supabase first, then Spoonacular for
    continental recipe ids.
    """
    pantry = await get_session_pantry_items(DEMO_USER_ID)
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
):
    """
    Called when the user finishes cooking a recipe.
    Removes the used ingredients from the session pantry, saves cook history,
    and triggers the Buddy agentic loop (PRD §8b.4).
    """
    remaining_items, removed = await remove_session_items(DEMO_USER_ID, body.items_used)
    # Save to cook_history for Buddy memory (PRD §6b.1)
    cook_history_repo = await get_cook_history_repository()
    await cook_history_repo.save_cook_history(body.recipe_title, body.items_used)
    # Trigger Buddy agent loop in background (PRD §8b.4)
    from app.routers.buddy import run_agent_loop
    background_tasks.add_task(run_agent_loop, "recipe_cooked")
    return {
        "removed": removed,
        "remaining": len(remaining_items),
        "message": f"Removed {removed} ingredient(s). {len(remaining_items)} item(s) left in pantry.",
    }
