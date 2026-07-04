"""
Collect&Go — missing-ingredient upsell suggester.

    suggest_articles(ingredient, upsell_mix, search_fn=search_local) -> dict

Given a missing ingredient (e.g. "melk", "pasta") and an upsell mix produced by
classify_customer (e.g. {"Everyday": 1, "Boni Selection": 2}), it searches the
Collect&Go assortment, tiers each matching article by brand, and returns the
articles that fill the requested per-tier mix — plus honest shortfall reporting.

Search is PLUGGABLE:
  • search_local        (default) — searches the synthetic dataset catalog, so the
                         whole pipeline runs offline and is fully testable.
  • search_collectandgo — live hook against collectandgo.be. The public site is a
                         login-/store-gated single-page app with no documented
                         public API, so this requires YOUR authenticated session
                         (cookies) + a chosen pickup point, and the endpoint/parse
                         must be confirmed against the network tab. See its docstring.

Brand tiers used everywhere (must match classify_customer's mix keys):
  "Everyday"  <  "Boni Selection"  <  "Boni Bio"  <  "Bio-Time"  <  "Nationaal A-merk"
"""

from pathlib import Path
import re
import pandas as pd

DATA_PATH = str(Path(__file__).with_name("CollectAndGo_synthetic_receipts.xlsx"))

# tier ranking (low = budget, high = premium) used for shortfall fallback
TIER_ORDER = ["Everyday", "Boni Selection", "Boni Bio", "Bio-Time", "Nationaal A-merk"]
_PRIVATE_LABEL = {"Everyday", "Boni Selection", "Boni Bio", "Bio-Time", "Colruyt"}


def tier_of(brand, is_bio=False):
    """Map a brand (+ bio flag) to one of the TIER_ORDER labels."""
    b = str(brand)
    if b == "Everyday":
        return "Everyday"
    if b == "Bio-Time":
        return "Bio-Time"
    if b == "Boni Bio":
        return "Boni Bio"
    if "Boni" in b:
        return "Boni Bio" if is_bio else "Boni Selection"
    if b == "Colruyt":
        return "Boni Selection"          # own budget line (e.g. Cara Pils)
    return "Nationaal A-merk"


# --------------------------------------------------------------------- search
def _catalog_from_dataset(data_path=DATA_PATH):
    """Distinct articles from the synthetic dataset, as the assortment proxy."""
    li = pd.read_excel(data_path, sheet_name="Line_Items")
    cat = (li.sort_values("unit_price_eur")
             .drop_duplicates(["product", "brand"])
             [["product", "brand", "category", "unit", "unit_price_eur", "is_bio"]])
    out = []
    for _, r in cat.iterrows():
        out.append({
            "product": r["product"],
            "brand": r["brand"],
            "category": r["category"],
            "unit": r["unit"],
            "price_eur": round(float(r["unit_price_eur"]), 2),
            "tier": tier_of(r["brand"], r["is_bio"] == "Ja"),
        })
    return out


def search_local(ingredient, data_path=DATA_PATH):
    """Offline search: match the ingredient against product name / category."""
    toks = [t for t in re.split(r"\W+", ingredient.lower()) if len(t) > 2]
    if not toks:
        toks = [ingredient.lower()]
    hits = []
    for a in _catalog_from_dataset(data_path):
        hay = f"{a['product']} {a['category']}".lower()
        if any(t in hay for t in toks):
            hits.append(a)
    return hits


