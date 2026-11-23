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
for (const r of ranking) {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(dir, r.slug + '.json'))), pr = T.profile(data, D);
    r.top = pr && pr.top[0] ? pr.top[0].key : null;
    // The plain-language city profile: what presses on the place, and the land and water it is tied to
    const reg = data.regional || {}, bs = typeof reg.basin === 'string' ? JSON.parse(reg.basin) : (reg.basin || {}), need = reg.need_km2_per_person || 0.0019;
    const fs50 = (reg.foodshed || []).find(f => f.km === 50), fs250 = (reg.foodshed || []).find(f => f.km === 250);
    const share = f => f && f.pop > 0 ? Math.min(100, Math.round(100 * f.crop_km2 / (f.pop * need))) : null;
    const PP = TM.prepare(data), st = T.placeStats(PP);
    summary[r.slug] = {
      pressures: (pr && pr.top || []).slice(0, 3).map(t => ({ key: t.key, t: t.t, what: t.what, who: t.who, pct: t.pct })),
      threads: { basin_km2: bs.area_km2 || null, basin_built: bs.shares && bs.shares.built != null ? Math.round(100 * bs.shares.built) : null,
        basin_forest: bs.shares ? Math.round(100 * ((bs.shares.forest || 0) + (bs.shares.wetland || 0))) : null,
        food50: share(fs50), food250: share(fs250), wild_km: st.wild != null ? +st.wild.toFixed(1) : null, natural: st.natural != null ? Math.round(100 * st.natural) : null },
      tests: { heatwave: Math.round(st.t_heatwave), flood: Math.round(st.t_flood), drought: Math.round(st.t_drought) }
    };
  } catch (e) { console.error('summary', r.slug, e.message); }
}
ranking.forEach((r, k) => { r.rank = k + 1; });
fs.writeFileSync(path.join(__dirname, '..', 'data', 'summary.json'), JSON.stringify({ updated: new Date().toISOString().slice(0, 10), places: summary }));
fs.writeFileSync(path.join(__dirname, '..', 'data', 'ranking.json'), JSON.stringify({ updated: new Date().toISOString().slice(0, 10), places: ranking }));
console.log('profile-dist:', n, 'places; ranking:', ranking.length);
