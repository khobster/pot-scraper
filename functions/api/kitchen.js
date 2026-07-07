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

Draw WIDELY from these columns — range across them, don't lean on the same few — keeping each dish coherent inside ONE flavor world so it hangs together:
- FLAVOR WORLD: French wine braise; Provençal; Italian ragù (soffritto-tomato); Northern Italian (butter, wine, risotto); North Indian (garam masala); South Indian coconut curry; Thai coconut-curry; Vietnamese caramel braise (kho); Filipino adobo; Chinese red-braise (soy, star anise); Sichuan chili; Japanese soy-mirin or curry; Korean gochujang braise; Mexican chile-cumin & adobo; Tex-Mex chili; Creole/Cajun trinity; Southern smothered or BBQ; Carolina Lowcountry; Caribbean/Jamaican curry & jerk; Spanish paprika-chorizo; Portuguese tomato-wine; Greek lemon-tomato-cinnamon (stifado); Moroccan/North African warm spice; Middle Eastern cumin-coriander; West African peanut stew; Cuban sofrito (ropa vieja); Hungarian paprika (goulash); German/Alsatian beer-mustard; or a clean American pot roast.
- BRAISING LIQUID: red or white wine, beer, hard cider, stock, coconut milk, crushed or fire-roasted tomatoes, coffee, soy-mirin, salsa verde, cream, mustard-cream.
- VEGETABLE (seasonal): mirepoix, fennel, bell peppers, poblano, mushrooms, hearty greens, cabbage, potatoes, sweet potato, winter squash, turnip, parsnip, green beans, peas, tomatillo, okra, corn.
- STARCH: white/basmati/jasmine rice, polenta or cheesy grits, mashed potato or sweet potato, egg noodles, pasta, couscous, farro, barley, orzo, tortillas, crusty bread, cornbread, biscuits, dumplings.
- FINISH: fresh herbs, gremolata, chimichurri, salsa verde, quick pickle, fresh chile, lemon or lime, yogurt or sour cream, feta, toasted nuts, crispy shallots, herb oil, grated parmesan.

TWO HARD RULES:
1. INSTANT POT ONLY — braise / stew / pressure / simmer. No plating tricks, no raw, no pastry, no sear-only.
2. WALMART / ALDI ONLY — every single ingredient must be reliably stocked at a normal US Walmart Supercenter (its international aisle counts: soy sauce, coconut milk, curry powder, garam masala, cumin, chili powder, chipotle in adobo, sriracha, gochujang, hoisin, fish sauce, rice vinegar, canned tomatoes, common spices) or Aldi. Do NOT use specialty-market items — no preserved lemon, ras el hanout, whole dried Oaxacan chiles, doubanjiang, gochugaru, fresh lemongrass, achiote, berbere, banana leaf, exotic offal. When a classic dish needs a specialty item, substitute the Walmart-available equivalent (chili powder + chipotle instead of dried chiles; lemon instead of preserved lemon; curry powder/garam masala from the spice aisle) and keep it honest.

Ground each dish in a real, recognizable reference and NAME it in "inspiration" — range WIDELY, don't repeat the usual handful. Pull from famous chefs (Julia Child, Jacques Pépin, Escoffier, Marcella Hazan, Lidia Bastianich, Madhur Jaffrey, Diana Kennedy, Rick Bayless, Paul Prudhomme, Leah Chase, Edna Lewis, Sean Brock, Andrea Nguyen, Maangchi, Fuchsia Dunlop, J. Kenji López-Alt, Yotam Ottolenghi, Claudia Roden, Marcus Samuelsson, José Andrés, Ina Garten, Emeril Lagasse), legendary restaurants (Antoine's, Commander's Palace, Galatoire's, Momofuku, Husk, The Grey, Rodney Scott's BBQ), or specific regions (Oaxaca, Puebla, Emilia-Romagna, Tuscany, Naples, Provence, Lyon, Alsace, Andalusia, Marseille, Sichuan, Hunan, Hanoi, Bangkok, Kerala, Punjab, Goa, Seoul, Manila, Kingston, Lagos, Lima, Havana, New Orleans, the Carolina Lowcountry, Budapest). The dish must genuinely reflect that reference's technique, not just borrow the name. Vary the references across the five. Favor the less-expected dish over the single most famous one for a given protein and cuisine — do NOT default to Coq au Vin for French chicken or Tikka Masala for Indian chicken; reach past the obvious into the deeper regional repertoire. Keep the "inspiration" value SHORT — just the name (a chef, restaurant, or region), not a sentence. Give each dish a real, appetizing name.`;

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
  const avoid = (Array.isArray(body.avoid) ? body.avoid : []).map((s) => String(s).slice(0, 80)).slice(-35);
  const avoidLine = avoid.length
    ? `\n\nAlready served on previous menus — do NOT repeat any of these or close variants; compose five genuinely DIFFERENT dishes: ${avoid.join('; ')}.`
    : '';

  const user = `Compose tonight's menu — 5 Instant Pot dishes, every one built on ${protein}, each a fresh recombination in a DIFFERENT flavor world, all shoppable at Walmart/Aldi. (seed: ${seed})${avoidLine}`;

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
