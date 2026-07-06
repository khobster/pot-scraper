// pot*scraper — the menu. An endless, randomly-ordered menu of dishes styled
// after the old Four Seasons card; click one for the recipe and cook it.

const ENDPOINTS = ['/api/cook', '/.netlify/functions/cook'];
const BATCH = 24;
const PIN = '<svg class="pin-sm" viewBox="0 0 32 46" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="5" width="14" height="9" rx="4.5"/><path d="M12 14 11 42"/><path d="M20 14 21 42"/><circle cx="16" cy="19" r="3.1"/><path d="M11 27 21 27"/></svg>';
const KITCHEN = ['/api/kitchen', '/.netlify/functions/kitchen'];
const PROTEINS = ['chicken thighs', 'chicken breast', 'whole chicken', 'ground beef', 'beef chuck roast',
  'beef short ribs', 'beef stew meat', 'pork shoulder', 'pork chops', 'boneless pork ribs', 'ground pork',
  'lamb shoulder', 'turkey', 'white beans', 'black beans', 'chickpeas', 'lentils', 'mushrooms', 'tofu'];
const state = { mode: 'seasons', data: { seasons: [], laundromat: [] }, deck: [], i: 0, q: '',
  kitchen: { protein: 'chicken thighs' } };
const active = () => state.data[state.mode];

const $ = (s) => document.querySelector(s);
const menu = $('#menu');
const footNote = $('#foot-note');

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// dish "hero" — the ingredient the menu sets in CAPS (proteins first)
const HEROES = ['beef', 'steak', 'brisket', 'chicken', 'pork', 'bacon', 'ham', 'sausage', 'chorizo',
  'lamb', 'mutton', 'turkey', 'duck', 'salmon', 'cod', 'tuna', 'fish', 'shrimp', 'crab', 'lobster',
  'tofu', 'chickpea', 'lentil', 'bean', 'mushroom', 'eggplant', 'potato', 'pasta', 'rice'];

function heroTitle(title, ingredients) {
  const extra = (ingredients || []).map((i) => i.name.toLowerCase());
  const words = HEROES.concat(extra.filter((w) => !HEROES.includes(w)));
  for (const w of words) {
    const re = new RegExp('\\b(' + w.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&') + 's?)\\b', 'i');
    const m = re.exec(title);
    if (m) {
      const s = m.index, e = s + m[0].length;
      return esc(title.slice(0, s)) + '<span class="hero">' + esc(title.slice(s, e)) + '</span>' + esc(title.slice(e));
    }
  }
  return esc(title);
}

function shuffle(a) {
  const arr = a.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// date line, menu-style ("SUMMER 2026 · FRIDAY, JULY 5")
(function setDate() {
  const now = new Date();
  const seasons = ['WINTER', 'WINTER', 'SPRING', 'SPRING', 'SPRING', 'SUMMER', 'SUMMER', 'SUMMER', 'AUTUMN', 'AUTUMN', 'AUTUMN', 'WINTER'];
  const days = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
  const months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER'];
  const el = $('#dateline');
  if (el) el.textContent = `${seasons[now.getMonth()]} ${now.getFullYear()} · ${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()}`;
})();

// ---- premium weighted scroll (Lenis) — that "Mercedes glide" ----
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let lenis = null;
if (window.Lenis && !reduceMotion) {
  lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, touchMultiplier: 1.4 });
  const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
  requestAnimationFrame(raf);
}

// each dish eases into view as you reach it
const revealIO = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); revealIO.unobserve(e.target); } });
}, { rootMargin: '0px 0px -6% 0px' });

// ---- load (two menus: the seasons recipes + the laundromat legends) ----
const FILES = { seasons: 'data/recipes.json', laundromat: 'data/pot-legends.json' };
function ensureData(mode, cb) {
  if (state.data[mode].length) return cb();
  fetch(FILES[mode]).then((r) => r.json())
    .then((d) => { state.data[mode] = d; cb(); })
    .catch(() => { footNote.textContent = 'could not load the menu.'; });
}
ensureData('seasons', reset);
ensureData('laundromat', () => {});   // preload so the toggle is instant

function currentSet() {
  const q = state.q.trim().toLowerCase();
  const all = active();
  if (!q) return all;
  return all.filter((r) => {
    const extra = r.ingredients ? r.ingredients.map((i) => i.name).join(' ') : (r.description || '');
    const hay = (r.title + ' ' + (r.cuisine || r.source || '') + ' ' + extra).toLowerCase();
    return hay.includes(q);
  });
}

