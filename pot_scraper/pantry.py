"""Charleston, SC pantry knowledge.

The whole 'practical' idea lives here: which ingredients you can grab today at
Walmart, Aldi, or Costco, and which ones are archaic / hard to source out of an
1800s cookbook. Matching is done against recipe *prose* (old cookbooks rarely
have tidy ingredient lists), so entries are lowercase substrings/words.
"""

import re

# Stores, in the order we like to shop them here.
WALMART = "Walmart"
ALDI = "Aldi"
COSTCO = "Costco"

# ingredient keyword -> stores that reliably carry it in the Charleston area.
# Kept broad on purpose: we match these words inside recipe text.
AVAILABLE = {
    # pantry staples
    "flour": [WALMART, ALDI, COSTCO],
    "sugar": [WALMART, ALDI, COSTCO],
    "brown sugar": [WALMART, ALDI],
    "salt": [WALMART, ALDI, COSTCO],
    "pepper": [WALMART, ALDI, COSTCO],
    "baking soda": [WALMART, ALDI],
    "baking powder": [WALMART, ALDI],
    "yeast": [WALMART, ALDI],
    "cornmeal": [WALMART, ALDI],
    "cornstarch": [WALMART, ALDI],
    "corn starch": [WALMART, ALDI],
    "oats": [WALMART, ALDI, COSTCO],
    "oatmeal": [WALMART, ALDI],
    "rice": [WALMART, ALDI, COSTCO],
    "vinegar": [WALMART, ALDI],
    "honey": [WALMART, ALDI, COSTCO],
    "molasses": [WALMART],
    "vanilla": [WALMART, ALDI],
    "cocoa": [WALMART, ALDI],
    "chocolate": [WALMART, ALDI, COSTCO],
    "olive oil": [WALMART, ALDI, COSTCO],
    "vegetable oil": [WALMART, ALDI, COSTCO],
    "oil": [WALMART, ALDI, COSTCO],
    "breadcrumbs": [WALMART, ALDI],
    "bread crumbs": [WALMART, ALDI],
    "bread": [WALMART, ALDI, COSTCO],
    # dairy + eggs
    "butter": [WALMART, ALDI, COSTCO],
    "milk": [WALMART, ALDI, COSTCO],
    "cream": [WALMART, ALDI, COSTCO],
    "egg": [WALMART, ALDI, COSTCO],
    "eggs": [WALMART, ALDI, COSTCO],
    "cheese": [WALMART, ALDI, COSTCO],
    "buttermilk": [WALMART, ALDI],
    # produce
    "onion": [WALMART, ALDI, COSTCO],
    "garlic": [WALMART, ALDI, COSTCO],
    "potato": [WALMART, ALDI, COSTCO],
    "potatoes": [WALMART, ALDI, COSTCO],
    "carrot": [WALMART, ALDI, COSTCO],
    "carrots": [WALMART, ALDI, COSTCO],
    "celery": [WALMART, ALDI, COSTCO],
    "tomato": [WALMART, ALDI, COSTCO],
    "tomatoes": [WALMART, ALDI, COSTCO],
    "cabbage": [WALMART, ALDI],
    "lettuce": [WALMART, ALDI, COSTCO],
    "spinach": [WALMART, ALDI, COSTCO],
    "peas": [WALMART, ALDI],
    "beans": [WALMART, ALDI, COSTCO],
    "corn": [WALMART, ALDI, COSTCO],
    "apple": [WALMART, ALDI, COSTCO],
    "apples": [WALMART, ALDI, COSTCO],
    "lemon": [WALMART, ALDI, COSTCO],
    "lemons": [WALMART, ALDI, COSTCO],
    "orange": [WALMART, ALDI, COSTCO],
    "parsley": [WALMART, ALDI],
    "parsnip": [WALMART],
    "parsnips": [WALMART],
    "turnip": [WALMART],
    "mushroom": [WALMART, ALDI, COSTCO],
    "mushrooms": [WALMART, ALDI, COSTCO],
    "raisins": [WALMART, ALDI],
    "currants": [WALMART],
    # meat + fish
    "beef": [WALMART, ALDI, COSTCO],
    "steak": [WALMART, ALDI, COSTCO],
    "brisket": [WALMART, COSTCO],
    "pork": [WALMART, ALDI, COSTCO],
    "bacon": [WALMART, ALDI, COSTCO],
    "ham": [WALMART, ALDI, COSTCO],
    "sausage": [WALMART, ALDI, COSTCO],
    "chicken": [WALMART, ALDI, COSTCO],
    "turkey": [WALMART, ALDI, COSTCO],
    "mutton": [WALMART],          # sold as lamb
    "lamb": [WALMART, COSTCO],
    "fish": [WALMART, ALDI, COSTCO],
    "salmon": [WALMART, ALDI, COSTCO],
    "cod": [WALMART, COSTCO],
    "shrimp": [WALMART, ALDI, COSTCO],
    # seasoning
    "nutmeg": [WALMART, ALDI],
    "cinnamon": [WALMART, ALDI, COSTCO],
    "cloves": [WALMART, ALDI],
    "ginger": [WALMART, ALDI],
    "allspice": [WALMART],
    "mustard": [WALMART, ALDI],
    "thyme": [WALMART, ALDI],
    "sage": [WALMART, ALDI],
    "bay": [WALMART, ALDI],
    "mace": [WALMART],
    "lard": [WALMART],
    "shortening": [WALMART, ALDI],
    "broth": [WALMART, ALDI, COSTCO],
    "stock": [WALMART, ALDI, COSTCO],
    "gravy": [WALMART, ALDI],
    "wine": [WALMART, ALDI],
    "brandy": [WALMART],
    # modern / global staples now stocked across Walmart, Aldi, Costco in
    # Charleston — so authentic regional recipes score fairly
    "soy sauce": [WALMART, ALDI, COSTCO],
    "sesame oil": [WALMART],
    "fish sauce": [WALMART],
    "oyster sauce": [WALMART],
    "hoisin": [WALMART],
    "rice vinegar": [WALMART],
    "coconut milk": [WALMART, ALDI, COSTCO],
    "curry powder": [WALMART, ALDI],
    "curry paste": [WALMART],
    "cumin": [WALMART, ALDI],
    "coriander": [WALMART, ALDI],
    "cilantro": [WALMART, ALDI],
    "turmeric": [WALMART, ALDI],
    "paprika": [WALMART, ALDI],
    "cayenne": [WALMART, ALDI],
    "chili": [WALMART, ALDI, COSTCO],
    "chilli": [WALMART, ALDI],
    "chili powder": [WALMART, ALDI],
    "chipotle": [WALMART],
    "jalapeno": [WALMART, ALDI],
    "lime": [WALMART, ALDI, COSTCO],
    "lemongrass": [WALMART],
    "pasta": [WALMART, ALDI, COSTCO],
    "spaghetti": [WALMART, ALDI, COSTCO],
    "linguine": [WALMART, ALDI],
    "penne": [WALMART, ALDI, COSTCO],
    "noodles": [WALMART, ALDI, COSTCO],
    "rice noodles": [WALMART],
    "tortilla": [WALMART, ALDI, COSTCO],
    "parmesan": [WALMART, ALDI, COSTCO],
    "mozzarella": [WALMART, ALDI, COSTCO],
    "ricotta": [WALMART, ALDI],
    "feta": [WALMART, ALDI, COSTCO],
    "basil": [WALMART, ALDI],
    "oregano": [WALMART, ALDI],
    "rosemary": [WALMART, ALDI],
    "cardamom": [WALMART],
    "garam masala": [WALMART],
    "scallion": [WALMART, ALDI],
    "green onion": [WALMART, ALDI],
    "bell pepper": [WALMART, ALDI, COSTCO],
    "avocado": [WALMART, ALDI, COSTCO],
    "black beans": [WALMART, ALDI, COSTCO],
    "chickpeas": [WALMART, ALDI, COSTCO],
    "lentils": [WALMART, ALDI],
    "yogurt": [WALMART, ALDI, COSTCO],
    "tofu": [WALMART, ALDI],
    "olive": [WALMART, ALDI, COSTCO],
    "tomato paste": [WALMART, ALDI],
    "coconut": [WALMART, ALDI],
    "peanut": [WALMART, ALDI, COSTCO],
    "sesame": [WALMART, ALDI],
    "ginger": [WALMART, ALDI],
    "garlic powder": [WALMART, ALDI],
    "shrimp": [WALMART, ALDI, COSTCO],
    "chorizo": [WALMART, ALDI],
    "couscous": [WALMART, ALDI],
    "quinoa": [WALMART, ALDI, COSTCO],
}

