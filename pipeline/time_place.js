// Builds data/time/<slug>.json for the "through time" dashboard: the old lakebed traced from elevation,
// today's land and people cell by cell, and one modeled future, all from the place's own Threadlands data.
// Usage: node pipeline/time_place.js mexico-city
const fs = require('fs'), path = require('path');
const slug = process.argv[2] || 'mexico-city';
const CFG = {
  'mexico-city': {
    seed: [19.4326, -99.1332],          // Zócalo, on the old island of Tenochtitlan
    lakeLine: 2250,                      // high-water line used by López-López et al. 2023, after Torres-Alves & Morales-Nápoles 2020
    bbox: [19.13, 19.87, -99.36, -98.76], // the basin floor and the hills around it
    future: { wetland: ['open', 'barren'], canopy: 20, climate: 'mid' }
  }
}[slug];
if (!CFG) throw new Error('No time config for ' + slug);
const TM = (function () { const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'model2.js'), 'utf8'); return new Function(src + '; return ThreadModel;')(); })();
const d = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'places', slug + '.json')));
const c = d.cells, N = c.lat.length, num = v => +v || 0;
// The old lake: every cell at or below the high-water line that connects to the seed through neighbours at or below it
let seed = 0, best = 1e9;
for (let i = 0; i < N; i++) { const q = (c.lat[i] - CFG.seed[0]) ** 2 + (c.lng[i] - CFG.seed[1]) ** 2; if (q < best) { best = q; seed = i; } }
const lake = new Uint8Array(N), st = [seed]; lake[seed] = 1;
while (st.length) { const i = st.pop(); for (const j of (c.nb[i] || [])) { if (j == null || lake[j]) continue; if (num(c.elev[j]) <= CFG.lakeLine) { lake[j] = 1; st.push(j); } } }
// Today's numbers, on and off the old lakebed
const S = { all: { pop: 0, km2: 0 }, lake: { pop: 0, km2: 0, built_km2: 0, hot: 0, flood: 0, lowgreen: 0 }, off: { pop: 0, hot: 0, flood: 0, lowgreen: 0 } };
for (let i = 0; i < N; i++) {
  const p = num(c.pop[i]), a = num(c.area[i]), g = num(c.tree[i]) + num(c.grass[i]) + num(c.shrub[i]) + num(c.wetland[i]);
  const hot = typeof c.lst_rel[i] === 'number' && c.lst_rel[i] >= 2, fl = num(c.flood[i]) >= 0.5, lg = g < 0.1;
  S.all.pop += p; S.all.km2 += a;
  const t = lake[i] ? S.lake : S.off; t.pop += p; if (hot) t.hot += p; if (fl) t.flood += p; if (lg) t.lowgreen += p;
  if (lake[i]) { S.lake.km2 += a; S.lake.built_km2 += a * num(c.built[i]); }
}
const pct = (x, y) => y ? Math.round(100 * x / y) : null;
const today = {
  pop_region: Math.round(S.all.pop), pop_lakebed: Math.round(S.lake.pop), lake_km2: Math.round(S.lake.km2), lakebed_built_km2: Math.round(S.lake.built_km2),
  hot_lake: pct(S.lake.hot, S.lake.pop), hot_off: pct(S.off.hot, S.off.pop), flood_lake: pct(S.lake.flood, S.lake.pop), flood_off: pct(S.off.flood, S.off.pop),
  lowgreen_lake: pct(S.lake.lowgreen, S.lake.pop), lowgreen_off: pct(S.off.lowgreen, S.off.pop),
  water_km2_now: Math.round(c.area.reduce((s, a, i) => s + (lake[i] ? a * (num(c.water[i]) + num(c.wetland[i])) : 0), 0))
};
// One modeled future: wetlands back on the unbuilt lakebed, and more street trees, in 2050 on the middle climate path
const PP = TM.prepare(d);
PP.setClimate(CFG.future.climate);
const bau = PP.BAU, fut = new Uint8Array(N);
let wkm = 0;
PP.base.forEach((b, i) => { if (lake[i] && CFG.future.wetland.includes(b)) { PP.paint.set(i, 'wetland'); fut[i] = 1; wkm += num(c.area[i]); } });
const plan = PP.evaluate({ canopy: CFG.future.canopy, corridors: 0, wetlands: 0, regen: 0, compact: 0 });
const r1 = v => +(+v).toFixed(1), pick = r => ({ index: r1(r.index), heat: r1(r.metrics.heat), flood: r1(r.metrics.flood), nature: r1(r.metrics.habitat), storage: r1(r.metrics.storage) });
const future = { climate: CFG.future.climate, wetland_km2: Math.round(wkm), canopy: CFG.future.canopy, bau: pick(bau), plan: pick(plan) };
// Cells inside the dashboard frame, compact
const B = CFG.bbox, cells = { lat: [], lng: [], lake: [], elev: [], built: [], green: [], water: [], hot: [], flood: [], pop: [], fut: [] };
for (let i = 0; i < N; i++) {
  if (c.lat[i] < B[0] || c.lat[i] > B[1] || c.lng[i] < B[2] || c.lng[i] > B[3]) continue;
  cells.lat.push(+c.lat[i].toFixed(4)); cells.lng.push(+c.lng[i].toFixed(4)); cells.lake.push(lake[i]); cells.elev.push(Math.round(num(c.elev[i])));
  cells.built.push(Math.round(100 * num(c.built[i]))); cells.green.push(Math.round(100 * (num(c.tree[i]) + num(c.grass[i]) + num(c.shrub[i]))));
  cells.water.push(Math.round(100 * (num(c.water[i]) + num(c.wetland[i])))); cells.hot.push(typeof c.lst_rel[i] === 'number' && c.lst_rel[i] >= 2 ? 1 : 0);
  cells.flood.push(num(c.flood[i]) >= 0.5 ? 1 : 0); cells.pop.push(Math.round(num(c.pop[i]))); cells.fut.push(fut[i]);
}
const out = { slug, name: d.name, updated: new Date().toISOString().slice(0, 10), hex_km2: +(+d.hex_km2).toFixed(2), lake_line_m: CFG.lakeLine, bbox: B, today, future, cells };
fs.mkdirSync(path.join(__dirname, '..', 'data', 'time'), { recursive: true });
fs.writeFileSync(path.join(__dirname, '..', 'data', 'time', slug + '.json'), JSON.stringify(out));
console.log(slug, cells.lat.length, 'cells', JSON.stringify(today), JSON.stringify(future));
