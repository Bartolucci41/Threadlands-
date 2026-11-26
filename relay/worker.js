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

// "Back this project": one count per project, one back per visitor per project.
// Counts live in a single KV entry so the website can read them all at once. Visitors are remembered only as a
// one-way fingerprint (a hash of their network address, the project and a secret salt), never the address itself.
async function knownProjects(env) {
  const site = env.SITE || 'https://threadlands.org';
  const r = await fetch(`${site}/data/projects.json`, { cf: { cacheTtl: 300 } });
  if (!r.ok) return new Set();
  const j = await r.json();
  return new Set((j.projects || []).map((p) => String(p.id)));
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
    // Cloudflare provides it with every request; nothing is stored.
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
    if (b.type === 'feedback') return feedback(b, request, env, origin);
    if (b.type === 'inbox-status') return inboxStatus(b, request, env, origin);
    const osm = String(b.osm || '');
    const name = String(b.name || '').slice(0, 80);
    const country = String(b.country || '').slice(0, 60);
    if (!/^[NWR]\d{1,12}$/.test(osm) || !name) return reply({ error: 'Choose a place from the search results.' }, 400, origin);

    const slug = [slugify(name), slugify(country), osm.toLowerCase()].filter(Boolean).join('-');

    // Already built? Then just open it.
    const site = env.SITE || 'https://threadlands.org';
    const have = await fetch(`${site}/data/places/${slug}.json`, { method: 'HEAD' });
    if (have.ok) return reply({ slug, ready: true }, 200, origin);

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
    return reply({ slug, ready: false }, 202, origin);
  },
};
