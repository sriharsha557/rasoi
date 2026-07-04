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


RECEIPT_ITEMS_PROMPT = """Extract all line items from this grocery receipt. For each item return:
raw_name, normalized_name, brand (if visible), quantity, unit, unit_price,
total_price, category (Dairy/Vegetable/Spice/Grains/Oils/Lentils/Other).
Return only valid JSON array, no markdown."""


async def extract_receipt_items(
    image_bytes: bytes, media_type: str = "image/jpeg"
) -> tuple[list[dict], str]:
    """
    Send a grocery receipt image to the vision model and extract line items.

    Returns (items, raw_text):
        items    — list of dicts: raw_name, normalized_name, brand, quantity, unit,
                   unit_price, total_price, category
        raw_text — the model's raw response text, kept for receipt_scans.raw_ocr_text
    """
    client = get_async_client()
    b64 = _encode_image(image_bytes)

    response = await client.chat.completions.create(
        model=get_model(),
        max_completion_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": RECEIPT_ITEMS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            }
        ],
        **completion_kwargs(),
    )

    raw_text = response.choices[0].message.content
    result = _parse_json_response(raw_text)
    items = result if isinstance(result, list) else []
    return items, raw_text


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
        f"- {item['name']}: {item.get('quantity', '')} {item.get('unit', '')}".rstrip()
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

    prompt = f"""You are Food Buddy, a kitchen AI. Given this pantry, suggest {max_recipes} meal recipes.
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
- DIVERSITY: make the {max_recipes} recipes genuinely different from each other —
  vary the cuisine, meal type, and cooking method, and collectively use a wide
  range of the available pantry ingredients instead of repeating the same core
  items in every recipe.
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
    quantity: str = "not specified",
    usage_context: str = "not specified",
    recipe_ingredients: list[str] | None = None,
) -> dict:
    """
    Decide whether a missing ingredient has a genuine functional substitute, or
    whether the user should be prompted to purchase it instead.

    Returns a dict:
        {
          "core_function": str,
          "has_substitutions": bool,
          "substitutions": [ {ingredient, ratio, notes, available} ],
          "recommend_purchase": bool,
          "purchase_reason": str,
        }

    `substitutions` are mapped from the model's {name, ratio, benefit, limitation}
    so downstream code (guardrails, frontend) keeps the {ingredient, ratio, notes,
    available} shape. `available` is true when the substitute is already in the
    pantry. `recommend_purchase` and `has_substitutions` are mutually exclusive.
    """
    client = get_async_client()

    pantry_names = [i.get("name", "") for i in pantry_items]
    pantry_list = ", ".join(n for n in pantry_names if n) or "none"
    ingredient_list = ", ".join(recipe_ingredients) if recipe_ingredients else "not specified"

    prompt = f"""You are a culinary substitution assistant. Given a missing ingredient and
its role in a recipe, decide whether it has a genuine functional substitute
available from a typical pantry, OR whether the user should be prompted to
purchase/order the ingredient instead.

Recipe: {recipe_name}
Missing ingredient: {missing_ingredient}
Quantity needed: {quantity}
How it's used in this recipe: {usage_context}
Other ingredients in the recipe: {ingredient_list}
User's available pantry items: {pantry_list}

Decision process:
1. Identify the CORE FUNCTION the missing ingredient serves in this recipe
   (e.g. aromatic base, heat/spice, acidity, binding, bulk/texture,
   sweetness, umami).
2. Check if any realistic pantry substitute can replicate that SAME core
   function closely enough that the dish still works as intended.
3. Ingredients with a narrow, hard-to-replace role (e.g. onion's aromatic
   savory base, garlic's pungency, a specific spice's flavor signature)
   usually do NOT have a good substitute — do not force one just because
   two things are both vegetables or both spicy.
4. Ingredients with a more flexible/replaceable role (e.g. one chili
   variety for heat, one leafy green for another, one acid for another)
   often DO have reasonable substitutes.

Rules:
- If a genuine substitute exists, return it under "substitutions" with an
  honest tradeoff description.
- If no ingredient can reasonably replicate the missing ingredient's core
  function, set "recommend_purchase" to true instead of forcing a weak
  substitution. Do not populate "substitutions" in this case.
- Never suggest a substitute just because it's "in the same category"
  (e.g. carrots and spinach are not onion substitutes just because
  they're vegetables — they don't replicate onion's aromatic/savory role).
- Maximum 1-2 substitutions if genuinely valid, ranked by closeness of fit.

Respond ONLY with valid JSON, no other text:

{{
  "core_function": "string (what role the ingredient plays in this recipe)",
  "has_substitutions": true or false,
  "substitutions": [
    {{
      "name": "string",
      "ratio": "string",
      "benefit": "string",
      "limitation": "string"
    }}
  ],
  "recommend_purchase": true or false,
  "purchase_reason": "string (only if recommend_purchase is true — brief, e.g. 'Onion's savory aromatic base can't be replicated by other pantry staples in this recipe.')"
}}

recommend_purchase and has_substitutions are mutually exclusive — exactly
one should reflect the real answer, never both true.
"""

    response = await client.chat.completions.create(
        model=get_model(),
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        **completion_kwargs(),
    )

    raw = response.choices[0].message.content
    result = _parse_json_response(raw)

    if not isinstance(result, dict):
        # Legacy/unexpected shape (bare array) — treat as substitutions list.
        result = {"substitutions": result if isinstance(result, list) else []}

    recommend_purchase = bool(result.get("recommend_purchase", False))
    raw_subs = [] if recommend_purchase else (result.get("substitutions") or [])

    pantry_lower = [p.lower() for p in pantry_names if p]
    mapped: list[dict] = []
    for sub in raw_subs:
        if not isinstance(sub, dict):
            continue
        name = sub.get("name") or sub.get("ingredient") or ""
        if not name:
            continue
        benefit = (sub.get("benefit") or "").strip()
        limitation = (sub.get("limitation") or "").strip()
        notes = sub.get("notes") or benefit
        if limitation:
            notes = f"{notes} Limitation: {limitation}".strip()
        name_lower = name.lower()
        available = any(name_lower in p or p in name_lower for p in pantry_lower)
        mapped.append({
            "ingredient": name,
            "ratio": sub.get("ratio", ""),
            "notes": notes,
            "available": available,
        })

    return {
        "core_function": result.get("core_function", ""),
        "has_substitutions": bool(mapped),
        "substitutions": mapped,
        "recommend_purchase": recommend_purchase and not mapped,
        "purchase_reason": result.get("purchase_reason", "") if recommend_purchase else "",
    }

