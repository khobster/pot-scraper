"""Classify a cookbook's cuisine of origin from its title/author.

Used two ways: to TAG each recipe with a cuisine, and to CURATE the library —
books that classify as None are generic Anglo-American domestic cookbooks (the
dated 'homemaker' bulk) and get dropped. TheMealDB recipes are tagged directly
from their area, not through here.
"""

import re

# Ordered — first match wins, so put the more specific / overlap-prone ones up
# top (Jewish before German so "International Jewish Cook Book" isn't called
# German; Italian's Apicius/Decameron before generic).
_PATTERNS = [
    ("Jewish",        r"jewish|hebrew|kosher"),
    ("French",        r"escoffier|gouff|\bfrench\b|fran[cç]ais|cordon bleu|parisian|proven[cç]|\blyon|gastronomy"),
    ("Italian",       r"italian|\bitaly\b|artusi|decameron|apicius|imperial rome|neapolitan|sicilian|macaroni cookery"),
    ("German",        r"german|deutsch|vienna|viennese|austrian|bavarian|pennsylvania[- ]dutch|\bmary at the farm"),
    ("Spanish",       r"spanish|\bspain\b|castil|valencia"),
    ("Portuguese",    r"portug"),
    ("Mexican",       r"mexican|\bmexico"),
    ("Chinese",       r"chinese|\bchina\b|cantonese"),
    ("Japanese",      r"japanese|\bjapan\b"),
    ("Indian",        r"\bindian\b|\bindia\b|\bcurr(y|ies)\b|hindoo|madras"),
    ("Thai",          r"\bthai\b|siam"),
    ("Vietnamese",    r"vietnam|annam"),
    ("Greek",         r"\bgreek\b|\bgreece\b"),
    ("Turkish",       r"turkish|ottoman"),
    ("Middle Eastern",r"arab|persian|syrian|lebanese|moroccan|\begypt"),
    ("Creole/Cajun",  r"creole|cajun|new orleans"),
    ("Scandinavian",  r"norwegian|swedish|danish|scandinav|finnish"),
    ("Russian",       r"russian|\brussia\b"),
]

# Non-cuisine technical manuals that keyword-match by accident — drop these even
# if they hit a pattern above (distilling/brewing/preserving guides).
_NOT_A_CUISINE = re.compile(r"distiller|distilling|brewing|brewer|preserving all kinds", re.I)


def cuisine_of_book(title, author=""):
    """Return a cuisine name, or None for generic Anglo-American / non-cuisine."""
    s = f"{title} {author}".lower()
    if _NOT_A_CUISINE.search(s):
        return None
    for name, pat in _PATTERNS:
        if re.search(pat, s):
            return name
    return None
