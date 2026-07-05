"""TheMealDB adapter — modern, authentic, cuisine-tagged recipes.

Free JSON API (test key "1"), already structured (ingredients + measures +
instructions + area), so no OCR and no prose-parsing. Fills the cuisines
Gutenberg is weak on: Spanish, Thai, Turkish, Chinese, Vietnamese, Mexican,
Japanese, Greek, etc. The whole free DB is ~733 meals; the a-z search endpoint
returns full meal objects, so 26 calls gets everything.
"""

import string
import requests

from .config import USER_AGENT

BASE = "https://www.themealdb.com/api/json/v1/1"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

# TheMealDB mixes demonyms and country names in strArea — fold to the demonym so
# its cuisines merge cleanly with the Gutenberg tags.
_AREA_NORMALIZE = {
    "France": "French", "Italy": "Italian", "China": "Chinese", "Japan": "Japanese",
    "India": "Indian", "Spain": "Spanish", "Portugal": "Portuguese", "Mexico": "Mexican",
    "Greece": "Greek", "Turkey": "Turkish", "Vietnam": "Vietnamese", "Thailand": "Thai",
    "Norway": "Norwegian", "Netherlands": "Dutch", "Poland": "Polish", "Russia": "Russian",
    "Ukraine": "Ukrainian", "Croatia": "Croatian", "Egypt": "Egyptian", "Morocco": "Moroccan",
    "Tunisia": "Tunisian", "Kenya": "Kenyan", "Argentina": "Argentine", "Uruguay": "Uruguayan",
    "Venezuela": "Venezuelan", "Slovakia": "Slovak", "United States": "American",
    "Malaysia": "Malaysian", "Ireland": "Irish", "Canada": "Canadian",
}


def fetch_all():
    """Return every meal in the free DB as raw TheMealDB dicts (de-duped)."""
    meals = {}
    for letter in string.ascii_lowercase:
        r = _session.get(f"{BASE}/search.php?f={letter}", timeout=30)
        r.raise_for_status()
        for m in (r.json().get("meals") or []):
            meals[m["idMeal"]] = m
    return list(meals.values())


def to_recipe(m):
    """Convert a raw TheMealDB meal into pot-scraper's recipe shape.

    Returns None for meals with no usable ingredients/instructions.
    """
    pairs = []
    for i in range(1, 21):
        ing = (m.get(f"strIngredient{i}") or "").strip()
        meas = (m.get(f"strMeasure{i}") or "").strip()
        if ing:
            pairs.append((meas, ing))
    instructions = (m.get("strInstructions") or "").strip()
    if not pairs or len(instructions) < 40:
        return None

    # Build a body that carries both the ingredient list and the method, so the
    # pantry scanner can see the ingredients and the display reads as a recipe.
    ing_lines = "\n".join(f"- {meas} {ing}".strip() for meas, ing in pairs)
    body = f"Ingredients:\n{ing_lines}\n\nMethod:\n{instructions}"

    area = (m.get("strArea") or "").strip()
    if not area or area == "Unknown":
        return None                      # no cuisine = useless for a cuisine app
    area = _AREA_NORMALIZE.get(area, area)
    source_url = (m.get("strSource") or "").strip() or f"https://www.themealdb.com/meal/{m['idMeal']}"

    return {
        "title": m["strMeal"].strip(),
        "body": body,
        "cuisine": area,
        "source_title": f"TheMealDB — {area}",
        "source_author": "TheMealDB",
        "source_id": "themealdb",
        "source_meal_id": m["idMeal"],
        "source_url": source_url,
        "image": (m.get("strMealThumb") or "").strip(),
    }
