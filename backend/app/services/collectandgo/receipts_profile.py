"""
Real Collect&Go customer-tier profiling, sourced from the `customer_receipts`
Supabase table (actual grocery pickup orders — receipt_id, customer_id,
product, brand, category, is_boni, is_bio, is_promo, quantity, unit_price_eur,
line_total_eur). Replaces the synthetic-dataset classify_customer() for
customers backed by this real receipt history.

Brand tiers: Everyday < Boni Selection < Boni Bio < Bio-Time < Nationaal
A-merk — see collect_and_go.tier_of() for the brand -> tier mapping, reused
here unchanged (it already matches this table's brand/is_bio values exactly).
"""

from collections import Counter

from app.clients.supabase_client import select_rows
from app.services.collectandgo.collect_and_go import tier_of

TABLE = "customer_receipts"

# Fixed upsell strategy per profile (goal + mix/3) — a lookup, not derived
# per-customer, matching the reference classification table.
PROFILE_STRATEGY = {
    "COST_CONSCIOUS": {
        "upsell_goal": "Budgetvriendelijk upsellen — in dezelfde prijsklasse blijven",
        "mix_per_3": {"Everyday": 1, "Boni Selection": 2},
    },
    "HEALTH_CONSCIOUS": {
        "upsell_goal": "Bio/gezond upsellen",
        "mix_per_3": {"Boni Bio": 2, "Bio-Time": 1},
    },
    "PREMIUM": {
        "upsell_goal": "Premium / nationale A-merken upsellen",
        "mix_per_3": {"Nationaal A-merk": 2, "Boni Selection": 1},
    },
}


def _scale_mix(mix: dict, to_total: int) -> dict:
    """Largest-remainder scaling of an integer mix (e.g. per-3) to a new total (e.g. per-5)."""
    from_total = sum(mix.values())
    raw = {t: c * to_total / from_total for t, c in mix.items()}
    floors = {t: int(v) for t, v in raw.items()}
    remainder = to_total - sum(floors.values())
    for t in sorted(mix, key=lambda t: raw[t] - floors[t], reverse=True)[:remainder]:
        floors[t] += 1
    return floors


def _profile_label(bio_share: float, national_share: float) -> str:
    if bio_share >= 0.5:
        return "HEALTH_CONSCIOUS"
    if national_share >= 0.5:
        return "PREMIUM"
    return "COST_CONSCIOUS"


async def fetch_customer_lines(customer_id: str) -> list:
    """All receipt line items for one customer."""
    return await select_rows(TABLE, {"customer_id": f"eq.{customer_id}", "limit": "5000"})


async def classify_customer_live(customer_id: str) -> dict:
    """
    Classify a customer from their real Collect&Go order history.

    Returns: recipe_profile, orders, avg_basket, bio_pct, boni_pct,
    national_pct, promo_pct, upsell_goal, mix_per_3, mix_per_5.
    """
    lines = await fetch_customer_lines(customer_id)
    if not lines:
        raise ValueError(f"No receipt history found for customer '{customer_id}'")

    n = len(lines)
    bio_share = sum(1 for r in lines if r["is_bio"]) / n
    boni_share = sum(1 for r in lines if r["is_boni"]) / n
    national_share = sum(1 for r in lines if tier_of(r["brand"], r["is_bio"]) == "Nationaal A-merk") / n
    promo_share = sum(1 for r in lines if r["is_promo"]) / n

    baskets = Counter()
    for r in lines:
        baskets[r["receipt_id"]] += float(r["line_total_eur"])
    orders = len(baskets)
    avg_basket = sum(baskets.values()) / orders

    profile = _profile_label(bio_share, national_share)
    strategy = PROFILE_STRATEGY[profile]
    mix_per_3 = dict(strategy["mix_per_3"])

    return {
        "customer_id": customer_id,
        "recipe_profile": profile,
        "orders": orders,
        "avg_basket": round(avg_basket, 2),
        "bio_pct": round(bio_share * 100),
        "boni_pct": round(boni_share * 100),
        "national_pct": round(national_share * 100),
        "promo_pct": round(promo_share * 100),
        "upsell_goal": strategy["upsell_goal"],
        "mix_per_3": mix_per_3,
        "mix_per_5": _scale_mix(mix_per_3, 5),
    }
