"""
Classify a Collect&Go customer's brand-tier buying pattern from their receipt
history, and derive a suggested upsell mix for missing-ingredient suggestions.

    classify_customer(customer_id, data_path=DATA_PATH) -> (profile, strategy)

Brand tiers (budget → premium): Everyday, Boni Selection, Boni Bio, Bio-Time,
Nationaal A-merk. See collect_and_go.tier_of() for the brand → tier mapping —
this module imports it so the two stay in sync.
"""

from pathlib import Path
from collections import Counter

import pandas as pd

from app.services.collectandgo.collect_and_go import TIER_ORDER, tier_of

DATA_PATH = str(Path(__file__).with_name("CollectAndGo_synthetic_receipts.xlsx"))


def _tier_shares(customer_id: str, data_path: str = DATA_PATH) -> dict[str, float]:
    """Fraction of this customer's line items falling in each brand tier."""
    li = pd.read_excel(data_path, sheet_name="Line_Items")
    mine = li[li["customer_id"] == customer_id]
    if mine.empty:
        return {t: 0.0 for t in TIER_ORDER}

    tiers = [tier_of(row.brand, row.is_bio == "Ja") for row in mine.itertuples()]
    counts = Counter(tiers)
    total = sum(counts.values())
    return {t: counts.get(t, 0) / total for t in TIER_ORDER}


def _profile_label(shares: dict[str, float]) -> str:
    everyday = shares.get("Everyday", 0.0)
    national = shares.get("Nationaal A-merk", 0.0)
    organic = shares.get("Boni Bio", 0.0) + shares.get("Bio-Time", 0.0)

    if everyday >= 0.5:
        return "Budget-conscious"
    if national >= 0.5:
        return "Brand loyalist"
    if organic >= 0.4:
        return "Health & organic focused"
    return "Balanced shopper"


def _mix_from_shares(shares: dict[str, float], total: int = 3) -> dict[str, int]:
    """Largest-remainder rounding of `shares` into `total` integer slots."""
    raw = {t: shares.get(t, 0.0) * total for t in TIER_ORDER}
    floors = {t: int(raw[t]) for t in TIER_ORDER}
    remainder = total - sum(floors.values())
    fracs = sorted(TIER_ORDER, key=lambda t: raw[t] - floors[t], reverse=True)
    for t in fracs[:remainder]:
        floors[t] += 1
    return floors


def _nudge_upmarket(mix: dict[str, int]) -> dict[str, int]:
    """
    Shift one budget-tier slot up a notch — a gentle "try a better brand" nudge
    rather than just mirroring exactly what the customer already buys.
    """
    mix = dict(mix)
    for lower, upper in zip(TIER_ORDER, TIER_ORDER[1:]):
        if mix.get(lower, 0) >= 2:
            mix[lower] -= 1
            mix[upper] = mix.get(upper, 0) + 1
            break
    return mix


def classify_customer(customer_id: str, data_path: str = DATA_PATH) -> tuple[str, dict]:
    """
    Returns (profile_label, strategy) where strategy has:
        tier_shares               — this customer's historical tier distribution
        suggested_mix_per_3_items — {tier: count} summing to 3, nudged one notch
                                     upmarket from their raw historical mix
    """
    shares = _tier_shares(customer_id, data_path)
    profile = _profile_label(shares)
    base_mix = _mix_from_shares(shares, total=3)
    suggested_mix = {t: c for t, c in _nudge_upmarket(base_mix).items() if c > 0}

    return profile, {
        "tier_shares": {t: round(v, 3) for t, v in shares.items()},
        "suggested_mix_per_3_items": suggested_mix,
    }


if __name__ == "__main__":
    for cust_id in ["CUST001", "CUST003", "CUST005", "CUST006"]:
        profile, strategy = classify_customer(cust_id)
        print(f"{cust_id}: {profile}  mix={strategy['suggested_mix_per_3_items']}  shares={strategy['tier_shares']}")
