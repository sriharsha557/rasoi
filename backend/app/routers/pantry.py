"""
Pantry router — session-based pantry (see PRD "session-based pantry").

There is no persistent, continuously-tracked inventory: the pantry is
whatever came back from the user's most recent scan (user_last_scan in
Supabase), shown as-is until the next scan or manual edit overwrites it.

Endpoints:
  GET    /api/pantry          — the last scan's items + when it happened
  POST   /api/pantry          — add one item to the current session
  PUT    /api/pantry/{name}   — update an item's quantity/expiry estimate
  DELETE /api/pantry/{name}   — remove an item from the current session
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_last_scan_repository, LastScanRepository, DEMO_USER_ID

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def _attach_expiry_flags(item: dict) -> dict:
    """
    Normalise a session-pantry item to the camelCase shape the frontend and
    recipe/substitution services expect. isExpiring/isExpired are always
    False — Food Buddy stopped continuously tracking expiry (see PRD "session-based
    pantry"): the expiration_date below is still whatever the vision model
    estimated at scan time, just not live-monitored afterwards.
    """
    item = dict(item)
    item["isExpired"] = False
    item["isExpiring"] = False
    item["acquisitionDate"] = item.pop("acquisition_date", "")
    item["expirationDate"] = item.pop("expiration_date", "")
    item.setdefault("id", item.get("name", ""))
    return item


async def get_session_pantry_items(user_id: str = DEMO_USER_ID) -> list[dict]:
    """Fetch the user's last scan and return its items, camelCased. Empty list if never scanned."""
    repo = await get_last_scan_repository()
    last_scan = await repo.get_last_scan(user_id)
    raw_items = (last_scan or {}).get("items_json") or []
    return [_attach_expiry_flags(i) for i in raw_items]


async def remove_session_items(user_id: str, names: list[str]) -> tuple[list[dict], int]:
    """
    Remove items (case-insensitive name match) from the user's last scan.
    Returns (remaining_items_camelCased, removed_count).
    """
    repo = await get_last_scan_repository()
    last_scan = await repo.get_last_scan(user_id)
    if not last_scan:
        return [], 0

    raw_items = last_scan.get("items_json") or []
    lower_names = {n.lower() for n in names}
    remaining = [i for i in raw_items if (i.get("name") or "").lower() not in lower_names]
    removed = len(raw_items) - len(remaining)

    if removed:
        await repo.save_last_scan(
            user_id=user_id,
            scan_type=last_scan.get("scan_type", "ingredient"),
            items=remaining,
            image_path=last_scan.get("image_path"),
        )
    return [_attach_expiry_flags(i) for i in remaining], removed


class PantryItemCreateRequest(BaseModel):
    name: str
    quantity: float = 1.0
    unit: str = "pcs"
    acquisitionDate: Optional[str] = None   # ISO 8601; defaults to today
    expirationDate: Optional[str] = None    # ISO 8601; defaults to today


class PantryItemUpdateRequest(BaseModel):
    quantity: Optional[float] = None
    expirationDate: Optional[str] = None  # ISO 8601 string


@router.get("")
async def get_pantry(userId: str = Query(DEMO_USER_ID)):
    """Return the session pantry: last scan's items plus when it happened."""
    repo: LastScanRepository = await get_last_scan_repository()
    last_scan = await repo.get_last_scan(userId)
    if not last_scan:
        return {"items": [], "hasLastScan": False, "scanDate": None, "scanType": None}

    items = [_attach_expiry_flags(i) for i in (last_scan.get("items_json") or [])]
    return {
        "items": items,
        "hasLastScan": True,
        "scanDate": last_scan.get("scan_date"),
        "scanType": last_scan.get("scan_type"),
    }


@router.post("")
async def add_pantry_item(
    body: PantryItemCreateRequest,
    userId: str = Query(DEMO_USER_ID),
    repo: LastScanRepository = Depends(get_last_scan_repository),
):
    """Add one item to the current session, replacing any existing item with the same name."""
    today = date.today().isoformat()
    new_item = {
        "name": body.name.strip().lower(),
        "quantity": body.quantity,
        "unit": body.unit,
        "acquisition_date": body.acquisitionDate or today,
        "expiration_date": body.expirationDate or today,
        "confidence": 1.0,
    }

    last_scan = await repo.get_last_scan(userId)
    existing_items = (last_scan or {}).get("items_json") or []
    items_by_name = {i["name"]: i for i in existing_items if i.get("name")}
    items_by_name[new_item["name"]] = new_item

    await repo.save_last_scan(
        user_id=userId,
        scan_type=(last_scan or {}).get("scan_type", "manual"),
        items=list(items_by_name.values()),
        image_path=(last_scan or {}).get("image_path"),
    )
    return {"success": True, "item": _attach_expiry_flags(new_item)}


@router.put("/{item_name}")
async def update_pantry_item(
    item_name: str,
    body: PantryItemUpdateRequest,
    userId: str = Query(DEMO_USER_ID),
    repo: LastScanRepository = Depends(get_last_scan_repository),
):
    """Update quantity and/or expiry estimate for a session pantry item, matched by name."""
    last_scan = await repo.get_last_scan(userId)
    if not last_scan:
        raise HTTPException(status_code=404, detail=f"Pantry item '{item_name}' not found.")

    items = last_scan.get("items_json") or []
    match = next((i for i in items if (i.get("name") or "").lower() == item_name.lower()), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Pantry item '{item_name}' not found.")

    if body.quantity is not None:
        match["quantity"] = body.quantity
    if body.expirationDate is not None:
        match["expiration_date"] = body.expirationDate

    await repo.save_last_scan(
        user_id=userId,
        scan_type=last_scan.get("scan_type", "ingredient"),
        items=items,
        image_path=last_scan.get("image_path"),
    )
    return {"success": True, "item": _attach_expiry_flags(match)}


@router.delete("/{item_name}")
async def delete_pantry_item(item_name: str, userId: str = Query(DEMO_USER_ID)):
    """Remove an item from the session pantry, matched by name."""
    _remaining, removed = await remove_session_items(userId, [item_name])
    if not removed:
        raise HTTPException(status_code=404, detail=f"Pantry item '{item_name}' not found.")
    return {"success": True, "message": f"Item '{item_name}' removed from pantry."}
