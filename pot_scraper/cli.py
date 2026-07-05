"""pot*scraper — pull cookable recipes out of public-domain cookbooks."""

import argparse
import random
import sys
import textwrap

from . import sources, parse, store, mealdb, spoonacular
from .cuisine import cuisine_of_book
from .score import score_recipe, shopping_list
from .config import PRACTICAL_THRESHOLD


# ---- pretty printing -------------------------------------------------------

def _stars(score):
    return "★" * score + "·" * (10 - score)


def _print_recipe(r, full=True):
    print()
    print(f"  {r['title'].upper()}")
    if r.get("cuisine"):
        print(f"  🍽  {r['cuisine']} cuisine")
    print(f"  from {r.get('source_title', '?')} ({r.get('source_author', '?')})")
    print(f"  practical {r['score']}/10  {_stars(r['score'])}")
    print()

    sl = shopping_list(r)
    if sl:
        print("  SHOPPING LIST (Charleston):")
        for st in ("Walmart", "Aldi", "Costco"):
            if st in sl:
                print(f"    {st}: {', '.join(sorted(set(sl[st])))}")
        print()

    if r.get("hard"):
        print("  ⚠ HARD TO SOURCE:")
        for h in r["hard"]:
            print(f"    {h['name']} — {h['reason']}")
        print()

    if r.get("measures"):
        hints = ", ".join(f"{m['unit']}→{m['modern']}" for m in r["measures"][:6])
        print(f"  OLD MEASURES: {hints}")
        print(f"  (run `pot-scraper modernize {r['id']}` to convert the whole recipe)")
        print()

    if full:
        print("  ORIGINAL:")
        for para in r["body"].split("\n\n"):
            wrapped = textwrap.fill(" ".join(para.split()), width=76,
                                    initial_indent="    ", subsequent_indent="    ")
            print(wrapped)
            print()

    if r.get("modernized"):
        _print_modern(r["modernized"])


def _print_modern(m):
    print("  ── MODERNIZED ──")
    print(f"  {m['title']}  · serves {m.get('servings', '?')}")
    print()
    print("  INGREDIENTS:")
    for ing in m.get("ingredients", []):
        print(f"    - {ing}")
    print()
    print("  STEPS:")
    for i, step in enumerate(m.get("steps", []), 1):
        wrapped = textwrap.fill(step, width=74, initial_indent=f"    {i}. ",
                                subsequent_indent="       ")
        print(wrapped)
    print()
    if m.get("shopping_list"):
        print("  SHOPPING LIST:")
        for s in m["shopping_list"]:
            print(f"    - {s['item']}  [{s['store']}]")
        print()
    if m.get("notes"):
        print("  NOTES:")
        print(textwrap.fill(m["notes"], width=76, initial_indent="    ",
                            subsequent_indent="    "))
        print()


# ---- commands --------------------------------------------------------------

def _ingest(query, limit, by, seen_books, quiet=False):
    """Fetch + parse + score one query's books. Returns list of new recipes;
    mutates seen_books."""
    books = sources.search_cookbooks(query, limit=limit, by=by)
    new_recipes = []
    for b in books:
        tag = str(b["id"])
        if tag in seen_books:
            continue
        try:
            text = sources.download_text(b["text_url"])
        except Exception as e:  # network / format issues shouldn't kill the run
            if not quiet:
                print(f"    ! download failed ({b['title'][:40]}): {e}")
            continue
        kept = 0
        for rec in parse.extract_recipes(text):
            score_recipe(rec)
            if rec["score"] == 0:
                continue
            rec["id"] = store.recipe_id(b["id"], rec["title"])
            rec["source_title"] = b["title"]
            rec["source_author"] = b["author"]
            rec["source_id"] = b["id"]
            rec["source_url"] = f"https://www.gutenberg.org/ebooks/{b['id']}"
            new_recipes.append(rec)
            kept += 1
        seen_books[tag] = b["title"]
        if not quiet:
            print(f"  · {b['title'][:52]:52s}  {kept} recipes")
    return new_recipes


def cmd_mealdb(args):
    print("Pulling authentic regional recipes from TheMealDB...")
    try:
        raw = mealdb.fetch_all()
    except Exception as e:
        print(f"TheMealDB fetch failed: {e}")
        return 1
    new_recipes = []
    for m in raw:
        rec = mealdb.to_recipe(m)
        if not rec:
            continue
        score_recipe(rec)
        if rec["score"] == 0:
            continue
        rec["id"] = store.recipe_id("themealdb", rec["source_meal_id"])
        new_recipes.append(rec)
    # idempotent refresh: drop any prior TheMealDB rows, then add the fresh set
    kept = [r for r in store.load_recipes() if r.get("source_id") != "themealdb"]
    store.save_recipes(kept)
    added = store.upsert_many(new_recipes)
    from collections import Counter
    by = Counter(r["cuisine"] for r in new_recipes)
    print(f"Added {added} TheMealDB recipes. Cuisines: " +
          ", ".join(f"{c} {n}" for c, n in by.most_common(12)))
    print(f"Library now holds {len(store.load_recipes())}.")
    return 0


