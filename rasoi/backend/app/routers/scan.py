"""
Scan router — POST /api/scan
Accepts an image upload, calls Claude Vision, saves results to pantry.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from datetime import date
from typing import Optional
from app.clients import claude_client
from app.database import get_repository, PantryRepository

router = APIRouter(prefix="/api/scan", tags=["scan"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("")
async def scan_image(
    image: UploadFile = File(...),
    scanType: str = Form("ingredient"),
    append: bool = Form(False),   # False = replace pantry, True = add to existing
    repo: PantryRepository = Depends(get_repository),
):
    """
    Scan an ingredient photo or grocery receipt.

    - Validates file type and size
    - Sends image to Claude Vision
    - When append=False (default): clears pantry then saves extracted items
    - When append=True: adds extracted items to existing pantry
    - Returns the saved pantry items
    """
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

    # Replace or append pantry depending on the 'append' flag
    if not append:
        await repo.delete_all()

    # Save each ingredient to the pantry
    today = date.today().isoformat()
    saved = []
    for ing in raw_ingredients:
        try:
            item = await repo.create(
                {
                    "name": str(ing.get("name", "unknown")).strip().lower(),
                    "quantity": float(ing.get("quantity", 1)),
                    "unit": str(ing.get("unit", "pcs")),
                    "acquisition_date": str(ing.get("acquisition_date", today)),
                    "expiration_date": str(ing.get("expiration_date", today)),
                }
            )
            saved.append(item)
        except Exception:
            # Skip items that fail to save (don't abort the whole request)
            continue

    # Attach confidence from raw extraction for the frontend
    saved_with_meta = []
    for item in saved:
        match = next(
            (i for i in raw_ingredients if i.get("name", "").lower() == item["name"]),
            None,
        )
        saved_with_meta.append(
            {**item, "confidence": match.get("confidence", 1.0) if match else 1.0}
        )

    return {
        "success": True,
        "ingredients": saved_with_meta,
        "message": f"Detected {len(saved_with_meta)} ingredient(s) from your {scanType}.",
    }