# Hard-to-source or archaic ingredients: term -> why it's a problem / the fix.
# Presence of these drags a recipe's practicality score down.
HARD_TO_SOURCE = {
    "suet": "raw beef suet — rarely stocked; substitute shortening or cold butter",
    "isinglass": "fish-bladder gelatin — use plain gelatin (Knox) instead",
    "hartshorn": "baker's ammonia — substitute baking powder",
    "saleratus": "old name for baking soda — just use baking soda",
    "verjuice": "sour grape juice — substitute lemon juice or vinegar",
    "oleomargarine": "old margarine — use butter or modern margarine",
    "calf's foot": "for gelatin stock — use powdered gelatin",
    "calves' feet": "for gelatin stock — use powdered gelatin",
    "sweetbreads": "offal — special-order from a butcher, not at Walmart/Aldi",
    "tripe": "offal — special-order; not typically stocked",
    "trotters": "pig's feet — occasional at Walmart, not Aldi/Costco",
    "marrow bones": "ask a butcher; not a standard shelf item",
    "salsify": "oyster plant — not stocked locally",
    "sorrel": "leafy green — farmers market only",
    "samphire": "sea vegetable — not available locally",
    "quince": "hard to find fresh — substitute apple + lemon",
    "medlar": "obsolete fruit — no substitute needed, skip",
    "rennet": "for junket/cheese — hard to find; specialty only",
    "treacle": "British — use molasses (Walmart)",
    "gum arabic": "candy-maker supply — specialty/online only",
    "orange-flower water": "specialty/online only",
    "dripping": "beef/bacon drippings — you save these yourself, not sold",
    # offal & old-butchery cuts you won't find at Walmart/Aldi/Costco
    "marrow": "beef marrow bones — butcher special-order only",
    "neat's foot": "cattle foot — not sold at grocery",
    "neats feet": "cattle feet — not sold at grocery",
    "neat's tongue": "ox tongue — butcher/specialty only",
    "neats tongue": "ox tongue — butcher/specialty only",
    "bullock": "old term for young ox — buy standard beef instead",
    "ox cheek": "beef cheek — butcher special-order",
    "bullocks cheeks": "beef cheeks — butcher special-order",
    "calf's head": "not stocked — skip or substitute a beef roast",
    "sheep's head": "not stocked — skip",
    "pig's head": "not stocked — butcher special-order",
    "cockscomb": "rooster combs — not available",
    "umbles": "deer offal — not available",
    "sturgeon": "not stocked locally — substitute a firm white fish",
    "capon": "castrated rooster — use a roasting chicken",
    "sippet": "old word for a small toast — just use toast",
}

