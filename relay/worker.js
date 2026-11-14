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

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return reply({}, 204, origin);
    if (request.method !== 'POST') return reply({ error: 'Use POST.' }, 405, origin);
    if (!ALLOWED.includes(origin)) return reply({ error: 'Requests are accepted from threadlands.org only.' }, 403, origin);

    let b;
    try { b = await request.json(); } catch (e) { return reply({ error: 'Bad request.' }, 400, origin); }
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
