"""
Suggestion router — GET /api/suggest

Calls the Supabase Postgres function suggest_product_for_missing(user_id,
ingredient_name) to recommend a specific product for a missing pantry
ingredient — brand, price, quality tier, and Blinkit/Zepto deep links.
"""

from fastapi import APIRouter, HTTPException, Query

from app.clients import supabase_client
from app.database import DEMO_USER_ID
from app import guardrails

router = APIRouter(prefix="/api/suggest", tags=["suggest"])


@router.get("")
async def suggest_product(
    ingredient: str = Query(..., description="Missing ingredient name, e.g. 'Butter'"),
    user_id: str = Query(DEMO_USER_ID, description="Supabase Auth UID (defaults to the demo user)"),
):
    """
    Suggest a specific product for a missing ingredient via the
    suggest_product_for_missing Postgres function.
    """
    if not supabase_client.is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured on the server.")

    try:
        ingredient = guardrails.sanitise_text_field(ingredient, max_len=100, field_name="ingredient")
        user_id = guardrails.sanitise_text_field(user_id, max_len=128, field_name="user_id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await supabase_client.call_rpc(
            "suggest_product_for_missing",
            {"user_id": user_id, "ingredient_name": ingredient},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Product suggestion lookup failed: {e}")

    # The RPC may return a single JSON object or a one-row array depending on
    # the function's declared return type — normalise to a single object.
    if isinstance(result, list):
        result = result[0] if result else None

    if not result:
        raise HTTPException(status_code=404, detail=f"No suggestion available for '{ingredient}'.")

    return {"ingredient": ingredient, "suggestion": result}
