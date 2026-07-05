"""Local JSON cache of scraped + scored recipes."""

import hashlib
import json

from .config import RECIPES_FILE, BOOKS_FILE, ensure_dirs


def recipe_id(source_id, title):
    h = hashlib.sha1(f"{source_id}:{title}".encode("utf-8")).hexdigest()
    return h[:8]


def load_recipes():
    if RECIPES_FILE.exists():
        return json.loads(RECIPES_FILE.read_text())
    return []


def save_recipes(recipes):
    ensure_dirs()
    RECIPES_FILE.write_text(json.dumps(recipes, indent=2))


def load_books():
    if BOOKS_FILE.exists():
        return json.loads(BOOKS_FILE.read_text())
    return {}


def save_books(books):
    ensure_dirs()
    BOOKS_FILE.write_text(json.dumps(books, indent=2))


def get(recipe_id_):
    for r in load_recipes():
        if r["id"] == recipe_id_:
            return r
    return None


def upsert_many(new_recipes):
    """Merge new recipes into the cache by id; returns count actually added."""
    existing = load_recipes()
    by_id = {r["id"]: r for r in existing}
    added = 0
    for r in new_recipes:
        if r["id"] not in by_id:
            added += 1
        by_id[r["id"]] = r
    save_recipes(list(by_id.values()))
    return added


def replace(recipe):
    """Persist an updated single recipe (e.g. after modernizing)."""
    recipes = load_recipes()
    for i, r in enumerate(recipes):
        if r["id"] == recipe["id"]:
            recipes[i] = recipe
            break
    save_recipes(recipes)
