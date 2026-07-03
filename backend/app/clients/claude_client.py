"""
AI client for Vision (image scanning) and Text (recipes, substitutions).

Uses the OpenAI SDK against an Azure AI Foundry (OpenAI-compatible) endpoint.
All functions are async and use AsyncOpenAI to avoid blocking the event loop.

NOTE: the module is still named ``claude_client`` for backwards compatibility
with existing imports across the codebase; it no longer uses Anthropic/Claude.
"""

import base64
import json
import re

from app.clients.ai_config import get_async_client, get_model, completion_kwargs


def _encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def _parse_json_response(text: str) -> dict | list:
    """Strip markdown fences and parse JSON from the model's response."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned.strip())


async def extract_ingredients(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    """
    Send image to Claude Vision and extract ingredients.

    Returns a list of dicts:
        [{ name, quantity, unit, acquisition_date, expiration_date, confidence }]
    """
    client = get_async_client()
    b64 = _encode_image(image_bytes)

    from datetime import date, timedelta
    today = date.today().isoformat()
    default_expiry = (date.today() + timedelta(days=7)).isoformat()

    prompt = f"""You are a kitchen AI assistant. Analyze this image and extract all visible food ingredients.

Return ONLY a JSON array (no explanation, no markdown fences) where each element has:
- "name": ingredient name (string, lowercase)
- "quantity": numeric amount (number, default 1)
- "unit": unit of measure like "pcs", "g", "ml", "kg", "l", "bunch", "pack" (string)
- "acquisition_date": today's date "{today}" (string, ISO 8601)
- "expiration_date": estimated expiry date (string, ISO 8601) — use fresh produce norms
- "confidence": confidence 0.0–1.0 (number)

If the image is a receipt, extract purchased items instead.
If nothing is identifiable, return an empty array [].

Example:
[
  {{"name": "tomato", "quantity": 4, "unit": "pcs", "acquisition_date": "{today}", "expiration_date": "{default_expiry}", "confidence": 0.95}}
]"""

    response = await client.chat.completions.create(
        model=get_model(),
        max_completion_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            }
        ],
        **completion_kwargs(),
    )

    raw = response.choices[0].message.content
    result = _parse_json_response(raw)
    return result if isinstance(result, list) else []


async def get_recipe_recommendations(
    pantry_items: list[dict],
    prioritize_expiring: bool = True,
    max_recipes: int = 5,
    cuisine: str = "any",
) -> list[dict]:
    """
    Ask Claude to generate meal recommendations from pantry contents.

    Returns a list of recipe dicts matching the frontend Recipe type.
    pantry_items are expected to have camelCase keys (isExpiring, isExpired)
    as produced by _attach_expiry_flags().
    """
    client = get_async_client()

    # Items have camelCase keys from _attach_expiry_flags
    expiring = [i for i in pantry_items if i.get("isExpiring") or i.get("isExpired")]
    expiring_names = [i["name"] for i in expiring]

    pantry_text = "\n".join(
        f"- {item['name']}: {item['quantity']} {item['unit']}"
        + (" [EXPIRING SOON]" if item.get("isExpiring") or item.get("isExpired") else "")
        for item in pantry_items
    )

    priority_note = (
        "IMPORTANT: Prioritize recipes that use expiring items: "
        + ", ".join(expiring_names)
        if prioritize_expiring and expiring_names
        else ""
    )

    cuisine_note = (
        f"CUISINE FILTER: Only suggest {cuisine} cuisine recipes."
        if cuisine and cuisine.lower() != "any"
        else ""
    )

    prompt = f"""You are RasOI, a kitchen AI. Given this pantry, suggest {max_recipes} meal recipes.
{priority_note}
{cuisine_note}

Pantry:
{pantry_text}

Return ONLY a JSON array (no markdown, no explanation). Each recipe:
{{
  "id": "unique-slug-string",
  "name": "Recipe Name",
  "cuisine": "Indian|Italian|Mexican|etc",
  "difficulty": "Easy|Medium|Hard",
  "prepTimeMinutes": 30,
  "matchPercentage": 85,
  "usesExpiringItems": true,
  "ingredients": [
    {{"name": "tomato", "quantity": 2, "unit": "pcs", "available": true}}
  ],
  "missingIngredients": ["cream"],
  "steps": [
    "Heat oil in a pan.",
    "Add onions and sauté for 3 minutes."
  ]
}}

Rules:
- matchPercentage: % of recipe ingredients available in pantry (0-100)
- usesExpiringItems: true if at least one expiring item is used
- steps: 4-7 clear cooking steps
- Sort by matchPercentage descending (expiring-using recipes first if prioritize_expiring)
"""

    response = await client.chat.completions.create(
        model=get_model(),
        max_completion_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
        **completion_kwargs(),
    )

    raw = response.choices[0].message.content
    result = _parse_json_response(raw)
    return result if isinstance(result, list) else []


async def get_substitutions(
    missing_ingredient: str,
    recipe_name: str,
    pantry_items: list[dict],
) -> list[dict]:
    """
    Ask Claude to suggest pantry-available substitutes for a missing ingredient.

    Returns list of { ingredient, ratio, notes, available }.
    """
    client = get_async_client()

    pantry_names = [i["name"] for i in pantry_items]

    prompt = f"""You are a kitchen AI. The recipe "{recipe_name}" needs "{missing_ingredient}" but it's not available.

Available pantry items: {", ".join(pantry_names) if pantry_names else "none"}

Suggest 1-3 substitutes. Return ONLY a JSON array:
[
  {{
    "ingredient": "substitute name",
    "ratio": "use X amount of substitute per Y of original",
    "notes": "brief explanation of taste/texture difference",
    "available": true
  }}
]

Prefer substitutes available in the pantry (available: true). If none fit, suggest common pantry staples (available: false).
"""

    response = await client.chat.completions.create(
        model=get_model(),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        **completion_kwargs(),
    )

    raw = response.choices[0].message.content
    result = _parse_json_response(raw)
    return result if isinstance(result, list) else []
