// Builds data/profile-dist.json: how every library place scores on each pressure, so a place can be compared with the rest.
const fs = require('fs'), path = require('path');
const T = require(path.join(__dirname, '..', 'assets', 'profile.js'));
const dir = path.join(__dirname, '..', 'data', 'places'), dist = {};
Object.keys(T.KEYS).forEach(k => dist[k] = []);
let n = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json'))) {
  try {
    const m = T.measure(JSON.parse(fs.readFileSync(path.join(dir, f)))); if (!m) continue; n++;
    for (const k in T.KEYS) { const s = T.KEYS[k](m); if (s !== null && s !== undefined && isFinite(s)) dist[k].push(+s.toFixed(4)); }
  } catch (e) { console.error(f, e.message); }
}
for (const k in dist) dist[k].sort((a, b) => a - b);
fs.writeFileSync(path.join(__dirname, '..', 'data', 'profile-dist.json'), JSON.stringify({ places: n, dist }));
console.log('profile-dist:', n, 'places');
