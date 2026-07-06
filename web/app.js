// pot*scraper browser — load the recipe subset, browse/search/filter, and
// modernize a chosen recipe via the Netlify function (key stays server-side).

// Modernize endpoints, tried in order: Cloudflare Pages Function first, then
// Netlify. Whichever platform the site is deployed on answers; the other 404s.
const ENDPOINTS = ['/api/cook', '/.netlify/functions/cook'];
const state = { all: [], view: [], store: 'all', cuisine: 'all', q: '' };

const $ = (s) => document.querySelector(s);
const grid = $('#grid');
const countEl = $('#count');

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const stars = (n) => '★'.repeat(n) + '·'.repeat(10 - n);

// ---- load ----
fetch('data/recipes.json')
  .then((r) => r.json())
  .then((data) => {
    state.all = data;
    populateCuisines(data);
    apply();
  })
  .catch(() => { countEl.textContent = 'could not load recipes.'; });

function populateCuisines(data) {
  const counts = {};
  data.forEach((r) => { if (r.cuisine) counts[r.cuisine] = (counts[r.cuisine] || 0) + 1; });
  const names = Object.keys(counts).sort((a, b) => counts[b] - counts[a]); // most recipes first
  const sel = $('#cuisine');
  names.forEach((c) => {
    const o = document.createElement('option');
    o.value = c; o.textContent = `${c} (${counts[c]})`;
    sel.appendChild(o);
  });
}

// ---- filter + render ----
function apply() {
  const q = state.q.trim().toLowerCase();
  state.view = state.all.filter((r) => {
    if (state.cuisine !== 'all' && r.cuisine !== state.cuisine) return false;
    if (state.store !== 'all') {
      const has = r.ingredients.some((i) => i.stores.includes(state.store));
      if (!has) return false;
    }
    if (q) {
      const hay = (r.title + ' ' + r.ingredients.map((i) => i.name).join(' ')).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  countEl.textContent = `${state.view.length.toLocaleString()} recipes`
    + (state.cuisine !== 'all' ? ` · ${state.cuisine}` : '')
    + (state.store !== 'all' ? ` · at ${state.store}` : '')
    + (q ? ` · “${state.q}”` : '');
  render();
}

function render() {
  const slice = state.view.slice(0, 120); // keep the DOM light
  grid.innerHTML = slice.map(cardHTML).join('') ||
    '<p style="color:var(--muted)">no recipes match — try a different word or store.</p>';
  [...grid.children].forEach((el, i) => {
    if (slice[i]) el.onclick = () => openDetail(slice[i]);
  });
  if (state.view.length > slice.length) {
    const more = document.createElement('p');
    more.style.cssText = 'grid-column:1/-1;color:var(--muted);text-align:center;font-family:monospace;font-size:13px';
    more.textContent = `+ ${state.view.length - slice.length} more — refine your search to see them`;
    grid.appendChild(more);
  }
}

function cardHTML(r) {
  const ing = r.ingredients.slice(0, 5).map((i) => `<span class="pill">${esc(i.name)}</span>`).join('');
  const thumb = r.image ? `<img class="thumb" src="${esc(r.image)}" alt="" loading="lazy">` : '';
  const cz = r.cuisine ? `<span class="cz">${esc(r.cuisine)}</span>` : '';
  return `<article class="card">
    ${thumb}
    <div class="card-body">
      <div class="card-top">${cz}<span class="score"><span class="stars">${stars(r.score)}</span> ${r.score}</span></div>
      <h3>${esc(r.title)}</h3>
      <div class="tags">${ing}</div>
      <span class="src">${esc(r.source_title.slice(0, 60))}</span>
    </div>
  </article>`;
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
  const measures = r.measures.length
    ? `<div class="block"><h4>old measures</h4><div class="measures">${r.measures.map((m) => esc(m.unit) + ' → ' + esc(m.modern)).join(' · ')}</div></div>` : '';
  const hard = r.hard.length
    ? `<div class="block"><div class="warn"><b>harder to source:</b> ${r.hard.map((h) => esc(h.name) + ' — ' + esc(h.reason)).join('; ')}</div></div>` : '';
  const img = r.image ? `<img class="d-img" src="${esc(r.image)}" alt="">` : '';
  const cz = r.cuisine ? `<span class="d-cz">${esc(r.cuisine)}</span>` : '';
  const srcLabel = r.source_title.startsWith('TheMealDB') ? 'TheMealDB' : 'Gutenberg';
  detailBody.innerHTML = `
    ${img}
    <h2 class="d-title">${cz}${esc(r.title)}</h2>
    <p class="d-src">from ${esc(r.source_title)} — ${esc(r.source_author)}
      · <a href="${esc(r.source_url)}" target="_blank" rel="noopener">${srcLabel}</a></p>
    <span class="d-score">${stars(r.score)} ${r.score}/10 practical</span>
    <div class="block"><h4>shopping list · Charleston</h4><div class="shop">${shopHTML(r)}</div></div>
    ${hard}
    ${measures}
    <div class="block"><h4>original recipe</h4><div class="orig">${esc(r.body)}</div></div>
    <button class="modernize-btn" id="mbtn">🍲 Cook it — Instant Pot + the traditional way</button>
    <div id="modernOut"></div>`;
  $('#mbtn').onclick = () => runCook(r);
  detail.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeDetail() { detail.hidden = true; document.body.style.overflow = ''; }
$('#close').onclick = closeDetail;
detail.onclick = (e) => { if (e.target === detail) closeDetail(); };
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !detail.hidden) closeDetail(); });

// ---- cook it 3 ways (calls the serverless function) ----
async function runCook(r) {
  const btn = $('#mbtn');
  const out = $('#modernOut');
  btn.disabled = true;
  btn.textContent = '🍲 Working it out… (a few seconds)';
  out.innerHTML = '';
  try {
    const payload = JSON.stringify({ title: r.title, body: r.body, source: r.source_title });
    let json = null;
    for (const url of ENDPOINTS) {
      const res = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload,
      });
      if (res.status === 404) continue;          // wrong platform's route — try the next
      json = await res.json();
      if (!res.ok || !json.ok) throw new Error(json.error || 'request failed');
      break;
    }
    if (!json) throw new Error('no cook function found on this deploy');
    out.innerHTML = cookHTML(json.data);
    btn.textContent = '🍲 Cook it again';
  } catch (e) {
    out.innerHTML = `<div class="err">Couldn’t do it: ${esc(e.message)}.<br>
      (If this is a fresh deploy, make sure <b>ANTHROPIC_API_KEY</b> is set in the site’s environment variables.)</div>`;
    btn.textContent = '🍲 Try again';
  } finally {
    btn.disabled = false;
  }
}

