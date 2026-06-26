"""
Pantry router — GET/POST/PUT/DELETE /api/pantry
Full CRUD for pantry items with expiry flag computation.

Endpoints:
  GET    /api/pantry          — list all items
  POST   /api/pantry          — add one item
  PUT    /api/pantry/{id}     — update item
  DELETE /api/pantry/{id}     — remove item
  GET    /api/pantry/expiring — items expiring soon (amber) or expired (red)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_repository, PantryRepository

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def _attach_expiry_flags(item: dict) -> dict:
    """Compute isExpiring / isExpired from expiration_date and attach to item dict."""
    try:
        exp = date.fromisoformat(item["expiration_date"])
        today = date.today()
        days_left = (exp - today).days
        item["isExpired"] = days_left < 0
        item["isExpiring"] = 0 <= days_left <= 2   # PRD: amber = expiring in 2 days
    except (KeyError, ValueError):
        item["isExpired"] = False
        item["isExpiring"] = False

    # camelCase aliases expected by the frontend TypeScript types
    item["acquisitionDate"] = item.pop("acquisition_date", "")
    item["expirationDate"] = item.pop("expiration_date", "")
    item["createdAt"] = item.pop("created_at", "")
    item["updatedAt"] = item.pop("updated_at", "")
    return item


class PantryItemCreateRequest(BaseModel):
    name: str
    quantity: float = 1.0
    unit: str = "pcs"
    acquisitionDate: Optional[str] = None   # ISO 8601; defaults to today
    expirationDate: Optional[str] = None    # ISO 8601; defaults to today


class PantryItemUpdateRequest(BaseModel):
    quantity: Optional[float] = None
    expirationDate: Optional[str] = None  # ISO 8601 string


@router.get("/expiring")
async def get_expiring(repo: PantryRepository = Depends(get_repository)):
    """Return items that are expiring within 2 days or already expired."""
    items = await repo.get_all()
    flagged = [_attach_expiry_flags(i) for i in items]
    expiring = [i for i in flagged if i.get("isExpiring") or i.get("isExpired")]
    return {"items": expiring}


@router.get("")
async def get_pantry(repo: PantryRepository = Depends(get_repository)):
    """Return all pantry items sorted by expiry date (soonest first)."""
    items = await repo.get_all()
    return {"items": [_attach_expiry_flags(i) for i in items]}


@router.post("")
async def add_pantry_item(
    body: PantryItemCreateRequest,
    repo: PantryRepository = Depends(get_repository),
):
    """Add a new item to the pantry."""
    today = date.today().isoformat()
    item = await repo.create({
        "name": body.name.strip().lower(),
        "quantity": body.quantity,
        "unit": body.unit,
        "acquisition_date": body.acquisitionDate or today,
        "expiration_date": body.expirationDate or today,
    })
    return {"success": True, "item": _attach_expiry_flags(item)}


@router.put("/{item_id}")
async def update_pantry_item(
    item_id: str,
    body: PantryItemUpdateRequest,
    repo: PantryRepository = Depends(get_repository),
):
    """Update quantity and/or expiry date for a pantry item."""
    updates = {}
    if body.quantity is not None:
        updates["quantity"] = body.quantity
    if body.expirationDate is not None:
        updates["expiration_date"] = body.expirationDate

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    updated = await repo.update(item_id, updates)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Pantry item '{item_id}' not found.")

    return {"success": True, "item": _attach_expiry_flags(updated)}


@router.delete("/{item_id}")
async def delete_pantry_item(
    item_id: str,
    repo: PantryRepository = Depends(get_repository),
):
    """Remove a pantry item."""
    deleted = await repo.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Pantry item '{item_id}' not found.")
    return {"success": True, "message": f"Item '{item_id}' removed from pantry."}
