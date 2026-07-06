"""Spoonacular adapter — real, modern, rated recipes.

Needs a free API key (spoonacular.com/food-api) in SPOONACULAR_API_KEY. We bias
toward Instant-Pot-friendly dish types (stews, curries, soups, braises, beans,
chili, risotto, roasts) since those translate best to pressure cooking — the
`cook it 3 ways` step then adds Instant Pot / air-fryer / stovetop methods.

Free tier is ~150 points/day, so pull a modest curated set and cache it.
"""

import os
import requests

from .config import USER_AGENT

BASE = "https://api.spoonacular.com/recipes/complexSearch"
RANDOM = "https://api.spoonacular.com/recipes/random"

# Dish types that shine in an Instant Pot and translate cleanly to stovetop.
IP_FRIENDLY_QUERIES = [
    "stew", "curry", "soup", "chili", "braised", "risotto", "beans",
    "pot roast", "pulled pork", "lentil", "chickpea", "shredded chicken",
]

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _key():
    k = os.environ.get("SPOONACULAR_API_KEY")
    if not k:
        raise RuntimeError(
            "SPOONACULAR_API_KEY not set. Get a free key at "
            "spoonacular.com/food-api and put it in ~/.pot-scraper/.env"
        )
    return k


def search(query=None, cuisine=None, number=20):
    """Return raw Spoonacular recipe dicts (full info + ingredients + steps)."""
    params = {
        "apiKey": _key(),
        "number": number,
        "addRecipeInformation": True,
        "addRecipeInstructions": True,
        "fillIngredients": True,
        "instructionsRequired": True,
        "sort": "popularity",
    }
    if query:
        params["query"] = query
    if cuisine:
        params["cuisine"] = cuisine
    r = _session.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def fetch_ip_friendly(per_query=12):
    """Pull a curated set of Instant-Pot-friendly recipes across dish types."""
    out, seen = [], set()
    for q in IP_FRIENDLY_QUERIES:
        for m in search(query=q, number=per_query):
            if m["id"] not in seen:
                seen.add(m["id"])
                out.append(m)
    return out


def fetch_random(total=200, tags="main course"):
    """Pull random real recipes — ~10x cheaper per point than complexSearch,
    and perfect for a random menu. Paginated in blocks of 100."""
    out = []
    while len(out) < total:
        n = min(100, total - len(out))
        params = {"apiKey": _key(), "number": n}
        if tags:
            params["include-tags"] = tags
        r = _session.get(RANDOM, params=params, timeout=30)
        r.raise_for_status()
        got = r.json().get("recipes", [])
        if not got:
            break
        out += got
    return out


def to_recipe(m):
    """Convert a Spoonacular recipe into pot-scraper's shape."""
    ings = m.get("extendedIngredients") or []
    if not ings:
        return None
    ing_lines = []
    for ing in ings:
        original = (ing.get("original") or ing.get("name") or "").strip()
        if original:
            ing_lines.append(f"- {original}")

    steps = []
    for block in (m.get("analyzedInstructions") or []):
        for step in (block.get("steps") or []):
            t = (step.get("step") or "").strip()
            if t:
                steps.append(t)
    method = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    if not method:
        return None

    body = "Ingredients:\n" + "\n".join(ing_lines) + "\n\nMethod:\n" + method
    cuisines = m.get("cuisines") or []
    cuisine = cuisines[0] if cuisines else ""   # blank beats a wrong dishType label

    return {
        "title": (m.get("title") or "Untitled").strip(),
        "body": body,
        "cuisine": cuisine,
        "source_title": "Spoonacular",
        "source_author": (m.get("sourceName") or "Spoonacular").strip(),
        "source_id": "spoonacular",
        "source_meal_id": str(m["id"]),
        "source_url": (m.get("sourceUrl") or f"https://spoonacular.com/recipes/{m['id']}"),
        "image": (m.get("image") or "").strip(),
        "ready_minutes": m.get("readyInMinutes"),
    }
