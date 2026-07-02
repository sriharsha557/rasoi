"""
Supabase Storage client for scan image uploads.

PRD §6.2 — Image Storage Flow:
  User uploads image → FastAPI receives file
  → Upload to Supabase Storage bucket rasoi-scans/{user_id}/{timestamp}_{type}.jpg
  → Return storage path + signed URL
  → Caller saves record to pantry_scans table

Bucket: rasoi-scans  (private, authenticated access only)
Path:   rasoi-scans/{user_id}/{timestamp}_{type}.jpg
Types:  fridge | receipt | pantry
Max:    5 MB per image
"""

import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

BUCKET = "rasoi-scans"
_SIGNED_URL_EXPIRY = 3600  # 1 hour


def _get_config() -> tuple[str, str]:
    """Return (supabase_url, service_role_key) or raise RuntimeError."""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY are not configured")
    return url, key


def is_configured() -> bool:
    """Return True if Supabase credentials are present in the environment."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))


async def upload_scan_image(
    image_bytes: bytes,
    scan_type: str = "ingredient",
    user_id: str = "guest",
    content_type: str = "image/jpeg",
) -> tuple[str, str]:
    """
    Upload a scan image to Supabase Storage.

    Args:
        image_bytes:  Raw image bytes (already validated ≤ 5 MB).
        scan_type:    "ingredient" | "receipt" — mapped to path slug.
        user_id:      Owner identifier (Supabase Auth UID or "guest").
        content_type: MIME type of the image.

    Returns:
        (storage_path, signed_url)
        storage_path — relative path inside the bucket, e.g. "guest/20260702_120000_fridge.jpg"
        signed_url   — pre-signed URL valid for 1 hour (empty string on failure)

    Raises:
        RuntimeError: if Supabase is not configured.
        httpx.HTTPStatusError: if the upload itself fails.
    """
    supabase_url, service_key = _get_config()

    # Map scan_type to PRD path slug
    type_slug = "receipt" if scan_type == "receipt" else "fridge"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    storage_path = f"{user_id}/{timestamp}_{type_slug}.jpg"

    upload_url = f"{supabase_url}/storage/v1/object/{BUCKET}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(upload_url, content=image_bytes, headers=headers)
        resp.raise_for_status()
        logger.info("[supabase] Uploaded %s (%d bytes)", storage_path, len(image_bytes))

    # Generate a short-lived signed URL so the frontend can display the image
    signed_url = await _create_signed_url(supabase_url, service_key, storage_path)
    return storage_path, signed_url


async def _create_signed_url(
    supabase_url: str,
    service_key: str,
    storage_path: str,
    expires_in: int = _SIGNED_URL_EXPIRY,
) -> str:
    """Request a signed URL from Supabase Storage for a private object."""
    sign_endpoint = f"{supabase_url}/storage/v1/object/sign/{BUCKET}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                sign_endpoint,
                json={"expiresIn": expires_in},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                relative = data.get("signedURL", "")
                return f"{supabase_url}/storage/v1{relative}" if relative else ""
    except Exception as exc:
        logger.warning("[supabase] Could not create signed URL: %s", exc)
    return ""


async def get_signed_url(storage_path: str, expires_in: int = _SIGNED_URL_EXPIRY) -> str:
    """
    Generate a fresh signed URL for an existing object.
    Returns empty string if Supabase is not configured or the call fails.
    """
    if not is_configured():
        return ""
    supabase_url, service_key = _get_config()
    return await _create_signed_url(supabase_url, service_key, storage_path, expires_in)