# Archaic units of measure. These don't make a recipe impractical, but they're
# exactly what the AI 'modernize' step should convert. term -> modern hint.
ARCHAIC_MEASURES = {
    "gill": "1/2 cup",
    "gills": "half-cups",
    "dram": "about 1/8 tsp",
    "drachm": "about 1/8 tsp",
    "peck": "~2 dry gallons",
    "bushel": "~8 dry gallons",
    "quartern": "a quarter (of a peck/loaf)",
    "teacupful": "~3/4 cup",
    "teacup": "~3/4 cup",
    "wineglass": "~1/4 cup",
    "wineglassful": "~1/4 cup",
    "tumbler": "~1.5 cups",
    "gross": "144",
    "score": "20 (old counting)",
    "the size of an egg": "about 3 tablespoons",
    "the size of a walnut": "about 1 tablespoon",
    "a piece of butter the size": "measure by tablespoons",
    "slow oven": "300-325 F",
    "moderate oven": "350-375 F",
    "quick oven": "400-450 F",
    "hot oven": "425-475 F",
}


def _normalize(s):
    """Fold the punctuation old cookbooks love so matching is robust:
    apostrophes vanish (neat's -> neats), hyphens/underscores become spaces
    (neats-tongues -> neats tongues), whitespace collapses."""
    s = s.lower()
    s = re.sub(r"[''`’]", "", s)
    s = re.sub(r"[-_/]", " ", s)
    return re.sub(r"\s+", " ", s)


def _compile(terms):
    """Word-boundary regexes over normalized terms (longest first so multi-word
    phrases win over their sub-words). Each term also matches a trailing plural
    's' on its final word."""
    out = []
    for term in sorted(terms, key=len, reverse=True):
        words = _normalize(term).split()
        pat = r"\b" + r"\s+".join(re.escape(w) for w in words) + r"s?\b"
        out.append((term, re.compile(pat, re.I)))
    return out


_AVAILABLE_RX = _compile(AVAILABLE.keys())
_HARD_RX = _compile(HARD_TO_SOURCE.keys())
_MEASURE_RX = _compile(ARCHAIC_MEASURES.keys())


def scan(text):
    """Scan recipe text and return what we found.

    Returns dict with:
      available: list of (ingredient, [stores])
      hard:      list of (ingredient, reason)
      measures:  list of (unit, modern_hint)
    De-duplicated, order-stable.
    """
    lower = _normalize(text)

    available, seen = [], set()
    for term, rx in _AVAILABLE_RX:
        if rx.search(lower) and term not in seen:
            # collapse obvious singular/plural dupes by first word
            key = term.rstrip("s")
            if key in seen:
                continue
            seen.add(term)
            seen.add(key)
            available.append((term, AVAILABLE[term]))

    hard = []
    for term, rx in _HARD_RX:
        if rx.search(lower):
            hard.append((term, HARD_TO_SOURCE[term]))

    measures = []
    for term, rx in _MEASURE_RX:
        if rx.search(lower):
            measures.append((term, ARCHAIC_MEASURES[term]))

    return {"available": available, "hard": hard, "measures": measures}
