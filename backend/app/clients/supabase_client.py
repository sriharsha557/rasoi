"""
Supabase Storage client for scan image uploads.

PRD §6.2 — Image Storage Flow:
  User uploads image → FastAPI receives file
  → Upload to Supabase Storage bucket rasoi-scans/{user_id}/{timestamp}_{type}.jpg
  → Return storage path + signed URL
  → Caller stores the path on user_last_scan (session pantry) or receipt_scans

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


def _rest_headers(service_key: str, prefer: str = "return=representation") -> dict:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


async def insert_row(table: str, payload: dict) -> dict:
    """Insert a single row into a Supabase table via PostgREST. Returns the inserted row."""
    supabase_url, service_key = _get_config()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/{table}",
            json=payload,
            headers=_rest_headers(service_key),
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else payload


async def insert_rows(table: str, payloads: list[dict]) -> list[dict]:
    """Insert multiple rows into a Supabase table via PostgREST. Returns the inserted rows."""
    if not payloads:
        return []
    supabase_url, service_key = _get_config()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/{table}",
            json=payloads,
            headers=_rest_headers(service_key),
        )
        resp.raise_for_status()
        return resp.json()


async def select_rows(table: str, params: dict) -> list[dict]:
    """GET rows from a Supabase table via PostgREST. `params` are PostgREST query filters."""
    supabase_url, service_key = _get_config()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/{table}",
            params=params,
            headers=_rest_headers(service_key),
        )
        resp.raise_for_status()
        return resp.json()


async def call_rpc(function_name: str, params: dict) -> dict | list:
    """Call a Supabase Postgres function via PostgREST RPC. Returns the parsed JSON result."""
    supabase_url, service_key = _get_config()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/rpc/{function_name}",
            json=params,
            headers=_rest_headers(service_key),
        )
        resp.raise_for_status()
        return resp.json()


async def upsert_rows(table: str, payloads: list[dict], on_conflict: str) -> list[dict]:
    """
    Upsert rows into a Supabase table via PostgREST, merging on conflict.

    `on_conflict` is a comma-separated list of columns matching a UNIQUE
    constraint on the table (e.g. "user_id,normalized_name,preferred_brand").
    """
    if not payloads:
        return []
    supabase_url, service_key = _get_config()
    headers = _rest_headers(service_key, prefer="resolution=merge-duplicates,return=representation")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/{table}",
            params={"on_conflict": on_conflict},
            json=payloads,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()
