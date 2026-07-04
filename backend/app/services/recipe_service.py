"""
Recipe Service — Meal recommendation and recipe catalogue queries.

Recipes in the local catalogue (Supabase tables) are served directly; any
cuisine not owned locally falls back to Spoonacular's global recipe catalogue.
"""

import httpx
import os
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.clients import claude_client
from app import guardrails
from app.services.planner_service import get_planner_recipes

logger = logging.getLogger(__name__)

# In-memory provider failure flags
_spoonacular_failed = False

# DEMO: pantry ingredient (lowercase substring) -> exact seeded recipe title
# to guarantee surfaces first, ahead of AI-generated suggestions.
_DEMO_TRIGGER_RECIPES = {
    "paneer": "Paneer Butter Masala",
    "chicken breast": "Grilled Herb Chicken with Roasted Vegetables & Yogurt Sauce",
}


class RecipeIngredientModel(BaseModel):
    id: str
    recipe_id: str
    name: str
    quantity: str | float | int | None = None
    is_optional: bool = False
    sort_order: int = 0
    available: bool = False


class RecipeStepModel(BaseModel):
    id: str
    recipe_id: str
    step_number: int
    instruction: str
    duration_min: int | None = None
    tip: str | None = None


class RecipeModel(BaseModel):
    id: str
    title: str
    cuisine: str | None = None
    meal_type: str | None = None
    diet: str | None = None
    ready_in_min: int | None = None
    servings: int | None = None
    image_url: str | None = None
    description: str | None = None
    calories_kcal: int | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    created_at: datetime | str | None = None
    ingredients: list[RecipeIngredientModel] = Field(default_factory=list)
    cooking_steps: list[RecipeStepModel] = Field(default_factory=list)
    match_percentage: float = 0.0
    missing_ingredients: list[str] = Field(default_factory=list)
    uses_expiring_items: bool = False


def _supabase_rest_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY are not configured")
    return url, key


