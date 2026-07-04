"""
Fetch missing-ingredient shopping options from the real Collect&Go order
history in `customer_receipts`.

    fetch_missing_ingredient_options(customer_id, missing_ingredient) -> dict

The customer's tier profile (see receipts_profile.classify_customer_live)
decides the upsell mix; suggest_articles() then fills it from the catalog of
products seen across ALL customers' receipts — a stand-in for the live
Collect&Go assortment until the real product-search API is wired in.
"""

from app.clients.supabase_client import select_rows
from app.services.collectandgo.collect_and_go import tier_of, suggest_articles, _match_ingredient
from app.services.collectandgo.receipts_profile import classify_customer_live

TABLE = "customer_receipts"


async def _catalog() -> list:
    """Distinct (product, brand) articles across all customers' receipts, tiered by brand."""
    rows = await select_rows(
        TABLE,
        {"select": "product,brand,category,unit,unit_price_eur,is_bio", "limit": "5000"},
    )
    catalog = {}
    for r in rows:
        key = (r["product"], r["brand"])
        price = round(float(r["unit_price_eur"]), 2)
        if key in catalog and catalog[key]["price_eur"] <= price:
            continue
        catalog[key] = {
            "product": r["product"],
            "brand": r["brand"],
            "category": r["category"],
            "unit": r["unit"],
            "price_eur": price,
            "tier": tier_of(r["brand"], r["is_bio"]),
        }
    return list(catalog.values())


async def fetch_missing_ingredient_options(customer_id: str, missing_ingredient: str) -> dict:
    """
    Input:  customer_id, missing_ingredient (e.g. "melk", "pasta", "koffie")
    Output: {customer_id, profile, missing_ingredient, mix, suggestions[], shortfall}
    where each suggestion is {tier, product, category, unit, price_eur, substituted_for_tier?}
    """
    profile_stats = await classify_customer_live(customer_id)
    catalog = await _catalog()
    hits = _match_ingredient(catalog, missing_ingredient)

    result = suggest_articles(
        missing_ingredient,
        profile_stats["mix_per_3"],
        search_fn=lambda *_a, **_k: hits,
    )

    return {
        "customer_id": customer_id,
        "profile": profile_stats["recipe_profile"].lower(),
        "missing_ingredient": missing_ingredient,
        "mix": result["requested_mix"],
        "suggestions": result["suggestions"],
        "shortfall": result["shortfall"],
    }


def format_suggestion_text(result: dict) -> str:
    """Render fetch_missing_ingredient_options()'s result in plain demo-text form."""
    lines = [
        f"{result['customer_id']} profile={result['profile']} "
        f"missing ingredient='{result['missing_ingredient']}' mix={result['mix']}"
    ]
    for s in result["suggestions"]:
        sub = f" (i.p.v. {s['substituted_for_tier']})" if "substituted_for_tier" in s else ""
        lines.append(f"[{s['tier']:<16}] {s['product']} €{s['price_eur']}{sub}")
    if result["shortfall"]:
        lines.append(f"! tekort in assortiment: {result['shortfall']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import asyncio

    async def _demo():
        for cid, ingredient in [("CUST001", "melk"), ("CUST003", "pasta"), ("CUST005", "koffie")]:
            res = await fetch_missing_ingredient_options(cid, ingredient)
            print(format_suggestion_text(res))
            print()

    asyncio.run(_demo())
