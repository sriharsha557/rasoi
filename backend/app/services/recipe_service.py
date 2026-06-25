"""
Recipe service — 3-tier auto-failover: Spoonacular → Edamam → Claude.

Provider state is in-memory and resets on server restart (per PRD §6a.1).
"""

import httpx
import os
import json
import logging
from datetime import date
from app.clients import claude_client

logger = logging.getLogger(__name__)

# In-memory provider failure flags
_spoonacular_failed = False
_edamam_failed = False


def _reset_provider_status():
    global _spoonacular_failed, _edamam_failed
    _spoonacular_failed = False
    _edamam_failed = False


def get_provider_status() -> dict:
    if not _spoonacular_failed:
        active = "spoonacular"
    elif not _edamam_failed:
        active = "edamam"
    else:
        active = "claude"
    return {
        "active": active,
        "spoonacular": "failed" if _spoonacular_failed else "ok",
        "edamam": "failed" if _edamam_failed else "ok",
        "claude": "ok",  # Claude is always the fallback
    }


def _normalise_spoonacular(raw: dict, pantry_names: set) -> dict:
    """Normalise a Spoonacular recipe into the shared Recipe shape."""
    ingredients = []
    for ing in raw.get("extendedIngredients", []):
        name = ing.get("name", "").lower()
        ingredients.append(
            {
                "name": name,
                "quantity": ing.get("amount", 1),
                "unit": ing.get("unit", "pcs"),
                "available": name in pantry_names,
            }
        )
    available_count = sum(1 for i in ingredients if i["available"])
    match_pct = (
        round(available_count / len(ingredients) * 100) if ingredients else 0
    )
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("title", ""),
        "cuisine": (raw.get("cuisines") or [""])[0],
        "difficulty": "Medium",
        "prepTimeMinutes": raw.get("readyInMinutes", 30),
        "matchPercentage": match_pct,
        "usesExpiringItems": False,
        "ingredients": ingredients,
        "missingIngredients": [i["name"] for i in ingredients if not i["available"]],
        "steps": [
            s.get("step", "")
            for s in (raw.get("analyzedInstructions") or [{"steps": []}])[0].get("steps", [])
        ],
    }


def _normalise_edamam(raw: dict, pantry_names: set) -> dict:
    """Normalise an Edamam recipe into the shared Recipe shape."""
    recipe = raw.get("recipe", {})
    ingredients = []
    for line in recipe.get("ingredientLines", []):
        name = line.lower().strip()
        ingredients.append(
            {"name": name, "quantity": 1, "unit": "pcs", "available": name in pantry_names}
        )
    available_count = sum(1 for i in ingredients if i["available"])
    match_pct = (
        round(available_count / len(ingredients) * 100) if ingredients else 0
    )
    return {
        "id": recipe.get("uri", "").split("#recipe_")[-1],
        "name": recipe.get("label", ""),
        "cuisine": (recipe.get("cuisineType") or [""])[0].title(),
        "difficulty": "Medium",
        "prepTimeMinutes": recipe.get("totalTime", 30),
        "matchPercentage": match_pct,
        "usesExpiringItems": False,
        "ingredients": ingredients,
        "missingIngredients": [i["name"] for i in ingredients if not i["available"]],
        "steps": ["Visit the recipe link for step-by-step instructions."],
    }


async def _try_spoonacular(
    pantry_items: list[dict],
    pantry_names: set,
    prioritize_expiring: bool,
    max_recipes: int,
) -> list[dict] | None:
    global _spoonacular_failed
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        _spoonacular_failed = True
        return None

    ingredients_csv = ",".join(i["name"] for i in pantry_items)
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": api_key,
        "ingredients": ingredients_csv,
        "number": max_recipes,
        "ranking": 1,  # maximize used ingredients
        "ignorePantry": False,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 402:
                logger.warning("Spoonacular quota exhausted — switching to Edamam")
                _spoonacular_failed = True
                return None
            resp.raise_for_status()
            recipes_raw = resp.json()
            # Fetch full recipe details for each result
            results = []
            for r in recipes_raw[:max_recipes]:
                detail_resp = await client.get(
                    f"https://api.spoonacular.com/recipes/{r['id']}/information",
                    params={"apiKey": api_key, "includeNutrition": False},
                )
                if detail_resp.status_code == 200:
                    results.append(_normalise_spoonacular(detail_resp.json(), pantry_names))
            return results if results else None
    except Exception as e:
        logger.warning(f"Spoonacular error: {e} — switching to Edamam")
        _spoonacular_failed = True
        return None


async def _try_edamam(
    pantry_items: list[dict],
    pantry_names: set,
    prioritize_expiring: bool,
    max_recipes: int,
) -> list[dict] | None:
    global _edamam_failed
    app_id = os.getenv("EDAMAM_APP_ID")
    app_key = os.getenv("EDAMAM_APP_KEY")
    if not app_id or not app_key:
        _edamam_failed = True
        return None

    query = " ".join(i["name"] for i in pantry_items[:5])  # Edamam query string
    url = "https://api.edamam.com/api/recipes/v2"
    params = {
        "type": "public",
        "q": query,
        "app_id": app_id,
        "app_key": app_key,
        "random": "true",
        "field": ["label", "cuisineType", "totalTime", "ingredientLines", "uri"],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                logger.warning("Edamam rate-limited — switching to Claude")
                _edamam_failed = True
                return None
            resp.raise_for_status()
            hits = resp.json().get("hits", [])[:max_recipes]
            return [_normalise_edamam(h, pantry_names) for h in hits] if hits else None
    except Exception as e:
        logger.warning(f"Edamam error: {e} — switching to Claude")
        _edamam_failed = True
        return None


async def get_recipes(
    pantry_items: list[dict],
    prioritize_expiring: bool = True,
    max_recipes: int = 5,
) -> dict:
    """
    Get recipe recommendations with 3-tier auto-failover.
    Returns { recipes, provider }.
    """
    global _spoonacular_failed, _edamam_failed

    pantry_names = {i["name"].lower() for i in pantry_items}

    # Tier 1: Spoonacular
    if not _spoonacular_failed:
        recipes = await _try_spoonacular(pantry_items, pantry_names, prioritize_expiring, max_recipes)
        if recipes:
            return {"recipes": _mark_expiring(recipes, pantry_items), "provider": "spoonacular"}

    # Tier 2: Edamam
    if not _edamam_failed:
        recipes = await _try_edamam(pantry_items, pantry_names, prioritize_expiring, max_recipes)
        if recipes:
            return {"recipes": _mark_expiring(recipes, pantry_items), "provider": "edamam"}

    # Tier 3: Claude (always available)
    recipes = await claude_client.get_recipe_recommendations(
        pantry_items, prioritize_expiring, max_recipes
    )
    return {"recipes": _mark_expiring(recipes, pantry_items), "provider": "claude"}


def _mark_expiring(recipes: list[dict], pantry_items: list[dict]) -> list[dict]:
    """Set usesExpiringItems=True for recipes that include an expiring ingredient."""
    expiring_names = {
        i["name"].lower()
        for i in pantry_items
        if i.get("isExpiring") or i.get("isExpired")
    }
    for recipe in recipes:
        recipe_ingredient_names = {
            ing["name"].lower() for ing in recipe.get("ingredients", [])
        }
        recipe["usesExpiringItems"] = bool(recipe_ingredient_names & expiring_names)
    # Sort: expiring-first, then by matchPercentage desc
    recipes.sort(key=lambda r: (-r["usesExpiringItems"], -r.get("matchPercentage", 0)))
    return recipes
