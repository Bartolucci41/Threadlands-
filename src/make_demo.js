// Converts the original fictional region into a version-1 place file.
const path = require('path');
const fs = require('fs');
const M = require(path.join(__dirname, '..', 'model.js'));

const SQ = Math.sqrt(3);
const KM_PER_UNIT = 1.0;          // one hex width = 1 km
const R = KM_PER_UNIT / SQ;       // circumradius in km
const LAT0 = 0.5, LNG0 = 0.5;     // fictional location, near nothing real
const kx = 111.32 * Math.cos(LAT0 * Math.PI / 180), ky = 110.57;
const AREA = 1.5 * SQ * R * R;    // hexagon area in km2

const FR = {
  core:   { built: 0.9, tree: 0.04, grass: 0.06 },
  mid:    { built: 0.7, tree: 0.15, grass: 0.15 },
  suburb: { built: 0.45, tree: 0.25, grass: 0.3 },
  farm:   { crop: 0.85, grass: 0.1, tree: 0.05 },
  forest: { tree: 0.85, shrub: 0.1, grass: 0.05 },
  water:  { water: 0.95, grass: 0.05 },
  park:   { built: 0.1, tree: 0.35, grass: 0.55 }
};
const DENS = { core: 9000, mid: 6000, suburb: 2500, farm: 60, forest: 5, water: 0, park: 50 };
const parkSet = new Set(M.PARKS);
const r2 = (v, d) => Math.round(v * Math.pow(10, d)) / Math.pow(10, d);

const cols = { lat: [], lng: [], area: [], inside: [], pop: [], elev: [], flood: [], water_km: [],
  built: [], tree: [], shrub: [], grass: [], crop: [], bare: [], water: [], wetland: [], nb: [], poly: [] };

M.T.forEach((t, i) => {
  const kind = parkSet.has(i) ? 'park' : t.base;
  const xk = t.x * KM_PER_UNIT, yk = t.y * KM_PER_UNIT;
  const lat = LAT0 - yk / ky, lng = LNG0 + xk / kx;
  cols.lat.push(r2(lat, 6)); cols.lng.push(r2(lng, 6));
  cols.area.push(r2(AREA, 4));
  cols.inside.push(1);
  cols.pop.push(Math.round(DENS[kind] * AREA * (0.85 + 0.3 * t.rnd2)));
  const rd = t.rd * KM_PER_UNIT;
  cols.elev.push(r2(20 + rd * 4 + t.rnd * 3, 1));
  cols.water_km.push(r2(rd, 2));
  cols.flood.push(kind === 'water' ? 0 : (t.rd < 2.4 ? r2(Math.max(0.2, 1 - t.rd / 2.4), 3) : 0));
  const f = FR[kind];
  ['built', 'tree', 'shrub', 'grass', 'crop', 'bare', 'water', 'wetland'].forEach((k) => cols[k].push(f[k] || 0));
  cols.nb.push(M.NB[i].slice());
  const poly = [];
  for (let k = 0; k < 6; k++) {
    const a = Math.PI / 180 * (60 * k - 30);
    const vx = xk + R * Math.cos(a), vy = yk + R * Math.sin(a);
    poly.push(r2(LAT0 - vy / ky, 6), r2(LNG0 + vx / kx, 6));
  }
  cols.poly.push(poly);
});

const place = {
  format: 'threadlands-place', version: 1,
  name: 'Fictional river city', query: 'demo', kind: 'demo',
  generated: '2026-11-13', h3_res: null, hex_km2: r2(AREA, 3),
  sources: ['Generated from a fixed seed. Not a real place.'],
  notes: ['Fictional region for demonstration. Load a place file to see a real one.'],
  cells: cols
};
const out = path.join(__dirname, 'demo-place.json');
fs.writeFileSync(out, JSON.stringify(place));
console.log('wrote', out, (fs.statSync(out).size / 1024).toFixed(1) + ' KB', M.T.length, 'cells');
