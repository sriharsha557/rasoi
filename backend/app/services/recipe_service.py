"""
Recipe Service — Meal recommendation generation and ingredient matching.

Provides intelligent recipe recommendations using Claude Text API with
ingredient matching percentages and expiration prioritization.

Async-first implementation with proper error handling and logging.

Validates: Requirements 4.5, 4.6, 4.7, 4.8
"""

import httpx
import os
import json
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from app.clients import claude_client
from app.database import PantryRepository
from app import guardrails

logger = logging.getLogger(__name__)

# In-memory provider failure flags
_spoonacular_failed = False
_edamam_failed = False


class RecipeService:
    """
    Service for generating meal recommendations.
    
    Provides async-first methods for recipe generation with ingredient
    matching percentages and expiration-aware prioritization.
    
    Implements 3-tier failover: Spoonacular → Edamam → Claude
    """
    
    def __init__(self, repository: PantryRepository):
        """
        Initialize recipe service.
        
        Args:
            repository: PantryRepository instance for pantry lookups
        """
        self.repository = repository
        logger.debug("[recipe_service] Initialized with repository")
    
    async def get_recommendations(
        self,
        pantry_items: Optional[List[Dict[str, Any]]] = None,
        prioritize_expiring: bool = True,
        max_recipes: int = 5,
    ) -> Dict[str, Any]:
        """
        Get meal recommendations based on available ingredients.
        
        Fetches pantry items if not provided, then coordinates with
        Text API (via 3-tier failover) to generate recipes. Computes
        ingredient matching percentages and flags recipes using expiring items.
        
        Args:
            pantry_items: Optional list of pantry items. If not provided,
                         fetches from repository.
            prioritize_expiring: Whether to prioritize recipes using expiring items
            max_recipes: Maximum number of recipes to generate
        
        Returns:
            Dictionary with:
            - success (bool): Whether recommendations were found
            - recipes (List[Dict]): Generated recipes with matching percentages
            - provider (str): Which provider was used (spoonacular/edamam/claude)
            - message (str): Result message
        
        Validates: Requirements 4.5, 4.6, 4.7, 4.8
        """
        logger.info(
            "[recipe_service] Generating recommendations "
            "(prioritize_expiring=%s, max=%d)",
            prioritize_expiring,
            max_recipes
        )
        
        try:
            # Fetch pantry items if not provided
            if pantry_items is None:
                pantry_items = await self.repository.get_all()
            
            if not pantry_items:
                logger.warning("[recipe_service] Pantry is empty, no recommendations possible")
                return {
                    "success": False,
                    "recipes": [],
                    "provider": None,
                    "message": "Your pantry is empty. Scan some ingredients first!",
                }
            
            # Call Claude Text API
            raw_recipes = await claude_client.get_recipe_recommendations(
                pantry_items=pantry_items,
                prioritize_expiring=prioritize_expiring,
                max_recipes=max_recipes
            )
            
            if not raw_recipes:
                logger.info("[recipe_service] No recipes generated")
                return {
                    "success": False,
                    "recipes": [],
                    "provider": "claude",
                    "message": "Could not generate recipes with your current pantry.",
                }
            
            logger.info(
                "[recipe_service] Generated %d recipes",
                len(raw_recipes)
            )
            
            # Compute match percentages
            enriched_recipes = []
            for recipe in raw_recipes:
                enriched = self.calculate_match_percentage(recipe, pantry_items)
                enriched_recipes.append(enriched)
            
            return {
                "success": True,
                "recipes": enriched_recipes,
                "provider": "claude",
                "message": f"Found {len(enriched_recipes)} recipes for your pantry.",
            }
        
        except Exception as e:
            logger.error("[recipe_service] Error generating recommendations: %s", str(e))
            return {
                "success": False,
                "recipes": [],
                "provider": None,
                "message": f"Failed to generate recipes: {str(e)}",
            }
    
    def calculate_match_percentage(
        self,
        recipe: Dict[str, Any],
        pantry_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate ingredient match percentage for a recipe.
        
        Computes the percentage of recipe ingredients available in the pantry.
        Sets matchPercentage field and identifies missing ingredients.
        
        Args:
            recipe: Recipe dictionary with 'ingredients' field
            pantry_items: List of available pantry items
        
        Returns:
            Recipe dict with updated matchPercentage and missingIngredients
        
        Validates: Requirement 4.6
        """
        recipe_ingredients = recipe.get("ingredients", [])
        if not recipe_ingredients:
            recipe["matchPercentage"] = 0.0
            recipe["missingIngredients"] = []
            return recipe
        
        # Get pantry ingredient names (case-insensitive)
        pantry_names = {item.get("name", "").lower().strip() for item in pantry_items}
        
        # Count available ingredients
        available_count = 0
        missing_ingredients = []
        
        for ingredient in recipe_ingredients:
            ing_name = ingredient.get("name", "").lower().strip()
            
            # Check if ingredient is in pantry
            if ing_name in pantry_names:
                available_count += 1
                ingredient["available"] = True
            else:
                ingredient["available"] = False
                missing_ingredients.append(ing_name)
        
        # Calculate match percentage
        total_ingredients = len(recipe_ingredients)
        match_pct = (available_count / total_ingredients * 100) if total_ingredients > 0 else 0.0
        
        recipe["matchPercentage"] = round(match_pct, 2)
        recipe["missingIngredients"] = missing_ingredients
        
        logger.debug(
            "[recipe_service] Recipe '%s': %d/%d ingredients available (%.1f%%)",
            recipe.get("name", "Unknown"),
            available_count,
            total_ingredients,
            match_pct
        )
        
        return recipe


def _reset_provider_status():
    """Reset provider failure flags (for testing/recovery)."""
    global _spoonacular_failed, _edamam_failed
    _spoonacular_failed = False
    _edamam_failed = False


async def get_recipes(
    pantry_items: list[dict],
    prioritize_expiring: bool = True,
    max_recipes: int = 5,
    cuisine: str = "any",
) -> dict:
    """
    Wrapper function for use in FastAPI routes.
    
    Coordinates recipe generation across all services using the 3-tier failover.
    
    Args:
        pantry_items: List of pantry items (already enriched with expiry flags)
        prioritize_expiring: Whether to prioritize recipes using expiring items
        max_recipes: Maximum number of recipes to return
        cuisine: Cuisine filter hint (best-effort)
    
    Returns:
        Dict with success, recipes, provider, message
    """
    service = RecipeService(repository=None)  # We don't need repo in get_recommendations
    pantry_names = {item.get("name", "").lower().strip() for item in pantry_items}
    
    # Try 3-tier failover
    recipes = await _try_spoonacular(pantry_items, pantry_names, prioritize_expiring, max_recipes)
    
    if recipes is None:
        recipes = await _try_edamam(pantry_items, pantry_names, prioritize_expiring, max_recipes)
    
    if recipes is None:
        # Fall back to Claude
        recipes = await claude_client.get_recipe_recommendations(
            pantry_items=pantry_items,
            prioritize_expiring=prioritize_expiring,
            max_recipes=max_recipes,
        )
    
    if not recipes:
        return {
            "success": False,
            "recipes": [],
            "provider": "claude",
            "message": "Could not generate recipes with your current pantry.",
        }
    
    # Mark expiring and sort
    recipes = _mark_expiring(recipes, pantry_items)
    
    return {
        "success": True,
        "recipes": recipes[:max_recipes],
        "provider": get_provider_status()["active"],
        "message": f"Found {len(recipes)} recipe(s) for your pantry.",
    }


def get_provider_status() -> dict:
    """Get current provider status."""
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
    # 14.2: Remove recipes that only use fully-expired ingredients
    recipes = guardrails.filter_expired_only_recipes(recipes, pantry_items)
    # Sort: expiring-first, then by matchPercentage desc
    recipes.sort(key=lambda r: (-r["usesExpiringItems"], -r.get("matchPercentage", 0)))
    return recipes
