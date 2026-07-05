"""Export the curated recipe library for the web front-end.

Since curation cut the library to ~7.5k authentic recipes, the whole thing now
fits in the browser — no per-book cap needed. Practical recipes first, and we
carry the cuisine tag (and TheMealDB image) so the site can filter by cuisine.
"""

import json
from pathlib import Path

from pot_scraper import store

BODY_CHARS = 1200
OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "recipes.json"


def main():
    rs = store.load_recipes()
    # practical first, then by score
    rs.sort(key=lambda r: (not r.get("practical"), -r["score"]))

    out = [{
        "id": r["id"],
        "title": r["title"],
        "body": r["body"][:BODY_CHARS],
        "score": r["score"],
        "cuisine": r.get("cuisine", ""),
        "ingredients": r["ingredients"],
        "hard": r["hard"],
        "measures": r["measures"],
        "source_title": r["source_title"],
        "source_author": r["source_author"],
        "source_url": r["source_url"],
        "image": r.get("image", ""),
    } for r in rs]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    cuisines = len({r["cuisine"] for r in out if r["cuisine"]})
    kb = OUT.stat().st_size / 1024
    print(f"Exported {len(out)} recipes across {cuisines} cuisines -> {OUT}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
