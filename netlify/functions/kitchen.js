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

Compose from these columns, keeping each dish coherent inside ONE flavor world so it hangs together:
- FLAVOR WORLD: French wine braise, Italian soffritto-tomato, Indian curry, Mexican chile-cumin, Thai coconut-curry, Chinese soy braise, Creole/Cajun trinity, Mediterranean, or a clean American braise.
- BRAISING LIQUID, VEGETABLE (seasonal), STARCH (rice, polenta/grits, mashed potato, egg noodles, couscous, tortillas, crusty bread), FINISH (fresh herb, citrus, quick pickle, yogurt/sour cream, scallion).

TWO HARD RULES:
1. INSTANT POT ONLY — braise / stew / pressure / simmer. No plating tricks, no raw, no pastry, no sear-only.
2. WALMART / ALDI ONLY — every single ingredient must be reliably stocked at a normal US Walmart Supercenter (its international aisle counts: soy sauce, coconut milk, curry powder, garam masala, cumin, chili powder, chipotle in adobo, sriracha, gochujang, hoisin, fish sauce, rice vinegar, canned tomatoes, common spices) or Aldi. Do NOT use specialty-market items — no preserved lemon, ras el hanout, whole dried Oaxacan chiles, doubanjiang, gochugaru, fresh lemongrass, achiote, berbere, banana leaf, exotic offal. When a classic dish needs a specialty item, substitute the Walmart-available equivalent (chili powder + chipotle instead of dried chiles; lemon instead of preserved lemon; curry powder/garam masala from the spice aisle) and keep it honest.

Draw on the best real technique from the great cooks (Julia Child, Marcella Hazan, Madhur Jaffrey, Diana Kennedy) so the combinations are grounded, not random. Give each dish a real, appetizing name.`;

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    dishes: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' },
          flavor_world: { type: 'string' },
          description: { type: 'string' },
          liquid: { type: 'string' },
          vegetable: { type: 'string' },
          starch: { type: 'string' },
          finish: { type: 'string' },
        },
        required: ['name', 'flavor_world', 'description', 'liquid', 'vegetable', 'starch', 'finish'],
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
