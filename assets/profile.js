/* Threadlands place profile: the biggest pressures on a place, environmental and social together,
   computed from the place's own measured cells. Works for every place, including newly built ones. */
(function (root) {
  function num(v) { return typeof v === 'number' && isFinite(v) ? v : 0; }
  function measure(data) {
    var c = data.cells || {}, n = (c.pop || []).length, R = data.regional || {};
    var P = 0, heatP = 0, floodP = 0, greyP = 0, crowdP = 0, treeW = 0, hotTreeW = 0, hotP = 0, coolTreeW = 0, coolP = 0;
    var floodLowInc = 0, lstN = 0, rows = [];
    for (var i = 0; i < n; i++) {
      var p = num(c.pop[i]); if (p <= 0) continue;
      var a = num(c.area && c.area[i]) || 1, dens = p / a;
      var tree = num(c.tree && c.tree[i]), green = tree + num(c.grass && c.grass[i]) + num(c.shrub && c.shrub[i]) + num(c.wetland && c.wetland[i]);
      var lst = c.lst_rel && c.lst_rel[i], fl = num(c.flood && c.flood[i]);
      P += p; treeW += p * tree;
      if (typeof lst === 'number') { lstN++; if (lst >= 2) heatP += p; }
      if (fl >= 0.5) floodP += p;
      if (green < 0.1) greyP += p;
      if (dens >= 15000) crowdP += p;
      rows.push({ p: p, dens: dens, tree: tree, lst: typeof lst === 'number' ? lst : null });
    }
    if (!P) return null;
    // The most crowded fifth of residents vs the rest: who carries the load
    rows.sort(function (x, y) { return y.dens - x.dens; });
    var acc = 0, top = { p: 0, tree: 0, lst: 0, lp: 0 }, rest = { p: 0, tree: 0, lst: 0, lp: 0 };
    rows.forEach(function (r) {
      var g = acc < P * 0.2 ? top : rest; acc += r.p;
      g.p += r.p; g.tree += r.p * r.tree; if (r.lst !== null) { g.lst += r.p * r.lst; g.lp += r.p; }
    });
    var fs = (R.foodshed || []).filter(function (f) { return f && f.km === 50; })[0] || (R.foodshed || [])[0];
    var need = num(R.need_km2_per_person), food = fs && need ? Math.min(2, num(fs.crop_km2) / Math.max(1, num(fs.pop) * need)) : null;
    return {
      pop: P,
      heat: lstN ? heatP / P : null,
      flood: floodP / P,
      grey: greyP / P,
      crowd: crowdP / P,
      trees: treeW / P,
      food: food,
      dense: { tree: top.p ? top.tree / top.p : 0, treeRest: rest.p ? rest.tree / rest.p : 0,
               lst: top.lp ? top.lst / top.lp : null, lstRest: rest.lp ? rest.lst / rest.lp : null }
    };
  }
  // Higher score = bigger pressure. Each is compared with every other place in the library when the spread is known.
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
  function describe(key, m) {
    var d = m.dense, ppl = function (s) { var v = s * m.pop; return v >= 1e6 ? (v / 1e6).toFixed(1) + ' million' : v >= 1e3 ? Math.round(v / 1e3) + ',000' : Math.round(v); };
    switch (key) {
      case 'heat': return { t: 'Heat', what: ppl(m.heat) + ' people (' + pctTxt(m.heat) + ') live where the ground runs at least 2°C hotter than is typical for the region.',
        who: d.lst !== null && d.lstRest !== null ? 'The most crowded fifth of residents average ' + deg(d.lst - d.lstRest) + ' compared with everyone else, with ' + pctTxt(d.tree) + ' tree cover against ' + pctTxt(d.treeRest) + '.' : '' };
      case 'flood': return { t: 'Flooding', what: ppl(m.flood) + ' people (' + pctTxt(m.flood) + ') live on low ground close to rivers or the sea, where water collects first.',
        who: 'Flooding hits hardest where homes are informal or below street level, and where families cannot afford to move or rebuild.' };
      case 'grey': return { t: 'No green nearby', what: ppl(m.grey) + ' people (' + pctTxt(m.grey) + ') live where less than a tenth of the ground is trees, grass or wetland.',
        who: 'Little green means more heat, more runoff and worse air, and it usually tracks lower incomes.' };
      case 'crowd': return { t: 'Crowding', what: pctTxt(m.crowd) + ' of people live at more than 15,000 per km².',
        who: 'Dense neighborhoods have the least room for parks, drainage or trees, so every other pressure lands on them harder.' };
      case 'trees': return { t: 'Few trees', what: 'The average resident has ' + pctTxt(m.trees) + ' tree cover around them.',
        who: d.treeRest > d.tree ? 'The most crowded fifth of residents get ' + pctTxt(d.tree) + ', against ' + pctTxt(d.treeRest) + ' for everyone else.' : 'Trees are spread fairly evenly between crowded and open neighborhoods.' };
      case 'food': return { t: 'Food from far away', what: 'Farmland within 50 km could feed ' + (m.food < 0.01 ? 'less than 1%' : 'about ' + pctTxt(Math.min(1, m.food))) + ' of the region’s people.',
        who: 'Food that travels far costs more when prices or supply lines break, and poorer households feel it first.' };
    }
  }
  function profile(data, dist) {
    var m = measure(data); if (!m) return null;
    var out = [];
    Object.keys(KEYS).forEach(function (k) {
      var s = KEYS[k](m); if (s === null || s === undefined) return;
      var p = dist ? pct(s, dist[k]) : null;
      out.push({ key: k, score: s, pct: p, rank: p !== null ? p : s * 100 });
    });
    out.sort(function (a, b) { return b.rank - a.rank; });
    return { m: m, top: out.slice(0, 3).map(function (o) { var d = describe(o.key, m); d.key = o.key; d.pct = o.pct; return d; }) };
  }
  var api = { measure: measure, profile: profile, KEYS: KEYS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.TLProfile = api;
})(this);