def cmd_spoonacular(args):
    print("Pulling Instant-Pot-friendly recipes from Spoonacular...")
    try:
        raw = spoonacular.fetch_ip_friendly()
    except Exception as e:
        print(f"Spoonacular fetch failed: {e}")
        return 1
    new_recipes = []
    for m in raw:
        rec = spoonacular.to_recipe(m)
        if not rec:
            continue
        score_recipe(rec)
        rec["id"] = store.recipe_id("spoonacular", rec["source_meal_id"])
        new_recipes.append(rec)
    kept = [r for r in store.load_recipes() if r.get("source_id") != "spoonacular"]
    store.save_recipes(kept)
    added = store.upsert_many(new_recipes)
    from collections import Counter
    by = Counter(r["cuisine"] for r in new_recipes)
    print(f"Added {added} Spoonacular recipes. Top cuisines: " +
          ", ".join(f"{c} {n}" for c, n in by.most_common(10)))
    print(f"Library now holds {len(store.load_recipes())}.")
    return 0


def cmd_curate(args):
    """Tag every recipe with a cuisine and drop generic Anglo-American books."""
    recipes = store.load_recipes()
    kept, dropped = [], 0
    for r in recipes:
        if r.get("cuisine"):                 # TheMealDB (already tagged)
            kept.append(r); continue
        c = cuisine_of_book(r.get("source_title", ""), r.get("source_author", ""))
        if c:
            r["cuisine"] = c
            kept.append(r)
        else:
            dropped += 1                     # generic Anglo domestic — cut it
    store.save_recipes(kept)
    from collections import Counter
    by = Counter(r["cuisine"] for r in kept)
    print(f"Kept {len(kept)} authentic recipes, dropped {dropped} Anglo-American.")
    print("By cuisine: " + ", ".join(f"{c} {n}" for c, n in by.most_common()))
    return 0


def cmd_fetch(args):
    seen_books = store.load_books()

    if args.mealdb:
        return cmd_mealdb(args)
    if args.spoonacular:
        return cmd_spoonacular(args)
    if args.broad:
        print("Broad sweep of Project Gutenberg's cooking shelves...")
        new_recipes = []
        for by, query, limit in sources.BROAD_PLAN:
            print(f"\n[{by}={query}]")
            new_recipes += _ingest(query, limit, by, seen_books)
    elif args.topic:
        print(f"Fetching Gutenberg topic shelf '{args.topic}'...")
        new_recipes = _ingest(args.topic, args.limit, "topic", seen_books)
    else:
        print(f"Searching Project Gutenberg for '{args.query}'...")
        new_recipes = _ingest(args.query, args.limit, "search", seen_books)

    if not new_recipes and not seen_books:
        print("No cookbooks found.")
        return 1

    added = store.upsert_many(new_recipes)
    store.save_books(seen_books)
    total = len(store.load_recipes())
    print(f"\nAdded {added} new recipes. Library now holds {total}.")
    return 0


def cmd_rescore(args):
    """Re-run scoring over the whole cached library (after a scoring change).
    No re-download."""
    recipes = store.load_recipes()
    if not recipes:
        print("No recipes yet. Run `pot-scraper fetch` first.")
        return 1
    kept = []
    for r in recipes:
        score_recipe(r)          # recomputes ingredients/hard/measures/score
        if r["score"] > 0:
            kept.append(r)
    store.save_recipes(kept)
    dropped = len(recipes) - len(kept)
    practical = sum(1 for r in kept if r.get("practical"))
    print(f"Rescored {len(kept)} recipes "
          f"({dropped} dropped as non-recipes). {practical} now practical.")
    return 0


def _pool(practical, cuisine=None):
    recipes = store.load_recipes()
    if not recipes:
        print("No recipes yet. Run `pot-scraper fetch` first.")
        return None
    if cuisine:
        want = cuisine.lower()
        recipes = [r for r in recipes if want in (r.get("cuisine", "") or "").lower()]
        if not recipes:
            cuisines = sorted({r.get("cuisine") for r in store.load_recipes() if r.get("cuisine")})
            print(f"No '{cuisine}' recipes. Available: {', '.join(cuisines)}")
            return None
    if practical:
        recipes = [r for r in recipes if r.get("practical")]
        if not recipes:
            print(f"No recipes scored >= {PRACTICAL_THRESHOLD}.")
            return None
    return recipes


