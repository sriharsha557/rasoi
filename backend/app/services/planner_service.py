"""Weekly meal planner, household, cuisine profile, and grocery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
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
    "south_indian": {
        "id": "south_indian",
        "name": "South Indian",
        "staples": ["rice", "dal", "coconut", "curry leaves", "tamarind"],
        "flavor_notes": ["tangy", "tempered spices", "rice-forward"],
        "preferred_meals": ["Sambar Rice Bowl", "Vegetable Uttapam", "Lemon Rice with Curd"],
    },
    "bengali": {
        "id": "bengali",
        "name": "Bengali",
        "staples": ["rice", "mustard oil", "potato", "fish", "panch phoron"],
        "flavor_notes": ["mustard", "subtle heat", "sweet-savoury balance"],
        "preferred_meals": ["Aloo Posto Plate", "Mustard Veg Rice", "Moong Dal Khichuri"],
    },
    "punjabi": {
        "id": "punjabi",
        "name": "Punjabi",
        "staples": ["wheat", "paneer", "chickpeas", "yogurt", "ghee"],
        "flavor_notes": ["rich", "warming spices", "protein-forward"],
        "preferred_meals": ["Chole Roti Bowl", "Paneer Bhurji Wrap", "Rajma Rice"],
    },
}


MEAL_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Sambar Rice Bowl",
        "profile": "south_indian",
        "ingredients": ["rice", "dal", "carrot", "tomato", "tamarind"],
        "nutrition": Nutrition(520, 18, 84, 12, 11),
    },
    {
        "name": "Vegetable Uttapam",
        "profile": "south_indian",
        "ingredients": ["rice", "urad dal", "onion", "tomato", "curd"],
        "nutrition": Nutrition(430, 15, 70, 10, 7),
    },
    {
        "name": "Aloo Posto Plate",
        "profile": "bengali",
        "ingredients": ["potato", "poppy seeds", "rice", "mustard oil"],
        "nutrition": Nutrition(480, 10, 78, 15, 8),
    },
    {
        "name": "Moong Dal Khichuri",
        "profile": "bengali",
        "ingredients": ["rice", "moong dal", "potato", "cauliflower", "ghee"],
        "nutrition": Nutrition(500, 17, 82, 11, 10),
    },
    {
        "name": "Chole Roti Bowl",
        "profile": "punjabi",
        "ingredients": ["chickpeas", "wheat flour", "onion", "tomato", "yogurt"],
        "nutrition": Nutrition(610, 24, 88, 18, 15),
    },
    {
        "name": "Paneer Bhurji Wrap",
        "profile": "punjabi",
        "ingredients": ["paneer", "wheat flour", "onion", "capsicum", "tomato"],
        "nutrition": Nutrition(560, 26, 58, 25, 8),
    },
]


DEFAULT_HOUSEHOLD = {
    "id": "home",
    "name": "My Household",
    "members": [
        {"id": "member-1", "name": "Primary cook", "dietaryPreferences": ["vegetarian"], "servings": 1},
        {"id": "member-2", "name": "Family member", "dietaryPreferences": [], "servings": 1},
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
            "id": "blinkit",
            "name": "Blinkit",
            "status": "deep_link_ready",
            "cartUrl": f"https://blinkit.com/s/?q={query}",
        },
        {
            "id": "zepto",
            "name": "Zepto",
            "status": "deep_link_ready",
            "cartUrl": f"https://www.zeptonow.com/search?query={query}",
        },
    ]


def build_weekly_plan(
    pantry_items: list[dict[str, Any]],
    region: str = "south_indian",
    household_size: int = 2,
    days: int = 7,
) -> dict[str, Any]:
    days = max(1, min(days, 14))
    household_size = max(1, min(household_size, 12))
    profile = CUISINE_PROFILES.get(region, CUISINE_PROFILES["south_indian"])
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


def _scale_nutrition(nutrition: Nutrition, servings: int) -> dict[str, int]:
    return {
        "calories": nutrition.calories * servings,
        "protein_g": nutrition.protein_g * servings,
        "carbs_g": nutrition.carbs_g * servings,
        "fat_g": nutrition.fat_g * servings,
        "fiber_g": nutrition.fiber_g * servings,
    }