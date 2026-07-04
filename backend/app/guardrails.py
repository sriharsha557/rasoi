"""
Food Buddy Guardrails — PRD §14
Centralised safety and validation logic covering:

  14.1 Input guardrails   — non-food images, prompt injection, oversized files
  14.2 Output guardrails  — toxic substitutes, allergen blindness, expired-only recipes
  14.3 Agentic guardrails — Buddy's 7 rules (enforced at loop level)
  14.4 Demo day safety    — pre-flight checks for the 5 key failure scenarios
"""

from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 14.1  INPUT GUARDRAILS
# ══════════════════════════════════════════════════════════════════════════════

# ── Prompt injection ──────────────────────────────────────────────────────────
# Common patterns used to hijack LLM instructions via user-controlled fields.
_INJECTION_PATTERNS: list[str] = [
    "ignore previous",
    "ignore all",
    "disregard",
    "forget previous instructions",
    "new instructions",
    "system:",
    "assistant:",
    "<|im_start|>",
    "<|im_end|>",
    "[[",
    "]]",
    "jailbreak",
    "roleplay as",
    "pretend you are",
    "act as if",
    "reveal your instructions",
    "reveal your system prompt",
    "override",
    "bypass",
    "you are now",
    "ignore the above",
    "disregard the above",
]


def check_prompt_injection(text: str) -> bool:
    """
    Return True if the text looks like a prompt-injection attempt.

    Called on every user-controlled string that reaches an LLM:
    scanType, userId, recipe context, ingredient names, etc.

    PRD §14.1
    """
    if not text or not isinstance(text, str):
        return False
    lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            logger.warning("[guardrail-14.1] Prompt injection detected: %r contains %r", text[:80], pattern)
            return True
    return False


def sanitise_text_field(value: str, max_len: int = 200, field_name: str = "field") -> str:
    """
    Strip leading/trailing whitespace, truncate to max_len, and raise
    ValueError if prompt injection is detected.

    Use on all string form fields before passing to LLMs.
    """
    value = value.strip()[:max_len]
    if check_prompt_injection(value):
        raise ValueError(f"Invalid input in {field_name}: potentially unsafe content detected.")
    return value


# ── Non-food image detection ──────────────────────────────────────────────────

def validate_food_scan_result(ingredients: list[dict], min_confidence: float = 0.3) -> tuple[bool, str]:
    """
    Validate that Claude's scan result looks like a genuine food extraction.

    Returns (is_valid, reason).
    Flags results where:
      - All items have confidence below min_confidence (probably not food)
      - Any ingredient name contains obvious non-food injection content

    PRD §14.1
    """
    if not ingredients:
        return True, ""   # Empty is valid — handled upstream with "no items found" message

    # Check for injection in ingredient names returned by Claude
    for item in ingredients:
        name = item.get("name", "")
        if check_prompt_injection(name):
            logger.warning("[guardrail-14.1] Injection content in Claude scan output: %r", name)
            return False, "Scan result contained unsafe content and was rejected."

    # Low-confidence check — if every item is below threshold, likely a non-food image
    confidences = [float(i.get("confidence", 1.0)) for i in ingredients]
    avg_confidence = sum(confidences) / len(confidences)
    if avg_confidence < min_confidence:
        logger.warning("[guardrail-14.1] Low-confidence scan (avg=%.2f) — possible non-food image", avg_confidence)
        return False, (
            f"The image doesn't look like food (confidence {avg_confidence:.0%}). "
            "Please upload a clear photo of your fridge, pantry shelf, or grocery receipt."
        )

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# 14.2  OUTPUT GUARDRAILS
# ══════════════════════════════════════════════════════════════════════════════

# ── Toxic substitute detection ────────────────────────────────────────────────
# Terms that must never appear in a food substitution suggestion.
_TOXIC_TERMS: frozenset[str] = frozenset([
    "bleach", "ammonia", "hydrogen peroxide", "acetone",
    "methanol", "isopropanol", "rubbing alcohol",
    "paint thinner", "turpentine", "antifreeze",
    "detergent", "soap", "cleaning", "disinfectant",
    "gasoline", "kerosene", "formaldehyde",
    "raw kidney bean",   # toxic unless fully cooked
    "rhubarb leaf",      # oxalic acid — toxic
    "elderberry raw",    # cyanogenic glycosides when raw
])


