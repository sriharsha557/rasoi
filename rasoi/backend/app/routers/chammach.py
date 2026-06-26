"""
Chammach Agentic Loop — WebSocket endpoint + background agent.

Observes pantry state via SQLite, calls Claude with tool_use,
and pushes ChammachEvent to all connected WebSocket clients.

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
from anthropic import AsyncAnthropic

from app.database import get_repository
from app.routers.pantry import _attach_expiry_flags
from app.services.recipe_service import get_recipes
from app.clients import claude_client as _claude_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chammach"])
_client = AsyncAnthropic()


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

async def _fetch_pantry() -> tuple[list[dict], list[dict]]:
    """Read all pantry items from SQLite; return (all_items, expiring_items)."""
    repo = await get_repository()
    raw = await repo.get_all()
    all_items = [_attach_expiry_flags(dict(row)) for row in raw]
    expiring = [i for i in all_items if i.get("isExpiring") or i.get("isExpired")]
    return all_items, expiring


# ── Tool definitions for Claude ────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "check_expiry",
        "description": (
            "Read the current pantry and return items expiring soon "
            "(red = today or past, amber = within 2 days). Always call this first."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_recipes",
        "description": (
            "Fetch meal recommendations using the current pantry ingredients. "
            "Prioritises expiring items."
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
        "name": "notify_user",
        "description": (
            "Push a message to the user via Chammach. "
            "This is always the FINAL tool call — call it once you have a clear recommendation."
        ),
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

_SYSTEM_PROMPT = """
You are Chammach, RasOI's agentic kitchen assistant — a friendly talking spoon.

Your job is to proactively help the user manage their kitchen:
- Check what is expiring and alert them before food goes to waste
- Recommend meals that use expiring ingredients first
- Suggest substitutes when ingredients are missing
- Be warm, concise, and helpful — speak like a friend, not a robot

RULES:
1. Always call check_expiry() first.
2. If expiring items exist, call search_recipes() to find meals that use them.
3. If a top recipe is missing an ingredient, call get_substitution().
4. Always end with notify_user() — this is your only way to talk to the user.
5. Maximum 4 tool calls per loop — be efficient.
6. Keep dialogue under 2 sentences. Be specific: name the ingredient, name the dish.
"""


# ── Tool executor ──────────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "check_expiry":
        all_items, expiring = await _fetch_pantry()
        if not expiring:
            return json.dumps({
                "expiring": [],
                "all_count": len(all_items),
                "message": "Nothing expiring soon. Pantry looks fresh.",
            })
        return json.dumps({
            "expiring": [
                {
                    "name": i["name"],
                    "status": "red" if i.get("isExpired") else "amber",
                    "expiry": i.get("expirationDate"),
                }
                for i in expiring
            ],
            "all_count": len(all_items),
        })

    elif tool_name == "search_recipes":
        count = int(tool_input.get("count", 3))
        all_items, _ = await _fetch_pantry()
        if not all_items:
            return json.dumps({"error": "Pantry is empty"})
        result = await get_recipes(
            pantry_items=all_items,
            prioritize_expiring=True,
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
                    "usesExpiringItems": r.get("usesExpiringItems", False),
                    "missingIngredients": r.get("missingIngredients", [])[:3],
                }
                for r in recipes[:count]
            ],
        })

    elif tool_name == "get_substitution":
        missing = tool_input.get("missing_ingredient", "")
        recipe_name = tool_input.get("recipe_name", "this recipe")
        all_items, _ = await _fetch_pantry()
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
    """
    logger.info("[chammach] Agent loop triggered by: %s", trigger)

    messages: list[dict] = [
        {
            "role": "user",
            "content": f"Trigger: {trigger}. Please check the pantry and help the user.",
        }
    ]

    final_event: ChammachEvent | None = None

    for _ in range(5):
        response = await _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=_SYSTEM_PROMPT,
            tools=_TOOLS,
            messages=messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_calls:
            text = text_blocks[0].text if text_blocks else "All good in the kitchen!"
            final_event = ChammachEvent(type="idle", dialogue=text[:200], animation="bounce")
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_call in tool_calls:
            logger.info("[chammach] Tool call: %s %s", tool_call.name, tool_call.input)
            result = await _execute_tool(tool_call.name, tool_call.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result,
            })
            if tool_call.name == "notify_user":
                inp = tool_call.input
                final_event = ChammachEvent(
                    type=inp.get("event_type", "idle"),
                    dialogue=inp.get("dialogue", ""),
                    animation=inp.get("animation", "bounce"),
                    data=inp.get("data"),
                )
                break

        if final_event:
            break

        messages.append({"role": "user", "content": tool_results})

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
