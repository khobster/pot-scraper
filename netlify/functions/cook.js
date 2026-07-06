// pot*scraper — "cook it 3 ways" (Netlify Function, /.netlify/functions/cook).
// Same tri-method translator as functions/api/cook.js, in Netlify handler form.
// Set ANTHROPIC_API_KEY in Netlify env vars.

const API = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-opus-4-8';
const VERSION = '2023-06-01';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Content-Type': 'application/json',
};

const SYSTEM = `You are a recipe translator for a home cook in Charleston, SC who cooks mostly in an Instant Pot and shops at Walmart, Aldi, and Costco.

Given a recipe, render the SAME dish two ways:
- instant_pot: the pressure-cook method with realistic times (sauté/brown step, liquid needed to come to pressure, pressure-cook minutes, natural vs quick release). Include practical tips (e.g. deglaze to avoid the burn warning).
- traditional: the most fitting NON-Instant-Pot way to make this dish — pick whatever is most natural for it (stovetop, oven-braised, slow cooker, etc.) and name it in "method". Give realistic total time and steps.
- shopping_list: every ingredient mapped to ONE store (Walmart, Aldi, or Costco).
- best_method: which of the two you'd pick for this dish and why.
- Keep it faithful to the original dish. Do not invent a different recipe.`;

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    dish: { type: 'string' },
    servings: { type: 'string' },
    ingredients: { type: 'array', items: { type: 'string' } },
    instant_pot: {
      type: 'object', additionalProperties: false,
      properties: { total_time: { type: 'string' }, steps: { type: 'array', items: { type: 'string' } } },
      required: ['total_time', 'steps'],
    },
    traditional: {
      type: 'object', additionalProperties: false,
      properties: { method: { type: 'string' }, total_time: { type: 'string' }, steps: { type: 'array', items: { type: 'string' } } },
      required: ['method', 'total_time', 'steps'],
    },
    shopping_list: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: { item: { type: 'string' }, store: { type: 'string', enum: ['Walmart', 'Aldi', 'Costco'] } },
        required: ['item', 'store'],
      },
    },
    best_method: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['dish', 'servings', 'ingredients', 'instant_pot', 'traditional', 'shopping_list', 'best_method', 'notes'],
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
  if (!text) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'need a recipe body' }) };

  const payload = {
    model: process.env.MODEL || MODEL,
    max_tokens: 3000,
    system: SYSTEM,
    messages: [{ role: 'user', content: `TITLE: ${title}\nSOURCE: ${source}\n\nRECIPE:\n${text}` }],
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
