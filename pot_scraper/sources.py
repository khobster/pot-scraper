"""Data source: Project Gutenberg via the Gutendex JSON API.

Public-domain cookbooks as clean UTF-8 plaintext. No OCR, no HTML scraping,
no API key. This is the whole reason pot-scraper works where the old
digital-library scraper didn't.
"""

import re
import requests

from .config import USER_AGENT

GUTENDEX = "https://gutendex.com/books/"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def search_cookbooks(query="cookery", limit=8):
    """Return up to `limit` cookbook records that have a plaintext format.

    Each record: {id, title, author, text_url}.
    Walks Gutendex pages until we have enough.
    """
    out = []
    url = f"{GUTENDEX}?search={requests.utils.quote(query)}"
    while url and len(out) < limit:
        r = _session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        for b in data.get("results", []):
            text_url = _pick_text_url(b.get("formats", {}))
            if not text_url:
                continue
            authors = b.get("authors") or []
            author = authors[0]["name"] if authors else "Unknown"
            out.append(
                {
                    "id": b["id"],
                    "title": b.get("title", "Untitled").strip(),
                    "author": author,
                    "text_url": text_url,
                }
            )
            if len(out) >= limit:
                break
        url = data.get("next")
    return out


def _pick_text_url(formats):
    """Prefer a UTF-8 plaintext download; fall back to any text/plain."""
    best = None
    for mime, url in formats.items():
        if not mime.startswith("text/plain"):
            continue
        if url.endswith(".zip"):
            continue
        if "utf-8" in mime.lower() or url.endswith(".utf-8"):
            return url
        best = best or url
    return best


def download_text(text_url):
    """Fetch a book's plaintext and strip the Gutenberg license boilerplate."""
    r = _session.get(text_url, timeout=60)
    r.raise_for_status()
    return _strip_boilerplate(r.text)


_START_RX = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
_END_RX = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)


def _strip_boilerplate(text):
    start = _START_RX.search(text)
    end = _END_RX.search(text)
    if start:
        text = text[start.end():]
    if end:
        # end search must run on the (possibly) trimmed text
        m = _END_RX.search(text)
        if m:
            text = text[: m.start()]
    return text.strip()
