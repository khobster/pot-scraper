"""Build a French Laundry dish dataset from the Wayback Machine.

The fan archive frenchlaundrymenus.com (offline) stored each day's menu as a
PDF. The Internet Archive has ~219 of them. We pull a spread of chef's-tasting
menus, extract text with pypdf, and have Claude repair the letter-spacing
artifacts + structure each into {name, description}. Dedup by name.
"""

import hashlib
import io
import json
import re
from pathlib import Path

import requests
import pypdf
import anthropic

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "french-laundry.json"
N_MENUS = 55
CDX = ("http://web.archive.org/cdx/search/cdx?url=frenchlaundrymenus.com/menu-pdfs*"
       "&output=json&collapse=urlkey&filter=statuscode:200")

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


def main():
    rows = requests.get(CDX, timeout=60).json()[1:]
    chefs = [(r[1], r[2]) for r in rows if r[2].lower().endswith("dinner.pdf")]
    step = max(1, len(chefs) // N_MENUS)
    sample = chefs[::step][:N_MENUS]
    print(f"{len(chefs)} chef's menus archived; sampling {len(sample)}")

    client = anthropic.Anthropic()
    seen = {}
    for i, (ts, url) in enumerate(sample):
        try:
            pdf = requests.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=40).content
            raw = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
            if len(raw) < 100:
                raise ValueError("empty pdf text")
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1600, system=SYS,
                messages=[{"role": "user", "content": raw[:4500]}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
            dishes = json.loads(next(b.text for b in r.content if b.type == "text"))["dishes"]
        except Exception as e:
            print(f"[{i+1}/{len(sample)}] skip {url.split('/')[-1]}: {e}")
            continue
        for d in dishes:
            k = norm(d["name"])
            if k and len(d["name"]) > 3 and k not in seen:
                d["source_url"] = f"https://web.archive.org/web/{ts}/{url}"
                seen[k] = d
        print(f"[{i+1}/{len(sample)}] {url.split('/')[-1]} -> {len(seen)} unique dishes")

    out = [{"id": hashlib.sha1(("fl:" + d["name"]).encode()).hexdigest()[:8],
            "title": d["name"], "description": d["description"], "source_url": d.get("source_url", "")}
           for d in seen.values()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    print(f"SAVED {len(out)} French Laundry dishes -> {OUT}")


if __name__ == "__main__":
    main()
