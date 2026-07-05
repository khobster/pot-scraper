# pot\*scraper

Pull genuinely cookable recipes out of public-domain cookbooks — and score each
one for a **Charleston grocery run** (Walmart / Aldi / Costco).

It reads old cookbooks from [Project Gutenberg](https://www.gutenberg.org) as
clean plaintext (no OCR, no HTML scraping, no API key), splits them into
individual recipes, and rates how practical each one is to actually make from
ingredients you can buy locally today. Pick one you like and have Claude
modernize the archaic measures and wood-stove directions on demand.

```
$ pot-scraper random --practical

  PLUM BROTH
  from A Plain Cookery Book for the Working Classes (Charles Elmé Francatelli)
  practical 10/10  ★★★★★★★★★★

  SHOPPING LIST (Charleston):
    Walmart: bread, broth, brown sugar, cinnamon, sugar

  ORIGINAL:
    Boil one quart of any kind of red plums in three pints of water with a
    piece of cinnamon and four ounces of brown sugar until the plums are
    entirely dissolved; then rub the whole through a sieve or colander...
```

## Install

```bash
git clone https://github.com/khobster/pot-scraper
cd pot-scraper
pip install -e .          # core CLI
pip install -e '.[ai]'    # + the on-demand `modernize` command
```

Python 3.10+. Core install only needs `requests`.

## Use

```bash
# Ingest and score cookbooks
pot-scraper fetch --broad              # sweep Gutenberg's whole cooking shelf (~500 books)
pot-scraper fetch --topic cooking --limit 200   # the curated "Cooking" bookshelf
pot-scraper fetch --query "bread baking" --limit 15   # keyword search
pot-scraper rescore                    # re-score the library after a scoring tweak

# Browse
pot-scraper stats                 # library summary
pot-scraper list --practical      # highest-scoring cookable recipes
pot-scraper random --practical    # a random cookable recipe + shopping list
pot-scraper show <id>             # one recipe in full

# Cook: modernize a specific recipe with Claude (needs an API key)
pot-scraper modernize <id>
```

## How "practical" is scored

Each recipe's text is scanned against a Charleston pantry lexicon
(`pot_scraper/pantry.py`):

- **Buyable ingredients** you can get at Walmart / Aldi / Costco push the score up.
- **Hard-to-source items** (suet, isinglass, neat's feet, saleratus, marrow…)
  push it down, each with a note on the modern substitute.
- Prose that doesn't read like cooking instructions (magazine essays, indexes)
  is rejected so it never scores as a recipe.

The score rewards **sourceability and simplicity** and docks for what makes a
recipe a project instead of dinner:

- each **hard-to-source** ingredient: −2.5
- **ingredient breadth** (a 15-item banquet dish isn't a weeknight cook): up to −5.5
- **method length** (long, fiddly, multi-stage): up to −4.5
- **archaic-measure friction**: light, since `modernize` fixes it

A recipe scoring **7/10 or higher** is flagged `practical`. In a ~500-book
library that lands around 75% of recipes — a real filter, not a rubber stamp:
plain boiled beef and plum broth score 9–10, while a 40-ingredient banquet
spread or a marrow-and-sweetbread pie sinks to 1–3. Archaic *measures* ("a
gill", "butter the size of an egg", "quick oven") barely dent the score; they're
exactly what the `modernize` step converts.

Changed the pantry or scoring? `pot-scraper rescore` re-scores the whole cached
library in place — no re-downloading.

## Modernize (on demand)

`pot-scraper modernize <id>` sends one recipe to Claude and gets back modern US
measures, oven temperatures in Fahrenheit, substitutions for anything archaic,
and a store-by-store shopping list. Scoring the whole library is free; you only
spend an API call on a recipe you actually want to cook. Model defaults to
`claude-opus-4-8` (override with `POT_SCRAPER_MODEL`).

**Set your API key once, locally.** Put it in `~/.pot-scraper/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

That file lives outside the repo and is never committed — so your key can't
leak. (Don't hardcode keys into source, especially in a public repo: GitHub and
Anthropic auto-scan public repos and revoke exposed keys.) `POT_SCRAPER_MODEL`
can also go in this file. Alternatively, just `export ANTHROPIC_API_KEY=...` in
your shell.

## Browser version (Cloudflare Pages or Netlify)

`web/` is a static browse/search/modernize UI over a variety-capped subset of
the library (`web/data/recipes.json` — regenerate with `python3
scripts/export_web.py`). The **Modernize** button calls a serverless function
that proxies Claude, so the API key stays server-side, never in the page.

**Cloudflare Pages** (function at `functions/api/modernize.js`):

1. Pages → **Create → Connect to Git** → pick this repo.
2. Build command: *(none)*. Build output directory: `web`.
3. **Settings → Variables and Secrets** → add secret `ANTHROPIC_API_KEY`
   (optional `MODEL`, defaults to `claude-opus-4-8`). Redeploy.

**Netlify** (function at `netlify/functions/modernize.js`, config in
`netlify.toml`): connect the repo, then set `ANTHROPIC_API_KEY` in Site
configuration → Environment variables.

The front-end auto-detects which platform served it (`/api/modernize` on
Cloudflare, `/.netlify/functions/modernize` on Netlify), so the same code
deploys to either.

## Data

Everything is public domain via Project Gutenberg. The local recipe cache lives
in `~/.pot-scraper/` (override with `POT_SCRAPER_HOME`) and is not committed.

## Layout

```
pot_scraper/
  sources.py    Gutendex search + plaintext download
  parse.py      split a cookbook into recipe blocks
  pantry.py     Charleston pantry + archaic-ingredient knowledge
  score.py      practicality scoring + shopping lists
  modernize.py  on-demand Claude modernization
  store.py      local JSON cache
  cli.py        the command-line interface
```

The lists in `pantry.py` are meant to grow — add ingredients and stores as you
learn what's actually on the shelves near you.