def cmd_random(args):
    recipes = _pool(args.practical, args.cuisine)
    if recipes is None:
        return 1
    _print_recipe(random.choice(recipes), full=not args.short)
    return 0


def cmd_list(args):
    recipes = _pool(args.practical, args.cuisine)
    if recipes is None:
        return 1
    recipes = sorted(recipes, key=lambda r: -r["score"])[: args.limit]
    for r in recipes:
        cz = (r.get("cuisine") or "")[:9]
        print(f"  {r['id']}  {r['score']}/10  {cz:9s}  {r['title'][:46]}")
    print(f"\n{len(recipes)} shown. `pot-scraper show <id>` for details.")
    return 0


def cmd_show(args):
    r = store.get(args.id)
    if not r:
        print(f"No recipe with id {args.id}.")
        return 1
    _print_recipe(r, full=True)
    return 0


def cmd_modernize(args):
    r = store.get(args.id)
    if not r:
        print(f"No recipe with id {args.id}.")
        return 1
    if r.get("modernized") and not args.refresh:
        _print_modern(r["modernized"])
        return 0
    from .modernize import modernize, ModernizeError
    print(f"Modernizing '{r['title']}' with Claude...")
    try:
        modernize(r)
    except ModernizeError as e:
        print(f"Error: {e}")
        return 1
    store.replace(r)
    _print_modern(r["modernized"])
    return 0


def cmd_stats(args):
    recipes = store.load_recipes()
    books = store.load_books()
    practical = [r for r in recipes if r.get("practical")]
    print(f"  Books ingested : {len(books)}")
    print(f"  Recipes cached : {len(recipes)}")
    print(f"  Practical (>= {PRACTICAL_THRESHOLD}) : {len(practical)}")
    if recipes:
        avg = sum(r["score"] for r in recipes) / len(recipes)
        print(f"  Average score  : {avg:.1f}/10")
    return 0


# ---- wiring ----------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="pot-scraper",
        description="Pull cookable recipes out of public-domain cookbooks.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="scrape + score cookbooks from Project Gutenberg")
    f.add_argument("--query", default="cookery", help="keyword search term (default: cookery)")
    f.add_argument("--topic", help="Gutenberg bookshelf/subject, e.g. 'cooking' (~487 books)")
    f.add_argument("--broad", action="store_true", help="sweep the whole cooking shelf + extras")
    f.add_argument("--mealdb", action="store_true", help="pull authentic regional recipes from TheMealDB")
    f.add_argument("--spoonacular", action="store_true", help="pull Instant-Pot-friendly recipes from Spoonacular (needs SPOONACULAR_API_KEY)")
    f.add_argument("--limit", type=int, default=8, help="max books to ingest for --query/--topic")
    f.set_defaults(func=cmd_fetch)

    cu = sub.add_parser("curate", help="tag by cuisine and drop generic Anglo-American recipes")
    cu.set_defaults(func=cmd_curate)

    r = sub.add_parser("random", help="show a random recipe")
    r.add_argument("--practical", action="store_true", help="only cookable-from-local recipes")
    r.add_argument("--cuisine", help="filter by cuisine, e.g. French, Italian, Thai")
    r.add_argument("--short", action="store_true", help="hide the original body text")
    r.set_defaults(func=cmd_random)

    l = sub.add_parser("list", help="list recipes by score")
    l.add_argument("--practical", action="store_true", help="only practical recipes")
    l.add_argument("--cuisine", help="filter by cuisine, e.g. French, Italian, Thai")
    l.add_argument("--limit", type=int, default=25)
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="show one recipe by id")
    s.add_argument("id")
    s.set_defaults(func=cmd_show)

    m = sub.add_parser("modernize", help="AI-modernize a recipe (needs ANTHROPIC_API_KEY)")
    m.add_argument("id")
    m.add_argument("--refresh", action="store_true", help="re-run even if already modernized")
    m.set_defaults(func=cmd_modernize)

    st = sub.add_parser("stats", help="library summary")
    st.set_defaults(func=cmd_stats)

    rs = sub.add_parser("rescore", help="re-run scoring over the cached library")
    rs.set_defaults(func=cmd_rescore)

    return p


def main(argv=None):
    from .config import load_env
    load_env()  # pick up ~/.pot-scraper/.env (e.g. ANTHROPIC_API_KEY) if present
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
