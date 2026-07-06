"""Build a canon of acclaimed, genuinely Instant-Pot-translatable dishes.

Unlike the French Laundry (precision plating, ~20% IP-able), every source here
is famous FOR pot cooking — braises, stews, curries, ragùs — so the Instant Pot
translation is real. Claude assembles each source's signature dishes; each dish
is tagged with its source/authority. Output: web/data/pot-legends.json.
"""

import hashlib
import json
import re
from pathlib import Path

import anthropic

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "pot-legends.json"

# (source label, cuisine tag, what to ask for)
SOURCES = [
    ("Julia Child", "French", "iconic French dishes from Julia Child's canon that are braises, stews, or pot dishes (Bœuf Bourguignon, Coq au Vin, Cassoulet, Blanquette de Veau, Daube, Pot-au-Feu, Cassoulet)"),
    ("The New Orleans grande dames", "Creole", "signature Creole/Cajun dishes from the legendary New Orleans restaurants (Antoine's, Commander's Palace, Galatoire's) that are gumbos, étouffées, braises, and stews"),
    ("Marcella Hazan", "Italian", "iconic Italian braises, ragùs, risottos and pot dishes from Marcella Hazan's canon (ragù bolognese, ossobuco, brasato al Barolo, risotto, minestrone, braised meats)"),
    ("Madhur Jaffrey", "Indian", "iconic Indian curries, dals and braises from Madhur Jaffrey's canon (dal makhani, rogan josh, butter chicken, korma, biryani, chana masala)"),
    ("Diana Kennedy", "Mexican", "iconic Mexican moles, braises and pot dishes from Diana Kennedy's canon (mole poblano, birria, cochinita pibil, pozole, tinga, carnitas)"),
    ("Paula Wolfert", "Moroccan", "iconic Moroccan and slow-Mediterranean tagines and braises from Paula Wolfert's canon (lamb tagine, harira, cassoulet, daube, chicken with preserved lemon)"),
    ("The ramen counter", "Japanese", "iconic Japanese simmered and pot dishes (tonkotsu/shoyu/miso ramen broth, oden, nikujaga, buta no kakuni, curry rice, chicken nabe)"),
    ("The phở house", "Vietnamese", "iconic Vietnamese pot, braise and soup dishes (phở broth, bò kho, thịt kho, cá kho tộ, bún bò Huế, cháo)"),
    ("The Korean pojangmacha", "Korean", "iconic Korean stews and braises — jjigae, jjim, tang (galbijjim, kimchi jjigae, doenjang jjigae, seolleongtang, dak-dori-tang, budae jjigae)"),
    ("Chinese red-braising", "Chinese", "iconic Chinese braises and simmered dishes (hong shao rou, Dongpo pork, mapo tofu, lion's head meatballs, congee, master-stock chicken, oxtail)"),
    ("The Jewish deli", "Jewish", "iconic Ashkenazi/Jewish-deli braises and soups (braised brisket, cholent, matzo ball soup, short ribs, stuffed cabbage, chicken fricassee)"),
    ("The Spanish table", "Spanish", "iconic Spanish pot dishes and braises (cocido madrileño, fabada asturiana, callos, rabo de toro, lentejas, pollo al chilindrón)"),
    ("Central Europe", "Hungarian", "iconic Central-European stews (Hungarian goulash, chicken paprikash, székelykáposzta, beef pörkölt)"),
]

SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"dishes": {"type": "array",
          "items": {"type": "object", "additionalProperties": False,
                    "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["name", "description"]}}}, "required": ["dishes"]}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    client = anthropic.Anthropic()
    out, seen = [], set()
    for label, cuisine, ask in SOURCES:
        try:
            r = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=2000,
                system="Return 18-22 genuinely famous, signature dishes for the request. Each must be a real dish an Instant Pot (pressure cooker) can genuinely make well — braises, stews, curries, soups, ragùs, simmered/pot dishes. name = the dish's proper name (keep accents/native spelling). description = one short evocative line (key ingredients / character). No plated/raw/pastry items.",
                messages=[{"role": "user", "content": ask}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
            dishes = json.loads(next(b.text for b in r.content if b.type == "text"))["dishes"]
        except Exception as e:
            print(f"  {label}: FAILED {e}")
            continue
        kept = 0
        for d in dishes:
            k = norm(d["name"])
            if k and k not in seen:
                seen.add(k)
                out.append({"id": hashlib.sha1(("pl:" + d["name"]).encode()).hexdigest()[:8],
                            "title": d["name"], "description": d["description"],
                            "source": label, "cuisine": cuisine, "fl": False})
                kept += 1
        OUT.write_text(json.dumps(out, ensure_ascii=False))   # save after each source
        print(f"  {label}: {kept} dishes  ({len(out)} total, saved)")

    print(f"SAVED {len(out)} pot-legend dishes -> {OUT}")


if __name__ == "__main__":
    main()