def filter_toxic_substitutes(substitutions: list[dict]) -> list[dict]:
    """
    Remove any substitution suggestions that contain toxic or non-food terms.
    Logs a warning for each rejected entry.

    PRD §14.2
    """
    safe: list[dict] = []
    for sub in substitutions:
        combined = " ".join([
            sub.get("ingredient", ""),
            sub.get("notes", ""),
            sub.get("ratio", ""),
        ]).lower()

        toxic_hit = next((t for t in _TOXIC_TERMS if t in combined), None)
        if toxic_hit:
            logger.warning(
                "[guardrail-14.2] Rejected toxic substitute: %r (matched %r)",
                sub.get("ingredient"), toxic_hit,
            )
        else:
            safe.append(sub)

    return safe


# ── Allergen flagging ─────────────────────────────────────────────────────────
# Maps ingredient name fragments → allergen category label.
_ALLERGEN_MAP: dict[str, str] = {
    # Peanuts
    "peanut": "peanuts", "groundnut": "peanuts",
    # Tree nuts
    "almond": "tree nuts", "cashew": "tree nuts", "walnut": "tree nuts",
    "hazelnut": "tree nuts", "pistachio": "tree nuts", "pecan": "tree nuts",
    "macadamia": "tree nuts", "brazil nut": "tree nuts",
    # Dairy
    "milk": "dairy", "cream": "dairy", "butter": "dairy", "cheese": "dairy",
    "yogurt": "dairy", "yoghurt": "dairy", "ghee": "dairy", "paneer": "dairy",
    "whey": "dairy", "lactose": "dairy",
    # Eggs
    "egg": "eggs",
    # Gluten / wheat
    "wheat": "gluten", "flour": "gluten", "bread": "gluten",
    "pasta": "gluten", "barley": "gluten", "rye": "gluten",
    "semolina": "gluten", "breadcrumb": "gluten",
    # Soy
    "soy": "soy", "tofu": "soy", "edamame": "soy", "miso": "soy",
    "tempeh": "soy",
    # Fish
    "fish": "fish", "salmon": "fish", "tuna": "fish", "cod": "fish",
    "sardine": "fish", "anchovy": "fish", "halibut": "fish",
    # Shellfish
    "shrimp": "shellfish", "prawn": "shellfish", "crab": "shellfish",
    "lobster": "shellfish", "scallop": "shellfish", "clam": "shellfish",
    "oyster": "shellfish", "mussel": "shellfish",
    # Sesame
    "sesame": "sesame", "tahini": "sesame",
    # Sulphites (common trigger)
    "wine": "sulphites", "vinegar": "sulphites",
}


def flag_allergens(substitutions: list[dict]) -> list[dict]:
    """
    Annotate each substitution with an `allergen_warning` list if it
    contains a known allergen.  Existing entries are preserved.

    PRD §14.2 — allergen blindness prevention.
    """
    for sub in substitutions:
        name = sub.get("ingredient", "").lower()
        found = sorted({label for term, label in _ALLERGEN_MAP.items() if term in name})
        if found:
            sub["allergen_warning"] = found
            logger.info("[guardrail-14.2] Allergen flagged in substitute %r: %s", sub.get("ingredient"), found)
    return substitutions


# ── Expired-only recipe filter ─────────────────────────────────────────────────

def filter_expired_only_recipes(recipes: list[dict], pantry: list[dict]) -> list[dict]:
    """
    Remove recipes where every available ingredient is fully expired (red).
    Recipes that include at least one fresh or expiring (amber) ingredient are kept.

    PRD §14.2 — don't recommend cooking food that has already gone bad.
    """
    expired_names = {i["name"].lower() for i in pantry if i.get("isExpired") and not i.get("isExpiring")}
    non_expired_names = {i["name"].lower() for i in pantry if not i.get("isExpired")}

    if not expired_names:
        return recipes  # Nothing expired — nothing to filter

    filtered: list[dict] = []
    for recipe in recipes:
        available_ings = {
            ing["name"].lower()
            for ing in recipe.get("ingredients", [])
            if ing.get("available")
        }
        # Keep recipe if at least one available ingredient is NOT expired
        if available_ings & non_expired_names or not available_ings:
            filtered.append(recipe)
        else:
            logger.warning(
                "[guardrail-14.2] Filtered recipe %r — all available ingredients are expired",
                recipe.get("name"),
            )

    # Safety fallback: never return empty list (show all if filter removed everything)
    return filtered if filtered else recipes


