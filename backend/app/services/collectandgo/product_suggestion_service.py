"""
Orchestrates the missing-ingredient upsell decision:

  1. If the user has explicit onboarding preferences (a set budget), derive
     the brand-tier mix from budget-per-person — respects what they told us.
  2. Otherwise, fall back to classify_customer()'s purchase-history-derived
     mix from their Collect&Go receipts.
  3. Run suggest_articles() against that mix to get real (synthetic-catalog)
     products, then attach a Collect&Go search link to each as a stand-in
     "shop" action until the real product-page API is wired in.

Onboarding budgets may be entered in € or ₹ (see budgetCurrency); the
Collect&Go catalog itself is always priced in €, so a ₹ budget is converted
via a fixed illustrative rate before applying the per-person/month bands
below — not a precise model, not a live FX rate.
"""

from urllib.parse import quote_plus

from app.services.collectandgo.classify_customer import classify_customer
from app.services.collectandgo.collect_and_go import suggest_articles

DEFAULT_CUSTOMER_ID = "CUST001"

# Illustrative, fixed conversion — not a live exchange rate.
INR_TO_EUR_RATE = 1 / 90


def _mix_from_budget(budget_amount: float, budget_period: str, family_size: int, budget_currency: str = "EUR") -> dict[str, int]:
    """Map a stated pantry budget to a brand-tier mix (illustrative € bands)."""
    if budget_currency == "INR":
        budget_amount = budget_amount * INR_TO_EUR_RATE

    monthly = budget_amount if budget_period == "monthly" else budget_amount * 4.33
    per_person = monthly / max(family_size, 1)

    if per_person < 60:
        return {"Everyday": 2, "Boni Selection": 1}
    if per_person < 120:
        return {"Everyday": 1, "Boni Selection": 1, "Boni Bio": 1}
    if per_person < 200:
        return {"Boni Selection": 1, "Boni Bio": 1, "Nationaal A-merk": 1}
    return {"Boni Bio": 1, "Bio-Time": 1, "Nationaal A-merk": 1}


def _collect_and_go_search_url(product_name: str) -> str:
    return f"https://www.collectandgo.be/nl/search?text={quote_plus(product_name)}"


def suggest_for_missing_ingredient(
    ingredient: str,
    preferences: dict | None = None,
    customer_id: str = DEFAULT_CUSTOMER_ID,
) -> dict:
    """
    Returns {ingredient, source, profile, mix, suggestions[], shortfall}.
    `source` is "preference" (budget-derived) or "purchase_history" (classify_customer).
    Each suggestion dict gets a `shopUrl` (Collect&Go search link) added.
    """
    has_preference = bool(
        preferences
        and preferences.get("onboardingCompleted")
        and preferences.get("budgetAmount")
    )

    if has_preference:
        mix = _mix_from_budget(
            preferences["budgetAmount"],
            preferences.get("budgetPeriod") or "monthly",
            preferences.get("familySize") or 1,
            preferences.get("budgetCurrency") or "EUR",
        )
        source = "preference"
        profile = "Based on your stated pantry budget"
    else:
        profile, strategy = classify_customer(customer_id)
        mix = strategy["suggested_mix_per_3_items"]
        source = "purchase_history"

    result = suggest_articles(ingredient, mix)
    for item in result["suggestions"]:
        item["shopUrl"] = _collect_and_go_search_url(item["product"])

    return {
        "ingredient": ingredient,
        "source": source,
        "profile": profile,
        "mix": mix,
        "suggestions": result["suggestions"],
        "shortfall": result["shortfall"],
    }
