// pot*scraper — THE KITCHEN (Cloudflare Pages Function, /api/kitchen).
//
// Composes a 5-dish Instant Pot menu the way a seasonal chef (Mike Lata / FIG)
// would: recombine a fixed vocabulary of building blocks into fresh dishes.
// Constrained two ways: (1) every dish plays to the Instant Pot's strengths,
// (2) EVERY ingredient is buyable at a Charleston Walmart/Aldi. The protein is
// fixed by the caller so they can actually shop for it.

const API = 'https://api.anthropic.com/v1/messages';
const DEFAULT_MODEL = 'claude-opus-4-8';
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

Ground each dish in a real, recognizable reference — a famous chef, a legendary restaurant, or a specific regional tradition — and name it in "inspiration" (e.g., "Julia Child", "Marcella Hazan", "Madhur Jaffrey", "Antoine's of New Orleans", "Oaxaca", "a Bangkok street stall", "Emilia-Romagna"). The dish should genuinely reflect that reference's technique, not just borrow the name. Vary the references across the five. Give each dish a real, appetizing name.`;

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

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: CORS });

export async function onRequestOptions() { return new Response('', { headers: CORS }); }

export async function onRequestPost(context) {
  const { request, env } = context;
  const key = env.ANTHROPIC_API_KEY;
  if (!key) return json({ error: 'ANTHROPIC_API_KEY not set' }, 500);

  let body;
  try { body = await request.json(); }
  catch { return json({ error: 'Invalid JSON' }, 400); }

  const protein = String(body.protein || 'chicken thighs').slice(0, 60);
  const seed = String(body.seed || '').slice(0, 40);

  const user = `Compose tonight's menu — 5 Instant Pot dishes, every one built on ${protein}, each a fresh recombination in a DIFFERENT flavor world, all shoppable at Walmart/Aldi. (menu seed: ${seed})`;

  const payload = {
    model: env.MODEL || DEFAULT_MODEL,
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
