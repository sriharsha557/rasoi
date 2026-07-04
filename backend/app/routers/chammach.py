"""
Chammach Agentic Loop — WebSocket endpoint + background agent.

Observes the session pantry (last scan) and cook history, calls the model
with tool_use, and pushes ChammachEvent to all connected WebSocket clients.

Endpoints:
  WS   /ws/chammach           — real-time event stream to frontend
  POST /api/chammach/trigger  — manual/cron trigger for the agent loop
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel

from app.database import get_cook_history_repository, DEMO_USER_ID
from app.routers.pantry import get_session_pantry_items
from app.services.recipe_service import get_recipes
from app.clients import claude_client as _claude_client
from app.clients import supabase_client
from app.clients.ai_config import get_async_client, get_model
from app import guardrails

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chammach"])


# ── Pydantic model ─────────────────────────────────────────────────────────────

class ChammachEvent(BaseModel):
    type: str                   # expiry_alert | meal_ready | substitution | idle | low_stock
    dialogue: str
    animation: str              # bounce | wiggle | talk
    data: Optional[dict] = None


# ── Connection manager ─────────────────────────────────────────────────────────

class _ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: ChammachEvent):
        payload = event.model_dump()
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = _ConnectionManager()


# ── Pantry helpers ─────────────────────────────────────────────────────────────

async def _fetch_pantry() -> list[dict]:
    """Read the session pantry (last scan) — no live expiry tracking."""
    return await get_session_pantry_items(DEMO_USER_ID)


# ── Tool definitions for Claude ────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "get_session_pantry",
        "description": (
            "Read the user's session pantry — the ingredients from their most recent "
            "scan. There's no live expiry tracking; this just reflects what was last "
            "scanned. Always call this first."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_recipes",
        "description": (
            "Fetch meal recommendations using the session pantry's ingredients."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of recipes to return (1-5)",
                    "default": 3,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_substitution",
        "description": "Find the best pantry substitute for a missing recipe ingredient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "missing_ingredient": {
                    "type": "string",
                    "description": "The ingredient that is missing",
                },
                "recipe_name": {
                    "type": "string",
                    "description": "The recipe this ingredient is needed for",
                },
            },
            "required": ["missing_ingredient"],
        },
    },
    {
        "name": "get_cook_history",
        "description": (
            "Retrieve the last 7 days of cooked meals to avoid recommending the same dish twice. "
            "Call this when the trigger is recipe_cooked, idle, or morning_plan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "How many days of history to retrieve (default 7)",
                    "default": 7,
                }
            },
            "required": [],
        },
    },
    {
        "name": "suggest_missing_products",
        "description": (
            "When a recipe has missing ingredients, suggest smart products "
            "based on user purchase history and generate shopping cart links"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "missing_ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of ingredients missing from the pantry, e.g. ['Cream', 'Butter']",
                },
                "recipe_name": {
                    "type": "string",
                    "description": "The recipe these ingredients are needed for",
                },
            },
            "required": ["missing_ingredients", "recipe_name"],
        },
    },
    {
        "name": "notify_user",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialogue": {
                    "type": "string",
                    "description": "Chammach's spoken message (1-2 sentences, friendly)",
                },
                "animation": {
                    "type": "string",
                    "enum": ["bounce", "wiggle", "talk"],
                },
                "event_type": {
                    "type": "string",
                    "enum": ["expiry_alert", "meal_ready", "substitution", "idle", "low_stock"],
                },
                "data": {
                    "type": "object",
                    "description": "Optional structured payload (recipe, substitute) for the frontend",
                },
            },
            "required": ["dialogue", "animation", "event_type"],
        },
    },
]

# OpenAI function-calling format derived from the Anthropic-style _TOOLS above.
_OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t["input_schema"],
        },
    }
    for t in _TOOLS
]

_SYSTEM_PROMPT = """
You are Chammach, RasOI's agentic kitchen assistant — a friendly talking spoon.

Your job is to proactively help the user manage their kitchen:
- Recommend meals using what's in their session pantry (their last scan)
- Suggest substitutes when ingredients are missing
- When a recommended recipe has missing ingredients, call suggest_missing_products()
  to find products from the user's usual brands and estimate the cost
- Use cook history to make suggestions feel personal, not repetitive — this is your
  strongest tool. Don't just avoid repeats; notice patterns and say so:
    "You've cooked Palak Paneer 3 times this month — try Matar Paneer today,
     you have all the ingredients!"
    "You haven't cooked dal in 10 days. Dal Tadka takes 30 minutes and you
     have everything."
    "Last time you made Palak Paneer you were missing cream. This time you
     have it — want to cook it properly?"
  A proactive, personalised suggestion beats a generic one every time.
