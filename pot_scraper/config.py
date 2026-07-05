"""Paths and defaults."""

import os
from pathlib import Path

# Local data lives outside the repo so the recipe cache isn't committed.
CACHE_DIR = Path(os.environ.get("POT_SCRAPER_HOME", Path.home() / ".pot-scraper"))
RECIPES_FILE = CACHE_DIR / "recipes.json"
BOOKS_FILE = CACHE_DIR / "books.json"          # which Gutenberg book ids we've ingested

# Model used by the on-demand `modernize` command (needs ANTHROPIC_API_KEY).
DEFAULT_MODEL = os.environ.get("POT_SCRAPER_MODEL", "claude-opus-4-8")

# A recipe is "practical" (cookable from local groceries) at/above this score.
PRACTICAL_THRESHOLD = 7

USER_AGENT = "pot-scraper/0.1 (+https://github.com/khobster/pot-scraper)"


def ensure_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_env():
    """Load KEY=VALUE lines from ~/.pot-scraper/.env into the environment
    (without overriding anything already set). This lives OUTSIDE the repo on
    purpose so a secret like ANTHROPIC_API_KEY can never be committed."""
    env_file = CACHE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        os.environ.setdefault(key, val)
