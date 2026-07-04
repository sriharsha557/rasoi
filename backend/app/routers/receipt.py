"""
Receipt scan router — POST /api/receipt/scan

Sends a grocery receipt photo to the vision model, extracts structured line
items (name, brand, quantity, price, category), and persists the scan plus
each line item to Supabase (receipt_scans / receipt_items).
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from datetime import date
from typing import Optional

from app.clients import claude_client
from app.clients import supabase_client
from app.database import DEMO_USER_ID
from app import guardrails
from app.services.brand_preferences_service import rebuild_brand_preferences

router = APIRouter(prefix="/api/receipt", tags=["receipt"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
VALID_CATEGORIES = {"Dairy", "Vegetable", "Spice", "Grains", "Oils", "Lentils", "Other"}


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_item(raw: dict) -> dict:
    """Normalise one vision-extracted line item into the receipt_items row shape."""
    category = str(raw.get("category") or "Other").strip()
    if category not in VALID_CATEGORIES:
        category = "Other"

    return {
        "raw_name": str(raw.get("raw_name") or "unknown").strip(),
        "normalized_name": str(raw.get("normalized_name") or raw.get("raw_name") or "unknown").strip().lower(),
        "brand": str(raw["brand"]).strip() if raw.get("brand") else None,
        "quantity": _to_float(raw.get("quantity"), 1.0),
        "unit": str(raw.get("unit") or "pcs").strip(),
        "unit_price": _to_float(raw.get("unit_price")),
        "total_price": _to_float(raw.get("total_price")),
        "category": category,
    }


@router.post("/scan")
async def scan_receipt(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    userId: str = Form(DEMO_USER_ID),
    storeName: Optional[str] = Form(None),
    scanDate: Optional[str] = Form(None),
):
    """
    Scan a grocery receipt image and persist it to Supabase.

    - Validates file type/size
    - Sends the image to the vision model for line-item extraction
    - Saves one row to `receipt_scans` and one row per item to `receipt_items`
    - Triggers a brand-preferences rebuild in the background
    - Returns the saved receipt id, totals, and normalised line items
    """
    if not supabase_client.is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured on the server.")

    try:
        userId = guardrails.sanitise_text_field(userId, max_len=128, field_name="userId")
        if storeName:
            storeName = guardrails.sanitise_text_field(storeName, max_len=200, field_name="storeName")
        if scanDate:
            scanDate = guardrails.sanitise_text_field(scanDate, max_len=10, field_name="scanDate")
            date.fromisoformat(scanDate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{image.content_type}'. Upload a JPEG or PNG image.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        size_mb = len(image_bytes) / (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File size ({size_mb:.1f} MB) exceeds the 5 MB limit.")

    media_type = image.content_type or "image/jpeg"

    try:
        raw_items, raw_text = await claude_client.extract_receipt_items(image_bytes, media_type)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to analyse receipt: {str(e)}")

    if not raw_items:
        return {"success": False, "items": [], "message": "No line items detected on this receipt."}

    items = [_clean_item(item) for item in raw_items]
    total_amount = round(sum(item["total_price"] for item in items), 2)

    scan_row = await supabase_client.insert_row(
        "receipt_scans",
        {
            "user_id": userId,
            "store_name": storeName or "Unknown Store",
            "scan_date": scanDate or date.today().isoformat(),
            "total_amount": total_amount,
            "raw_ocr_text": raw_text,
        },
    )
    receipt_id = scan_row["id"]

    saved_items = await supabase_client.insert_rows(
        "receipt_items",
        [{**item, "receipt_id": receipt_id, "user_id": userId} for item in items],
    )

    background_tasks.add_task(rebuild_brand_preferences, userId)

    return {
        "success": True,
        "receiptId": receipt_id,
        "storeName": scan_row.get("store_name"),
        "scanDate": scan_row.get("scan_date"),
        "totalAmount": scan_row.get("total_amount"),
        "items": saved_items,
        "message": f"Saved {len(saved_items)} item(s) from your receipt.",
    }
