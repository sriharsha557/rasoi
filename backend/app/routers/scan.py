"""
Scan router — POST /api/scan
Accepts an image upload, calls the vision model, saves the result as the
user's session pantry (user_last_scan) — see PRD "session-based pantry".

Image storage flow (PRD §6.2):
  image → validate → upload to Supabase Storage (best-effort)
  → send bytes to the vision model → overwrite (or append to) the last scan
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from datetime import date
from typing import Optional
from app.clients import claude_client
from app.clients import supabase_client
from app.database import get_last_scan_repository, LastScanRepository, DEMO_USER_ID
from app import guardrails

router = APIRouter(prefix="/api/scan", tags=["scan"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("")
async def scan_image(
    image: UploadFile = File(...),
    scanType: str = Form("ingredient"),
    append: bool = Form(False),   # False = replace last scan, True = merge into it
    userId: str = Form(DEMO_USER_ID),
    knownExpirationDate: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    repo: LastScanRepository = Depends(get_last_scan_repository),
):
    """
    Scan an ingredient photo or grocery receipt into the session pantry.

    - Validates file type and size
    - Checks form fields for prompt injection (PRD §14.1)
    - Uploads image to Supabase Storage (best-effort — scan continues if Supabase is not configured)
    - Sends image to the vision model for ingredient extraction
    - Validates extraction output for non-food images and injection (PRD §14.1)
    - When append=False (default): overwrites the last scan with these items
    - When append=True: merges these items into the existing last scan
    - Returns the session's items plus the Supabase image URL
    """
    # ── 14.1: Prompt injection check on form inputs ──────────────────────────
    try:
        scanType = guardrails.sanitise_text_field(scanType, max_len=50, field_name="scanType")
        userId   = guardrails.sanitise_text_field(userId,   max_len=128, field_name="userId")
        if knownExpirationDate:
            knownExpirationDate = guardrails.sanitise_text_field(
                knownExpirationDate,
                max_len=10,
                field_name="knownExpirationDate",
            )
            date.fromisoformat(knownExpirationDate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    # Validate content type
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{image.content_type}'. Upload a JPEG or PNG image.",
        )

    # Read and validate size
    image_bytes = await image.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        size_mb = len(image_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size ({size_mb:.1f} MB) exceeds the 5 MB limit.",
        )

    # Determine media type
    media_type = image.content_type or "image/jpeg"

    # ── Supabase Storage upload (PRD §6.2) ──────────────────────────────────
    # Best-effort: if Supabase is not configured the scan still works normally.
    image_storage_path: str = ""
    image_signed_url: str = ""
    if supabase_client.is_configured():
        try:
            image_storage_path, image_signed_url = await supabase_client.upload_scan_image(
                image_bytes=image_bytes,
                scan_type=scanType,
                user_id=userId,
                content_type=media_type,
            )
        except Exception as exc:
            # Non-fatal — log and continue with vision extraction
            import logging
            logging.getLogger(__name__).warning(
                "[scan] Supabase upload failed (continuing without storage): %s", exc
            )

    try:
        raw_ingredients = await claude_client.extract_ingredients(image_bytes, media_type)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to analyse image: {str(e)}",
        )

    if not raw_ingredients:
        return {
            "success": False,
            "ingredients": [],
            "message": "No ingredients detected in the image. Try a clearer photo.",
        }

    # ── 14.1: Validate scan output (non-food image + injection in output)
    is_valid, reason = guardrails.validate_food_scan_result(raw_ingredients)
    if not is_valid:
        return {
            "success": False,
            "ingredients": [],
            "message": reason,
        }

    # Normalise extracted items for the session pantry
    today = date.today().isoformat()
    new_items = [
        {
            "name": str(ing.get("name", "unknown")).strip().lower(),
            "quantity": float(ing.get("quantity", 1)),
            "unit": str(ing.get("unit", "pcs")),
            "acquisition_date": str(ing.get("acquisition_date", today)),
            "expiration_date": knownExpirationDate or str(ing.get("expiration_date", today)),
            "confidence": float(ing.get("confidence", 1.0)),
        }
        for ing in raw_ingredients
    ]

    if append:
        existing = await repo.get_last_scan(userId)
        prior_items = (existing or {}).get("items_json") or []
        # Replace same-named items rather than duplicating them
        prior_by_name = {i["name"]: i for i in prior_items if i.get("name")}
        for item in new_items:
            prior_by_name[item["name"]] = item
        items = list(prior_by_name.values())
    else:
        items = new_items

    saved = await repo.save_last_scan(
        user_id=userId,
        scan_type=scanType,
        items=items,
        image_path=image_storage_path or None,
    )

    # Trigger Buddy agentic loop in background — PRD §8b.6 agentic moment #1
    # "Auto-recommend on scan complete — no button click needed"
    from app.routers.buddy import run_agent_loop
    background_tasks.add_task(run_agent_loop, "pantry_scan_completed")
    # Append-only signal for future personalization (cuisine affinity, promotions)
    background_tasks.add_task(repo.log_scan_history, userId, scanType, new_items)

    return {
        "success": True,
        "ingredients": saved.get("items_json", items),
        "message": f"Detected {len(new_items)} ingredient(s) from your {scanType}.",
        "imageUrl": image_signed_url or None,       # signed URL (1 hour) — None if Supabase not used
        "imagePath": image_storage_path or None,    # storage path for future signed URL refresh
    }
