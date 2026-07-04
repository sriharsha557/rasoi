"""
Purchase history router — powers the /history page.

Endpoints:
  GET /api/history/receipts           — timeline of receipt_scans, each with its receipt_items
  GET /api/history/brand-preferences   — per-category brand loyalty summary
  GET /api/history/summary             — buying-patterns overview card
"""

import logging
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Query

from app.clients import supabase_client
from app.database import DEMO_USER_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])

# Candidate column names for a per-row savings figure on a `smart_substitutions`
# table/view — schema isn't ours, so we try the plausible names and use the
# first one present rather than assuming an exact column name.
_SAVINGS_FIELD_CANDIDATES = ("savings_eur", "potential_savings_eur", "savings", "potential_savings")


@router.get("/receipts")
async def get_receipt_history(userId: str = Query(DEMO_USER_ID)):
    """Timeline of receipt_scans for a user, each with its receipt_items nested."""
    if not supabase_client.is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured on the server.")

    scans = await supabase_client.select_rows(
        "receipt_scans",
        {
            "select": "id,store_name,scan_date,total_amount,raw_ocr_text",
            "user_id": f"eq.{userId}",
            "order": "scan_date.desc",
        },
    )
    if not scans:
        return {"receipts": []}

    receipt_ids = [scan["id"] for scan in scans]
    items = await supabase_client.select_rows(
        "receipt_items",
        {
            "select": "id,receipt_id,raw_name,normalized_name,brand,quantity,unit,unit_price,total_price,category",
            "receipt_id": f"in.({','.join(receipt_ids)})",
        },
    )
    items_by_receipt: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        items_by_receipt[item["receipt_id"]].append(item)

    receipts = [
        {
            "id": scan["id"],
            "storeName": scan.get("store_name") or "Unknown Store",
            "scanDate": scan.get("scan_date"),
            "totalAmount": scan.get("total_amount"),
            "items": items_by_receipt.get(scan["id"], []),
        }
        for scan in scans
    ]
    return {"receipts": receipts}


@router.get("/brand-preferences")
async def get_brand_preferences(userId: str = Query(DEMO_USER_ID)):
    """
    Per-category brand loyalty: preferred brand, avg price paid for it, and
    how many times the category was purchased overall.

    Colour coding:
      green — one brand, bought 2+ times (consistent buyer)
      amber — multiple brands in the category (mixed buyer)
      grey  — bought only once (not enough history to tell)
    """
    if not supabase_client.is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured on the server.")

    items = await supabase_client.select_rows(
        "receipt_items",
        {
            "select": "category,normalized_name,brand,unit_price",
            "user_id": f"eq.{userId}",
        },
    )
    if not items:
        return {"categories": []}

    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_category[item.get("category") or "Other"].append(item)

    categories = []
    for category, rows in by_category.items():
        brand_counts = Counter(row.get("brand") or "Unbranded" for row in rows)
        preferred_brand, preferred_count = brand_counts.most_common(1)[0]
        distinct_brands = len(brand_counts)
        total_purchases = len(rows)

        preferred_prices = [
            float(row["unit_price"])
            for row in rows
            if (row.get("brand") or "Unbranded") == preferred_brand and row.get("unit_price") is not None
        ]
        avg_price = round(sum(preferred_prices) / len(preferred_prices), 2) if preferred_prices else None

        if total_purchases <= 1:
            consistency = "grey"
        elif distinct_brands == 1:
            consistency = "green"
        else:
            consistency = "amber"

        categories.append({
            "category": category,
            "preferredBrand": preferred_brand,
            "avgPrice": avg_price,
            "timesPurchased": total_purchases,
            "distinctBrands": distinct_brands,
            "consistency": consistency,
        })

    categories.sort(key=lambda c: c["timesPurchased"], reverse=True)
    return {"categories": categories}


async def _estimate_potential_savings(user_id: str) -> float | None:
    """
    Best-effort read of a `smart_substitutions` table/view for this user,
    summing whichever plausible savings column is present. Returns None if
    the table isn't reachable (not yet created, different schema, etc.)
    rather than failing the whole summary endpoint.
    """
    try:
        rows = await supabase_client.select_rows(
            "smart_substitutions",
            {"select": "*", "user_id": f"eq.{user_id}"},
        )
    except Exception as exc:
        logger.info("[history] smart_substitutions not reachable: %s", exc)
        return None

    if not rows:
        return 0.0

    for field in _SAVINGS_FIELD_CANDIDATES:
        if field in rows[0]:
            return round(sum(float(row.get(field) or 0) for row in rows), 2)

    logger.info("[history] smart_substitutions rows found but no known savings column: %s", list(rows[0].keys()))
    return None


@router.get("/summary")
async def get_buying_patterns_summary(userId: str = Query(DEMO_USER_ID)):
    """Buying-patterns overview: total spent, most purchased item, favourite store, potential savings."""
    if not supabase_client.is_configured():
        raise HTTPException(status_code=503, detail="Supabase is not configured on the server.")

    scans = await supabase_client.select_rows(
        "receipt_scans",
        {"select": "store_name,total_amount", "user_id": f"eq.{userId}"},
    )
    items = await supabase_client.select_rows(
        "receipt_items",
        {"select": "normalized_name", "user_id": f"eq.{userId}"},
    )

    total_spent = round(sum(float(s.get("total_amount") or 0) for s in scans), 2)

    favourite_store = None
    if scans:
        store_counts = Counter(s.get("store_name") for s in scans if s.get("store_name"))
        if store_counts:
            favourite_store = store_counts.most_common(1)[0][0]

    most_purchased_item = None
    if items:
        item_counts = Counter(i.get("normalized_name") for i in items if i.get("normalized_name"))
        if item_counts:
            most_purchased_item = item_counts.most_common(1)[0][0]

    potential_savings = await _estimate_potential_savings(userId)

    return {
        "totalSpent": total_spent,
        "mostPurchasedItem": most_purchased_item,
        "favouriteStore": favourite_store,
        "potentialSavings": potential_savings,
    }