function reset() {
  menu.innerHTML = '';
  state.deck = shuffle(currentSet());
  state.i = 0;
  footNote.textContent = state.q ? '' : 'the menu never ends · scroll on';
  renderBatch();
  requestAnimationFrame(fillViewport);
}

function fillViewport() {
  if (document.body.scrollHeight <= window.innerHeight + 300 && state.deck.length) {
    if (renderBatch()) requestAnimationFrame(fillViewport);
  }
}

function renderBatch() {
  if (!state.deck.length) { footNote.textContent = 'no dishes match — try another word'; return false; }
  const frag = document.createDocumentFragment();
  for (let n = 0; n < BATCH; n++) {
    if (state.i >= state.deck.length) {
      if (state.q) { footNote.textContent = '— end of matches —'; break; }
      state.deck = shuffle(active());   // endless: reshuffle and keep going
      state.i = 0;
    }
    frag.appendChild(entryEl(state.deck[state.i++]));
  }
  menu.appendChild(frag);
  return true;
}

function entryEl(r) {
  const el = document.createElement('article');
  el.className = 'entry reveal';
  if (state.mode === 'laundromat') {
    const desc = r.description ? `<div class="desc">${esc(r.description)}</div>` : '';
    const src = r.fl
      ? `<div class="src-line">${PIN}The French Laundry</div>`
      : `<div class="src-line">${esc(r.source)}${r.year ? ' · ' + esc(r.year) : ''}</div>`;
    el.innerHTML = `<div class="name">${esc(r.title)}</div>${desc}${src}`;
  } else {
    const desc = r.ingredients.slice(0, 3).map((i) => esc(i.name)).join(', ');
    const flag = r.cuisine ? `<div class="flag">${esc(r.cuisine)}</div>` : '';
    el.innerHTML = `<div class="name">${heroTitle(r.title, r.ingredients)}</div>
      ${desc ? `<div class="desc">${desc}</div>` : ''}${flag}`;
  }
  el.onclick = () => openDetail(r);
  revealIO.observe(el);
  return el;
}

new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting && state.mode !== 'kitchen' && active().length) renderBatch();
}, { rootMargin: '700px' }).observe($('#sentinel'));

// ---- THE KITCHEN: a menu that composes itself (FIG-style) ----
function showKitchen() {
  menu.innerHTML = `
    <div class="kitchen-controls">
      <div class="kc-row"><span class="kc-label">tonight's five, built on</span>
        <select id="protein" class="kc-select"></select></div>
      <button id="reroll" class="kc-reroll">↻ compose a new menu</button>
      <p class="kc-note">every ingredient shoppable at Walmart or Aldi</p>
    </div>
    <div id="kitchen-menu"></div>`;
  const sel = $('#protein');
  sel.innerHTML = PROTEINS.map((p) => `<option${p === state.kitchen.protein ? ' selected' : ''}>${p}</option>`).join('');
  sel.onchange = (e) => { state.kitchen.protein = e.target.value; loadKitchen(false); };
  $('#reroll').onclick = () => loadKitchen(true);
  loadKitchen(false);
}

function loadKitchen(reroll) {
  const km = $('#kitchen-menu');
  const today = new Date().toISOString().slice(0, 10);
  const protein = state.kitchen.protein;
  const cacheKey = `kitchen:${today}:${protein}`;
  if (!reroll) {
    const cached = localStorage.getItem(cacheKey);
    if (cached) { try { return renderKitchen(JSON.parse(cached)); } catch (e) {} }
  }
  km.innerHTML = `<p class="kc-loading">composing tonight's menu…</p>`;
  const seed = reroll ? today + ':' + Math.random().toString(36).slice(2, 8) : today;
  (async () => {
    try {
      let json = null;
      for (const url of KITCHEN) {
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ protein, seed }) });
        if (res.status === 404) continue;
        json = await res.json();
        if (!res.ok || !json.ok) throw new Error(json.error || 'request failed');
        break;
      }
      if (!json) throw new Error('no kitchen function on this deploy');
      localStorage.setItem(cacheKey, JSON.stringify(json.data.dishes));
      renderKitchen(json.data.dishes);
    } catch (e) {
      km.innerHTML = `<div class="err">Couldn’t compose the menu: ${esc(e.message)}.</div>`;
    }
  })();
}

