// Threadlands request relay (Cloudflare Worker).
// The website's "Build this place" button posts here; the relay asks GitHub to run the robot.
// It holds the GitHub key, so the key never appears in the public website.
//
// Settings (Cloudflare dashboard -> Worker -> Settings -> Variables):
//   GITHUB_TOKEN  (secret)  fine-grained token with "Contents: read and write" on Bartolucci41/Threadlands-
//   REPO          (text)    Bartolucci41/Threadlands-
//   SITE          (text)    https://threadlands.org
//   SUPPORT       (KV namespace binding)  where "Back this project" and "Stand with" counts are kept (Workers KV, free tier)
//   SALT          (secret, optional)      any long random text; makes the stored visitor fingerprints unguessable
//   INBOX_KEY     (secret)  a long password of your choosing; opens the private feedback inbox at threadlands.org/inbox/

const ALLOWED = ['https://threadlands.org', 'https://www.threadlands.org', 'https://bartolucci41.github.io'];
const recent = new Map(); // per-visitor limit inside one worker instance (a soft brake, not a guarantee)

function slugify(t) {
  return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
}

function reply(body, status, origin) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': ALLOWED.includes(origin) ? origin : ALLOWED[0],
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Inbox-Key',
      'Vary': 'Origin',
    },
  });
}

const KINDS = ['trees', 'park', 'wetland', 'corridor', 'rain', 'farm', 'river', 'transit', 'other'];
const STATUSES = ['proposed', 'approved', 'underway', 'built'];
function url(u) { u = String(u || '').trim().slice(0, 400); return /^https:\/\/[^\s<>"]+$/.test(u) ? u : ''; }
function text(t, n) { return String(t || '').replace(/[<>]/g, '').replace(/\s+/g, ' ').trim().slice(0, n); }
async function project(b, request, env, origin) {
  const p = {
    place: String(b.place || '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 80),
    name: text(b.name, 100), kind: KINDS.includes(b.kind) ? b.kind : 'other', status: STATUSES.includes(b.status) ? b.status : 'proposed',
    year: Math.max(1990, Math.min(2060, parseInt(b.year, 10) || new Date().getFullYear())),
    lat: Math.round(Number(b.lat) * 1e5) / 1e5, lng: Math.round(Number(b.lng) * 1e5) / 1e5,
    area_km2: Math.max(0, Math.min(5000, Number(b.area_km2) || 0)),
    who: text(b.who, 100), summary: text(b.summary, 600), source_url: url(b.source_url), source_title: text(b.source_title, 140), involved: url(b.involved),
  };
  if (!p.place || !p.name || !isFinite(p.lat) || !isFinite(p.lng) || Math.abs(p.lat) > 90 || Math.abs(p.lng) > 180) return reply({ error: 'Add a name and place the project on the map.' }, 400, origin);
  if (!p.source_url) return reply({ error: 'Add a link to a public source (a news story, an official page or a report).' }, 400, origin);
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('p' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 5) return reply({ error: 'You have sent several projects in the last hour. Please try again later.' }, 429, origin);
  times.push(now); recent.set('p' + ip, times);
  const r = await fetch(`https://api.github.com/repos/${env.REPO || 'Bartolucci41/Threadlands-'}/dispatches`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'Accept': 'application/vnd.github+json', 'User-Agent': 'threadlands-relay', 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: 'project-submitted', client_payload: { project: p } }),
  });
  if (r.status !== 204) return reply({ error: 'The project could not be sent right now.', status: r.status }, 502, origin);
  return reply({ ok: true }, 202, origin);
}

