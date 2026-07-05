"""Export a browsable subset of the recipe library for the web front-end.

The full library (~53k recipes) is too big to ship to a browser, so we take a
quality-first, variety-capped slice: practical recipes only, best scores first,
but capped per source book so no single cookbook dominates.
"""

import json
import random
from pathlib import Path

from pot_scraper import store

CAP_PER_BOOK = 10
CAP_TOTAL = 3000
BODY_CHARS = 1600

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "recipes.json"


def main():
    rs = [r for r in store.load_recipes() if r.get("practical")]
    random.seed(7)
    random.shuffle(rs)                      # randomize ties within a score
    rs.sort(key=lambda r: -r["score"])      # stable: best first, varied within

    per_book, out = {}, []
    for r in rs:
        b = r.get("source_id")
        if per_book.get(b, 0) >= CAP_PER_BOOK:
            continue
        per_book[b] = per_book.get(b, 0) + 1
        out.append({
            "id": r["id"],
            "title": r["title"],
            "body": r["body"][:BODY_CHARS],
            "score": r["score"],
            "ingredients": r["ingredients"],
            "hard": r["hard"],
            "measures": r["measures"],
            "source_title": r["source_title"],
            "source_author": r["source_author"],
            "source_url": r["source_url"],
        })
        if len(out) >= CAP_TOTAL:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    books = len({r["source_title"] for r in out})
    kb = OUT.stat().st_size / 1024
    print(f"Exported {len(out)} recipes from {books} books -> {OUT}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
