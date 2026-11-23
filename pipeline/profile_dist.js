// Builds data/profile-dist.json: how every library place scores on each pressure, so a place can be compared with the rest.
const fs = require('fs'), path = require('path');
const T = require(path.join(__dirname, '..', 'assets', 'profile.js'));
const TM = (function () { const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'model2.js'), 'utf8'); return new Function(src + '; return ThreadModel;')(); })();
const ctx = {};
const dir = path.join(__dirname, '..', 'data', 'places'), dist = {};
Object.keys(T.KEYS).forEach(k => dist[k] = []);
let n = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json'))) {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(dir, f)));
    const m = T.measure(data); if (!m) continue; n++;
    try {
      const st = T.placeStats(TM.prepare(data));
      for (const k in st) if (st[k] !== null && isFinite(st[k])) (ctx[k] = ctx[k] || []).push(+(+st[k]).toFixed(4));
    } catch (e) { console.error('stats', f, e.message); }
    for (const k in T.KEYS) { const s = T.KEYS[k](m); if (s !== null && s !== undefined && isFinite(s)) dist[k].push(+s.toFixed(4)); }
  } catch (e) { console.error(f, e.message); }
}
for (const k in dist) dist[k].sort((a, b) => a - b);
for (const k in ctx) ctx[k].sort((a, b) => a - b);
fs.writeFileSync(path.join(__dirname, '..', 'data', 'profile-dist.json'), JSON.stringify({ places: n, dist, ctx }));
console.log('profile-dist:', n, 'places');
