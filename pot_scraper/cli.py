"""pot*scraper — pull cookable recipes out of public-domain cookbooks."""

import argparse
import random
import sys
import textwrap

from . import sources, parse, store
from .score import score_recipe, shopping_list
from .config import PRACTICAL_THRESHOLD


# ---- pretty printing -------------------------------------------------------

def _stars(score):
    return "★" * score + "·" * (10 - score)


def _print_recipe(r, full=True):
    print()
    print(f"  {r['title'].upper()}")
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

def cmd_fetch(args):
    print(f"Searching Project Gutenberg for '{args.query}' cookbooks...")
    books = sources.search_cookbooks(args.query, limit=args.limit)
    if not books:
        print("No cookbooks found.")
        return 1

    seen_books = store.load_books()
    new_recipes = []
    for b in books:
        tag = str(b["id"])
        if tag in seen_books and not args.refetch:
            print(f"  · skipping (already have) {b['title'][:55]}")
            continue
        print(f"  · {b['title'][:55]} — {b['author']}")
        try:
            text = sources.download_text(b["text_url"])
        except Exception as e:  # network / format issues shouldn't kill the run
            print(f"    ! download failed: {e}")
            continue
        found = parse.extract_recipes(text)
        kept = 0
        for rec in found:
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
        print(f"    {kept} cookable recipes")
        seen_books[tag] = b["title"]

    added = store.upsert_many(new_recipes)
    store.save_books(seen_books)
    total = len(store.load_recipes())
    print(f"\nAdded {added} new recipes. Library now holds {total}.")
    return 0


def _pool(practical):
    recipes = store.load_recipes()
    if not recipes:
        print("No recipes yet. Run `pot-scraper fetch` first.")
        return None
    if practical:
        recipes = [r for r in recipes if r.get("practical")]
        if not recipes:
            print(f"No recipes scored >= {PRACTICAL_THRESHOLD}. "
                  "Try `pot-scraper fetch --limit 15` for more.")
            return None
    return recipes


def cmd_random(args):
    recipes = _pool(args.practical)
    if recipes is None:
        return 1
    _print_recipe(random.choice(recipes), full=not args.short)
    return 0


def cmd_list(args):
    recipes = _pool(args.practical)
    if recipes is None:
        return 1
    recipes = sorted(recipes, key=lambda r: -r["score"])[: args.limit]
    for r in recipes:
        flag = "practical" if r.get("practical") else "         "
        print(f"  {r['id']}  {r['score']}/10  {flag}  {r['title'][:50]}")
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
    f.add_argument("--query", default="cookery", help="search term (default: cookery)")
    f.add_argument("--limit", type=int, default=8, help="number of books to ingest")
    f.add_argument("--refetch", action="store_true", help="re-ingest books already seen")
    f.set_defaults(func=cmd_fetch)

    r = sub.add_parser("random", help="show a random recipe")
    r.add_argument("--practical", action="store_true", help="only cookable-from-local recipes")
    r.add_argument("--short", action="store_true", help="hide the original body text")
    r.set_defaults(func=cmd_random)

    l = sub.add_parser("list", help="list recipes by score")
    l.add_argument("--practical", action="store_true", help="only practical recipes")
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

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
