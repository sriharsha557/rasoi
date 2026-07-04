"""
Cuisine-aware Indian brand suggestions for missing ingredients.

A small curated map of common Indian kitchen staples to popular Indian brands
with approximate ₹ prices. Used when the recipe's cuisine is Indian, as an
alternative to the Belgian Collect&Go (Colruyt) catalog. Prices are
illustrative, not live.
"""

from urllib.parse import quote_plus

# ingredient keyword -> curated Indian brand products (value → premium)
_INDIAN_CATALOG: dict[str, list[dict]] = {
    "butter": [
        {"product": "Milky Mist Butter", "brand": "Milky Mist", "unit": "500 g", "price": 255, "tier": "Value"},
        {"product": "Amul Butter", "brand": "Amul", "unit": "500 g", "price": 265, "tier": "Popular"},
        {"product": "Nandini Butter", "brand": "Nandini", "unit": "500 g", "price": 245, "tier": "Value"},
    ],
    "milk": [
        {"product": "Nandini Toned Milk", "brand": "Nandini", "unit": "1 L", "price": 54, "tier": "Value"},
        {"product": "Amul Taaza Toned Milk", "brand": "Amul", "unit": "1 L", "price": 66, "tier": "Popular"},
        {"product": "Milky Mist Full Cream Milk", "brand": "Milky Mist", "unit": "1 L", "price": 74, "tier": "Premium"},
    ],
    "paneer": [
        {"product": "Milky Mist Paneer", "brand": "Milky Mist", "unit": "200 g", "price": 99, "tier": "Popular"},
        {"product": "Amul Malai Paneer", "brand": "Amul", "unit": "200 g", "price": 95, "tier": "Popular"},
        {"product": "iD Fresh Paneer", "brand": "iD Fresh", "unit": "200 g", "price": 89, "tier": "Value"},
    ],
    "curd": [
        {"product": "Milky Mist Curd", "brand": "Milky Mist", "unit": "400 g", "price": 40, "tier": "Popular"},
        {"product": "Amul Masti Dahi", "brand": "Amul", "unit": "400 g", "price": 38, "tier": "Value"},
        {"product": "Nestlé a+ Dahi", "brand": "Nestlé", "unit": "400 g", "price": 45, "tier": "Premium"},
    ],
    "yogurt": [
        {"product": "Epigamia Greek Yogurt", "brand": "Epigamia", "unit": "400 g", "price": 90, "tier": "Premium"},
        {"product": "Amul Masti Dahi", "brand": "Amul", "unit": "400 g", "price": 38, "tier": "Value"},
        {"product": "Milky Mist Greek Yogurt", "brand": "Milky Mist", "unit": "400 g", "price": 80, "tier": "Popular"},
    ],
    "ghee": [
        {"product": "Amul Pure Ghee", "brand": "Amul", "unit": "1 L", "price": 640, "tier": "Popular"},
        {"product": "GRB Ghee", "brand": "GRB", "unit": "1 L", "price": 610, "tier": "Value"},
        {"product": "Milky Mist Ghee", "brand": "Milky Mist", "unit": "1 L", "price": 660, "tier": "Premium"},
    ],
    "cheese": [
        {"product": "Amul Cheese Slices", "brand": "Amul", "unit": "200 g", "price": 130, "tier": "Popular"},
        {"product": "Go Cheese Cubes", "brand": "Go", "unit": "200 g", "price": 145, "tier": "Premium"},
        {"product": "Britannia Cheese Block", "brand": "Britannia", "unit": "200 g", "price": 125, "tier": "Value"},
    ],
    "cream": [
        {"product": "Amul Fresh Cream", "brand": "Amul", "unit": "250 ml", "price": 75, "tier": "Popular"},
        {"product": "Milky Mist Fresh Cream", "brand": "Milky Mist", "unit": "250 ml", "price": 78, "tier": "Premium"},
    ],
    "bread": [
        {"product": "Britannia Brown Bread", "brand": "Britannia", "unit": "400 g", "price": 45, "tier": "Popular"},
        {"product": "Modern Sandwich Bread", "brand": "Modern", "unit": "400 g", "price": 40, "tier": "Value"},
        {"product": "English Oven Multigrain", "brand": "English Oven", "unit": "400 g", "price": 60, "tier": "Premium"},
    ],
    "oil": [
        {"product": "Fortune Sunflower Oil", "brand": "Fortune", "unit": "1 L", "price": 150, "tier": "Popular"},
        {"product": "Gold Winner Oil", "brand": "Gold Winner", "unit": "1 L", "price": 140, "tier": "Value"},
        {"product": "Saffola Gold Oil", "brand": "Saffola", "unit": "1 L", "price": 175, "tier": "Premium"},
    ],
    "rice": [
        {"product": "India Gate Basmati", "brand": "India Gate", "unit": "1 kg", "price": 130, "tier": "Popular"},
        {"product": "Daawat Rozana Basmati", "brand": "Daawat", "unit": "1 kg", "price": 95, "tier": "Value"},
        {"product": "Kohinoor Super Basmati", "brand": "Kohinoor", "unit": "1 kg", "price": 160, "tier": "Premium"},
    ],
    "atta": [
        {"product": "Aashirvaad Atta", "brand": "Aashirvaad", "unit": "5 kg", "price": 270, "tier": "Popular"},
        {"product": "Fortune Chakki Atta", "brand": "Fortune", "unit": "5 kg", "price": 255, "tier": "Value"},
        {"product": "Pillsbury Chakki Atta", "brand": "Pillsbury", "unit": "5 kg", "price": 265, "tier": "Popular"},
    ],
    "flour": [
        {"product": "Aashirvaad Atta", "brand": "Aashirvaad", "unit": "5 kg", "price": 270, "tier": "Popular"},
        {"product": "Fortune Chakki Atta", "brand": "Fortune", "unit": "5 kg", "price": 255, "tier": "Value"},
    ],
    "sugar": [
        {"product": "Madhur Pure Sugar", "brand": "Madhur", "unit": "1 kg", "price": 48, "tier": "Popular"},
        {"product": "Dhampure Sugar", "brand": "Dhampure", "unit": "1 kg", "price": 52, "tier": "Premium"},
    ],
    "tea": [
        {"product": "Tata Tea Gold", "brand": "Tata Tea", "unit": "500 g", "price": 275, "tier": "Popular"},
        {"product": "Red Label Tea", "brand": "Brooke Bond", "unit": "500 g", "price": 260, "tier": "Value"},
        {"product": "Taj Mahal Tea", "brand": "Taj Mahal", "unit": "500 g", "price": 320, "tier": "Premium"},
    ],
    "salt": [
        {"product": "Tata Salt", "brand": "Tata", "unit": "1 kg", "price": 28, "tier": "Popular"},
        {"product": "Aashirvaad Salt", "brand": "Aashirvaad", "unit": "1 kg", "price": 30, "tier": "Value"},
    ],
    "masala": [
        {"product": "Everest Garam Masala", "brand": "Everest", "unit": "100 g", "price": 75, "tier": "Popular"},
        {"product": "MDH Garam Masala", "brand": "MDH", "unit": "100 g", "price": 80, "tier": "Popular"},
        {"product": "Catch Garam Masala", "brand": "Catch", "unit": "100 g", "price": 70, "tier": "Value"},
    ],
}


def _collect_and_go_url(product_name: str) -> str:
    return f"https://www.collectandgo.be/nl/search?text={quote_plus(product_name)}"


def _match_key(ingredient: str) -> str | None:
    ing = ingredient.strip().lower()
    if ing in _INDIAN_CATALOG:
        return ing
    for key in _INDIAN_CATALOG:
        if key in ing or ing in key:
            return key
    return None


def suggest_indian_brands(ingredient: str, max_items: int = 3) -> list[dict]:
    """Return up to `max_items` Indian brand products for a missing ingredient."""
    key = _match_key(ingredient)
    products = _INDIAN_CATALOG.get(key, []) if key else []
    out: list[dict] = []
    for p in products[:max_items]:
        out.append({
            "product": p["product"],
            "brand": p["brand"],
            "category": key or "grocery",
            "unit": p["unit"],
            "price_eur": p["price"],   # numeric price (₹ here; see currency)
            "currency": "INR",
            "tier": p["tier"],
            "shopUrl": _collect_and_go_url(p["product"]),
        })
    return out