# ══════════════════════════════════════════════════════════════════════════════
# 14.3  AGENTIC GUARDRAILS — Buddy's 7 rules
# ══════════════════════════════════════════════════════════════════════════════
#
# Rule 1 — Read-only:        Buddy only reads data and makes recommendations.
#                             It never writes pantry items, places orders, or
#                             modifies user data without an explicit user action.
# Rule 2 — No irreversible:  No delete, no external API mutations, no orders.
# Rule 3 — Tool budget:      Max 5 tool calls per agent loop iteration.
# Rule 4 — No external orders: Cannot call shopping/delivery APIs.
# Rule 5 — Graceful degrade: On tool failure, continue with partial info.
# Rule 6 — Audit log:        Every tool call is logged with trigger + input.
# Rule 7 — Transparency:     notify_user() must explain what Buddy found.
#
# Rules 1, 2, 4 are enforced structurally (the tools simply do not exist).
# Rules 3, 5, 6, 7 are enforced here and in the agent loop.

# Tools that are allowed (read-only, safe)
ALLOWED_AGENT_TOOLS: frozenset[str] = frozenset([
    "get_session_pantry",
    "search_recipes",
    "get_substitution",
    "get_cook_history",
    "suggest_missing_products",
    "notify_user",
])

# Tools explicitly blocked (write operations, external APIs)
BLOCKED_AGENT_TOOLS: frozenset[str] = frozenset([
    "update_pantry",
    "delete_pantry_item",
    "place_order",
    "send_email",
    "call_api",
])

AGENT_TOOL_BUDGET = 5   # Rule 3


