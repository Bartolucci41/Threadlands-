/* Threadlands place profile: the biggest pressures on a place, environmental and social together,
   computed from the place's own measured cells. Works for every place, including newly built ones. */
(function (root) {
  function num(v) { return typeof v === 'number' && isFinite(v) ? v : 0; }
  function measure(data) {
    var c = data.cells || {}, n = (c.pop || []).length, R = data.regional || {}, cellKm2 = +data.hex_km2 || null;
    var P = 0, heatP = 0, floodP = 0, greyP = 0, crowdP = 0, treeW = 0, hotTreeW = 0, hotP = 0, coolTreeW = 0, coolP = 0;
    var floodLowInc = 0, lstN = 0, rows = [], cityP = 0, cityGreyP = 0, inside = c.inside || [];
    for (var i = 0; i < n; i++) {
      var p = num(c.pop[i]); if (p <= 0) continue;
      var a = num(c.area && c.area[i]) || 1, dens = p / a;
      var tree = num(c.tree && c.tree[i]), green = tree + num(c.grass && c.grass[i]) + num(c.shrub && c.shrub[i]) + num(c.wetland && c.wetland[i]);
      var lst = c.lst_rel && c.lst_rel[i], fl = num(c.flood && c.flood[i]);
      P += p; treeW += p * tree;
      if (typeof lst === 'number') { lstN++; if (lst >= 2) heatP += p; }
      if (fl >= 0.5) floodP += p;
      if (green < 0.1) greyP += p;
      if (inside[i]) { cityP += p; if (green < 0.1) cityGreyP += p; }
      if (dens >= 15000) crowdP += p;
      rows.push({ p: p, dens: dens, tree: tree, fl: fl >= 0.5 ? 1 : 0, lst: typeof lst === 'number' ? lst : null });
    }
    if (!P) return null;
    // The most crowded fifth of residents vs the rest: who carries the load
    rows.sort(function (x, y) { return y.dens - x.dens; });
    var acc = 0, top = { p: 0, tree: 0, fl: 0, lst: 0, lp: 0 }, rest = { p: 0, tree: 0, fl: 0, lst: 0, lp: 0 };
    rows.forEach(function (r) {
      var g = acc < P * 0.2 ? top : rest; acc += r.p;
      g.p += r.p; g.tree += r.p * r.tree; g.fl += r.p * r.fl; if (r.lst !== null) { g.lst += r.p * r.lst; g.lp += r.p; }
    });
    var fs = (R.foodshed || []).filter(function (f) { return f && f.km === 50; })[0] || (R.foodshed || [])[0];
    var need = num(R.need_km2_per_person), food = fs && need ? Math.min(2, num(fs.crop_km2) / Math.max(1, num(fs.pop) * need)) : null;
    return {
      pop: P,
      heat: lstN ? heatP / P : null,
      flood: floodP / P,
      grey: greyP / P, cellKm2: cellKm2, greyCity: cityP ? cityGreyP / cityP : null, bufferKm: +data.buffer_km || null,
      crowd: crowdP / P,
      trees: treeW / P,
      food: food,
      dense: { tree: top.p ? top.tree / top.p : 0, treeRest: rest.p ? rest.tree / rest.p : 0, fl: top.p ? top.fl / top.p : 0, flRest: rest.p ? rest.fl / rest.p : 0,
               lst: top.lp ? top.lst / top.lp : null, lstRest: rest.lp ? rest.lst / rest.lp : null }
    };
  }
  // Higher score = bigger pressure. Each is compared with every other place in the library when the spread is known.
  // Only measures that are worked out the same way everywhere are compared between places.
  // Heat, flooding, green cover and tree cover depend on each place's grid-cell size (0.1 to tens of km²)
  // and on how population is spread within cells, so they are reported for the place alone until that is fixed.
  var COMPARABLE = { food: true };
  var KEYS = {
    heat: function (m) { return m.heat; },
    flood: function (m) { return m.flood; },
    grey: function (m) { return m.grey; },
    crowd: function (m) { return m.crowd; },
    trees: function (m) { return 1 - m.trees; },
    food: function (m) { return m.food === null ? null : 1 - Math.min(1, m.food); }
  };
  function pct(v, list) { if (!list || !list.length) return null; var k = 0; while (k < list.length && list[k] <= v) k++; return Math.round(100 * k / list.length); }
  function pctTxt(x) { return Math.round(x * 100) + '%'; }
  function deg(x) { return (x > 0 ? '+' : '') + x.toFixed(1) + '°C'; }
  function cellTxt(m) { var a = m.cellKm2; return a ? ' (about ' + (a < 0.5 ? a.toFixed(1) : a < 10 ? Math.round(a) : Math.round(a / 5) * 5) + ' km\u00b2)' : ''; }
  function describe(key, m) {
    var d = m.dense, ppl = function (s) { var v = s * m.pop; return v >= 1e6 ? (v / 1e6).toFixed(1) + ' million' : v >= 1e3 ? Math.round(v / 1e3) + ',000' : Math.round(v); };
    switch (key) {
      case 'heat': return { t: 'Heat', f: 'Residents in local heat hot spots', layer: 'heat', what: ppl(m.heat) + ' people (' + pctTxt(m.heat) + ') live where satellites measure the ground at least 2°C hotter than is typical for the region.',
        who: d.lst !== null && d.lstRest !== null ? 'The most densely populated fifth of residents average ' + deg(d.lst - d.lstRest) + ' compared with everyone else, with ' + pctTxt(d.tree) + ' tree cover against ' + pctTxt(d.treeRest) + '.' : '' };
      case 'flood': return { t: 'Flooding', f: 'High modeled exposure', layer: 'flood', what: 'The model places ' + ppl(m.flood) + ' people (' + pctTxt(m.flood) + ') on low ground close to rivers or the sea, where water collects first.',
        who: d.fl > d.flRest * 1.2 && d.fl >= 0.05 ? 'High population density adds to the exposure: ' + pctTxt(d.fl) + ' of the most densely populated fifth of residents live on that low ground, against ' + pctTxt(d.flRest) + ' of everyone else.' : 'The model works in grid cells, not streets, so it shows where water tends to collect, not which streets flood.' };
      case 'grey': return { t: 'Trees & green space', f: 'Residents in low-green-cover cells', layer: 'green',
        what: 'In the wider study region' + (m.bufferKm ? ' (the city and ' + Math.round(m.bufferKm) + ' km around it)' : '') + ', ' + ppl(m.grey) + ' people (' + pctTxt(m.grey) + ') live in grid cells' + cellTxt(m) + ' where less than 10% of the ground is mapped as trees, grass, shrubs or wetland (ESA WorldCover 2021).' + (m.greyCity !== null ? ' Inside the city itself: ' + pctTxt(m.greyCity) + '.' : ''),
        who: 'Not counted as green: water, cropland, bare ground and built-up land. Parks, open space and water outside a resident\u2019s own cell are not counted either. Results depend on the cell size and on how population is spread within cells, so treat them as indicative.' };
      case 'crowd': return { t: 'Population', f: 'High population density', layer: null, what: pctTxt(m.crowd) + ' of people live at more than 15,000 per km².',
        who: 'Dense neighborhoods have the least room for parks, drainage or trees.' };
      case 'trees': return { t: 'Trees & green space', f: 'Tree cover in residents\u2019 cells', layer: 'green', what: 'The average resident has ' + pctTxt(m.trees) + ' tree cover in the grid cell' + cellTxt(m) + ' around their home (ESA WorldCover 2021). Results depend on the cell size, so treat them as indicative.',
        who: d.treeRest > d.tree ? 'The most densely populated fifth of residents get ' + pctTxt(d.tree) + ', against ' + pctTxt(d.treeRest) + ' for everyone else.' : 'Trees are spread fairly evenly between dense and open neighborhoods.' };
      case 'food': return { t: 'Food', f: 'Limited nearby farmland capacity', layer: null, what: 'Farmland within 50 km could feed ' + (m.food < 0.01 ? 'less than 1%' : 'about ' + pctTxt(Math.min(1, m.food))) + ' of the region’s people.',
        who: 'This measures farmland capacity nearby, not where the city’s food actually comes from.' };
    }
  }
  function profile(data, dist) {
    var m = measure(data); if (!m) return null;
    var out = [];
    Object.keys(KEYS).forEach(function (k) {
      if (k === 'crowd') return;
      var s = KEYS[k](m); if (s === null || s === undefined) return;
      var p = dist && COMPARABLE[k] ? pct(s, dist[k]) : null;
      out.push({ key: k, score: s, pct: p, rank: p !== null ? p : s * 100 });
    });
    // Findings compared with other places come first; the rest are ordered by how high they are for this place
    out.sort(function (a, b) { return ((b.pct !== null) - (a.pct !== null)) || b.rank - a.rank; });
    // Only pressures that stand out: worse than most places (when the library spread is known) and not near zero
    var OWN = { heat: 0.15, flood: 0.15, grey: 0.25, trees: 0.9, food: 0.75 };   // trees: average tree cover under 10%; food: nearby farmland feeds under a quarter
    var strong = out.filter(function (o) { return o.score > 0.02 && (o.pct === null ? o.score >= (OWN[o.key] || 0.15) : o.pct >= 50); });
    if (!strong.length) strong = out.slice(0, 1);
    out = strong;
    return { m: m, top: out.slice(0, 3).map(function (o) { var d = describe(o.key, m); d.key = o.key; d.pct = o.pct; return d; }) };
  }
  // Headline facts about a place, computed the same way everywhere so any place can be ranked against the library.
  // P is a prepared ThreadModel place. Higher is not always worse: CTX says which way is better.
  function placeStats(P) {
    var c = P.place.cells, n = P.N, base = P.BAU_TODAY, pop = 0, area = 0, land = 0, flood = 0, hot = 0, hotN = 0, sx = 0, sy = 0, sw = 0;
    for (var i = 0; i < n; i++) {
      if (!P.inside[i]) continue;
      var a = Number(c.area[i]) || 0, pp = Number(c.pop[i]) || 0, isLand = (Number(c.water[i]) || 0) < 0.5;
      pop += pp; area += a;
      if (isLand) {
        land += a; if ((Number(c.flood[i]) || 0) >= 0.5) flood += a;
        var lr = c.lst_rel ? c.lst_rel[i] : null;
        if (lr != null && isFinite(Number(lr))) { hot += Number(lr); hotN++; }
      }
      var w = pp + 0.01; sx += P.X[i] * w; sy += P.Y[i] * w; sw += w;
    }
    var cx = sx / sw, cy = sy / sw, wild = Infinity, natural = 0, natTotal = 0;
    for (i = 0; i < n; i++) {
      var cv = base.cover[i]; if (cv === 'water') continue;
      natTotal++;
      if (cv === 'forest' || cv === 'wetland' || cv === 'open') natural++;
      if (cv === 'forest' || cv === 'wetland') { var d = Math.hypot(P.X[i] - cx, P.Y[i] - cy); if (d < wild) wild = d; }
    }
    var reg = P.place.regional || {}, out = {
      pop: pop, density: area > 0 ? pop / area : null, heat: hotN ? hot / hotN : null, flood: land > 0 ? flood / land : null,
      basin: reg.basin && reg.basin.area_km2 ? reg.basin.area_km2 : null, wild: isFinite(wild) ? wild : null, natural: natTotal ? natural / natTotal : null,
      food: null, index: base.index
    };
    if (reg.foodshed && reg.foodshed.length && pop > 0) out.food = reg.foodshed[0].crop_km2 / (pop * (reg.need_km2_per_person || 0.0019));
    for (var m in base.metrics) out['m_' + m] = base.metrics[m];
    for (var t in base.tests) out['t_' + t] = base.tests[t];
    return out;
  }
  // Where a value sits among all library places: share of places with a lower value (0 to 100)
  function rankIn(v, list) {
    if (v === null || v === undefined || !isFinite(v) || !list || list.length < 5) return null;
    if (list[list.length - 1] - list[0] < 1e-6) return null;               // a score that is the same everywhere says nothing
    var lo = 0, eq = 0; for (var k = 0; k < list.length; k++) { if (list[k] < v) lo++; else if (list[k] === v) eq++; }
    return Math.max(1, Math.min(99, Math.round(100 * (lo + eq / 2) / list.length)));
  }
  // ---- Real projects: what one adds when placed on today's map, and whether it counts toward the index.
  // Land cover is from 2021 satellite data, so projects built in or before 2021 are taken as already in it.
  var PTOOL = { wetland: 'wetland', park: 'park', trees: 'park', corridor: 'corridor', river: 'corridor', farm: 'regen' };
  var LANDCOVER_YEAR = 2021;
  function projectCounts(p) { return p.status === 'approved' || p.status === 'underway' || (p.status === 'built' && (p.year || 0) > LANDCOVER_YEAR); }
  function projectEffect(P, p, ZERO) {
    var c = P.place.cells, d = [], kx = Math.cos(p.lat * Math.PI / 180) * 111.32, people = 0;
    for (var i = 0; i < P.N; i++) { var dx = (c.lng[i] - p.lng) * kx, dy = (c.lat[i] - p.lat) * 110.57, dd = dx * dx + dy * dy; d.push([dd, i]); if (dd <= 1) people += +c.pop[i] || 0; }
    d.sort(function (a, b) { return a[0] - b[0]; });
    var fx = { people: people, index: 0 }, tool = PTOOL[p.kind];
    if (!tool || !(p.area_km2 > 0) || !d.length || d[0][0] > 4) return fx;
    var hexA = 0, m = Math.min(50, P.N); for (var k = 0; k < m; k++) hexA += +c.area[k] || 0; hexA /= m;
    var n = Math.max(1, Math.min(400, Math.round(p.area_km2 / hexA))), save = P.paint;
    try {
      P.paint = new Map(); var b = P.evaluate(ZERO);
      d.slice(0, n).forEach(function (x) { P.paint.set(x[1], tool); });
      var r = P.evaluate(ZERO);
      fx.index = r.index - b.index; fx.heat = r.metrics.heat - b.metrics.heat; fx.flood = r.metrics.flood - b.metrics.flood; fx.habitat = r.metrics.habitat - b.metrics.habitat;
    } finally { P.paint = save; }
    return fx;
  }
  // All counting projects together (painted at once, so overlaps are not double counted)
  function projectsEffect(P, list, ZERO) {
    var c = P.place.cells, hexA = 0, m = Math.min(50, P.N), save = P.paint, used = 0;
    for (var k = 0; k < m; k++) hexA += +c.area[k] || 0; hexA /= m;
    try {
      P.paint = new Map(); var b = P.evaluate(ZERO);
      list.filter(projectCounts).forEach(function (p) {
        var tool = PTOOL[p.kind]; if (!tool || !(p.area_km2 > 0)) return;
        var kx = Math.cos(p.lat * Math.PI / 180) * 111.32, d = [];
        for (var i = 0; i < P.N; i++) { var dx = (c.lng[i] - p.lng) * kx, dy = (c.lat[i] - p.lat) * 110.57; d.push([dx * dx + dy * dy, i]); }
        d.sort(function (a, b2) { return a[0] - b2[0]; });
        if (!d.length || d[0][0] > 4) return;
        d.slice(0, Math.max(1, Math.min(400, Math.round(p.area_km2 / hexA)))).forEach(function (x) { P.paint.set(x[1], tool); });
        used++;
      });
      var r = used ? P.evaluate(ZERO) : b;
      return { index: r.index - b.index, counted: used };
    } finally { P.paint = save; }
  }
  var api = { measure: measure, profile: profile, KEYS: KEYS, placeStats: placeStats, rankIn: rankIn, projectEffect: projectEffect, projectsEffect: projectsEffect, projectCounts: projectCounts };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.TLProfile = api;
})(this);
