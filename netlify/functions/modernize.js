// pot*scraper — modernize an old recipe, server-side.
//
// Takes a historical recipe {title, body, source} and asks Claude to convert
// it into modern US measures, Fahrenheit oven temps, substitutions for
// hard-to-source ingredients, and a Charleston (Walmart/Aldi/Costco) shopping
// list. The API key stays here in Netlify env vars — never in the browser.
//
// Set ANTHROPIC_API_KEY in Netlify env vars (Site config -> Environment).

const API = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-opus-4-8'; // matches the CLI default; override via env MODEL
const VERSION = '2023-06-01';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Content-Type': 'application/json',
};

const SYSTEM = `You are modernizing a historical recipe for a home cook in Charleston, SC who shops at Walmart, Aldi, and Costco.

Convert the recipe faithfully — same dish, not a new one:
- Translate archaic measures (gill, teacupful, "butter the size of an egg", peck, dram) to US cups/tbsp/tsp/lb.
- Convert wood-stove directions ("slow oven", "quick oven", "hob") to modern oven temperatures in Fahrenheit and clear stovetop steps.
- Replace or substitute hard-to-source ingredients (suet, isinglass, saleratus, neat's feet, etc.) with items available at Walmart/Aldi/Costco, and explain each swap in notes.
- Build a shopping list mapping each ingredient to ONE store: Walmart, Aldi, or Costco.
- Keep it practical and unfussy. Do not invent ingredients that aren't implied by the original.`;

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    title: { type: 'string' },
    servings: { type: 'string' },
    ingredients: { type: 'array', items: { type: 'string' } },
    steps: { type: 'array', items: { type: 'string' } },
    shopping_list: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          item: { type: 'string' },
          store: { type: 'string', enum: ['Walmart', 'Aldi', 'Costco'] },
        },
        required: ['item', 'store'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['title', 'servings', 'ingredients', 'steps', 'shopping_list', 'notes'],
};

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 200, headers: CORS, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: CORS, body: JSON.stringify({ error: 'Method not allowed' }) };

  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'ANTHROPIC_API_KEY not set in Netlify env vars' }) };

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Invalid JSON in request body' }) }; }

  const title = String(body.title || '').slice(0, 200);
  const text = String(body.body || '').slice(0, 6000);
  const source = String(body.source || '').slice(0, 200);
  if (!text) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'need a recipe body to modernize' }) };

  const user =
    `ORIGINAL TITLE: ${title}\n` +
    `SOURCE: ${source}\n\n` +
    `ORIGINAL TEXT:\n${text}`;

  const payload = {
    model: process.env.MODEL || MODEL,
    max_tokens: 2500,
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