- Be warm, concise, and helpful — speak like a friend, not a robot

AGENTIC RULES (mandatory — PRD §14.3):
1. READ-ONLY: You only read data and make recommendations. Never delete or modify pantry items.
2. NO IRREVERSIBLE ACTIONS: Never place orders, send messages, or modify external systems.
3. TOOL BUDGET: Maximum 5 tool calls per response. Be efficient — combine insights.
4. NO EXTERNAL ORDERS: You cannot call shopping, delivery, or payment APIs.
5. GRACEFUL DEGRADATION: If a tool returns an error, continue with what you know.
6. AUDIT TRAIL: Be specific — name the ingredient, name the dish, name the pattern you noticed.
7. TRANSPARENCY: Your notify_user message must explain what you found and why you recommend it.

WORKFLOW:
1. Always call get_session_pantry() first.
2. Call get_cook_history() to see what's been cooked recently — use it to avoid
   repeats and to spot patterns worth mentioning (a favourite dish, a dish not
   made in a while, a past attempt that was missing one ingredient).
3. Call search_recipes() for meal ideas using the session pantry.
4. If a top recipe is missing an ingredient, call get_substitution().
5. If a top recipe has missing ingredients the user would need to buy, call
   suggest_missing_products() with those ingredient names and the recipe name.
   When you do, phrase your notify_user() dialogue like:
   "You're missing {n} ingredients for {recipe}. Based on what you usually buy,
   I've found them on Blinkit for ~₹{total}. Shall I open your cart?"
   (Never actually open the cart or place an order — Rule 2/4 below. Just offer.)