// "Add what you know": an observation pinned on the map (too hot here, water collects here, a proposal...).
// It opens a GitHub issue for review; nothing appears on the map until it is checked (see observation-reviewed.yml).
const OBS = ['heat', 'water', 'shade', 'green', 'change', 'idea', 'other'];
async function observation(b, request, env, origin) {
  const o = {
    place: String(b.place || '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 80),
    kind: OBS.includes(b.kind) ? b.kind : 'other', text: text(b.text, 500), source_url: url(b.source_url),
    lat: Math.round(Number(b.lat) * 1e5) / 1e5, lng: Math.round(Number(b.lng) * 1e5) / 1e5,
  };
  if (!o.place || !o.text || !isFinite(o.lat) || !isFinite(o.lng) || Math.abs(o.lat) > 90 || Math.abs(o.lng) > 180) return reply({ error: 'Say what you noticed and tap the map where it is.' }, 400, origin);
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('o' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 10) return reply({ error: 'You have sent several notes in the last hour. Please try again later.' }, 429, origin);
  times.push(now); recent.set('o' + ip, times);
  const r = await fetch(`https://api.github.com/repos/${env.REPO || 'Bartolucci41/Threadlands-'}/dispatches`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'Accept': 'application/vnd.github+json', 'User-Agent': 'threadlands-relay', 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: 'observation-submitted', client_payload: { observation: o } }),
  });
  if (r.status !== 204) return reply({ error: 'Your note could not be sent right now.', status: r.status }, 502, origin);
  return reply({ ok: true }, 202, origin);
}

// "What would make this place better?": a simple idea with where it would help and, optionally, why.
// It may join an existing idea (same thing, own location and reason) or connect to a related idea, project or group.
// Like observations, it opens a GitHub issue for review; nothing is public until it is checked (see proposal-reviewed.yml).
const TOPIC_KEYS = ['food', 'mobility', 'trees', 'heat', 'water', 'parks', 'safety', 'waste', 'air'];
async function proposal(b, request, env, origin) {
  const num = (v) => (v === null || v === '' || v === undefined || !isFinite(Number(v))) ? null : Math.round(Number(v) * 1e4) / 1e4;
  const o = {
    place: String(b.place || '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 80),
    idea: text(b.idea, 120), why: text(b.why, 280), area: text(b.area, 80),
    scope: ['pin', 'area', 'city'].includes(b.scope) ? b.scope : '',
    topic: (Array.isArray(b.topic) ? b.topic : []).filter((t) => TOPIC_KEYS.includes(t)).slice(0, 4),
    lat: num(b.lat), lng: num(b.lng),
    mode: ['new', 'join', 'connect'].includes(b.mode) ? b.mode : 'new',
    link_kind: ['proposal', 'project', 'group'].includes(b.link_kind) ? b.link_kind : '', link_id: String(b.link_id || '').replace(/[^A-Za-z0-9_-]/g, '').slice(0, 40),
  };
  if (o.scope !== 'pin') { o.lat = null; o.lng = null; }
  if (!o.place || o.idea.length < 4 || !o.scope) return reply({ error: 'Write your idea and say where it would help.' }, 400, origin);
  if (o.scope === 'pin' && (o.lat === null || o.lng === null || Math.abs(o.lat) > 90 || Math.abs(o.lng) > 180)) return reply({ error: 'Tap the map to drop a pin.' }, 400, origin);
  if (o.scope === 'area' && !o.area) return reply({ error: 'Choose a neighborhood.' }, 400, origin);
  if (o.mode !== 'new' && (!o.link_kind || !o.link_id)) o.mode = 'new';
  if (!(await knownPlaces(env)).has(o.place)) return reply({ error: 'Unknown place.' }, 400, origin);
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('i' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 8) return reply({ error: 'You have sent several ideas in the last hour. Please try again later.' }, 429, origin);
  times.push(now); recent.set('i' + ip, times);
  const r = await fetch(`https://api.github.com/repos/${env.REPO || 'Bartolucci41/Threadlands-'}/dispatches`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'Accept': 'application/vnd.github+json', 'User-Agent': 'threadlands-relay', 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: 'proposal-submitted', client_payload: { proposal: o } }),
  });
  if (r.status !== 204) return reply({ error: 'Your idea could not be sent right now.', status: r.status }, 502, origin);
  return reply({ ok: true }, 202, origin);
}

