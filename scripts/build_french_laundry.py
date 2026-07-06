"""Extract real French Laundry dishes from the Wayback-archived menu PDFs.

frenchlaundrymenus.com (offline) stored each day's menu as a PDF; the Internet
Archive has ~219 of them (chef's + vegetable tasting). We pull them all — with
polite delays + retries so Wayback doesn't rate-limit us — extract text with
pypdf, and have Claude repair the letter-spacing artifacts + structure each
dish. Dedup by name; accumulate across runs. Writes web/data/french-laundromat.json.
"""

import hashlib
import io
import json
import re
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pypdf
import anthropic

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "french-laundromat.json"
CDX = ("http://web.archive.org/cdx/search/cdx?url=frenchlaundrymenus.com/menu-pdfs*"
       "&output=json&collapse=urlkey&filter=statuscode:200")
DELAY = 1.3   # seconds between Wayback fetches (be polite; avoids the rate-limit wall)

SYS = ("You are given raw text from a French Laundry menu PDF. Dish NAMES are in caps "
       "with letter-spacing artifacts (\"JAPANE SE\"=\"Japanese\", \"SAUT ÉED\"=\"Sautéed\"). "
       "Return each dish: name (clean, Title Case, keep quotes like \"Oysters and Pearls\") "
       "and description (the line(s) under it, cleaned). Skip headers, prix fixe / supplement "
       "/ service lines, 'or' separators, and section labels.")
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"dishes": {"type": "array",
          "items": {"type": "object", "additionalProperties": False,
                    "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["name", "description"]}}}, "required": ["dishes"]}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def session():
    s = requests.Session()
    retry = Retry(total=5, connect=5, backoff_factor=1.5,
                  status_forcelist=[429, 502, 503, 504], raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def save(seen):
    out = [{"id": hashlib.sha1(("fl:" + d["name"]).encode()).hexdigest()[:8],
            "title": d["name"], "description": d["description"],
            "source": "The French Laundry", "year": "", "fl": True}
           for d in seen.values()]
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    return len(out)


def main():
    sess = session()
    rows = requests.get(CDX, timeout=60).json()[1:]
    menus = [(r[1], r[2]) for r in rows]  # (timestamp, url) — chef's + veg
    print(f"{len(menus)} archived menu PDFs")

    # seed from whatever's already there so re-runs accumulate
    seen = {}
    if OUT.exists():
        for d in json.loads(OUT.read_text()):
            seen[norm(d["title"])] = {"name": d["title"], "description": d.get("description", "")}
    print(f"starting from {len(seen)} existing dishes")

    client = anthropic.Anthropic()
    for i, (ts, url) in enumerate(menus):
        try:
            time.sleep(DELAY)
            pdf = sess.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=45).content
            raw = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
            if len(raw) < 100:
                raise ValueError("empty pdf text")
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1600, system=SYS,
                messages=[{"role": "user", "content": raw[:4500]}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
            dishes = json.loads(next(b.text for b in r.content if b.type == "text"))["dishes"]
        except Exception as e:
            print(f"[{i+1}/{len(menus)}] skip {url.split('/')[-1]}: {str(e)[:60]}")
            continue
        for d in dishes:
            k = norm(d["name"])
            if k and len(d["name"]) > 3 and k not in seen:
                seen[k] = {"name": d["name"], "description": d["description"]}
        if (i + 1) % 10 == 0:
            n = save(seen)
            print(f"[{i+1}/{len(menus)}] {url.split('/')[-1]} -> {n} unique dishes (saved)")

    n = save(seen)
    print(f"DONE: {n} French Laundry dishes -> {OUT}")


if __name__ == "__main__":
    main()
