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
# Ingest and score cookbooks (default: 8 books matching "cookery")
pot-scraper fetch
pot-scraper fetch --query "bread baking" --limit 15

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

A recipe scoring **7/10 or higher** is flagged `practical` — cookable from a
normal local grocery run. Archaic *measures* ("a gill", "butter the size of an
egg", "quick oven") don't hurt the score; they're exactly what the `modernize`
step converts.

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