function renderKitchen(dishes) {
  const km = $('#kitchen-menu');
  km.innerHTML = '';
  dishes.forEach((d) => {
    const el = document.createElement('article');
    el.className = 'entry reveal';
    el.innerHTML = `<div class="name">${esc(d.name)}</div>
      <div class="desc">${esc(d.description)}</div>
      <div class="src-line">${esc(d.flavor_world)}</div>`;
    el.onclick = () => openKitchen(d);
    km.appendChild(el);
    revealIO.observe(el);
  });
}

function openKitchen(d) {
  detailBody.innerHTML = `
    <h2 class="d-title">${esc(d.name)}</h2>
    <p class="d-source">${esc(d.flavor_world)} · built on ${esc(state.kitchen.protein)}</p>
    <p class="d-desc">${esc(d.description)}</p>
    <div class="divider"></div>
    <div class="block"><h4>the building blocks</h4><div class="shop">
      <div><span class="store">braise:</span> ${esc(d.liquid)}</div>
      <div><span class="store">vegetable:</span> ${esc(d.vegetable)}</div>
      <div><span class="store">starch:</span> ${esc(d.starch)}</div>
      <div><span class="store">finish:</span> ${esc(d.finish)}</div>
    </div></div>
    <button class="cook-btn" id="mbtn">🍲 Cook it — full Instant Pot + traditional recipe</button>
    <div id="cookOut"></div>`;
  $('#mbtn').onclick = () => runCook(d);
  detail.hidden = false;
  document.body.style.overflow = 'hidden';
  detail.scrollTop = 0;
  if (lenis) lenis.stop();
}

// ---- detail ----
const detail = $('#detail');
const detailBody = $('#detailBody');

function shopHTML(r) {
  const by = {};
  r.ingredients.forEach((i) => { const s = i.stores[0]; (by[s] = by[s] || []).push(i.name); });
  return ['Walmart', 'Aldi', 'Costco'].filter((s) => by[s]).map((s) =>
    `<div><span class="store">${s}:</span> ${by[s].join(', ')}</div>`).join('');
}

function openDetail(r) {
  if (state.mode === 'laundromat') return openLaundromat(r);
  const cz = r.cuisine ? `<span class="d-cz">${esc(r.cuisine)}</span>` : '';
  const hard = r.hard && r.hard.length
    ? `<div class="block"><div class="warn"><b>harder to source:</b> ${r.hard.map((h) => esc(h.name)).join(', ')}</div></div>` : '';
  detailBody.innerHTML = `
    <h2 class="d-title">${heroTitle(r.title, r.ingredients)}</h2>
    ${cz}
    <p class="d-src"><a href="${esc(r.source_url)}" target="_blank" rel="noopener">original recipe ↗</a></p>
    <div class="divider"></div>
    <div class="block"><h4>shopping list · Charleston</h4><div class="shop">${shopHTML(r)}</div></div>
    ${hard}
    <div class="block"><h4>the recipe</h4><div class="orig">${esc(r.body)}</div></div>
    <button class="cook-btn" id="mbtn">🍲 Cook it — Instant Pot + the traditional way</button>
    <div id="cookOut"></div>`;
  $('#mbtn').onclick = () => runCook(r);
  detail.hidden = false;
  document.body.style.overflow = 'hidden';
  detail.scrollTop = 0;
  if (lenis) lenis.stop();          // freeze the page glide while the card is open
}

function openLaundromat(r) {
  const src = r.fl ? `${PIN}The French Laundry` : `${esc(r.source)}${r.year ? ' · ' + esc(r.year) : ''}`;
  const desc = r.description ? `<p class="d-desc">${esc(r.description)}</p>` : '';
  detailBody.innerHTML = `
    <h2 class="d-title">${esc(r.title)}</h2>
    <p class="d-source">${src}</p>
    ${desc}
    <div class="divider"></div>
    <button class="cook-btn" id="mbtn">🍲 Cook it — Instant Pot + the traditional way</button>
    <div id="cookOut"></div>`;
  $('#mbtn').onclick = () => runCook(r);
  detail.hidden = false;
  document.body.style.overflow = 'hidden';
  detail.scrollTop = 0;
  if (lenis) lenis.stop();
}

function closeDetail() {
  detail.hidden = true;
  document.body.style.overflow = '';
  if (lenis) lenis.start();
}
$('#close').onclick = closeDetail;
detail.onclick = (e) => { if (e.target === detail) closeDetail(); };
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !detail.hidden) closeDetail(); });

