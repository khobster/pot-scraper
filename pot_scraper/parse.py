"""Turn a whole cookbook's plaintext into individual recipe blocks.

Old cookbooks vary wildly, so the strategy is: detect headings *generously*
(short lines surrounded by blank lines, in ALL CAPS / numbered / short Title
Case), split the book on them, then let the ingredient scorer downstream throw
away anything that isn't actually a recipe (front matter, indexes, chapter
intros). We don't need perfect heading detection — the pantry scan is the real
filter.
"""

import re

# "No. 12." / "12." / "CHAPTER" style prefixes we strip off titles.
_NUM_PREFIX = re.compile(r"^(no\.?\s*\d+[\.\)]?\s*|\d+[\.\)]\s*)", re.I)
_SKIP_TITLES = re.compile(
    r"^(contents|index|preface|introduction|chapter|appendix|glossary|"
    r"illustrations|footnotes?|transcriber)", re.I
)


def _alpha_upper_ratio(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def _is_heading(line, prev_blank, next_blank):
    """A recipe heading is a short line, blank-line-isolated, that looks like a
    title rather than a sentence."""
    s = line.strip()
    if not (prev_blank and next_blank and s):
        return False
    if len(s) > 70:
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    if s.endswith((",", ";", ":")):
        return False
    # numbered recipe, e.g. "No. 1. BOILED BEEF."
    if _NUM_PREFIX.match(s):
        return True
    # ALL CAPS / mostly caps heading
    if _alpha_upper_ratio(s) > 0.6:
        return True
    # short Title Case heading (<=8 words), e.g. "Yorkshire Pudding"
    words = s.split()
    if len(words) <= 8 and s[0].isupper() and not s.endswith("."):
        capish = sum(1 for w in words if w[:1].isupper())
        if capish >= max(1, len(words) - 1):
            return True
    return False


def _clean_title(s):
    s = s.strip().strip("_").strip()          # Gutenberg _italics_ markup
    s = _NUM_PREFIX.sub("", s).strip()
    s = s.strip("_").strip().rstrip(".").strip()
    # Normalize screaming caps to title case for readability, keep short words.
    if _alpha_upper_ratio(s) > 0.8:
        s = s.title()
    return s


def _looks_like_toc(body):
    """Table-of-contents / index blocks are full of page-number lines and dot
    leaders. Detect and reject them so they don't score as recipes."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if len(lines) < 6:
        return False
    page_refs = sum(1 for ln in lines if re.search(r"\d\s*$", ln) or "...." in ln)
    return page_refs / len(lines) > 0.35


def extract_recipes(text):
    """Yield {title, body} dicts for candidate recipes in a book's text."""
    lines = text.splitlines()
    n = len(lines)

    # find heading line indices
    heads = []
    for i, line in enumerate(lines):
        prev_blank = (i == 0) or (lines[i - 1].strip() == "")
        next_blank = (i + 1 >= n) or (lines[i + 1].strip() == "")
        if _is_heading(line, prev_blank, next_blank):
            # normalize before the skip check so "_Contents_" is caught
            title = _NUM_PREFIX.sub("", line.strip().strip("_").strip())
            if _SKIP_TITLES.match(title):
                continue
            heads.append(i)

    recipes = []
    for idx, start in enumerate(heads):
        end = heads[idx + 1] if idx + 1 < len(heads) else n
        title = _clean_title(lines[start])
        body = "\n".join(lines[start + 1:end]).strip()
        # collapse runs of blank lines
        body = re.sub(r"\n{3,}", "\n\n", body)
        if not title or len(body) < 80:
            continue
        if _looks_like_toc(body):
            continue
        recipes.append({"title": title, "body": body})
    return recipes
