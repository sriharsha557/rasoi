"""
Brand preference rebuild — aggregates a user's receipt_items history into
user_brand_preferences.

Runs automatically after every successful receipt scan (as a background
task) and on demand via POST /api/preferences/rebuild.
"""

import logging
from collections import Counter, defaultdict

from app.clients import supabase_client

logger = logging.getLogger(__name__)


async def rebuild_brand_preferences(user_id: str) -> dict:
    """
    Recompute this user's brand preferences from their full receipt_items
    history and upsert the aggregates into user_brand_preferences.

    Groups receipt_items by (normalized_name, brand) and computes, per group:
        category       — the group's receipt_items.category (required NOT NULL column)
        purchase_count — number of line items purchased
        avg_price      — average unit_price across the group
        max_price      — highest unit_price seen
        last_purchased — most recent receipt_scans.scan_date for the group

    Upserts on conflict (user_id, normalized_name, preferred_brand), so this
    is idempotent — safe to call repeatedly and re-run from scratch.

    Returns {"groups": <int>, "updated": <int>}.
    """
    if not supabase_client.is_configured():
        logger.warning("[brand_prefs] Supabase not configured — skipping rebuild for %s", user_id)
        return {"groups": 0, "updated": 0}

    items = await supabase_client.select_rows(
        "receipt_items",
        {
            "select": "receipt_id,normalized_name,brand,unit_price,category",
            "user_id": f"eq.{user_id}",
        },
    )
    if not items:
        logger.info("[brand_prefs] No receipt items for user %s — nothing to rebuild", user_id)
        return {"groups": 0, "updated": 0}

    # Fetch scan_date for every receipt referenced, so last_purchased can be derived
    # without assuming a specific PostgREST resource-embedding relationship.
    receipt_ids = sorted({item["receipt_id"] for item in items if item.get("receipt_id")})
    scans = (
        await supabase_client.select_rows(
            "receipt_scans",
            {"select": "id,scan_date", "id": f"in.({','.join(receipt_ids)})"},
        )
        if receipt_ids
        else []
    )
    scan_dates = {scan["id"]: scan.get("scan_date") for scan in scans}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for item in items:
        # preferred_brand is NOT NULL in user_brand_preferences — unbranded produce
        # (vegetables, loose items) has no brand, so fall back to a sentinel.
        key = (item.get("normalized_name") or "unknown", item.get("brand") or "Unbranded")
        groups[key].append(item)

    rows = []
    for (normalized_name, brand), group_items in groups.items():
        prices = [float(i["unit_price"]) for i in group_items if i.get("unit_price") is not None]
        dates = [scan_dates.get(i.get("receipt_id")) for i in group_items]
        dates = [d for d in dates if d]
        category_counts = Counter(i.get("category") or "Other" for i in group_items)
        category = category_counts.most_common(1)[0][0]

        rows.append(
            {
                "user_id": user_id,
                "normalized_name": normalized_name,
                "preferred_brand": brand,
                "category": category,
                "purchase_count": len(group_items),
                "avg_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "last_purchased": max(dates) if dates else None,
            }
        )

    saved = await supabase_client.upsert_rows(
        "user_brand_preferences",
        rows,
        on_conflict="user_id,normalized_name,preferred_brand",
    )
    logger.info(
        "[brand_prefs] Rebuilt %d brand preference group(s) for user %s", len(saved), user_id
    )
    return {"groups": len(groups), "updated": len(saved)}
