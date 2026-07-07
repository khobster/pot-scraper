// pot*scraper — THE KITCHEN (Netlify Function, /.netlify/functions/kitchen).
// Same composing engine as functions/api/kitchen.js, in Netlify handler form.

const API = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-opus-4-8';
const VERSION = '2023-06-01';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Content-Type': 'application/json',
};

const SYSTEM = `You are the chef of an Instant Pot restaurant. You compose the menu the way Mike Lata composes FIG in Charleston: not from memorized recipes, but by recombining a fixed vocabulary of building blocks into new dishes.

Draw WIDELY from these columns — range across them, don't lean on the same few — keeping each dish coherent inside ONE flavor world so it hangs together:
- FLAVOR WORLD: French wine braise; Provençal; Italian ragù (soffritto-tomato); Northern Italian (butter, wine, risotto); North Indian (garam masala); South Indian coconut curry; Thai coconut-curry; Vietnamese caramel braise (kho); Filipino adobo; Chinese red-braise (soy, star anise); Sichuan chili; Japanese soy-mirin or curry; Korean gochujang braise; Mexican chile-cumin & adobo; Tex-Mex chili; Creole/Cajun trinity; Southern smothered or BBQ; Carolina Lowcountry; Caribbean/Jamaican curry & jerk; Spanish paprika-chorizo; Portuguese tomato-wine; Greek lemon-tomato-cinnamon (stifado); Moroccan/North African warm spice; Middle Eastern cumin-coriander; West African peanut stew; Cuban sofrito (ropa vieja); Hungarian paprika (goulash); German/Alsatian beer-mustard; or a clean American pot roast.
- BRAISING LIQUID: red or white wine, beer, hard cider, stock, coconut milk, crushed or fire-roasted tomatoes, coffee, soy-mirin, salsa verde, cream, mustard-cream.
- VEGETABLE (seasonal): mirepoix, fennel, bell peppers, poblano, mushrooms, hearty greens, cabbage, potatoes, sweet potato, winter squash, turnip, parsnip, green beans, peas, tomatillo, okra, corn.
- STARCH: white/basmati/jasmine rice, polenta or cheesy grits, mashed potato or sweet potato, egg noodles, pasta, couscous, farro, barley, orzo, tortillas, crusty bread, cornbread, biscuits, dumplings.
- FINISH: fresh herbs, gremolata, chimichurri, salsa verde, quick pickle, fresh chile, lemon or lime, yogurt or sour cream, feta, toasted nuts, crispy shallots, herb oil, grated parmesan.

TWO HARD RULES:
1. INSTANT POT ONLY — braise / stew / pressure / simmer. No plating tricks, no raw, no pastry, no sear-only.
2. WALMART / ALDI ONLY — every single ingredient must be reliably stocked at a normal US Walmart Supercenter (its international aisle counts: soy sauce, coconut milk, curry powder, garam masala, cumin, chili powder, chipotle in adobo, sriracha, gochujang, hoisin, fish sauce, rice vinegar, canned tomatoes, common spices) or Aldi. Do NOT use specialty-market items — no preserved lemon, ras el hanout, whole dried Oaxacan chiles, doubanjiang, gochugaru, fresh lemongrass, achiote, berbere, banana leaf, exotic offal. When a classic dish needs a specialty item, substitute the Walmart-available equivalent (chili powder + chipotle instead of dried chiles; lemon instead of preserved lemon; curry powder/garam masala from the spice aisle) and keep it honest.

Ground each dish in a real, recognizable reference and NAME it in "inspiration" — range WIDELY, don't repeat the usual handful. Pull from famous chefs (Julia Child, Jacques Pépin, Escoffier, Marcella Hazan, Lidia Bastianich, Madhur Jaffrey, Diana Kennedy, Rick Bayless, Paul Prudhomme, Leah Chase, Edna Lewis, Sean Brock, Andrea Nguyen, Maangchi, Fuchsia Dunlop, J. Kenji López-Alt, Yotam Ottolenghi, Claudia Roden, Marcus Samuelsson, José Andrés, Ina Garten, Emeril Lagasse), legendary restaurants (Antoine's, Commander's Palace, Galatoire's, Momofuku, Husk, The Grey, Rodney Scott's BBQ), or specific regions (Oaxaca, Puebla, Emilia-Romagna, Tuscany, Naples, Provence, Lyon, Alsace, Andalusia, Marseille, Sichuan, Hunan, Hanoi, Bangkok, Kerala, Punjab, Goa, Seoul, Manila, Kingston, Lagos, Lima, Havana, New Orleans, the Carolina Lowcountry, Budapest). The dish must genuinely reflect that reference's technique, not just borrow the name. Vary the references across the five. Keep the "inspiration" value SHORT — just the name (a chef, restaurant, or region), not a sentence. Give each dish a real, appetizing name.`;

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    dishes: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' },
          inspiration: { type: 'string' },
          flavor_world: { type: 'string' },
          description: { type: 'string' },
          liquid: { type: 'string' },
          vegetable: { type: 'string' },
          starch: { type: 'string' },
          finish: { type: 'string' },
        },
        required: ['name', 'inspiration', 'flavor_world', 'description', 'liquid', 'vegetable', 'starch', 'finish'],
      },
    },
  },
  required: ['dishes'],
};

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 200, headers: CORS, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: CORS, body: JSON.stringify({ error: 'Method not allowed' }) };

  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'ANTHROPIC_API_KEY not set' }) };

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  const protein = String(body.protein || 'chicken thighs').slice(0, 60);
  const seed = String(body.seed || '').slice(0, 40);
  const user = `Compose tonight's menu — 5 Instant Pot dishes, every one built on ${protein}, each a fresh recombination in a DIFFERENT flavor world, all shoppable at Walmart/Aldi. (menu seed: ${seed})`;

  const payload = {
    model: process.env.MODEL || MODEL,
    max_tokens: 2600,
    system: SYSTEM,
    messages: [{ role: 'user', content: user }],
    output_config: { format: { type: 'json_schema', schema: SCHEMA } },
  };

  try {
    const r = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': VERSION },
      body: JSON.stringify(payload),
    });
    const raw = await r.text();
    if (!r.ok) return { statusCode: r.status, headers: CORS, body: JSON.stringify({ error: 'Anthropic API error', detail: raw.slice(0, 600) }) };
    const msg = JSON.parse(raw);
    const jsonText = (msg.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
    let data;
    try { data = JSON.parse(jsonText); }
    catch { return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: 'model did not return JSON', raw: jsonText.slice(0, 400) }) }; }
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ ok: true, data }) };
  } catch (e) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'Failed to reach Anthropic API: ' + String(e.message || e).slice(0, 300) }) };
  }
};
