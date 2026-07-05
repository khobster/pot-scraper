// pot*scraper — "cook it 3 ways" (Cloudflare Pages Function, /api/cook).
//
// Takes a recipe {title, body, source} and returns it rendered for an Instant
// Pot kitchen: pressure-cook method + air-fryer-lid note + conventional
// stovetop/oven translation, with a Charleston shopping list. Key stays in
// Cloudflare env (ANTHROPIC_API_KEY).

const API = 'https://api.anthropic.com/v1/messages';
const DEFAULT_MODEL = 'claude-opus-4-8';
const VERSION = '2023-06-01';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Content-Type': 'application/json',
};

const SYSTEM = `You are a recipe translator for a home cook in Charleston, SC who cooks mostly in an Instant Pot (including its air-fryer lid) and shops at Walmart, Aldi, and Costco.

Given a recipe, render the SAME dish three ways so it can be made in the Instant Pot or without it:
- instant_pot: the pressure-cook method with realistic times (sauté/brown step, liquid needed to come to pressure, pressure-cook minutes, natural vs quick release). Include practical tips (e.g. deglaze to avoid the burn warning).
- air_fryer: honestly say whether the Instant Pot air-fryer lid helps for THIS dish (great for crisping/roasting, useless for wet/soupy dishes). If useful, how; if not, say so and suggest where the lid could help as a companion step.
- stovetop_oven: the conventional translation with realistic total time.
- shopping_list: every ingredient mapped to ONE store (Walmart, Aldi, or Costco).
- best_method: which method you'd pick for this dish and why.
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
    air_fryer: {
      type: 'object', additionalProperties: false,
      properties: { suitable: { type: 'boolean' }, note: { type: 'string' } },
      required: ['suitable', 'note'],
    },
    stovetop_oven: {
      type: 'object', additionalProperties: false,
      properties: { total_time: { type: 'string' }, steps: { type: 'array', items: { type: 'string' } } },
      required: ['total_time', 'steps'],
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
  required: ['dish', 'servings', 'ingredients', 'instant_pot', 'air_fryer', 'stovetop_oven', 'shopping_list', 'best_method', 'notes'],
};

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: CORS });

export async function onRequestOptions() {
  return new Response('', { headers: CORS });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const key = env.ANTHROPIC_API_KEY;
  if (!key) return json({ error: 'ANTHROPIC_API_KEY not set in Cloudflare Pages env' }, 500);

  let body;
  try { body = await request.json(); }
  catch { return json({ error: 'Invalid JSON in request body' }, 400); }

  const title = String(body.title || '').slice(0, 200);
  const text = String(body.body || '').slice(0, 6000);
  const source = String(body.source || '').slice(0, 200);
  if (!text) return json({ error: 'need a recipe body' }, 400);

  const payload = {
    model: env.MODEL || DEFAULT_MODEL,
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
    if (!r.ok) return json({ error: 'Anthropic API error', detail: raw.slice(0, 600) }, r.status);
    const msg = JSON.parse(raw);
    const jsonText = (msg.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
    let data;
    try { data = JSON.parse(jsonText); }
    catch { return json({ error: 'model did not return JSON', raw: jsonText.slice(0, 400) }, 502); }
    return json({ ok: true, data });
  } catch (e) {
    return json({ error: 'Failed to reach Anthropic API: ' + String(e.message || e).slice(0, 300) }, 500);
  }
}