function methodBlock(icon, name, time, steps) {
  const li = (steps || []).map((s) => `<li>${esc(s)}</li>`).join('');
  return `<div class="method">
    <div class="method-head"><span class="method-name">${icon} ${name}</span>
      ${time ? `<span class="method-time">${esc(time)}</span>` : ''}</div>
    <ol>${li}</ol>
  </div>`;
}

function cookHTML(m) {
  const ing = (m.ingredients || []).map((i) => `<li>${esc(i)}</li>`).join('');
  const shop = (m.shopping_list || []).map((s) => `<li>${esc(s.item)} <span class="pill">${esc(s.store)}</span></li>`).join('');
  const ip = m.instant_pot || {};
  const tr = m.traditional || {};
  return `<div class="modern">
    <h3>${esc(m.dish || 'Recipe')}</h3>
    <div class="serves">serves ${esc(m.servings || '?')}</div>
    <div class="block"><h4>ingredients</h4><ul>${ing}</ul></div>
    ${methodBlock('⚡', 'Instant Pot', ip.total_time, ip.steps)}
    ${methodBlock('🔥', tr.method || 'Traditional', tr.total_time, tr.steps)}
    ${m.best_method ? `<div class="block"><h4>which to pick</h4><p>${esc(m.best_method)}</p></div>` : ''}
    <div class="block"><h4>shopping list · Charleston</h4><ul>${shop}</ul></div>
    ${m.notes ? `<div class="block"><h4>notes</h4><p>${esc(m.notes)}</p></div>` : ''}
  </div>`;
}

// ---- controls ----
$('#search').addEventListener('input', (e) => { state.q = e.target.value; apply(); });
$('#cuisine').addEventListener('change', (e) => { state.cuisine = e.target.value; apply(); });
$('#stores').addEventListener('click', (e) => {
  const b = e.target.closest('.chip'); if (!b) return;
  [...$('#stores').children].forEach((c) => c.classList.remove('on'));
  b.classList.add('on');
  state.store = b.dataset.store;
  apply();
});
$('#surprise').addEventListener('click', () => {
  if (!state.view.length) return;
  openDetail(state.view[Math.floor(Math.random() * state.view.length)]);
});
