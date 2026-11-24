// Builds data/profile-dist.json: how every library place scores on each pressure, so a place can be compared with the rest.
const fs = require('fs'), path = require('path');
const T = require(path.join(__dirname, '..', 'assets', 'profile.js'));
const TM = (function () { const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'model2.js'), 'utf8'); return new Function(src + '; return ThreadModel;')(); })();
const ctx = {}, ranking = [], summary = {};
const IX = (() => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'index.json'))).places || []; } catch (e) { return []; } })();
const BYSLUG = {}; IX.forEach(e => { BYSLUG[e.slug] = e; });
const PROJ = (() => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'projects.json'))).projects || []; } catch (e) { return []; } })();
const dir = path.join(__dirname, '..', 'data', 'places'), dist = {};
Object.keys(T.KEYS).forEach(k => dist[k] = []);
let n = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json'))) {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(dir, f)));
    const m = T.measure(data); if (!m) continue; n++;
    try {
      const PP = TM.prepare(data), st = T.placeStats(PP), slug = f.replace(/\.json$/, ''), ie = BYSLUG[slug] || {};
      const top = (T.profile(data, null) || { top: [] }).top[0];
      ranking.push({ slug, name: ie.name || data.name, country: ie.country || '', cc: ie.cc || data.country_code || '', requested: !!ie.requested,
        index: +PP.BAU_TODAY.index.toFixed(1), projects: (() => { const mine = PROJ.filter(p => p.place === slug); if (!mine.length) return undefined; const e = T.projectsEffect(PP, mine, TM.ZERO); return { n: mine.length, counted: e.counted, add: +e.index.toFixed(2) }; })(), heat: Math.round(PP.BAU_TODAY.metrics.heat), habitat: Math.round(PP.BAU_TODAY.metrics.habitat),
        food: Math.round(PP.BAU_TODAY.metrics.food), pop: Math.round(st.pop), top: top ? top.key : null });
      for (const k in st) if (st[k] !== null && isFinite(st[k])) (ctx[k] = ctx[k] || []).push(+(+st[k]).toFixed(4));
    } catch (e) { console.error('stats', f, e.message); }
    for (const k in T.KEYS) { const s = T.KEYS[k](m); if (s !== null && s !== undefined && isFinite(s)) dist[k].push(+s.toFixed(4)); }
  } catch (e) { console.error(f, e.message); }
}
for (const k in dist) dist[k].sort((a, b) => a - b);
for (const k in ctx) ctx[k].sort((a, b) => a - b);
fs.writeFileSync(path.join(__dirname, '..', 'data', 'profile-dist.json'), JSON.stringify({ places: n, dist, ctx }));
ranking.forEach(r => { r.base = r.index; if (r.projects && r.projects.add) r.index = +(r.index + r.projects.add).toFixed(1); });
ranking.sort((a, b) => b.index - a.index);
// re-rank pressures now that the library spread is known
const D = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'profile-dist.json'))).dist;
// The study boundary for the profile's small map: the modeled region and the city inside it, as simple outlines,
// with the people and area each figure refers to
function hull(pts) {
  pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (pts.length < 3) return pts;
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const p of pts) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
  return lo.slice(0, -1).concat(up.slice(0, -1)).map((p) => [+p[0].toFixed(3), +p[1].toFixed(3)]);
}
function study(data) {
  const c = data.cells || {}, n = (c.lat || []).length, all = [], city = [];
  let popR = 0, popC = 0, kmR = 0, kmC = 0;
  for (let i = 0; i < n; i++) {
    const p = [+c.lng[i], +c.lat[i]], pop = +c.pop[i] || 0, a = +(c.area || [])[i] || 0;
    all.push(p); popR += pop; kmR += a;
    if (+(c.inside || [])[i]) { city.push(p); popC += pop; kmC += a; }
  }
  return { region: hull(all), city: hull(city), pop_region: Math.round(popR), pop_city: Math.round(popC), km2_region: Math.round(kmR), km2_city: Math.round(kmC), buffer_km: data.buffer_km ? Math.round(data.buffer_km) : null };
}
for (const r of ranking) {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(dir, r.slug + '.json'))), pr = T.profile(data, D);
    r.top = pr && pr.top[0] ? pr.top[0].key : null;
    // The plain-language city profile: what presses on the place, and the land and water it is tied to
    const reg = data.regional || {}, bs = typeof reg.basin === 'string' ? JSON.parse(reg.basin) : (reg.basin || {}), need = reg.need_km2_per_person || 0.0019;
    const fs50 = (reg.foodshed || []).find(f => f.km === 50), fs250 = (reg.foodshed || []).find(f => f.km === 250);
    const share = f => f && f.pop > 0 ? Math.min(100, Math.round(100 * f.crop_km2 / (f.pop * need))) : null;
    const PP = TM.prepare(data), st = T.placeStats(PP), mm = T.measure(data);
    // Measured values people can compare directly, each in its own units
    if (mm) r.vals = { tree: Math.round(100 * mm.trees), green_low: Math.round(100 * mm.grey), heat: mm.heat == null ? null : Math.round(100 * mm.heat), flood: Math.round(100 * mm.flood), farm: share(fs50), wild_km: st.wild != null ? +st.wild.toFixed(1) : null };
    summary[r.slug] = {
      pressures: (pr && pr.top || []).slice(0, 3).map(t => ({ key: t.key, t: t.t, f: t.f, layer: t.layer, what: t.what, who: t.who, pct: t.pct })),
      threads: { basin_km2: bs.area_km2 || null, basin_built: bs.shares && bs.shares.built != null ? Math.round(100 * bs.shares.built) : null,
        basin_forest: bs.shares ? Math.round(100 * ((bs.shares.forest || 0) + (bs.shares.wetland || 0))) : null,
        food50: share(fs50), food250: share(fs250), wild_km: st.wild != null ? +st.wild.toFixed(1) : null, natural: st.natural != null ? Math.round(100 * st.natural) : null },
      tests: { heatwave: Math.round(st.t_heatwave), flood: Math.round(st.t_flood), drought: Math.round(st.t_drought) },
      study: study(data)
    };
  } catch (e) { console.error('summary', r.slug, e.message); }
}
ranking.forEach((r, k) => { r.rank = k + 1; });
fs.writeFileSync(path.join(__dirname, '..', 'data', 'summary.json'), JSON.stringify({ updated: new Date().toISOString().slice(0, 10), places: summary }));
fs.writeFileSync(path.join(__dirname, '..', 'data', 'ranking.json'), JSON.stringify({ updated: new Date().toISOString().slice(0, 10), places: ranking }));
console.log('profile-dist:', n, 'places; ranking:', ranking.length);
