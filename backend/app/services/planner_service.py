"""Weekly meal planner, household, cuisine profile, and grocery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Nutrition:
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    fiber_g: int


CUISINE_PROFILES: dict[str, dict[str, Any]] = {
    "belgian": {
        "id": "belgian",
        "name": "Belgian",
        "staples": ["potato", "leek", "belgian endive", "mustard", "butter"],
        "flavor_notes": ["hearty", "buttery", "comforting"],
        "preferred_meals": ["Stoofvlees met Frites", "Witloof Gratin", "Erwtensoep"],
    },
    "mediterranean": {
        "id": "mediterranean",
        "name": "Mediterranean",
        "staples": ["olive oil", "tomato", "chickpeas", "feta", "lemon"],
        "flavor_notes": ["bright", "herby", "olive-oil-forward"],
        "preferred_meals": ["Greek Chickpea Salad Bowl", "Mediterranean Veg Couscous", "Tomato Feta Orzo"],
    },
    "asian": {
        "id": "asian",
        "name": "Asian",
        "staples": ["rice", "soy sauce", "ginger", "noodles", "sesame oil"],
        "flavor_notes": ["umami", "aromatic", "wok-fried"],
        "preferred_meals": ["Vegetable Fried Rice", "Ginger Soy Noodle Bowl", "Sesame Tofu Stir-fry"],
    },
}


MEAL_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Stoofvlees met Frites",
        "profile": "belgian",
        "ingredients": ["beef", "onion", "belgian beer", "potato", "bay leaf"],
        "nutrition": Nutrition(650, 32, 62, 26, 6),
    },
    {
        "name": "Witloof Gratin",
        "profile": "belgian",
        "ingredients": ["belgian endive", "ham", "cheese sauce", "potato"],
        "nutrition": Nutrition(480, 22, 34, 28, 7),
    },
    {
        "name": "Greek Chickpea Salad Bowl",
        "profile": "mediterranean",
        "ingredients": ["chickpeas", "tomato", "feta", "cucumber", "olive oil"],
        "nutrition": Nutrition(460, 17, 48, 20, 12),
    },
    {
        "name": "Mediterranean Veg Couscous",
        "profile": "mediterranean",
        "ingredients": ["couscous", "zucchini", "tomato", "olive oil", "lemon"],
        "nutrition": Nutrition(500, 14, 78, 13, 9),
    },
    {
        "name": "Vegetable Fried Rice",
        "profile": "asian",
        "ingredients": ["rice", "carrot", "peas", "soy sauce", "egg"],
        "nutrition": Nutrition(540, 16, 82, 15, 6),
    },
    {
        "name": "Ginger Soy Noodle Bowl",
        "profile": "asian",
        "ingredients": ["noodles", "ginger", "soy sauce", "spring onion", "sesame oil"],
        "nutrition": Nutrition(510, 15, 76, 14, 5),
    },
]


DEFAULT_HOUSEHOLD = {
    "id": "5d6b4c66-945a-414e-92e4-8fe99ca89e6a",
    "name": "Captain Cook",
    "email": "captaincook@foodbuddy.app",
    "cuisinePref": ["Belgian", "Mediterranean"],
    "dietaryRestrictions": [],
    "members": [
        {"id": "5d6b4c66-945a-414e-92e4-8fe99ca89e6a", "name": "Captain Cook", "dietaryPreferences": [], "servings": 2},
        {"id": "member-2", "name": "Demo family member", "dietaryPreferences": [], "servings": 1},
    ],
    "defaultServings": 2,
}


def get_cuisine_profiles() -> list[dict[str, Any]]:
    return list(CUISINE_PROFILES.values())


def get_household_profile() -> dict[str, Any]:
    return DEFAULT_HOUSEHOLD


def get_delivery_partners(query_items: list[str] | None = None) -> list[dict[str, str]]:
    query = quote_plus(", ".join(query_items or ["groceries"]))
    return [
        {
            "id": "collectandgo",
            "name": "Collect&Go",
            "status": "deep_link_ready",
            "cartUrl": f"https://www.collectandgo.be/nl/search?text={query}",
        },
    ]


def get_planner_recipe_by_name(meal_name: str) -> dict[str, Any] | None:
    """Return a lightweight recipe detail for planner template meals."""
    requested = _normalise_lookup(meal_name)
    meal = next(
        (
            template
            for template in MEAL_TEMPLATES
            if _normalise_lookup(template["name"]) == requested
            or requested in _normalise_lookup(template["name"])
            or _normalise_lookup(template["name"]) in requested
        ),
        None,
    )
    if not meal:
        return None

    profile = CUISINE_PROFILES.get(meal["profile"], CUISINE_PROFILES["belgian"])
    ingredients = [
        {
            "id": f"planner-{meal['name'].lower().replace(' ', '-')}-{index}",
            "recipe_id": f"planner-{meal['name'].lower().replace(' ', '-')}",
            "name": ingredient,
            "quantity": "as needed",
            "unit": "",
            "is_optional": False,
            "sort_order": index,
            "available": False,
        }
        for index, ingredient in enumerate(meal["ingredients"], start=1)
    ]
    steps = [
        {
            "id": f"planner-{meal['name'].lower().replace(' ', '-')}-step-1",
            "recipe_id": f"planner-{meal['name'].lower().replace(' ', '-')}",
            "step_number": 1,
            "instruction": "Prep and measure all listed ingredients.",
            "duration_min": 5,
            "tip": "Keep pantry ingredients separate from items you need to buy.",
        },
        {
            "id": f"planner-{meal['name'].lower().replace(' ', '-')}-step-2",
            "recipe_id": f"planner-{meal['name'].lower().replace(' ', '-')}",
            "step_number": 2,
            "instruction": "Cook the base ingredients until tender, then season to match the selected regional profile.",
            "duration_min": 20,
            "tip": f"{profile['name']} meals lean {', '.join(profile['flavor_notes'][:2])}.",
        },
        {
            "id": f"planner-{meal['name'].lower().replace(' ', '-')}-step-3",
            "recipe_id": f"planner-{meal['name'].lower().replace(' ', '-')}",
            "step_number": 3,
            "instruction": "Finish with fresh garnish and serve hot.",
            "duration_min": 5,
            "tip": "Adjust salt, acid, and spice at the end.",
        },
    ]
    nutrition = meal["nutrition"]
    return {
        "id": f"planner-{meal['name'].lower().replace(' ', '-')}",
        "title": meal["name"],
        "name": meal["name"],
        "cuisine": profile["name"],
        "meal_type": "Lunch",
        "mealType": "Lunch",
        "diet": "vegetarian",
        "ready_in_min": 30,
        "readyInMin": 30,
        "prepTimeMinutes": 30,
        "servings": 2,
        "image_url": None,
        "imageUrl": None,
        "image": None,
        "description": f"A planner-generated {profile['name']} meal built around {', '.join(meal['ingredients'][:3])}.",
        "calories_kcal": nutrition.calories,
        "caloriesKcal": nutrition.calories,
        "protein_g": nutrition.protein_g,
        "proteinG": nutrition.protein_g,
        "carbs_g": nutrition.carbs_g,
        "carbsG": nutrition.carbs_g,
        "fat_g": nutrition.fat_g,
        "fatG": nutrition.fat_g,
        "fiber_g": nutrition.fiber_g,
        "fiberG": nutrition.fiber_g,
        "ingredients": ingredients,
        "recipeIngredients": ingredients,
        "cooking_steps": steps,
        "cookingSteps": steps,
        "steps": [step["instruction"] for step in steps],
        "matchPercentage": 0,
        "missingIngredients": meal["ingredients"],
        "usesExpiringItems": False,
        "source": "planner",
    }


def get_planner_recipes(
    cuisine: str | None = None,
    meal_type: str | None = None,
    diet: str | None = None,
    max_ready_time: int | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Return lightweight planner recipes for catalogue fallback views."""
    recipes = [get_planner_recipe_by_name(meal["name"]) for meal in MEAL_TEMPLATES]
    filtered = [recipe for recipe in recipes if recipe]

    cuisine_value = _normalise_lookup(cuisine or "any")
    if cuisine_value and cuisine_value != "any":
        filtered = [recipe for recipe in filtered if _normalise_lookup(recipe.get("cuisine", "")) == cuisine_value]

    meal_type_value = _normalise_lookup(meal_type or "any")
    if meal_type_value and meal_type_value != "any":
        filtered = [recipe for recipe in filtered if _normalise_lookup(recipe.get("mealType", "")) == meal_type_value]

    diet_value = _normalise_lookup(diet or "any")
    if diet_value and diet_value != "any":
        filtered = [recipe for recipe in filtered if _normalise_lookup(recipe.get("diet", "")) == diet_value]

    if max_ready_time:
        filtered = [recipe for recipe in filtered if int(recipe.get("prepTimeMinutes") or 0) <= max_ready_time]

    return filtered[:limit]