6. Always end with notify_user() — this is your only way to talk to the user.
"""


# ── Tool executor ──────────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_session_pantry":
        all_items = await _fetch_pantry()
        if not all_items:
            return json.dumps({
                "items": [],
                "message": "No session pantry yet — the user hasn't scanned anything.",
            })
        return json.dumps({
            "items": [
                {"name": i["name"], "quantity": i["quantity"], "unit": i["unit"]}
                for i in all_items
            ],
            "count": len(all_items),
        })

    elif tool_name == "search_recipes":
        count = int(tool_input.get("count", 3))
        all_items = await _fetch_pantry()
        if not all_items:
            return json.dumps({"error": "Session pantry is empty — nothing scanned yet"})
        result = await get_recipes(
            pantry_items=all_items,
            prioritize_expiring=False,
            max_recipes=count,
        )
        recipes = result.get("recipes", [])
        return json.dumps({
            "provider": result.get("provider", "unknown"),
            "recipes": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "prepTimeMinutes": r.get("prepTimeMinutes", 30),
                    "matchPercentage": r.get("matchPercentage", 0),
                    "missingIngredients": r.get("missingIngredients", [])[:3],
                }
                for r in recipes[:count]
            ],
        })

    elif tool_name == "get_substitution":
        missing = tool_input.get("missing_ingredient", "")
        recipe_name = tool_input.get("recipe_name", "this recipe")
        all_items = await _fetch_pantry()
        if not all_items:
            return json.dumps({"error": "No pantry items available for substitution"})
        try:
            subs = await _claude_client.get_substitutions(
                missing_ingredient=missing,
                recipe_name=recipe_name,
                pantry_items=all_items,
            )
            return json.dumps({"substitutions": subs})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    elif tool_name == "get_cook_history":
        days = int(tool_input.get("days", 7))
        repo = await get_cook_history_repository()
        history = await repo.get_cook_history(days=days)
        if not history:
            return json.dumps({
                "history": [],
                "message": "No meals cooked in the last 7 days.",
            })
        return json.dumps({
            "history": [
                {
                    "recipe_title": h["recipe_title"],
                    "cooked_at": h["cooked_at"],
                    "ingredients_used": h["ingredients_used"],
                }
                for h in history
            ],
        })

    elif tool_name == "suggest_missing_products":
        missing = tool_input.get("missing_ingredients") or []
        recipe_name = tool_input.get("recipe_name", "this recipe")
        if not missing:
            return json.dumps({"error": "No missing ingredients provided"})

        suggestions = []
        total_inr = 0.0
        for ingredient in missing[:10]:  # Rule 3-adjacent: bound fan-out per tool call
            try:
                result = await supabase_client.call_rpc(
                    "suggest_product_for_missing",
                    {"user_id": DEMO_USER_ID, "ingredient_name": ingredient},
                )
                if isinstance(result, list):
                    result = result[0] if result else None
                if result:
                    suggestions.append({"ingredient": ingredient, **result})
                    total_inr += float(result.get("price_inr") or 0)
                else:
                    suggestions.append({"ingredient": ingredient, "error": "No suggestion found"})
            except Exception as exc:
                suggestions.append({"ingredient": ingredient, "error": str(exc)})

        return json.dumps({
            "recipe_name": recipe_name,
            "suggestions": suggestions,
            "estimated_total_inr": round(total_inr, 2),
        })

    elif tool_name == "notify_user":
        # Terminal tool — the caller extracts the event from tool_input
        return json.dumps({"status": "delivered"})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── Agent loop ─────────────────────────────────────────────────────────────────

async def run_agent_loop(trigger: str = "pantry_updated") -> None:
    """
    One iteration of Chammach's Observe-Think-Plan-Act loop.
    Claude decides which tools to call and in what order.
    Terminates when Claude calls notify_user() or after 5 iterations.

    Enforces PRD §14.3 agentic guardrails:
      - Rule 3: tool budget (max 5 calls)
      - Rule 5: graceful degradation on tool errors
      - Rule 6: audit log per tool call
      - Rule 7: transparency via validate_chammach_dialogue()
    """
    logger.info("[chammach] Agent loop triggered by: %s", trigger)

    client = get_async_client()
    model = get_model()

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Trigger: {trigger}. Please check the pantry and help the user.",
        },
    ]

    final_event: ChammachEvent | None = None

    for _ in range(5):
        # NOTE: gpt-5.5 rejects `reasoning_effort` together with function `tools`
        # on /chat/completions, so we omit completion_kwargs() here.
        response = await client.chat.completions.create(
            model=model,
            max_completion_tokens=4096,
            tools=_OPENAI_TOOLS,
            messages=messages,
        )

        choice = response.choices[0].message
        tool_calls = choice.tool_calls or []

        if not tool_calls:
            text = choice.content or "All good in the kitchen!"
            final_event = ChammachEvent(type="idle", dialogue=text[:200], animation="bounce")
            break

        messages.append({
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        tool_call_index = 0
        for tool_call in tool_calls:
            tool_call_index += 1

            tool_name = tool_call.function.name
            try:
                tool_input = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = {}

            # Rule 1/2/4: Block disallowed tools before execution
            allowed, rejection_reason = guardrails.validate_agent_tool_call(
                tool_name, tool_input
            )
            if not allowed:
                logger.warning("[chammach-14.3] Blocked tool call: %s — %s", tool_name, rejection_reason)
                result = json.dumps({"error": rejection_reason})
            else:
                # Rule 5: Graceful degradation — tool errors don't abort the loop
                try:
                    result = await _execute_tool(tool_name, tool_input)
                except Exception as tool_exc:
                    logger.warning("[chammach-14.3] Tool %s failed: %s", tool_name, tool_exc)
                    result = json.dumps({"error": f"Tool temporarily unavailable: {tool_exc}"})

            # Rule 6: Audit log every call
            guardrails.log_agent_tool_call(
                trigger=trigger,
                tool_name=tool_name,
                tool_input=tool_input,
                result_summary=result[:120],
                call_index=tool_call_index,
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
            if tool_name == "notify_user":
                inp = tool_input
                # Rule 7: Transparency — validate and sanitise dialogue
                dialogue = guardrails.validate_chammach_dialogue(inp.get("dialogue", ""))
                final_event = ChammachEvent(
                    type=inp.get("event_type", "idle"),
                    dialogue=dialogue,
                    animation=inp.get("animation", "bounce"),
                    data=inp.get("data"),
                )
                break

        if final_event:
            break

    if final_event:
        logger.info("[chammach] Broadcasting: %s", final_event.dialogue)
        await manager.broadcast(final_event)
    else:
        await manager.broadcast(
            ChammachEvent(type="idle", dialogue="Your pantry is all set!", animation="bounce")
        )


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@router.websocket("/ws/chammach")
async def chammach_ws(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("[chammach] Client connected. Active: %d", len(manager.active))
    try:
        await websocket.send_json(
            ChammachEvent(
                type="idle",
                dialogue="Namaste! I'm Chammach. Show me your fridge and I'll handle the rest!",
                animation="bounce",
            ).model_dump()
        )
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                trigger = msg.get("trigger", "user_action")
            except json.JSONDecodeError:
                trigger = "user_action"
            asyncio.create_task(run_agent_loop(trigger))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("[chammach] Client disconnected. Active: %d", len(manager.active))


# ── HTTP trigger ───────────────────────────────────────────────────────────────

@router.post("/api/chammach/trigger")
async def trigger_agent(
    background_tasks: BackgroundTasks,
    trigger: str = "manual",
):
    """Manually trigger the Chammach agent loop (cron, post-scan hooks, testing)."""
    background_tasks.add_task(run_agent_loop, trigger)
    return {"status": "agent loop started", "trigger": trigger}
