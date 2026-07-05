"""On-demand AI modernization of a single old recipe.

Free scoring covers the whole library; this step only runs when you pick a
recipe you actually want to cook. Uses Claude to convert archaic measures and
wood-stove directions into modern kitchen steps plus a Charleston shopping
list. Requires the `anthropic` package and ANTHROPIC_API_KEY.
"""

from typing import List
from .config import DEFAULT_MODEL
from .pantry import WALMART, ALDI, COSTCO


class ModernizeError(RuntimeError):
    pass


def _build_schema():
    """Import pydantic lazily so the core CLI works without it."""
    from pydantic import BaseModel, Field

    class ShopItem(BaseModel):
        item: str = Field(description="Grocery item with quantity, e.g. '2 lb beef chuck'")
        store: str = Field(description=f"One of: {WALMART}, {ALDI}, {COSTCO}")

    class ModernRecipe(BaseModel):
        title: str
        servings: str = Field(description="Modern serving estimate, e.g. '4-6'")
        ingredients: List[str] = Field(description="Modern ingredient list with US measures")
        steps: List[str] = Field(description="Numbered-in-order modern cooking steps, oven temps in Fahrenheit")
        shopping_list: List[ShopItem] = Field(description="What to buy, mapped to a Charleston store")
        notes: str = Field(description="Substitutions for anything archaic or hard to source")

    return ModernRecipe


_PROMPT = """You are modernizing a historical recipe for a home cook in Charleston, SC \
who shops at Walmart, Aldi, and Costco.

Convert the recipe below into a modern version:
- Translate archaic measures (gill, teacupful, "butter the size of an egg", peck) to US cups/tbsp/tsp/lb.
- Convert wood-stove directions ("slow oven", "quick oven", "hob") to modern oven temps in Fahrenheit and stovetop instructions.
- Replace or substitute hard-to-source ingredients (suet, isinglass, saleratus, etc.) with items available at Walmart/Aldi/Costco, and explain the swap in notes.
- Keep the dish faithful to the original; do not invent a different recipe.
- Build a shopping list mapping each ingredient to ONE store (Walmart, Aldi, or Costco).

ORIGINAL TITLE: {title}
SOURCE: {source}

ORIGINAL TEXT:
{body}
"""


def modernize(recipe):
    """Return a dict of the modernized recipe (also cached onto recipe['modernized'])."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        raise ModernizeError(
            "The 'anthropic' package is required for `modernize`. "
            "Install it with: pip install 'pot-scraper[ai]'"
        )

    import anthropic

    schema = _build_schema()
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    prompt = _PROMPT.format(
        title=recipe["title"],
        source=f"{recipe.get('source_title', '?')} ({recipe.get('source_author', '?')})",
        body=recipe["body"][:6000],
    )

    try:
        resp = client.messages.parse(
            model=DEFAULT_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
    except anthropic.AuthenticationError:
        raise ModernizeError(
            "ANTHROPIC_API_KEY is missing or invalid. Put it in "
            "~/.pot-scraper/.env  (line:  ANTHROPIC_API_KEY=sk-ant-...) "
            "or export it in your shell."
        )
    except anthropic.APIError as e:
        raise ModernizeError(f"Claude API error: {e}")

    parsed = resp.parsed_output
    if parsed is None:
        raise ModernizeError("Model did not return a parseable recipe (try again).")

    result = parsed.model_dump()
    recipe["modernized"] = result
    return result