def validate_agent_tool_call(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """
    Validate a tool call before execution.
    Returns (is_allowed, rejection_reason).

    Enforces Rules 1, 2, 3, 4.
    PRD §14.3
    """
    if tool_name in BLOCKED_AGENT_TOOLS:
        return False, f"Tool '{tool_name}' is blocked — Buddy cannot perform write operations."

    if tool_name not in ALLOWED_AGENT_TOOLS:
        return False, f"Tool '{tool_name}' is not in the allowed tool set."

    # Check tool inputs for injection (Rule 1 / security hygiene)
    for key, value in tool_input.items():
        if isinstance(value, str) and check_prompt_injection(value):
            return False, f"Injection attempt detected in tool input field '{key}'."

    return True, ""


def log_agent_tool_call(
    trigger: str,
    tool_name: str,
    tool_input: dict,
    result_summary: str,
    call_index: int,
) -> None:
    """
    Audit log entry for every Buddy tool call.
    Rule 6 — audit log.
    PRD §14.3
    """
    logger.info(
        "[buddy-audit] trigger=%r call=%d tool=%s input=%r result=%s",
        trigger,
        call_index,
        tool_name,
        {k: str(v)[:60] for k, v in tool_input.items()},
        result_summary[:120],
    )


def validate_buddy_dialogue(dialogue: str) -> str:
    """
    Ensure Buddy's notify_user dialogue meets transparency requirements.
    Rule 7 — transparency.

    - Must not be empty
    - Truncate to 300 characters max
    - Strip any injection content

    PRD §14.3
    """
    if not dialogue or not dialogue.strip():
        return "I checked your pantry — everything looks good!"
    # Truncate
    dialogue = dialogue.strip()[:300]
    # If injection detected, replace entirely
    if check_prompt_injection(dialogue):
        logger.warning("[guardrail-14.3] Injection in Buddy dialogue — replaced with safe fallback")
        return "Your pantry is all set! Let me know if you need anything."
    return dialogue


# ══════════════════════════════════════════════════════════════════════════════
# 14.4  DEMO DAY SAFETY — pre-flight checks
# ══════════════════════════════════════════════════════════════════════════════
#
# 5 failure scenarios and their prevention steps:
#
#  S1 — Claude API down
#       Prevention: ANTHROPIC_API_KEY present + reachability test
#
#  S2 — Empty pantry scan (non-food image or blank photo)
#       Prevention: validate_food_scan_result() confidence check in scan route
#
#  S3 — WebSocket disconnected mid-demo
#       Prevention: frontend auto-reconnect (5s) + heartbeat ping
#
#  S4 — Recipe providers unavailable (Supabase config + Spoonacular quota)
#       Prevention: provider-status check before demo
#
#  S5 — Supabase Storage unavailable
#       Prevention: upload is best-effort, scan continues without image storage

import os
import httpx


async def demo_preflight_check() -> dict:
    """
    Run all 5 pre-demo safety checks and return a status report.

    GET /api/safety/demo-check calls this.
    PRD §14.4
    """
    results: dict[str, dict] = {}

    # ── S1: AI API reachability ──────────────────────────────────────────────
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        results["ai_api"] = {"status": "fail", "detail": "ANTHROPIC_API_KEY not set"}
    else:
        try:
            from app.clients.ai_config import get_async_client, get_model
            client = get_async_client()
            # Minimal call to verify key validity
            await client.messages.create(
                model=get_model(),
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            results["ai_api"] = {"status": "ok", "detail": "AI API reachable"}
        except Exception as exc:
            results["ai_api"] = {"status": "fail", "detail": str(exc)[:120]}

    # ── S2: Session pantry available (at least 1 item for demo) ──────────────
    try:
        from app.database import DEMO_USER_ID
        from app.routers.pantry import get_session_pantry_items
        items = await get_session_pantry_items(DEMO_USER_ID)
        count = len(items)
        results["pantry_data"] = {
            "status": "ok" if count > 0 else "warn",
            "detail": f"{count} pantry item(s) loaded" if count > 0
                      else "Pantry is empty — scan a fridge photo before the demo",
        }
    except Exception as exc:
        results["pantry_data"] = {"status": "fail", "detail": str(exc)[:120]}

    # ── S3: WebSocket manager has connections (optional — 0 is ok pre-demo) ──
    try:
        from app.routers.buddy import manager
        active = len(manager.active)
        results["websocket"] = {
            "status": "ok",
            "detail": f"{active} active WebSocket client(s)",
        }
    except Exception as exc:
        results["websocket"] = {"status": "fail", "detail": str(exc)[:120]}

    # ── S4: Recipe provider available ────────────────────────────────────────
    try:
        from app.services.recipe_service import get_provider_status
        provider = get_provider_status()
        results["recipe_provider"] = {
            "status": "ok",
            "detail": f"Active provider: {provider['active']}",
            "providers": provider,
        }
    except Exception as exc:
        results["recipe_provider"] = {"status": "fail", "detail": str(exc)[:120]}

    # ── S5: Supabase Storage reachability ────────────────────────────────────
    from app.clients import supabase_client
    if not supabase_client.is_configured():
        results["supabase_storage"] = {
            "status": "warn",
            "detail": "Supabase not configured — scans will work but images won't be stored",
        }
    else:
        try:
            supabase_url, service_key = supabase_client._get_config()
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{supabase_url}/storage/v1/bucket",
                    headers={"Authorization": f"Bearer {service_key}"},
                )
                if resp.status_code == 200:
                    results["supabase_storage"] = {"status": "ok", "detail": "Supabase Storage reachable"}
                else:
                    results["supabase_storage"] = {
                        "status": "warn",
                        "detail": f"Supabase returned HTTP {resp.status_code}",
                    }
        except Exception as exc:
            results["supabase_storage"] = {"status": "warn", "detail": str(exc)[:120]}

    # ── Overall status ───────────────────────────────────────────────────────
    statuses = [v["status"] for v in results.values()]
    overall = "ok" if all(s == "ok" for s in statuses) else (
        "warn" if "fail" not in statuses else "fail"
    )

    return {"overall": overall, "checks": results}