def build_weekly_plan(
    pantry_items: list[dict[str, Any]],
    region: str = "belgian",
    household_size: int = 2,
    days: int = 7,
) -> dict[str, Any]:
    days = max(1, min(days, 14))
    household_size = max(1, min(household_size, 12))
    profile = CUISINE_PROFILES.get(region, CUISINE_PROFILES["belgian"])
    pantry_names = {_item_name(item) for item in pantry_items if _item_name(item)}
    preferred = [meal for meal in MEAL_TEMPLATES if meal["profile"] == profile["id"]]
    fallback = [meal for meal in MEAL_TEMPLATES if meal not in preferred]
    rotation = preferred + fallback
    start = date.today()
    plan_days = []
    grocery_counts: dict[str, int] = {}
    totals = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0}

    for index in range(days):
        meal = rotation[index % len(rotation)]
        missing = [ingredient for ingredient in meal["ingredients"] if ingredient.lower() not in pantry_names]
        for ingredient in missing:
            grocery_counts[ingredient] = grocery_counts.get(ingredient, 0) + household_size

        nutrition = _scale_nutrition(meal["nutrition"], household_size)
        for key, value in nutrition.items():
            totals[key] += value

        plan_days.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "mealName": meal["name"],
                "region": profile["name"],
                "servings": household_size,
                "usesPantryItems": [ingredient for ingredient in meal["ingredients"] if ingredient.lower() in pantry_names],
                "missingIngredients": missing,
                "nutrition": nutrition,
            }
        )

    grocery_items = [
        {"name": name, "quantity": quantity, "unit": "servings"}
        for name, quantity in sorted(grocery_counts.items())
    ]

    return {
        "profile": profile,
        "household": {**DEFAULT_HOUSEHOLD, "defaultServings": household_size},
        "days": plan_days,
        "nutritionalSummary": {
            "dailyAverage": {key: round(value / days) for key, value in totals.items()},
            "weeklyTotal": totals,
        },
        "groceryList": grocery_items,
        "deliveryPartners": get_delivery_partners([item["name"] for item in grocery_items]),
    }


def _item_name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("ingredient") or "").lower().strip()


def _normalise_lookup(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _scale_nutrition(nutrition: Nutrition, servings: int) -> dict[str, int]:
    return {
        "calories": nutrition.calories * servings,
        "protein_g": nutrition.protein_g * servings,
        "carbs_g": nutrition.carbs_g * servings,
        "fat_g": nutrition.fat_g * servings,
        "fiber_g": nutrition.fiber_g * servings,
    }