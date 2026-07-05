"""Practicality scoring: can you cook this from a Charleston grocery run?"""

import re

from .pantry import scan
from .config import PRACTICAL_THRESHOLD

# Verbs and quantity units that show up thick in real recipes but sparsely in
# the essays/ads that old cookbook-magazines mix in. Used to reject prose that
# merely *mentions* food from scoring as a cookable recipe.
_COOK_VERB = re.compile(
    r"\b(bake|baked|baking|boil|boiled|boiling|stir|simmer|roast|roasted|fry|"
    r"fried|broil|broiled|chop|chopped|mince|minced|knead|grease|greased|"
    r"grate|grated|whisk|beat|beaten|pour|sprinkle|season|dredge|parboil|"
    r"stew|stewed|braise|saute|preheat|dissolve|strain|strained|garnish|"
    r"baste|marinate|blanch|scald|simmer|thicken|mix|mixed|knead)\b", re.I)
_QUANTITY = re.compile(
    r"\b(cup|cups|tablespoon|tablespoons|teaspoon|teaspoons|tbsp|tsp|ounce|"
    r"ounces|oz|pound|pounds|lb|lbs|pint|pints|quart|quarts|gill|dozen|pinch|"
    r"cupful|spoonful|teacupful|wineglass)\b", re.I)


def _recipe_signal(text):
    """How 'recipe-like' the prose is: distinct cooking verbs + quantity hits."""
    verbs = {m.group(0).lower() for m in _COOK_VERB.finditer(text)}
    quantities = len(_QUANTITY.findall(text))
    return len(verbs) + min(quantities, 4)


def score_recipe(recipe):
    """Attach practicality data to a recipe dict (mutates + returns it).

    Adds:
      ingredients   -> [{name, stores}]
      hard          -> [{name, reason}]
      measures      -> [{unit, modern}]
      score         -> 0-10 int (0 = probably not a real recipe)
      practical     -> bool
    """
    body = recipe["body"]
    found = scan(recipe["title"] + "\n" + body)
    avail = found["available"]
    hard = found["hard"]
    measures = found["measures"]

    if len(avail) < 2 or _recipe_signal(body) < 3:
        # Too few recognizable ingredients, or prose that doesn't read like
        # cooking instructions (an index entry, a chapter intro, a magazine
        # essay that merely mentions food) — not a cookable recipe.
        score = 0
    else:
        # "Practical" = you can source it locally AND cook it without a project.
        # Start at 10 and dock for the things that make that harder.
        n_ing = len(avail) + len(hard)
        words = len(body.split())
        s = 10.0

        # 1. Sourceability — each hard-to-find item is a real blocker/substitution.
        s -= 2.5 * len(hard)

        # 2. Simplicity — a 15-ingredient banquet dish isn't a weeknight cook,
        #    even if every ingredient is at Walmart.
        if n_ing >= 16:
            s -= 5.5
        elif n_ing >= 12:
            s -= 4
        elif n_ing >= 9:
            s -= 2.5
        elif n_ing >= 6:
            s -= 1

        # 3. Effort — long method sections mean fiddly, multi-stage recipes.
        if words > 600:
            s -= 4.5
        elif words > 400:
            s -= 3
        elif words > 250:
            s -= 1.5
        elif words > 130:
            s -= 0.5

        # 4. Archaic-measure friction — light touch, since `modernize` fixes it.
        s -= 0.5 * min(len(measures), 4)

        score = max(1, min(10, round(s)))

    recipe["ingredients"] = [{"name": n, "stores": s} for n, s in avail]
    recipe["hard"] = [{"name": n, "reason": r} for n, r in hard]
    recipe["measures"] = [{"unit": u, "modern": m} for u, m in found["measures"]]
    recipe["score"] = score
    recipe["practical"] = score >= PRACTICAL_THRESHOLD
    return recipe


def shopping_list(recipe):
    """Group buyable ingredients by store for a quick Charleston run."""
    by_store = {}
    for ing in recipe.get("ingredients", []):
        # send each item to its cheapest/nearest single store (first listed)
        store = ing["stores"][0]
        by_store.setdefault(store, []).append(ing["name"])
    return by_store