async def _supabase_get(table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    supabase_url, service_key = _supabase_rest_config()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{supabase_url}/rest/v1/{table}",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def _normalise_name(value: str) -> str:
    value = re.sub(r"\([^)]*\)", " ", value.lower())
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _ingredient_matches(recipe_ingredient: str, pantry_ingredient: str) -> bool:
    recipe_name = _normalise_name(recipe_ingredient)
    pantry_name = _normalise_name(pantry_ingredient)
    if not recipe_name or not pantry_name:
        return False
    return recipe_name == pantry_name or recipe_name in pantry_name or pantry_name in recipe_name


def _pantry_names(pantry_items: list[dict[str, Any]]) -> set[str]:
    return {_normalise_name(item.get("name", "")) for item in pantry_items if item.get("name")}


def _compute_match(
    ingredients: list[dict[str, Any]],
    pantry_names: set[str],
) -> tuple[float, list[str], list[dict[str, Any]]]:
    if not ingredients:
        return 0.0, [], []

    available_count = 0
    missing: list[str] = []
    enriched: list[dict[str, Any]] = []

    for ingredient in ingredients:
        name = ingredient.get("name", "")
        normalised_name = _normalise_name(name)
        available = any(_ingredient_matches(name, pantry_name) for pantry_name in pantry_names)
        if available:
            available_count += 1
        elif not ingredient.get("is_optional"):
            missing.append(normalised_name)
        enriched.append({**ingredient, "available": available})

    required_count = sum(1 for ingredient in ingredients if not ingredient.get("is_optional")) or len(ingredients)
    required_available = sum(
        1
        for ingredient in enriched
        if ingredient.get("available") and not ingredient.get("is_optional")
    )
    match_pct = round(required_available / required_count * 100, 2) if required_count else 0.0
    return match_pct, missing, enriched


def _uses_expiring(recipe: dict[str, Any], pantry_items: list[dict[str, Any]]) -> bool:
    expiring_names = {
        _normalise_name(item.get("name", ""))
        for item in pantry_items
        if item.get("isExpiring") or item.get("isExpired")
    }
    ingredient_names = {
        ingredient.get("name", "")
        for ingredient in recipe.get("ingredients", [])
    }
    return any(
        _ingredient_matches(recipe_name, pantry_name)
        for recipe_name in ingredient_names
        for pantry_name in expiring_names
    )


# Ingredients with a high glycemic impact — used only to softly re-rank
# recipes for users who've flagged diabetes, never to label a recipe as
# medically "safe" or "unsafe". Not a substitute for professional dietary advice.
_HIGH_GI_INGREDIENT_TERMS = frozenset([
    "sugar", "jaggery", "honey", "white rice", "maida", "refined flour",
    "white bread", "cornflakes", "soda", "cola", "syrup",
])


def _health_match(recipe: dict[str, Any], health_conditions: list[str], health_goal: str) -> tuple[int, str | None]:
    """
    Heuristic 0-100 health-match score plus a soft, non-medical note, derived
    from the recipe's existing nutrition fields and ingredient list. This is a
    rough re-ranking signal for a demo, not medical guidance — deliberately
    conservative (only diabetes + the fitness goals get scored; other
    conditions are stored for future use but not scored without real signal).
    """
    calories = recipe.get("caloriesKcal")
    protein = recipe.get("proteinG")
    carbs = recipe.get("carbsG")
    fiber = recipe.get("fiberG")

    if calories is None and protein is None and carbs is None:
        return 100, None  # no nutrition data available — don't penalize

    score = 100
    note: str | None = None

    if "diabetes" in health_conditions:
        ingredient_text = " ".join(
            (ing.get("name") or "") for ing in (recipe.get("ingredients") or [])
        ).lower()
        if any(term in ingredient_text for term in _HIGH_GI_INGREDIENT_TERMS):
            score -= 30
        if carbs is not None and carbs > 60 and (fiber or 0) < 5:
            score -= 15
        if score < 100:
            note = "Lower glycemic-impact pick for your profile"

    if health_goal == "weight_loss":
        if calories is not None and calories > 600:
            score -= 20
            note = note or "Lighter option for your weight-loss goal"
        elif fiber is not None and fiber >= 8:
            score = min(100, score + 5)
    elif health_goal in ("muscle_gain", "general_fitness"):
        if protein is not None and protein >= 25:
            score = min(100, score + 10)
            note = note or "High-protein pick for your fitness goal"
        elif protein is not None and protein < 12:
            score -= 15

    # Nothing specific to flag, but a profile is active — give a generic
    # affirming note so the UI can still show the recipe was considered.
    if note is None and (health_conditions or health_goal != "maintenance"):
        note = "Matches your health profile"

    return max(0, min(100, score)), note


def _apply_health_profile(
    recipes: list[dict[str, Any]],
    health_conditions: list[str] | None,
    health_goal: str | None,
) -> list[dict[str, Any]]:
    """Attach healthMatchPercentage/healthNote to each recipe dict, in place."""
    health_conditions = health_conditions or []
    health_goal = health_goal or "maintenance"
    for recipe in recipes:
        score, note = _health_match(recipe, health_conditions, health_goal)
        recipe["healthMatchPercentage"] = score
        recipe["healthNote"] = note
    return recipes


def _to_api_recipe(recipe: RecipeModel, source: str = "supabase") -> dict[str, Any]:
    ingredients = [ingredient.model_dump() for ingredient in recipe.ingredients]
    cooking_steps = [step.model_dump() for step in recipe.cooking_steps]
    steps = [step["instruction"] for step in cooking_steps]
    ready_in_min = recipe.ready_in_min or 0
    return {
        "id": recipe.id,
        "title": recipe.title,
        "name": recipe.title,
        "cuisine": recipe.cuisine,
        "meal_type": recipe.meal_type,
        "mealType": recipe.meal_type,
        "diet": recipe.diet,
        "ready_in_min": ready_in_min,
        "readyInMin": ready_in_min,
        "prepTimeMinutes": ready_in_min,
        "servings": recipe.servings,
        "image_url": recipe.image_url,
        "imageUrl": recipe.image_url,
        "image": recipe.image_url,
        "description": recipe.description,
        "calories_kcal": recipe.calories_kcal,
        "caloriesKcal": recipe.calories_kcal,
        "protein_g": recipe.protein_g,
        "proteinG": recipe.protein_g,
        "carbs_g": recipe.carbs_g,
        "carbsG": recipe.carbs_g,
        "fat_g": recipe.fat_g,
        "fatG": recipe.fat_g,
        "fiber_g": recipe.fiber_g,
        "fiberG": recipe.fiber_g,
        "created_at": recipe.created_at,
        "ingredients": ingredients,
        "recipeIngredients": ingredients,
        "cooking_steps": cooking_steps,
        "cookingSteps": cooking_steps,
        "steps": steps,
        "matchPercentage": recipe.match_percentage,
        "match_percentage": recipe.match_percentage,
        "missingIngredients": recipe.missing_ingredients,
        "missing_ingredients": recipe.missing_ingredients,
        "usesExpiringItems": recipe.uses_expiring_items,
        "uses_expiring_items": recipe.uses_expiring_items,
        "source": source,
    }


def _normalise_ai_recipe(raw: dict[str, Any], pantry_names: set[str]) -> dict[str, Any]:
    """
    Normalise an AI-generated recipe into the shared API recipe shape and
    recompute ingredient matching against the actual pantry.
    """
    ingredients_in = raw.get("ingredients", []) or []
    match_pct, missing, enriched = _compute_match(ingredients_in, pantry_names)

    steps = [s for s in (raw.get("steps", []) or []) if s]
    recipe_id = str(raw.get("id") or _normalise_name(raw.get("name", "recipe")).replace(" ", "-") or "recipe")
    cooking_steps = [
        {
            "id": f"{recipe_id}-{idx + 1}",
            "recipe_id": recipe_id,
            "step_number": idx + 1,
            "instruction": step,
            "duration_min": None,
            "tip": None,
        }
        for idx, step in enumerate(steps)
    ]
    ready = raw.get("prepTimeMinutes") or 30

    return {
        "id": recipe_id,
        "title": raw.get("name", ""),
        "name": raw.get("name", ""),
        "cuisine": raw.get("cuisine"),
        "meal_type": None,
        "mealType": None,
        "diet": None,
        "difficulty": raw.get("difficulty"),
        "ready_in_min": ready,
        "readyInMin": ready,
        "prepTimeMinutes": ready,
        "servings": None,
        "image_url": None,
        "imageUrl": None,
        "image": None,
        "description": None,
        "caloriesKcal": raw.get("caloriesKcal"),
        "calories_kcal": raw.get("caloriesKcal"),
        "proteinG": raw.get("proteinG"),
        "protein_g": raw.get("proteinG"),
        "carbsG": raw.get("carbsG"),
        "carbs_g": raw.get("carbsG"),
        "fiberG": raw.get("fiberG"),
        "fiber_g": raw.get("fiberG"),
        "ingredients": enriched,
        "recipeIngredients": enriched,
        "cooking_steps": cooking_steps,
        "cookingSteps": cooking_steps,
        "steps": steps,
        "matchPercentage": match_pct,
        "match_percentage": match_pct,
        "missingIngredients": missing,
        "missing_ingredients": missing,
        "usesExpiringItems": bool(raw.get("usesExpiringItems", False)),
        "uses_expiring_items": bool(raw.get("usesExpiringItems", False)),
        "source": "claude",
    }


async def get_recipe_ingredients(recipe_id: str, pantry_names: set[str] | None = None) -> list[dict[str, Any]]:
    rows = await _supabase_get(
        "recipe_ingredients",
        {
            "select": "id,recipe_id,name,quantity,is_optional,sort_order",
            "recipe_id": f"eq.{recipe_id}",
            "order": "sort_order.asc,name.asc",
        },
    )
    pantry_names = pantry_names or set()
    return [
        {
            **row,
            "quantity": row.get("quantity") if row.get("quantity") is not None else "",
            "unit": "",
            "available": _normalise_name(row.get("name", "")) in pantry_names,
        }
        for row in rows
    ]


async def get_recipe_steps(recipe_id: str) -> list[dict[str, Any]]:
    return await _supabase_get(
        "recipe_steps",
        {
            "select": "id,recipe_id,step_number,instruction,duration_min,tip",
            "recipe_id": f"eq.{recipe_id}",
            "order": "step_number.asc",
        },
    )


async def get_recipe(recipe_id: str, pantry_items: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    rows = await _supabase_get(
        "recipes",
        {
            "select": "id,title,cuisine,meal_type,diet,ready_in_min,servings,image_url,description,calories_kcal,protein_g,carbs_g,fat_g,fiber_g,created_at",
            "id": f"eq.{recipe_id}",
            "limit": 1,
        },
    )
    if not rows:
        return None

    pantry_items = pantry_items or []
    names = _pantry_names(pantry_items)
    ingredient_rows = await get_recipe_ingredients(recipe_id, names)
    step_rows = await get_recipe_steps(recipe_id)
    match_pct, missing, enriched_ingredients = _compute_match(ingredient_rows, names)
    recipe = RecipeModel(
        **rows[0],
        ingredients=enriched_ingredients,
        cooking_steps=step_rows,
        match_percentage=match_pct,
        missing_ingredients=missing,
        uses_expiring_items=_uses_expiring({"ingredients": enriched_ingredients}, pantry_items),
    )
    return _to_api_recipe(recipe)


async def search_recipes(
    filters: dict[str, Any] | None = None,
    pantry_items: list[dict[str, Any]] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    filters = filters or {}
    params: dict[str, Any] = {
        "select": "id,title,cuisine,meal_type,diet,ready_in_min,servings,image_url,description,calories_kcal,protein_g,carbs_g,fat_g,fiber_g,created_at",
        "order": "ready_in_min.asc,title.asc",
        "limit": limit,
    }

    cuisine = filters.get("cuisine")
    if cuisine and cuisine != "any":
        cuisine_value = str(cuisine).strip()
        if cuisine_value.lower() == "indian":
            params["cuisine"] = 'in.("South Indian","North Indian","Pan Indian")'
        else:
            params["cuisine"] = f"eq.{cuisine_value}"
    meal_type = filters.get("meal_type")
    if meal_type and meal_type != "any":
        params["meal_type"] = f"ilike.{meal_type}"
    diet = filters.get("diet")
    if diet and diet != "any":
        params["diet"] = f"ilike.{diet}"
    max_ready_time = filters.get("max_ready_time")
    if max_ready_time:
        params["ready_in_min"] = f"lte.{int(max_ready_time)}"
    query = filters.get("query")
    if query:
        params["title"] = f"ilike.*{query}*"

    rows = await _supabase_get("recipes", params)
    pantry_items = pantry_items or []
    names = _pantry_names(pantry_items)
    recipes: list[dict[str, Any]] = []
    for row in rows:
        recipe_id = row["id"]
        ingredients = await get_recipe_ingredients(recipe_id, names)
        steps = await get_recipe_steps(recipe_id)
        match_pct, missing, enriched_ingredients = _compute_match(ingredients, names)
        recipe = RecipeModel(
            **row,
            ingredients=enriched_ingredients,
            cooking_steps=steps,
            match_percentage=match_pct,
            missing_ingredients=missing,
            uses_expiring_items=_uses_expiring({"ingredients": enriched_ingredients}, pantry_items),
        )
        recipes.append(_to_api_recipe(recipe))

    return recipes


def _reset_provider_status():
    """Reset provider failure flags (for testing/recovery)."""
    global _spoonacular_failed
    _spoonacular_failed = False


async def get_recipes(
    pantry_items: list[dict],
    prioritize_expiring: bool = True,
    max_recipes: int = 5,
    cuisine: str = "any",
    meal_type: str | None = None,
    diet: str | None = None,
    max_ready_time: int | None = None,
    health_conditions: list[str] | None = None,
    health_goal: str | None = None,
) -> dict:
    """
    Wrapper function for use in FastAPI routes.

    Coordinates recipe generation across all services using the 3-tier failover.

    Args:
        pantry_items: List of pantry items (already enriched with expiry flags)
        prioritize_expiring: Whether to prioritize recipes using expiring items
        max_recipes: Maximum number of recipes to return
        cuisine: Cuisine filter hint (best-effort)
        health_conditions: Onboarding health conditions (e.g. ["diabetes"]) — used
            to softly re-rank recipes via healthMatchPercentage, not to filter them.
        health_goal: Onboarding fitness goal (weight_loss/muscle_gain/general_fitness/maintenance)

    Returns:
        Dict with success, recipes, provider, message
    """
    pantry_names = {item.get("name", "").lower().strip() for item in pantry_items}
    pantry_names_norm = _pantry_names(pantry_items)
    cuisine_value = (cuisine or "any").strip()
    filters = {
        "cuisine": cuisine_value if cuisine_value != "any" else None,
        "meal_type": meal_type,
        "diet": diet,
        "max_ready_time": max_ready_time,
    }

    recipes: list[dict] | None = None
    provider = "supabase"

    # DEMO: guarantee these exact seeded recipes surface when their signature
    # ingredient is scanned, rather than leaving it to (nondeterministic) AI
    # generation. Only applies to the default "any cuisine" flow.
    demo_recipes: list[dict] = []
    if cuisine_value.lower() == "any":
        for trigger, title in _DEMO_TRIGGER_RECIPES.items():
            if any(trigger in name for name in pantry_names):
                try:
                    match = await search_recipes({"query": title}, pantry_items, 1)
                except Exception as exc:
                    logger.warning("Demo trigger recipe lookup failed for %r: %s", title, exc)
                    match = []
                if match:
                    demo_recipes.append(match[0])

    if cuisine_value.lower() in {"italian", "mexican"}:
        recipes = await _try_spoonacular(
            pantry_items,
            pantry_names,
            prioritize_expiring,
            max_recipes,
            cuisine_value,
        )
        provider = "spoonacular"
    elif cuisine_value.lower() == "any":
        # "What can I cook" — generate recipes that actually use the pantry
        # items via the AI model, then recompute matches against the pantry.
        # Capped at 3 diverse recipes (keeps latency down and results varied).
        ai_count = min(max_recipes, 3)
        remaining = max(0, ai_count - len(demo_recipes))
        try:
            ai_recipes = (
                await claude_client.get_recipe_recommendations(
                    pantry_items=pantry_items,
                    prioritize_expiring=prioritize_expiring,
                    max_recipes=remaining,
                    cuisine=cuisine_value,
                    health_conditions=health_conditions,
                    health_goal=health_goal,
                )
                if remaining
                else []
            )
            recipes = [_normalise_ai_recipe(r, pantry_names_norm) for r in (ai_recipes or [])]
            provider = "claude"
        except Exception as exc:
            logger.error("AI recipe generation failed: %s", exc)
            recipes = []
        # Fall back to the Supabase catalogue if the AI produced nothing.
        if not recipes and not demo_recipes:
            try:
                recipes = await search_recipes(filters, pantry_items, max_recipes)
                provider = "supabase"
            except Exception as exc:
                logger.error("Supabase recipe lookup failed: %s", exc)
                recipes = []
    else:
        try:
            recipes = await search_recipes(filters, pantry_items, max_recipes)
        except Exception as exc:
            logger.error("Supabase recipe lookup failed: %s", exc)
            recipes = []
    
    if not recipes:
        if cuisine_value.lower() not in {"italian", "mexican"}:
            recipes = get_planner_recipes(
                cuisine=cuisine_value,
                meal_type=meal_type,
                diet=diet,
                max_ready_time=max_ready_time,
                limit=max_recipes,
            )

    # DEMO: merge in the trigger recipes (deduped by title) before scoring,
    # so they get the same expiring/health-match treatment as everything else.
    if demo_recipes:
        demo_titles = {r["title"] for r in demo_recipes}
        recipes = demo_recipes + [r for r in (recipes or []) if r.get("title") not in demo_titles]
        provider = "supabase"

    if not recipes:
        return {
            "success": False,
            "recipes": [],
            "provider": provider,
            "message": "Could not generate recipes with your current pantry.",
        }

    # Mark expiring and sort
    recipes = _mark_expiring(recipes, pantry_items)
    recipes = _apply_health_profile(recipes, health_conditions, health_goal)

    # DEMO: pin trigger recipes back to the front — matchPercentage sorting
    # above shouldn't be able to bury a guaranteed demo recipe. Stable sort
    # preserves the existing order otherwise.
    if demo_recipes:
        demo_titles = {r["title"] for r in demo_recipes}
        recipes.sort(key=lambda r: r.get("title") not in demo_titles)

    return {
        "success": True,
        "recipes": recipes[:max_recipes],
        "provider": provider,
        "message": f"Found {len(recipes)} recipe(s) for your pantry.",
    }


def get_provider_status() -> dict:
    """Get current provider status."""
    active = "supabase+spoonacular" if not _spoonacular_failed else "supabase"
    return {
        "active": active,
        "supabase": "ok",
        "spoonacular": "failed" if _spoonacular_failed else "ok",
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
    nutrients = {
        nutrient.get("name", "").lower(): nutrient.get("amount")
        for nutrient in raw.get("nutrition", {}).get("nutrients", [])
    }
    steps = [
        {
            "id": f"{raw.get('id', '')}-{s.get('number', index + 1)}",
            "recipe_id": str(raw.get("id", "")),
            "step_number": s.get("number", index + 1),
            "instruction": s.get("step", ""),
            "duration_min": None,
            "tip": None,
        }
        for inst in raw.get("analyzedInstructions", [])
        for index, s in enumerate(inst.get("steps", []))
    ]
    dish_types = raw.get("dishTypes") or []
    return {
        "id": str(raw.get("id", "")),
        "title": raw.get("title", ""),
        "name": raw.get("title", ""),
        "cuisine": (raw.get("cuisines") or [""])[0],
        "meal_type": dish_types[0] if dish_types else None,
        "mealType": dish_types[0] if dish_types else None,
        "diet": (raw.get("diets") or [None])[0],
        "ready_in_min": raw.get("readyInMinutes", 30),
        "readyInMin": raw.get("readyInMinutes", 30),
        "prepTimeMinutes": raw.get("readyInMinutes", 30),
        "servings": raw.get("servings", 2),
        "image_url": raw.get("image", ""),
        "imageUrl": raw.get("image", ""),
        "image": raw.get("image", ""),
        "description": raw.get("summary", ""),
        "calories_kcal": nutrients.get("calories"),
        "caloriesKcal": nutrients.get("calories"),
        "protein_g": nutrients.get("protein"),
        "proteinG": nutrients.get("protein"),
        "carbs_g": nutrients.get("carbohydrates"),
        "carbsG": nutrients.get("carbohydrates"),
        "fat_g": nutrients.get("fat"),
        "fatG": nutrients.get("fat"),
        "fiber_g": nutrients.get("fiber"),
        "fiberG": nutrients.get("fiber"),
        "matchPercentage": match_pct,
        "usesExpiringItems": False,
        "ingredients": ingredients,
        "recipeIngredients": ingredients,
        "missingIngredients": [i["name"] for i in ingredients if not i["available"]],
        "cooking_steps": steps,
        "cookingSteps": steps,
        "steps": [step["instruction"] for step in steps],
        "source": "spoonacular",
    }


async def _try_spoonacular(
    pantry_items: list[dict],
    pantry_names: set,
    prioritize_expiring: bool,
    max_recipes: int,
    cuisine: str,
) -> list[dict] | None:
    global _spoonacular_failed
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        _spoonacular_failed = True
        return None

    ingredients_csv = ",".join(i["name"] for i in pantry_items[:10])
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": api_key,
        "includeIngredients": ingredients_csv,
        "cuisine": cuisine,
        "number": max_recipes,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "instructionsRequired": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 402:
                logger.warning("Spoonacular quota exhausted")
                _spoonacular_failed = True
                return None
            resp.raise_for_status()
            recipes_raw = resp.json().get("results", [])
            results = [_normalise_spoonacular(recipe, pantry_names) for recipe in recipes_raw[:max_recipes]]
            return results if results else None
    except Exception as e:
        logger.warning("Spoonacular error: %s", e)
        _spoonacular_failed = True
        return None


async def search_continental_recipe(query: str, pantry_items: list[dict] | None = None) -> dict[str, Any] | None:
    """Search Spoonacular for one Italian/Mexican recipe by title."""
    global _spoonacular_failed
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        _spoonacular_failed = True
        return None

    pantry_names = _pantry_names(pantry_items or [])
    params = {
        "apiKey": api_key,
        "query": query,
        "cuisine": "Italian,Mexican",
        "number": 1,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "instructionsRequired": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.spoonacular.com/recipes/complexSearch",
                params=params,
            )
            if response.status_code == 402:
                _spoonacular_failed = True
                return None
            response.raise_for_status()
            results = response.json().get("results", [])
            return _normalise_spoonacular(results[0], pantry_names) if results else None
    except Exception as exc:
        logger.warning("Spoonacular title search failed: %s", exc)
        _spoonacular_failed = True
        return None


async def get_continental_recipe(recipe_id: str, pantry_items: list[dict] | None = None) -> dict[str, Any] | None:
    """Load full Spoonacular details for one continental recipe id."""
    global _spoonacular_failed
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        _spoonacular_failed = True
        return None

    pantry_names = _pantry_names(pantry_items or [])
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.spoonacular.com/recipes/{recipe_id}/information",
                params={"apiKey": api_key, "includeNutrition": True},
            )
            if response.status_code == 404:
                return None
            if response.status_code == 402:
                _spoonacular_failed = True
                return None
            response.raise_for_status()
            recipe = _normalise_spoonacular(response.json(), pantry_names)
            cuisine = (recipe.get("cuisine") or "").lower()
            return recipe if cuisine in {"italian", "mexican"} else None
    except Exception as exc:
        logger.warning("Spoonacular recipe detail failed: %s", exc)
        _spoonacular_failed = True
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