// "Back this project": one count per project, one back per visitor per project.
// Counts live in a single KV entry so the website can read them all at once. Visitors are remembered only as a
// one-way fingerprint (a hash of their network address, the project and a secret salt), never the address itself.
async function knownProjects(env) {
  // Projects and published ideas can both be backed ("I want this too" on an idea counts the same way)
  const site = env.SITE || 'https://threadlands.org', ids = new Set();
  for (const [file, key] of [['projects.json', 'projects'], ['proposals.json', 'proposals']]) {
    try { const r = await fetch(`${site}/data/${file}`, { cf: { cacheTtl: 300 } }); if (r.ok) ((await r.json())[key] || []).forEach((p) => ids.add(String(p.id))); } catch (e) { /* one list missing shouldn't block the other */ }
  }
  return ids;
}
async function fingerprint(text) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(d)].slice(0, 12).map((b) => b.toString(16).padStart(2, '0')).join('');
}
async function counts(env) {
  return (await env.SUPPORT.get('counts', { type: 'json' })) || {};
}
async function back(b, request, env, origin) {
  if (!env.SUPPORT) return reply({ error: 'Backing is not switched on yet.' }, 503, origin);
  const id = String(b.id || '').slice(0, 40);
  if (!id || !(await knownProjects(env)).has(id)) return reply({ error: 'Unknown project.' }, 400, origin);
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('b' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 30) return reply({ error: 'Please try again later.' }, 429, origin);
  times.push(now); recent.set('b' + ip, times);
  const key = 'v:' + id + ':' + (await fingerprint(ip + '|' + id + '|' + (env.SALT || 'threadlands')));
  const c = await counts(env);
  if (await env.SUPPORT.get(key)) return reply({ id, n: c[id] || 0, already: true }, 200, origin);
  c[id] = (c[id] || 0) + 1;
  await env.SUPPORT.put(key, '1', { expirationTtl: 60 * 60 * 24 * 365 });
  await env.SUPPORT.put('counts', JSON.stringify(c));
  return reply({ id, n: c[id] }, 200, origin);
}

// "Stand with" a place: one entry per visitor per place, with how they are connected to it.
// Counts per place and per tie live in one KV entry; a visitor can change their tie or step back.
const TIES = ['live', 'from', 'work', 'care'];
async function knownPlaces(env) {
  const site = env.SITE || 'https://threadlands.org';
  const r = await fetch(`${site}/data/index.json`, { cf: { cacheTtl: 300 } });
  if (!r.ok) return new Set();
  const j = await r.json();
  return new Set((j.places || []).map((p) => String(p.slug)));
}
async function stand(b, request, env, origin) {
  if (!env.SUPPORT) return reply({ error: 'Standing with places is not switched on yet.' }, 503, origin);
  const place = String(b.place || '').slice(0, 80), tie = b.on === false ? null : String(b.tie || 'care');
  if (!place || !(await knownPlaces(env)).has(place)) return reply({ error: 'Unknown place.' }, 400, origin);
  if (tie && !TIES.includes(tie)) return reply({ error: 'Unknown tie.' }, 400, origin);
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('s' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 40) return reply({ error: 'Please try again later.' }, 429, origin);
  times.push(now); recent.set('s' + ip, times);
  const key = 's:' + place + ':' + (await fingerprint(ip + '|' + place + '|' + (env.SALT || 'threadlands')));
  const was = await env.SUPPORT.get(key);
  const all = (await env.SUPPORT.get('stands', { type: 'json' })) || {};
  const c = all[place] || (all[place] = {});
  if (was === tie) return reply({ place, counts: c }, 200, origin);
  if (was) c[was] = Math.max(0, (c[was] || 0) - 1);
  if (tie) { c[tie] = (c[tie] || 0) + 1; await env.SUPPORT.put(key, tie, { expirationTtl: 60 * 60 * 24 * 365 * 2 }); }
  else await env.SUPPORT.delete(key);
  await env.SUPPORT.put('stands', JSON.stringify(all));
  return reply({ place, counts: c }, 200, origin);
}

