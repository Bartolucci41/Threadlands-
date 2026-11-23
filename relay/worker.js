// Threadlands request relay (Cloudflare Worker).
// The website's "Build this place" button posts here; the relay asks GitHub to run the robot.
// It holds the GitHub key, so the key never appears in the public website.
//
// Settings (Cloudflare dashboard -> Worker -> Settings -> Variables):
//   GITHUB_TOKEN  (secret)  fine-grained token with "Contents: read and write" on Bartolucci41/Threadlands-
//   REPO          (text)    Bartolucci41/Threadlands-
//   SITE          (text)    https://threadlands.org

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
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
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

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return reply({}, 204, origin);
    if (request.method !== 'POST') return reply({ error: 'Use POST.' }, 405, origin);
    if (!ALLOWED.includes(origin)) return reply({ error: 'Requests are accepted from threadlands.org only.' }, 403, origin);

    let b;
    try { b = await request.json(); } catch (e) { return reply({ error: 'Bad request.' }, 400, origin); }

    // A visitor proposing a real project for the map: checked here, then opened as an issue for review on GitHub
    if (b.type === 'project') return project(b, request, env, origin);
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
