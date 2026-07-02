"""
Substitution router — POST /api/substitute
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.clients import claude_client
from app.routers.pantry import _attach_expiry_flags
from app.database import get_repository, PantryRepository
from app import guardrails

router = APIRouter(prefix="/api/substitute", tags=["substitutions"])


class SubstitutionRequest(BaseModel):
    recipeId: str
    missingIngredient: str
    recipeContext: str  # recipe name used for Claude prompt context


@router.post("")
async def substitute(
    body: SubstitutionRequest,
    repo: PantryRepository = Depends(get_repository),
):
    """
    Suggest pantry-available substitutes for a missing ingredient.
    """
    if not body.missingIngredient.strip():
        raise HTTPException(status_code=400, detail="missingIngredient cannot be empty.")

    # 14.1: Injection check on user-supplied fields
    try:
        missing = guardrails.sanitise_text_field(body.missingIngredient, max_len=100, field_name="missingIngredient")
        context = guardrails.sanitise_text_field(body.recipeContext, max_len=200, field_name="recipeContext")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    raw_items = await repo.get_all()
    pantry = [_attach_expiry_flags(i) for i in raw_items]

    try:
        subs = await claude_client.get_substitutions(
            missing_ingredient=missing,
            recipe_name=context,
            pantry_items=pantry,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Substitution lookup failed: {e}")

    # 14.2: Filter toxic suggestions + flag allergens
    subs = guardrails.filter_toxic_substitutes(subs)
    subs = guardrails.flag_allergens(subs)

    return {"substitutions": subs}