// ---- Feedback: a private queue. Reports are kept in KV, never published; only the inbox key can read them.
const FB_KINDS = ['broken', 'data', 'unclear', 'idea'];
const FB_STATUS = ['new', 'looking', 'fixed', 'closed'];
async function feedback(b, request, env, origin) {
  if (!env.SUPPORT) return reply({ error: 'Feedback is not switched on yet.' }, 503, origin);
  const kind = FB_KINDS.includes(b.kind) ? b.kind : '';
  const said = String(b.text || '').replace(/[<>]/g, '').trim().slice(0, 2000);
  if (!kind || said.length < 3) return reply({ error: 'Choose what kind of feedback it is and tell us what you saw.' }, 400, origin);
  const email = String(b.email || '').trim().slice(0, 200);
  if (email && !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(email)) return reply({ error: 'That email address does not look right.' }, 400, origin);
  let context = {};
  try { context = JSON.parse(JSON.stringify(b.context || {}).slice(0, 3000)); } catch (e) { context = {}; }
  const shot = typeof b.shot === 'string' && /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(b.shot) && b.shot.length < 2.2e6 ? b.shot : '';
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown', now = Date.now();
  const times = (recent.get('f' + ip) || []).filter((t) => now - t < 3600e3);
  if (times.length >= 10) return reply({ error: 'You have sent a lot of feedback in the last hour. Please try again later.' }, 429, origin);
  times.push(now); recent.set('f' + ip, times);
  // newest first when the inbox lists keys in order
  const id = String(9999999999999 - now).padStart(13, '0') + '-' + Math.random().toString(36).slice(2, 8);
  const item = { id, at: new Date(now).toISOString(), kind, text: said, email, context, hasShot: !!shot, status: 'new' };
  await env.SUPPORT.put('fb:' + id, JSON.stringify(item), { metadata: { kind, at: item.at, status: 'new' } });
  if (shot) await env.SUPPORT.put('fbshot:' + id, shot);
  return reply({ ok: true }, 201, origin);
}
function inboxOk(request, env) {
  const k = request.headers.get('X-Inbox-Key') || '';
  return !!env.INBOX_KEY && k.length >= 12 && k === env.INBOX_KEY;
}
async function inbox(request, env, origin) {
  if (!inboxOk(request, env)) return reply({ error: 'Wrong inbox key.' }, 401, origin);
  const q = new URL(request.url).searchParams, one = q.get('inbox');
  if (one && one !== '1') {
    const item = await env.SUPPORT.get('fb:' + one, { type: 'json' });
    if (!item) return reply({ error: 'Not found.' }, 404, origin);
    if (item.hasShot) item.shot = await env.SUPPORT.get('fbshot:' + one);
    return reply(item, 200, origin);
  }
  const list = await env.SUPPORT.list({ prefix: 'fb:', limit: 200 });
  const items = await Promise.all(list.keys.map((k) => env.SUPPORT.get(k.name, { type: 'json' })));
  return reply({ items: items.filter(Boolean) }, 200, origin);
}
async function inboxStatus(b, request, env, origin) {
  if (!inboxOk(request, env)) return reply({ error: 'Wrong inbox key.' }, 401, origin);
  const id = String(b.id || ''), status = FB_STATUS.includes(b.status) ? b.status : '';
  const item = await env.SUPPORT.get('fb:' + id, { type: 'json' });
  if (!item || !status) return reply({ error: 'Not found.' }, 404, origin);
  item.status = status; item.note = String(b.note || item.note || '').slice(0, 1000);
  await env.SUPPORT.put('fb:' + id, JSON.stringify(item), { metadata: { kind: item.kind, at: item.at, status } });
  return reply({ ok: true }, 200, origin);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return reply({}, 204, origin);
    // Anyone can read how many people back each project
    if (request.method === 'GET' && new URL(request.url).searchParams.has('counts')) {
      if (!env.SUPPORT) return reply({ error: 'Backing is not switched on yet.' }, 503, origin);
      const res = reply({ counts: await counts(env), stands: (await env.SUPPORT.get('stands', { type: 'json' })) || {} }, 200, origin);
      res.headers.set('Cache-Control', 'public, max-age=60');
      return res;
    }
    // The private feedback inbox (needs the inbox key)
    if (request.method === 'GET' && new URL(request.url).searchParams.has('inbox')) return inbox(request, env, origin);
    // Approximate location from the connection, city level, for when the browser can't share one.
    // Cloudflare estimates it from the connection. This worker does not write it to storage or log it;
    // Cloudflare's own request logs may still hold request details for a short time (Workers Logs: up to 7 days).
    if (request.method === 'GET' && new URL(request.url).searchParams.has('where')) {
      const cf = request.cf || {};
      if (cf.latitude == null) return reply({ error: 'unknown' }, 404, origin);
      return reply({ lat: +cf.latitude, lng: +cf.longitude, city: cf.city || '', country: cf.country || '' }, 200, origin);
    }
    if (request.method !== 'POST') return reply({ error: 'Use POST.' }, 405, origin);
    if (!ALLOWED.includes(origin)) return reply({ error: 'Requests are accepted from threadlands.org only.' }, 403, origin);

    let b;
    try { b = await request.json(); } catch (e) { return reply({ error: 'Bad request.' }, 400, origin); }

    // A visitor proposing a real project for the map: checked here, then opened as an issue for review on GitHub
    if (b.type === 'project') return project(b, request, env, origin);
    if (b.type === 'back') return back(b, request, env, origin);
    if (b.type === 'stand') return stand(b, request, env, origin);
    if (b.type === 'observation') return observation(b, request, env, origin);
    if (b.type === 'proposal') return proposal(b, request, env, origin);
    if (b.type === 'feedback') return feedback(b, request, env, origin);
    if (b.type === 'inbox-status') return inboxStatus(b, request, env, origin);
    // Build a new place. Only an OpenStreetMap record chosen from the search results is accepted: the relay looks the
    // record up itself and takes its name, country and kind from there, never from what the visitor typed.
    const osm = String(b.osm || '').toUpperCase();
    if (!/^[NWR]\d{1,12}$/.test(osm)) return reply({ error: 'Choose a place from the search results.' }, 400, origin);
    const site = env.SITE || 'https://threadlands.org';
    const suffix = '-' + osm.toLowerCase();

    // Already built, under any name? Then just open it.
    try {
      const idx = await (await fetch(`${site}/data/index.json`, { cf: { cacheTtl: 60 } })).json();
      const hit = (Array.isArray(idx) ? idx : idx.places || []).find((e) => String(e.slug || '').endsWith(suffix));
      if (hit) return reply({ slug: hit.slug, ready: true }, 200, origin);
    } catch (e) { /* the index is a shortcut; the build itself also refuses duplicates */ }

    // Look the record up on the server
    let rec;
    try {
      const lr = await fetch(`https://nominatim.openstreetmap.org/lookup?osm_ids=${osm}&format=jsonv2&addressdetails=1&accept-language=en`,
        { headers: { 'User-Agent': 'threadlands-relay (https://threadlands.org)' } });
      rec = (await lr.json())[0];
    } catch (e) { return reply({ error: 'Could not check that place right now. Please try again in a minute.' }, 502, origin); }
    if (!rec) return reply({ error: 'That place could not be found on OpenStreetMap.' }, 404, origin);
    const okKind = rec.category === 'boundary' || rec.category === 'place' || (rec.addresstype && /^(city|town|village|municipality|county|state|region|suburb|quarter|neighbourhood|borough|district|province|island|postcode|hamlet)$/.test(rec.addresstype));
    if (!okKind) return reply({ error: 'Choose a city, town, district or region from the search results.' }, 400, origin);
    const a = rec.address || {};
    const name = String(rec.name || (rec.display_name || '').split(',')[0] || '').slice(0, 80);
    const country = String(a.country || (rec.display_name || '').split(',').pop() || '').trim().slice(0, 60);
    if (!name) return reply({ error: 'That place has no name on OpenStreetMap.' }, 400, origin);
    const slug = [slugify(name), slugify(country), osm.toLowerCase()].filter(Boolean).join('-');
    const has = await fetch(`${site}/data/places/${slug}.json`, { method: 'HEAD' });
    if (has.ok) return reply({ slug, ready: true }, 200, origin);

    // A build already running for this record? Then wait for that one instead of starting another.
    const key = 'build:' + osm;
    if (env.SUPPORT) {
      const running = await env.SUPPORT.get(key);
      if (running) return reply({ slug: running, ready: false, building: true }, 202, origin);
    }

    // Soft limit: three new requests per visitor per hour
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const now = Date.now();
    const times = (recent.get(ip) || []).filter((t) => now - t < 3600e3);
    if (times.length >= 3) return reply({ error: 'You have requested several places in the last hour. Please try again later.' }, 429, origin);
    times.push(now); recent.set(ip, times);

    const r = await fetch(`https://api.github.com/repos/${env.REPO || 'Bartolucci41/Threadlands-'}/dispatches`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'threadlands-relay',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_type: 'build-place', client_payload: { slug, query: 'osm:' + osm } }),
    });
    if (r.status !== 204) return reply({ error: 'The build robot did not accept the request.', status: r.status }, 502, origin);
    if (env.SUPPORT) await env.SUPPORT.put(key, slug, { expirationTtl: 90 * 60 });   // a build takes up to about 75 minutes
    return reply({ slug, ready: false }, 202, origin);
  },
};
