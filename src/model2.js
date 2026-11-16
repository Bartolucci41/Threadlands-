/* Threadlands model v2: works on any place file (format "threadlands-place", version 1).
   A place file holds hex cells with land cover fractions, population, elevation, a flood weight,
   neighbor lists and outlines. prepare(place) derives everything the levers need;
   the returned object's evaluate(levers) scores one scenario. */
const ThreadModel = (function () {
  'use strict';

  const BUDGET = 240;
  const COST = { canopy: 0.9, corridors: 0.6, wetlands: 0.85, regen: 0.8, compact: 1.6 };
  const LEVER_KEYS = ['canopy', 'corridors', 'wetlands', 'regen', 'compact'];
  const ZERO = { canopy: 0, corridors: 0, wetlands: 0, regen: 0, compact: 0 };
  let BREEZE = 0.3, BREEZE_KM = 5;   // strength and inland reach of sea and lake breezes
  let SURF_W = 0.75;
  let USE_CAL = true;            // share of heat intensity set by built surface rather than population density
  const KH = 1.6;              // heat load that scores 0 on heat relief
  const NEED_KM2 = 0.0019;     // cropland per person for full self-sufficiency (0.19 ha, about the world average)
  const RETIRED_CROP = 0.5;    // share of a retired sprawl hex that returns to cropland
  const URBAN = { core: 1, mid: 1, suburb: 1, greenway: 1 };
  const COOL = { forest: 1, wetland: 1, water: 0.9, pond: 0.9, park: 1, corridor: 0.8, greenway: 0.8, open: 0.7, regen: 0.4, farm: 0.25, barren: 0.05 };
  const HAB = { water: 0.5, pond: 0.6, forest: 1, wetland: 1, open: 0.7, park: 0.8, corridor: 0.9, greenway: 0.55, regen: 0.55, farm: 0.12, barren: 0.1 };
  const MOVE = { forest: 0.3, wetland: 0.3, open: 0.6, park: 0.3, farm: 1, barren: 1.5, water: 3, suburb: 2.5, mid: 4, core: 6 };
  // Climate scenarios for about 2050 (IPCC AR6): extra warming over land since 2011-2020, rain intensity, sea level
  const CLIMATE = {
    today: { key: 'today', name: 'Today', dT: 0, slr: 0 },
    mid: { key: 'mid', name: '2050, middle path', dT: 1.3, slr: 0.20 },
    high: { key: 'high', name: '2050, high emissions', dT: 1.9, slr: 0.23 }
  };
  const REQUIRED = ['lat', 'lng', 'area', 'pop', 'built', 'tree', 'shrub', 'grass', 'crop', 'bare', 'water', 'wetland', 'flood', 'nb', 'poly'];

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function validate(d) {
    if (!d || typeof d !== 'object') throw new Error('This file is not a Threadlands place file.');
    if (d.format !== 'threadlands-place') throw new Error('This file is not a Threadlands place file. Make one with the place builder notebook.');
    if (d.version !== 1) throw new Error('This place file uses format version ' + d.version + '. This page reads version 1.');
    const c = d.cells;
    if (!c) throw new Error('The place file has no cells.');
    for (const k of REQUIRED) {
      if (!Array.isArray(c[k])) throw new Error('The place file is missing the "' + k + '" column.');
    }
    const n = c.lat.length;
    if (n < 20) throw new Error('The place has only ' + n + ' hexes. Make the region larger and try again.');
    if (n > 6000) throw new Error('The place has ' + n + ' hexes. Rebuild it with MAX_HEXES at 6000 or fewer.');
    for (const k of REQUIRED) {
      if (c[k].length !== n) throw new Error('The "' + k + '" column has ' + c[k].length + ' rows, but the place has ' + n + ' hexes.');
    }
    return n;
  }

  function hash01(i, salt) {
    let a = (i * 2654435761 + salt * 974711) >>> 0;
    a ^= a >>> 15; a = Math.imul(a, 2246822507) >>> 0;
    a ^= a >>> 13; a = Math.imul(a, 3266489909) >>> 0;
    a ^= a >>> 16;
    return (a >>> 0) / 4294967296;
  }

  function quantile(arr, q) {
    if (!arr.length) return 0;
    const s = arr.slice().sort((x, y) => x - y);
    const p = clamp(q, 0, 1) * (s.length - 1);
    const lo = Math.floor(p), hi = Math.ceil(p);
    return s[lo] + (s[hi] - s[lo]) * (p - lo);
  }

  // Binary min-heap for Dijkstra
  function Heap() { this.k = []; this.v = []; }
  Heap.prototype.push = function (key, val) {
    const k = this.k, v = this.v;
    let i = k.length; k.push(key); v.push(val);
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (k[p] <= k[i]) break;
      [k[p], k[i]] = [k[i], k[p]]; [v[p], v[i]] = [v[i], v[p]]; i = p;
    }
  };
  Heap.prototype.pop = function () {
    const k = this.k, v = this.v;
    const topK = k[0], topV = v[0];
    const lk = k.pop(), lv = v.pop();
    if (k.length) {
      k[0] = lk; v[0] = lv;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < k.length && k[l] < k[m]) m = l;
        if (r < k.length && k[r] < k[m]) m = r;
        if (m === i) break;
        [k[m], k[i]] = [k[i], k[m]]; [v[m], v[i]] = [v[i], v[m]]; i = m;
      }
    }
    return [topK, topV];
  };
  Heap.prototype.size = function () { return this.k.length; };

  function prepare(d) {
    const N = validate(d);
    const c = d.cells;
    const num = (k, i) => { const x = Number(c[k][i]); return isFinite(x) ? x : 0; };
    const NB = c.nb.map((l) => (Array.isArray(l) ? l.filter((j) => Number.isInteger(j) && j >= 0 && j < N) : []));
    const notes = [];

    // Projection to km around the place center
    let lat0 = 0, lng0 = 0;
    for (let i = 0; i < N; i++) { lat0 += num('lat', i); lng0 += num('lng', i); }
    lat0 /= N; lng0 /= N;
    // Web Mercator scaled to km at the center, so maps line up exactly with street and satellite tiles
    const mxf = (lng) => (lng + 180) / 360;
    const myf = (lat) => { const s = Math.sin(Math.max(-85, Math.min(85, lat)) * Math.PI / 180); return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); };
    const MK = 40075.017 * Math.cos(lat0 * Math.PI / 180), mx0 = mxf(lng0), my0 = myf(lat0);
    const MERC = { mx0, my0, K: MK };
    const X = new Float64Array(N), Y = new Float64Array(N);
    for (let i = 0; i < N; i++) { X[i] = (mxf(num('lng', i)) - mx0) * MK; Y[i] = (myf(num('lat', i)) - my0) * MK; }
    const POLY = c.poly.map((p) => {
      const out = [];
      if (!Array.isArray(p)) return out;
      for (let j = 0; j + 1 < p.length; j += 2) out.push((mxf(Number(p[j + 1])) - mx0) * MK, (myf(Number(p[j])) - my0) * MK);
      return out;
    });

    const area = new Float64Array(N), pop = new Float64Array(N), flood = new Float64Array(N);
    const fr = {};
    ['built', 'tree', 'shrub', 'grass', 'crop', 'bare', 'water', 'wetland'].forEach((k) => {
      fr[k] = new Float64Array(N);
      for (let i = 0; i < N; i++) fr[k][i] = clamp(num(k, i), 0, 1);
    });
    let meanArea = 0;
    for (let i = 0; i < N; i++) meanArea += Math.max(0, num('area', i));
    meanArea /= N;
    for (let i = 0; i < N; i++) {
      area[i] = num('area', i) > 0 ? num('area', i) : meanArea || 1;
      pop[i] = Math.max(0, num('pop', i));
      flood[i] = clamp(num('flood', i), 0, 1);
    }
    const river = new Float64Array(N);
    const hasRivers = Array.isArray(c.river) && c.river.length === N;
    if (hasRivers) for (let i = 0; i < N; i++) river[i] = clamp(Number(c.river[i]) || 0, 0, 1);
    const inside = Array.isArray(c.inside) && c.inside.length === N ? c.inside.map((v) => !!v) : new Array(N).fill(true);
    let totalPop = 0;
    for (let i = 0; i < N; i++) totalPop += pop[i];
    if (totalPop <= 0) {
      for (let i = 0; i < N; i++) { pop[i] = fr.built[i] * area[i] * 3000; totalPop += pop[i]; }
      notes.push('The file has no population data, so population is estimated at 3,000 people per km² of built-up land.');
    }

    // 1. Classify each hex
    const base = new Array(N);
    const isUrbanCand = (i) => fr.built[i] >= 0.25 && fr.water[i] < 0.5;
    const usePop = totalPop > 0;
    const dens = new Float64Array(N);
    const urbanDens = [];
    for (let i = 0; i < N; i++) {
      dens[i] = usePop ? pop[i] / area[i] : fr.built[i];
      if (isUrbanCand(i)) urbanDens.push(dens[i]);
    }
    const q75 = quantile(urbanDens, 0.75), q35 = quantile(urbanDens, 0.35);
    for (let i = 0; i < N; i++) {
      const g = fr;
      if (g.water[i] >= 0.5) base[i] = 'water';
      else if (isUrbanCand(i)) base[i] = dens[i] >= q75 ? 'core' : dens[i] >= q35 ? 'mid' : 'suburb';
      else if (g.wetland[i] >= 0.3) base[i] = 'wetland';
      else if (g.tree[i] >= 0.4) base[i] = 'forest';
      else if (g.crop[i] >= 0.3) base[i] = 'farm';
      else if (g.grass[i] + g.shrub[i] >= 0.4) base[i] = 'open';
      else if (g.bare[i] >= 0.5) base[i] = 'barren';
      else {
        const opts = [['farm', g.crop[i]], ['forest', g.tree[i]], ['open', g.grass[i] + g.shrub[i]], ['barren', g.bare[i]], ['wetland', g.wetland[i]], ['water', g.water[i]]];
        opts.sort((a, b) => b[1] - a[1]);
        base[i] = opts[0][1] > 0 ? opts[0][0] : 'open';
      }
    }
    let nWaterHex = 0;
    for (let i = 0; i < N; i++) if (base[i] === 'water') nWaterHex++;
    let landN = 0, landHigh = 0;
    for (let i = 0; i < N; i++) if (base[i] !== 'water') { landN++; if (flood[i] >= 0.8) landHigh++; }
    if (landN && landHigh / landN > 0.6) notes.push('Almost all land here is low and close to water, so flood screening can’t tell places apart much. Flood exposure on the map mostly reflects where people live.');
    if (!hasRivers && nWaterHex > 0 && nWaterHex < 0.01 * N) notes.push('Few rivers or lakes show up at this scale. Small rivers and canals are often too narrow for satellite land cover, so some flood-prone land may be missing.');
    if (!urbanDens.length) notes.push('No built-up hexes were found, so heat, flood exposure and travel scores have little to work with.');

    // 2. City parks: green hexes mostly surrounded by city
    const isUrb = (b) => b === 'core' || b === 'mid' || b === 'suburb';
    const parkCand = [];
    for (let i = 0; i < N; i++) {
      if (!(base[i] === 'forest' || base[i] === 'open' || base[i] === 'wetland')) continue;
      let u = 0;
      for (const j of NB[i]) if (isUrb(base[j])) u++;
      if (u >= 3) parkCand.push([fr.tree[i] + fr.grass[i] + fr.shrub[i], i]);
    }
    parkCand.sort((a, b) => b[0] - a[0]);
    const PARKS = parkCand.slice(0, 12).map((x) => x[1]);
    let newParks = false;
    if (!PARKS.length) {
      // No green islands found: place up to three new park sites in the densest districts, spread apart
      const cores = [];
      for (let i = 0; i < N; i++) if (base[i] === 'core') cores.push(i);
      cores.sort((a, b) => dens[b] - dens[a]);
      if (cores.length) {
        PARKS.push(cores[0]);
        while (PARKS.length < Math.min(3, cores.length)) {
          let best = -1, bd = -1;
          for (const i of cores) {
            if (PARKS.indexOf(i) >= 0) continue;
            let m = 1e18;
            for (const p of PARKS) m = Math.min(m, (X[i] - X[p]) ** 2 + (Y[i] - Y[p]) ** 2);
            if (m > bd) { bd = m; best = i; }
          }
          if (best < 0) break;
          PARKS.push(best);
        }
        newParks = true;
        notes.push('No green islands were found inside the city, so ' + PARKS.length + ' new park sites were placed in the densest districts.');
      }
    }
    const parkSet = new Set(PARKS);
    PARKS.forEach((i) => { base[i] = 'park'; });

    // 3. The main natural habitat area: largest connected block of forest, wetland and open land
    const natural = (b) => b === 'forest' || b === 'wetland' || b === 'open';
    const ncomp = new Int32Array(N).fill(-1);
    let bestComp = -1, bestSize = 0, compId = 0;
    for (let i = 0; i < N; i++) {
      if (!natural(base[i]) || ncomp[i] >= 0) continue;
      let size = 0;
      const st = [i]; ncomp[i] = compId;
      while (st.length) {
        const a = st.pop(); size++;
        for (const j of NB[a]) if (natural(base[j]) && ncomp[j] < 0) { ncomp[j] = compId; st.push(j); }
      }
      if (size > bestSize) { bestSize = size; bestComp = compId; }
      compId++;
    }

    // 4. Corridors: cheapest path from the habitat block to each park
    const corr = new Map();
    const parkPaths = [];
    let Lmax = 0;
    if (bestComp >= 0 && PARKS.length) {
      const dist = new Float64Array(N).fill(Infinity);
      const prev = new Int32Array(N).fill(-1);
      const h = new Heap();
      for (let i = 0; i < N; i++) if (ncomp[i] === bestComp) { dist[i] = 0; h.push(0, i); }
      while (h.size()) {
        const [dk, a] = h.pop();
        if (dk > dist[a]) continue;
        for (const j of NB[a]) {
          const nd = dk + (MOVE[base[j]] || 1);
          if (nd < dist[j]) { dist[j] = nd; prev[j] = a; h.push(nd, j); }
        }
      }
      for (const p of PARKS) {
        if (!isFinite(dist[p])) continue;
        const path = [];
        let a = prev[p];
        while (a >= 0 && ncomp[a] !== bestComp) { path.push(a); a = prev[a]; }
        path.reverse();
        let k = 0;
        const conv = [];
        for (const i of path) {
          const b = base[i];
          if (b === 'water' || b === 'forest' || b === 'wetland' || b === 'park') continue;
          const was = corr.get(i);
          corr.set(i, was === undefined ? k : Math.min(was, k));
          conv.push(i);
          k++;
        }
        parkPaths.push({ park: p, cells: conv });
        Lmax = Math.max(Lmax, k);
      }
    }
    if (bestComp < 0) notes.push('No natural habitat block was found, so corridors have nothing to start from.');

    // 5. Floodplain land that could become wetland, wettest first
    const restorable = [];
    for (let i = 0; i < N; i++) {
      if ((base[i] === 'farm' || base[i] === 'open') && flood[i] > 0.12) restorable.push(i);
    }
    restorable.sort((a, b) => (flood[b] + hash01(b, 7) * 0.05) - (flood[a] + hash01(a, 7) * 0.05));
    const wetP = new Float64Array(N).fill(2);
    const wetWgt = new Float64Array(N);
    let restorableW = 0;
    restorable.forEach((i, k) => { wetP[i] = (k + 1) / restorable.length; wetWgt[i] = 0.5 + flood[i]; restorableW += wetWgt[i]; });
    if (!restorable.length) notes.push('No farmland or open land sits in a floodplain, so the wetlands lever has nothing to restore.');

    // 6. Sprawl, farthest from the city's center of population first
    let cx = 0, cy = 0, cw = 0;
    for (let i = 0; i < N; i++) {
      if (!isUrb(base[i])) continue;
      const w = usePop ? pop[i] : fr.built[i];
      cx += X[i] * w; cy += Y[i] * w; cw += w;
    }
    if (cw > 0) { cx /= cw; cy /= cw; }
    const subs = [];
    for (let i = 0; i < N; i++) if (base[i] === 'suburb') subs.push(i);
    const sd = (i) => Math.hypot(X[i] - cx, Y[i] - cy);
    subs.sort((a, b) => sd(b) - sd(a));
    const subP = new Float64Array(N).fill(2);
    subs.forEach((i, k) => { subP[i] = (k + 1) / subs.length; });
    const subOrder = subs.slice();

    // Fixed quantities
    const rnd3 = new Float64Array(N);
    for (let i = 0; i < N; i++) rnd3[i] = hash01(i, 3);
    let POP0 = 0, nUrban0 = 0;
    for (let i = 0; i < N; i++) if (isUrb(base[i])) { POP0 += pop[i]; nUrban0++; }
    const uDens = [];
    for (let i = 0; i < N; i++) if (isUrb(base[i])) uDens.push(usePop ? pop[i] / area[i] : fr.built[i]);
    const DREF = Math.max(1e-9, quantile(uDens, 0.9));
    // Hot ground follows paved and roofed surface more than head count (checked against Landsat in Milan)
    const uBuilt = [];
    for (let i = 0; i < N; i++) if (isUrb(base[i])) uBuilt.push(fr.built[i]);
    const BREF = Math.max(1e-9, quantile(uBuilt, 0.9));
    const cropArea = new Float64Array(N);
    for (let i = 0; i < N; i++) cropArea[i] = area[i] * Math.max(fr.crop[i], base[i] === 'farm' ? 0.3 : 0);
    const DEMAND = totalPop * NEED_KM2;
    const near2 = NB.map((l, i) => {
      const s = new Set(l);
      for (const j of l) for (const m of NB[j]) if (m !== i) s.add(m);
      return Array.from(s);
    });

    // Low coastal land: under 3 m and within two rings of the sea, where rising seas add exposure
    const elevA = new Float64Array(N);
    for (let i = 0; i < N; i++) elevA[i] = Array.isArray(c.elev) ? Number(c.elev[i]) || 0 : 99;
    const seaHex = new Uint8Array(N);
    for (let i = 0; i < N; i++) if (base[i] === 'water' && fr.water[i] >= 0.95 && elevA[i] <= 1.5) seaHex[i] = 1;
    const lowCoast = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      if (base[i] === 'water' || elevA[i] > 3) continue;
      for (const j of near2[i]) if (seaHex[j]) { lowCoast[i] = 1; break; }
    }
    let floodEff = flood;
    let climate = CLIMATE.today;
    // Sea and lake breeze: land near a large water body (over 50 km2: sea, bay or big lake) runs cooler, fading inland
    const breeze = new Float64Array(N);
    const CAL = new Float64Array(N).fill(1);   // per-hex correction from satellite readings, when the file has them
    let breezeCount = 0;
    {
      const seen = new Uint8Array(N), bigW = [];
      for (let i = 0; i < N; i++) {
        if (seen[i] || !(fr.water[i] >= 0.95)) continue;
        const q = [i]; seen[i] = 1; let a2 = 0;
        for (let k = 0; k < q.length; k++) {
          const a = q[k]; a2 += area[a];
          for (const b of NB[a]) if (!seen[b] && fr.water[b] >= 0.95) { seen[b] = 1; q.push(b); }
        }
        if (a2 >= 50) for (const a of q) bigW.push(a);
      }
      if (bigW.length) {
        for (let i = 0; i < N; i++) {
          let d2 = Infinity;
          for (const j of bigW) { const dx = X[i] - X[j], dy = Y[i] - Y[j], d = dx * dx + dy * dy; if (d < d2) d2 = d; }
          breeze[i] = Math.exp(-Math.sqrt(d2) / BREEZE_KM);
          if (breeze[i] > 0.3 && fr.water[i] < 0.5) breezeCount++;
        }
      }
    }
    function setFloodClimate() {
      if (climate.dT === 0 && climate.slr === 0) { floodEff = flood; return; }
      const rainX = 1 + 0.07 * climate.dT;
      floodEff = new Float64Array(N);
      for (let i = 0; i < N; i++) floodEff[i] = Math.min(1.5, flood[i] * rainX + (lowCoast[i] ? 2 * climate.slr : 0));
    }
    let E0 = 0;
    const out = {
      N, BUDGET, COST, LEVER_KEYS, ZERO, NB, X, Y, POLY, MERC, inside, base, PARKS, newParks, Lmax,
      restorableCount: restorable.length, subCount: subs.length, notes, totalPop, place: d,
      corridorCount: corr.size, river, hasRivers
    };

    function evaluate(L) {
      const cv = 1 - Math.pow(1 - clamp(L.canopy, 0, 100) / 100, 1.8);
      const co = L.corridors / 100, we = L.wetlands / 100, rg = L.regen / 100;
      let cp = L.compact / 100;
      // Studio: designed elements, each with a maturity m from 0 (just built) to 1 (fully grown)
      const studio = out.studio;
      const SD = studio && studio.size ? studio : null;
      if (SD) {
        // Infill housing makes room for people, so the farthest sprawl can be left unbuilt
        let cap = 0;
        for (const [i, v] of SD) for (const it of (Array.isArray(v) ? v : [v])) {
          if (it.kind === 'housing' && isUrb(base[i])) cap += (it.residents != null ? it.residents : 0.3 * pop[i] * (it.share == null ? 1 : it.share)) * it.m;
        }
        if (cap > 0) {
          let cum = 0, t = 0;
          for (const k of subOrder) { cum += pop[k]; if (cum > cap) break; t = subP[k]; }
          cp = Math.max(cp, t);
        }
      }
      const cover = new Array(N), ucls = new Array(N).fill(null), retired = new Uint8Array(N);
      let nWet = 0, wetW = 0, nGreen = 0, nSub = 0, nSubActive = 0;

      for (let i = 0; i < N; i++) {
        let cvr = base[i], u = isUrb(base[i]) ? base[i] : null;
        if (base[i] === 'suburb') {
          nSub++;
          if (cp > 0 && subP[i] <= cp + 1e-9) { cvr = 'farm'; u = null; retired[i] = 1; } else nSubActive++;
        }
        if ((cvr === 'farm' || cvr === 'open') && !retired[i] && we > 0 && wetP[i] <= we + 1e-9) {
          cvr = 'wetland'; nWet++; wetW += wetWgt[i];
        }
        if (!parkSet.has(i)) {
          const k = corr.get(i);
          if (k !== undefined && co > 0 && k < co * Lmax - 1e-9 && cvr !== 'water' && cvr !== 'forest' && cvr !== 'wetland') {
            if (u) { cvr = 'greenway'; nGreen++; } else cvr = 'corridor';
          }
        }
        if (cvr === 'farm' && rnd3[i] < rg) cvr = 'regen';
        cover[i] = cvr; ucls[i] = u;
      }

      // The viewer's own sketch: hand-placed parks, wetlands, corridors and regenerative farms
      const paint = out.paint;
      if (paint && paint.size) {
        for (const [i, tool] of paint) {
          const c0 = cover[i];
          if (tool === 'park') {
            if (ucls[i]) { cover[i] = 'park'; ucls[i] = null; }
            else if (c0 !== 'water' && c0 !== 'wetland' && c0 !== 'park') cover[i] = 'forest';
          } else if (tool === 'wetland') {
            if (!ucls[i] && c0 !== 'water' && c0 !== 'wetland' && c0 !== 'park') { cover[i] = 'wetland'; nWet++; wetW += 0.5 + flood[i]; }
          } else if (tool === 'corridor') {
            if (c0 !== 'water' && c0 !== 'forest' && c0 !== 'wetland' && c0 !== 'park' && c0 !== 'corridor' && c0 !== 'greenway') {
              if (ucls[i]) { cover[i] = 'greenway'; nGreen++; } else cover[i] = 'corridor';
            }
          } else if (tool === 'regen') {
            if (c0 === 'farm') cover[i] = 'regen';
          }
        }
      }

      // Studio conversions and local effects
      const lc = new Float64Array(N), lflood = new Float64Array(N).fill(1);
      let urbFarm = 0, energy = 0, nTransit = 0, nRain = 0;
      if (SD) {
        for (const [i, v] of SD) for (const it of (Array.isArray(v) ? v : [v])) {
          const m = clamp(it.m, 0, 1), sh = it.share == null ? 1 : Math.max(0, it.share), c0 = cover[i], urb = !!ucls[i];
          const g = (k) => { lc[i] = 1 - (1 - lc[i]) * (1 - Math.min(0.95, k)); };
          switch (it.kind) {
            case 'trees': if (urb) { g(0.6 * m * sh); lflood[i] *= 1 - Math.min(0.5, 0.05 * m * sh); } break;
            case 'roof': if (urb) { g(0.25 * m * sh); lflood[i] *= 1 - Math.min(0.5, 0.1 * m * sh); } break;
            case 'raingarden': if (urb) { g(0.05 * m * sh); lflood[i] *= 1 - Math.min(0.6, 0.25 * m * sh); nRain += m * sh; } break;
            case 'urbanfarm': if (urb) { g(0.1 * m * sh); urbFarm += 0.02 * area[i] * m * sh / 0.6; } break;
            case 'farmblock': {
              // A block cleared and farmed: share is the fraction of the hex farmed; yields about equal to field crops
              urbFarm += area[i] * Math.min(1, sh) * m / 0.6;
              if (urb) g(0.3 * Math.min(1, sh) * m);
              if (urb && sh >= 0.6 && m >= 0.5) { cover[i] = 'farm'; ucls[i] = null; }
              break;
            }
            case 'park': {
              if (urb) { g(0.8 * Math.min(1, sh) * m); if (sh >= 0.6 && m >= 0.5) { cover[i] = 'park'; ucls[i] = null; } }
              break;
            }
            case 'solar': if (urb) energy += it.mwh || 0; break;
            case 'transit': if (urb || it.share != null) nTransit += m * sh; break;
            case 'pond':
              if (sh >= 1 && m >= 0.5 && c0 !== 'water' && c0 !== 'pond') { cover[i] = 'pond'; ucls[i] = null; wetW += 1 + flood[i]; }
              else if (sh < 1) { wetW += m * sh * (1 + flood[i]); if (urb) g(0.2 * sh * m); }
              break;
            case 'wetland':
              if (m >= 0.5 && sh >= 0.5 && !ucls[i] && c0 !== 'water' && c0 !== 'wetland' && c0 !== 'pond') { cover[i] = 'wetland'; nWet++; wetW += 0.5 + flood[i]; }
              break;
            case 'forest':
              if (m >= 0.5 && sh >= 0.5 && !ucls[i] && c0 !== 'water' && c0 !== 'wetland' && c0 !== 'pond' && c0 !== 'forest') cover[i] = 'forest';
              break;
            case 'corridor':
              if (m >= 0.5 && sh >= 0.3 && c0 !== 'water' && c0 !== 'forest' && c0 !== 'wetland' && c0 !== 'park' && c0 !== 'corridor' && c0 !== 'greenway' && c0 !== 'pond') {
                if (ucls[i]) { cover[i] = 'greenway'; nGreen++; } else cover[i] = 'corridor';
              }
              break;
            case 'regen': if (m >= 0.5 && sh >= 0.5 && c0 === 'farm') cover[i] = 'regen'; break;
          }
        }
      }
      let lcSum = 0, lcN = 0;
      for (let i = 0; i < N; i++) if (ucls[i]) { lcSum += lc[i]; lcN++; }
      const cvAll = 1 - (1 - cv) * (1 - (lcN ? lcSum / lcN : 0));   // city-wide greening, for storage and habitat

      // People stay in the region: sprawl that is pulled back moves into the remaining city
      let popAct = 0;
      for (let i = 0; i < N; i++) if (ucls[i]) popAct += pop[i];
      const scale = popAct > 0 ? POP0 / popAct : 1;

      // Heat
      const heat = new Float64Array(N);
      let sw = 0, sh = 0;
      for (let i = 0; i < N; i++) {
        if (!URBAN[cover[i]]) continue;
        const dRaw = usePop ? (pop[i] * scale) / area[i] : fr.built[i] * scale;
        const dn = Math.min(1.5, (1 - SURF_W) * dRaw / DREF + SURF_W * fr.built[i] / BREF) * (cover[i] === 'greenway' ? 0.8 : 1);
        let cs = 0;
        for (const j of NB[i]) cs += COOL[cover[j]] || 0;
        const coolN = Math.min(1, cs / 3);
        const cvi = 1 - (1 - cv) * (1 - lc[i]);
        const hv = (0.4 + 0.6 * dn) * (1 - 0.55 * cvi) * (1 - 0.5 * coolN) * (1 - BREEZE * breeze[i]) * CAL[i] * (1 + 0.1 * climate.dT);
        heat[i] = hv;
        const w = usePop ? pop[i] * scale + 1e-9 : area[i];
        sw += w; sh += w * hv;
      }
      const avgHeat = sw > 0 ? sh / sw : 0;
      const heatScore = sw > 0 ? 100 * clamp(1 - avgHeat / KH, 0, 1) : 100;

      // Floods
      let farmA = 0, regenA = 0;
      for (let i = 0; i < N; i++) {
        const a = retired[i] ? area[i] * RETIRED_CROP : cropArea[i];
        if (cover[i] === 'farm') farmA += a; else if (cover[i] === 'regen') regenA += a;
      }
      const wetFrac = restorableW > 0 ? Math.min(1, wetW / restorableW) : (wetW > 0 ? Math.min(1, wetW / Math.max(1, 0.05 * N)) : 0);
      const regenShare = farmA + regenA > 0 ? regenA / (farmA + regenA) : 0;
      const rainBonus = nUrban0 > 0 ? 0.08 * Math.min(1, nRain / Math.max(3, 0.05 * nUrban0)) : 0;
      const retention = clamp(0.6 * wetFrac + 0.18 * cvAll + 0.14 * regenShare + rainBonus, 0, 0.92);
      const floodExp = new Float64Array(N);
      let E = 0;
      for (let i = 0; i < N; i++) {
        if (!URBAN[cover[i]] || floodEff[i] <= 0) continue;
        const p = usePop ? pop[i] * scale : area[i] * fr.built[i];
        floodExp[i] = p * floodEff[i] * (cover[i] === 'greenway' ? 0.8 : 1) * lflood[i];
        E += floodExp[i];
      }
      const risk = E0 > 0 ? (E / E0) * (1 - retention) : 0;
      const floodScore = 100 * clamp(1 - 0.7 * risk, 0, 1);
      const storage = 100 * retention;

      // Food
      let supply = 0, supplyDry = 0;
      for (let i = 0; i < N; i++) {
        if (cover[i] !== 'farm' && cover[i] !== 'regen') continue;
        const a = retired[i] ? area[i] * RETIRED_CROP : cropArea[i];
        const isRegen = cover[i] === 'regen';
        supply += a * (isRegen ? 0.96 : 1) * (1 - 0.04 * climate.dT);
        let wetNear = false;
        for (const j of near2[i]) if (cover[j] === 'wetland') { wetNear = true; break; }
        supplyDry += a * ((isRegen ? 0.9 * (1 - 0.04 * climate.dT) : 0.58 * (1 - 0.08 * climate.dT)) + (wetNear ? 0.14 : 0));
      }
      supply += 0.6 * urbFarm * (1 - 0.04 * climate.dT);          // urbFarm is stored as field-crop-equivalent area / 0.6
      supplyDry += 0.5 * urbFarm;
      const food = DEMAND > 0 ? Math.min(100, 100 * supply / DEMAND) : 100;
      const foodDry = DEMAND > 0 ? Math.min(100, 100 * supplyDry / DEMAND) : 100;

      // Habitat network
      const hw = new Float64Array(N);
      let sumW = 0;
      for (let i = 0; i < N; i++) {
        const cvr = cover[i];
        hw[i] = (cvr === 'core' || cvr === 'mid' || cvr === 'suburb') ? 0.06 + 0.25 * (1 - (1 - cv) * (1 - lc[i])) : (HAB[cvr] || 0);
        sumW += hw[i];
      }
      const comp = new Int32Array(N).fill(-1);
      const compW = [];
      for (let i = 0; i < N; i++) {
        if (hw[i] < 0.5 || comp[i] >= 0) continue;
        const id = compW.length;
        let w = 0;
        const st = [i]; comp[i] = id;
        while (st.length) {
          const a = st.pop(); w += hw[a];
          for (const j of NB[a]) if (hw[j] >= 0.5 && comp[j] < 0) { comp[j] = id; st.push(j); }
        }
        compW.push(w);
      }
      let lcc = -1, lw = 0, totW = 0;
      compW.forEach((w, id) => { totW += w; if (w > lw) { lw = w; lcc = id; } });
      const lccShare = totW > 0 ? lw / totW : 0;
      let parkConn = 0;
      for (const p of PARKS) if (comp[p] === lcc) parkConn++;
      parkConn = PARKS.length ? parkConn / PARKS.length : lccShare;
      const amount = clamp(sumW / (N * 0.55), 0, 1);
      const habitat = 100 * (0.35 * amount + 0.25 * lccShare + 0.4 * parkConn);

      // Travel
      const greenRef = Math.max(4, 0.02 * nUrban0);
      const transitRef = Math.max(3, 0.03 * nUrban0);
      const mobility = 100 * clamp(0.22 + 0.62 * (1 - Math.pow(1 - cp, 1.8)) * (nSub > 0 ? 1 : 0.5) + 0.1 * Math.min(1, nGreen / greenRef) + 0.04 * cvAll
        + 0.2 * Math.min(1, nTransit / transitRef), 0, 1);

      const tests = {
        heatwave: 0.5 * heatScore + 0.25 * habitat + 0.25 * food,
        flood: 0.5 * floodScore + 0.25 * habitat + 0.25 * food,
        drought: 0.4 * foodDry + 0.2 * storage + 0.2 * heatScore + 0.2 * habitat
      };
      const index = 0.8 * (tests.heatwave + tests.flood + tests.drought) / 3 + 0.2 * mobility;
      return {
        cover, ucls, heat, floodExp, comp, lcc, retention, scale, E, energy, lc, compactUsed: cp, urbanFarmKm2: 0.6 * urbFarm,
        metrics: { heat: heatScore, flood: floodScore, habitat, food, foodDry, storage, mobility },
        tests, index
      };
    }

    out.paint = new Map();
    out.studio = new Map();
    out.evaluate = evaluate;
    const bau = evaluate(ZERO);
    E0 = bau.E;
    // Satellite correction: where Landsat readings exist, nudge each built-up hex's heat toward what was measured.
    // The model's own pattern is kept for the honest check (HEAT_MODEL); levers still act on the corrected heat.
    out.HEAT_MODEL = Float64Array.from(bau.heat);
    out.calibrated = false;
    const lr = c.lst_rel, ln = c.lst_n;
    if (lr && USE_CAL) {
      const xs = [], ys = [], ids = [];
      for (let i = 0; i < N; i++) if (bau.heat[i] > 0 && lr[i] != null && isFinite(Number(lr[i]))) { xs.push(bau.heat[i]); ys.push(Number(lr[i])); ids.push(i); }
      if (xs.length >= 20) {
        let mx = 0, my = 0;
        for (let k = 0; k < xs.length; k++) { mx += xs[k]; my += ys[k]; }
        mx /= xs.length; my /= xs.length;
        let sxy = 0, sxx = 0;
        for (let k = 0; k < xs.length; k++) { sxy += (xs[k] - mx) * (ys[k] - my); sxx += (xs[k] - mx) * (xs[k] - mx); }
        const slope = sxx > 0 ? sxy / sxx : 0;     // degrees C per unit of model heat
        if (slope > 1) {
          for (let k = 0; k < xs.length; k++) {
            const i = ids[k], resid = ys[k] - (my + slope * (xs[k] - mx));
            const trust = 0.7 * Math.min(1, (ln ? Number(ln[i]) || 1 : 5) / 5);
            const target = xs[k] + trust * resid / slope;
            CAL[i] = Math.max(0.5, Math.min(1.6, target / xs[k]));
          }
          out.calibrated = true;
          out.calSlope = slope;
        }
      }
    }
    out.BAU = evaluate(ZERO);
    out.BAU_TODAY = out.BAU;
    out.lowCoastCount = lowCoast.reduce((a, b) => a + b, 0);
    out.setClimateRaw = function (dT, slr) {
      climate = { key: 'custom', name: 'Custom', dT: dT, slr: slr };
      setFloodClimate();
      out.climate = climate;
      out.BAU = evaluate(ZERO);
    };
    out.setClimate = function (key) {
      climate = CLIMATE[key] || CLIMATE.today;
      setFloodClimate();
      out.climate = climate;
      out.BAU = evaluate(ZERO);
    };
    out.evaluateIn = function (key, L) {
      const saved = climate, savedF = floodEff;
      climate = CLIMATE[key] || CLIMATE.today;
      setFloodClimate();
      const r = evaluate(L);
      climate = saved; floodEff = savedF;
      return r;
    };
    out.breezeCount = breezeCount;
    out.climate = climate;
    if (E0 <= 0) notes.push('Almost nobody lives in the floodplain here, so flood safety starts at 100.');
    let maxExp = 0;
    for (let i = 0; i < N; i++) maxExp = Math.max(maxExp, out.BAU.floodExp[i]);
    out.maxFloodExp = maxExp || 1;

    // Typical distance between neighboring hex centers, in km
    let sp = 0, spn = 0;
    for (let i = 0; i < N && spn < 400; i += Math.max(1, Math.floor(N / 200))) {
      for (const j of NB[i]) { sp += Math.hypot(X[i] - X[j], Y[i] - Y[j]); spn++; }
    }
    out.spacingKm = spn ? sp / spn : 1;
    out.center = [cx, cy];

    // Where to start: the specific places where each action pays off most, ranked on today's map
    out.priorities = function (topN) {
      topN = topN || 8;
      const bau = out.BAU;
      const reachKm = Math.round(out.spacingKm * 2 * 10) / 10;
      const urbanBase = (i) => isUrb(base[i]);
      // Highest scores first, skipping sites that touch one already picked so the list covers more ground
      const take = (arr) => {
        arr.sort((a, b) => b.score - a.score);
        const picked = [], blocked = new Set();
        for (const it of arr) {
          if (picked.length >= topN) break;
          if (blocked.has(it.i)) continue;
          picked.push(it);
          blocked.add(it.i);
          for (const j of near2[it.i]) blocked.add(j);
        }
        return picked;
      };

      // Wetlands: wettest farmland and open land with the most people in flood-prone homes nearby
      const wet = restorable.map((i) => {
        let prot = 0;
        for (const j of [i].concat(near2[i])) if (urbanBase(j) && flood[j] > 0) prot += pop[j] * flood[j];
        return { i, prot };
      });
      const maxProt = Math.max(1, ...wet.map((w) => w.prot));
      const wetlands = take(wet.map((w) => ({
        i: w.i, cells: [w.i], score: 0.5 * flood[w.i] + w.prot / maxProt,
        why: (w.prot >= 1 ? 'Protects about ' + Math.round(w.prot).toLocaleString('en-US') + ' people in flood-prone homes within ' + reachKm + ' km' : 'Holds floodwater on the floodplain') +
          (flood[w.i] >= 0.6 ? ', on very low ground by the water' : '') + '.'
      })));

      // Street trees: hottest, most crowded built-up hexes
      const trees = [];
      for (let i = 0; i < N; i++) {
        if (!urbanBase(i) || parkSet.has(i)) continue;
        trees.push({ i, cells: [i], score: bau.heat[i] * Math.sqrt(pop[i] + 1),
          why: 'Heat load ' + Math.round(bau.heat[i] / 1.4 * 100) + ' of 100 where about ' + Math.round(pop[i]).toLocaleString('en-US') + ' people live.' });
      }

      // Corridors: parks still cut off from the main habitat, cheapest links serving the most people first
      const corridors = parkPaths.filter((pp) => pp.cells.length > 0).map((pp) => {
        let people = 0;
        for (const j of [pp.park].concat(near2[pp.park])) people += pop[j];
        const isolated = bau.comp[pp.park] !== bau.lcc;
        return {
          i: pp.park, cells: pp.cells.concat([pp.park]),
          score: (isolated ? 1 : 0.3) * Math.sqrt(people + 1) / (pp.cells.length + 2),
          why: (isolated ? 'Joins a cut-off park to the wild land' : 'Strengthens a park’s link to the wild land') + ' with ' + pp.cells.length + ' hex' + (pp.cells.length === 1 ? '' : 'es') +
            ' of corridor. About ' + Math.round(people).toLocaleString('en-US') + ' people live within ' + reachKm + ' km.'
        };
      });

      // Regenerative farming: farmland on the floodplain or next to habitat, where living soil does double duty
      const regen = [];
      for (let i = 0; i < N; i++) {
        if (base[i] !== 'farm') continue;
        let hab = 0;
        for (const j of NB[i]) if (natural(base[j]) || base[j] === 'water' || base[j] === 'park') hab++;
        const hn = NB[i].length ? hab / NB[i].length : 0;
        if (flood[i] <= 0 && hn <= 0) continue;
        regen.push({ i, cells: [i], score: flood[i] + hn,
          why: [flood[i] > 0 ? 'On the floodplain, where living soil soaks up water' : '', hab ? 'next to ' + hab + ' hex' + (hab === 1 ? '' : 'es') + ' of habitat' : ''].filter(Boolean).join(', ').replace(/^n/, 'N') + '.' });
      }

      // Compact growth: outermost sprawl first, flood-prone sprawl sooner
      const compact = subs.map((i) => ({
        i, cells: [i], score: (1 - subP[i]) + 0.8 * flood[i],
        why: 'Outer sprawl with about ' + Math.round(pop[i]).toLocaleString('en-US') + ' people to rehouse in the city' + (flood[i] > 0.1 ? ', and flood-prone' : '') + '.'
      }));

      return { wetlands, canopy: take(trees), corridors: take(corridors), regen: take(regen), compact: take(compact), reachKm };
    };

    out.locate = function (i) {
      const dx = X[i] - cx, dy = Y[i] - cy;
      const d = Math.hypot(dx, dy);
      if (d < Math.max(0.6, out.spacingKm * 0.7)) return 'At the center';
      const dirs = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
      const ang = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
      const name = dirs[Math.round(ang / 45) % 8];
      return (d >= 10 ? Math.round(d) : d.toFixed(1)) + ' km ' + name + ' of the center';
    };
    return out;
  }

  const effort = (L) => LEVER_KEYS.reduce((s, k) => s + L[k] * COST[k], 0);

  // Best mix within the effort cap, searched on a coarse grid in small batches so the page stays responsive
  function searchBest(P, step, onProgress, onDone) {
    const vals = [];
    for (let v = 0; v <= 100; v += step) vals.push(v);
    const combos = [];
    for (const a of vals) for (const b of vals) for (const c of vals) for (const d of vals) for (const e of vals) {
      const L = { canopy: a, corridors: b, wetlands: c, regen: d, compact: e };
      if (effort(L) <= BUDGET + 1e-9) combos.push(L);
    }
    let i = 0, best = null, bestI = -1, cancelled = false;
    function chunk() {
      if (cancelled) return;
      const t0 = Date.now();
      while (i < combos.length && Date.now() - t0 < 30) {
        const r = P.evaluate(combos[i]);
        if (r.index > bestI) { bestI = r.index; best = combos[i]; }
        i++;
      }
      if (onProgress) onProgress(i / combos.length);
      if (i < combos.length) setTimeout(chunk, 0); else onDone(best, bestI);
    }
    setTimeout(chunk, 0);
    return { cancel: () => { cancelled = true; }, total: combos.length };
  }

  return { setSurfW: function (w) { SURF_W = w; }, setBreeze: function (s, km) { BREEZE = s; BREEZE_KM = km; }, setUseCal: function (v) { USE_CAL = v; }, CLIMATE, prepare, validate, effort, searchBest, BUDGET, COST, LEVER_KEYS, ZERO, NEED_KM2 };
})();
if (typeof module !== 'undefined') module.exports = ThreadModel;
