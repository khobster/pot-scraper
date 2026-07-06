"""Build the 'french laundromat' dataset: legendary-restaurant dishes.

Combines:
  - The French Laundry dishes (from the Wayback PDFs; french-laundry.json)
  - NYPL 'What's on the Menu?' dishes from legendary restaurants, joined
    Menu -> MenuPage -> MenuItem -> Dish and tagged with the restaurant + year.

NYPL CSVs are expected in /tmp/nypl (download:
  https://s3.amazonaws.com/menusdata.nypl.org/gzips/2021_08_01_07_01_17_data.tgz )
"""

import csv
import hashlib
import json
import re
from pathlib import Path

NYPL = Path("/tmp/nypl")
WEB = Path(__file__).resolve().parent.parent / "web" / "data"
FL_IN = WEB / "french-laundry.json"
OUT = WEB / "french-laundromat.json"

csv.field_size_limit(10_000_000)

# canonical label -> uppercase sponsor patterns (priority order: first match wins,
# so a dish shared by several is credited to the higher one)
FAMOUS = [
    ("Delmonico's", ["DELMONICO"]),
    ("The Waldorf-Astoria", ["WALDORF"]),
    ("Sherry's", ["SHERRY"]),
    ("Hotel Astor", ["HOTEL ASTOR", "ASTOR HOUSE", "ASTOR,"]),
    ("The Plaza", ["PLAZA"]),
    ("The Ritz-Carlton", ["RITZ"]),
    ("Rector's", ["RECTOR'S", "RECTORS"]),
    ("Lüchow's", ["LÜCHOW", "LUCHOW"]),
    ("Hoffman House", ["HOFFMAN HOUSE"]),
    ("The St. Regis", ["ST. REGIS", "ST REGIS"]),
    ("The Knickerbocker", ["KNICKERBOCKER"]),
    ("Hotel Savoy", ["SAVOY HOTEL", "HOTEL SAVOY"]),
]

TRIVIAL = {
    "coffee", "tea", "milk", "bread", "butter", "olives", "celery", "radishes",
    "salted almonds", "almonds", "water", "cigars", "cigarettes", "assorted cakes",
    "mashed potatoes", "boiled potatoes", "sliced tomatoes", "stewed tomatoes",
    "orange marmalade", "cream", "sugar", "ice water", "rolls", "toast", "pickles",
    "demi tasse", "demi-tasse", "cafe noir", "café noir", "assorted nuts",
}
WINE = re.compile(r"(\bbrut\b|extra dry|\bsec\b|& co|&co|\d{4}|champagne|mumm|"
                  r"pommery|moet|clicquot|cliquot|perrier|heidsieck|sauterne|"
                  r"claret|burgundy|sherry wine|madeira|vermouth|cognac)", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def restaurant_for(sponsor):
    s = (sponsor or "").upper()
    for label, pats in FAMOUS:
        if any(p in s for p in pats):
            return label
    return None


def load_nypl():
    prio = {lbl: i for i, (lbl, _) in enumerate(FAMOUS)}
    # 1. famous menus -> (label, year)
    menu = {}
    with open(NYPL / "Menu.csv", encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            lbl = restaurant_for(r.get("sponsor"))
            if lbl:
                yr = (r.get("date") or "")[:4]
                menu[r["id"]] = (lbl, yr if yr.isdigit() else "")
    # 2. page -> menu
    page = {}
    with open(NYPL / "MenuPage.csv", encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            if r.get("menu_id") in menu:
                page[r["id"]] = r["menu_id"]
    # 3. stream items -> dish_id -> best (priority,label,year)
    dish_src = {}
    with open(NYPL / "MenuItem.csv", encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            mid = page.get(r.get("menu_page_id"))
            if not mid:
                continue
            did = r.get("dish_id")
            if not did:
                continue
            lbl, yr = menu[mid]
            p = prio[lbl]
            cur = dish_src.get(did)
            if cur is None or p < cur[0]:
                dish_src[did] = (p, lbl, yr)
    # 4. dish names
    out, per = [], {}
    with open(NYPL / "Dish.csv", encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            src = dish_src.get(r["id"])
            if not src:
                continue
            name = (r.get("name") or "").strip()
            low = name.lower()
            if not (11 <= len(name) <= 80):
                continue
            if low in TRIVIAL or WINE.search(name):
                continue
            if not re.search(r"[A-Za-z].*\s.*[A-Za-z]", name):  # need >=2 words
                continue
            _, lbl, yr = src
            if per.get(lbl, 0) >= 90:                # cap per restaurant
                continue
            per[lbl] = per.get(lbl, 0) + 1
            out.append({"title": name.title() if name.isupper() else name,
                        "description": "", "source": lbl, "year": yr, "fl": False})
    return out


def main():
    combined, seen = [], set()

    # French Laundry first (they get priority + the special mark)
    for d in json.loads(FL_IN.read_text()):
        k = norm(d["title"])
        if k and k not in seen:
            seen.add(k)
            combined.append({"title": d["title"], "description": d.get("description", ""),
                             "source": "The French Laundry", "year": "", "fl": True})

    for d in load_nypl():
        k = norm(d["title"])
        if k and k not in seen:
            seen.add(k)
            combined.append(d)

    for d in combined:
        d["id"] = hashlib.sha1(("lm:" + d["title"]).encode()).hexdigest()[:8]

    OUT.write_text(json.dumps(combined, ensure_ascii=False))
    from collections import Counter
    by = Counter(d["source"] for d in combined)
    print(f"SAVED {len(combined)} laundromat dishes -> {OUT}")
    for s, n in by.most_common():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