def search_collectandgo(ingredient, session, base_url="https://www.collectandgo.be",
                        lang="nl", limit=24):
    """
    LIVE hook for collectandgo.be (template — verify before production use).

    The public site renders products client-side via an internal JSON endpoint and
    requires an authenticated session + selected pickup point to return articles and
    prices. Steps to wire this up reliably:
      1. Log in on collectandgo.be and pick a store in a real browser.
      2. Open DevTools > Network, search a term, and copy the XHR the page fires
         (path, query params, and the JSON response shape).
      3. Set `endpoint`/params/parsing below to match what you observed.
      4. Pass a `requests.Session` carrying your auth cookies as `session`.

    Returns the same article dict shape as search_local so suggest_articles works
    unchanged. Raises if the response can't be parsed — no silent guessing.
    """
    # NOTE: path + response keys below are placeholders to be confirmed in step 2/3.
    endpoint = f"{base_url}/{lang}/api/products/search"
    resp = session.get(endpoint, params={"q": ingredient, "limit": limit}, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    raw = payload.get("products") or payload.get("results") or payload.get("data") or []
    out = []
    for p in raw:
        brand = p.get("brand") or p.get("brandName") or ""
        is_bio = bool(p.get("isBio")) or "bio" in str(p.get("labels", "")).lower()
        out.append({
            "product": p.get("name") or p.get("title") or p.get("description", ""),
            "brand": brand,
            "category": p.get("category") or p.get("categoryName", ""),
            "unit": p.get("content") or p.get("quantity", ""),
            "price_eur": p.get("price") or p.get("salesPrice"),
            "tier": tier_of(brand, is_bio),
            "url": p.get("url") or p.get("productUrl"),
        })
    return out


# ------------------------------------------------------------------- ranking
def _sort_key(rank_by):
    return (lambda a: (a["price_eur"] is None, a["price_eur"] or 0)) if rank_by == "price" \
        else (lambda a: a["product"])


def suggest_articles(ingredient, upsell_mix, search_fn=search_local,
                     rank_by="price", fill_shortfall=True, **search_kwargs):
    """
    Return upsell article suggestions for a missing ingredient.

    ingredient   : e.g. "melk", "pasta", "koffie"
    upsell_mix   : {tier: count}, e.g. {"Everyday": 1, "Boni Selection": 2}
                   (use classify_customer(...)[1]["suggested_mix_per_3_items"])
    search_fn    : search_local (default) or search_collectandgo
    rank_by      : "price" (cheapest first within a tier) or "name"
    fill_shortfall: if a tier lacks enough matches, borrow from the nearest tier.

    Returns dict: {ingredient, requested_mix, suggestions[], by_tier{}, shortfall{}, found}
    """
    articles = list(search_fn(ingredient, **search_kwargs))
    articles.sort(key=_sort_key(rank_by))

    by_tier = {}
    for a in articles:
        by_tier.setdefault(a["tier"], []).append(a)

    used = set()
    suggestions, out_by_tier, shortfall = [], {}, {}

    def take(pool, k):
        picked = []
        for a in pool:
            if id(a) in used:
                continue
            picked.append(a); used.add(id(a))
            if len(picked) == k:
                break
        return picked

    for tier, count in upsell_mix.items():
        picked = take(by_tier.get(tier, []), count)
        missing = count - len(picked)

        if missing and fill_shortfall:
            # borrow from nearest tiers by rank distance
            ref = TIER_ORDER.index(tier) if tier in TIER_ORDER else len(TIER_ORDER)
            nearest = sorted(
                (t for t in by_tier if t != tier),
                key=lambda t: abs((TIER_ORDER.index(t) if t in TIER_ORDER else 99) - ref))
            for t in nearest:
                if missing == 0:
                    break
                borrowed = take(by_tier[t], missing)
                for b in borrowed:
                    b = dict(b); b["substituted_for_tier"] = tier
                    picked.append(b)
                missing -= len(borrowed)

        if missing:
            shortfall[tier] = missing
        out_by_tier[tier] = picked
        suggestions.extend(picked)

    return {
        "ingredient": ingredient,
        "requested_mix": dict(upsell_mix),
        "found": len(articles),
        "suggestions": suggestions,
        "by_tier": out_by_tier,
        "shortfall": shortfall,
    }


# ------------------------------------------------------------------- demo
if __name__ == "__main__":
    from classify_customer import classify_customer

    demos = [("CUST001", "melk"), ("CUST003", "pasta"), ("CUST005", "koffie")]
    for cid, ingredient in demos:
        profile, strat = classify_customer(cid)
        mix = strat["suggested_mix_per_3_items"]
        res = suggest_articles(ingredient, mix)
        print(f"\n{cid}  profile={profile}  missing ingredient='{ingredient}'  mix={mix}")
        for a in res["suggestions"]:
            sub = f"  (i.p.v. {a['substituted_for_tier']})" if "substituted_for_tier" in a else ""
            print(f"   [{a['tier']:<16}] {a['product']:<42} €{a['price_eur']}{sub}")
        if res["shortfall"]:
            print(f"   ! tekort in assortiment: {res['shortfall']}")