// ---- cook it ----
async function runCook(r) {
  const btn = $('#mbtn'), out = $('#cookOut');
  btn.disabled = true;
  btn.textContent = '🍲 Working it out…';
  out.innerHTML = '';
  try {
    let body, source;
    const title = r.title || r.name;
    if (state.mode === 'kitchen') {
      source = `${r.flavor_world} · ${state.kitchen.protein}`;
      body = `${r.name}. ${r.description}. Built on ${state.kitchen.protein}, in the ${r.flavor_world} flavor world. `
        + `Braising liquid: ${r.liquid}. Vegetable: ${r.vegetable}. Starch: ${r.starch}. Finish: ${r.finish}. `
        + `Keep every ingredient available at a Charleston Walmart or Aldi.`;
    } else if (state.mode === 'laundromat') {
      source = r.fl ? 'The French Laundry' : r.source;
      body = r.description
        ? r.description
        : `A classic dish, "${r.title}", as served historically at ${r.source}${r.year ? ' (' + r.year + ')' : ''}. Reconstruct it faithfully.`;
    } else { body = r.body; source = r.source_title; }
    const payload = JSON.stringify({ title, body, source });
    let json = null;
    for (const url of ENDPOINTS) {
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload });
      if (res.status === 404) continue;
      json = await res.json();
      if (!res.ok || !json.ok) throw new Error(json.error || 'request failed');
      break;
    }
    if (!json) throw new Error('no cook function on this deploy');
    out.innerHTML = cookHTML(json.data);
    btn.textContent = '🍲 Cook it again';
  } catch (e) {
    out.innerHTML = `<div class="err">Couldn’t do it: ${esc(e.message)}.</div>`;
    btn.textContent = '🍲 Try again';
  } finally { btn.disabled = false; }
}

function methodBlock(icon, name, time, steps) {
  const li = (steps || []).map((s) => `<li>${esc(s)}</li>`).join('');
  return `<div class="method">
    <div class="method-head"><span class="method-name">${icon} ${esc(name)}</span>
      ${time ? `<span class="method-time">${esc(time)}</span>` : ''}</div>
    <ol>${li}</ol></div>`;
}

function cookHTML(m) {
  const ing = (m.ingredients || []).map((i) => `<li>${esc(i)}</li>`).join('');
  const shop = (m.shopping_list || []).map((s) => `<li>${esc(s.item)} <span class="pill">${esc(s.store)}</span></li>`).join('');
  const ip = m.instant_pot || {}, tr = m.traditional || {};
  return `<div class="cooked">
    <h3>${esc(m.dish || 'Recipe')}</h3>
    <div class="serves">serves ${esc(m.servings || '?')}</div>
    <div class="block"><h4>ingredients</h4><ul>${ing}</ul></div>
    ${methodBlock('⚡', 'Instant Pot', ip.total_time, ip.steps)}
    ${methodBlock('🔥', tr.method || 'Traditional', tr.total_time, tr.steps)}
    ${m.best_method ? `<div class="block"><h4>which to pick</h4><p style="text-align:center">${esc(m.best_method)}</p></div>` : ''}
    <div class="block"><h4>shopping list · Charleston</h4><ul>${shop}</ul></div>
    ${m.notes ? `<div class="block"><h4>notes</h4><p style="text-align:center">${esc(m.notes)}</p></div>` : ''}
  </div>`;
}

// ---- the clothespin toggle: cycle DINNER -> THE LAUNDROMAT -> THE KITCHEN ----
const MODES = ['seasons', 'laundromat', 'kitchen'];
const TITLES = { seasons: 'DINNER', laundromat: 'THE LAUNDROMAT', kitchen: 'THE KITCHEN' };
function setMode(mode) {
  state.mode = mode;
  document.body.classList.toggle('laundromat', mode === 'laundromat');
  document.body.classList.toggle('kitchen', mode === 'kitchen');
  $('.dinner').textContent = TITLES[mode];
  $('#search').style.display = mode === 'kitchen' ? 'none' : '';
  $('#search').placeholder = mode === 'laundromat' ? 'find a classic' : 'find a dish';
  state.q = ''; $('#search').value = '';
  window.scrollTo(0, 0);
  if (lenis) lenis.scrollTo(0, { immediate: true });
  if (mode === 'kitchen') showKitchen();
  else ensureData(mode, reset);
}
$('#toggle').onclick = () => setMode(MODES[(MODES.indexOf(state.mode) + 1) % MODES.length]);

// ---- search ----
let t;
$('#search').addEventListener('input', (e) => {
  state.q = e.target.value;
  clearTimeout(t);
  t = setTimeout(reset, 180);
});
