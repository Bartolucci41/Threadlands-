/* Threadlands for everyone: followed places, live weather and alerts, and the shared data files.
   Used by the home page (My places) and the city profile page. Plain JavaScript, no build step. */
(function () {
  var KEY = 'threadlands:follows', UNITS = 'threadlands:units';
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } return null; }
  function follows() { try { var a = JSON.parse(store(KEY) || '[]'); return Array.isArray(a) ? a.filter(function (s) { return typeof s === 'string'; }) : []; } catch (e) { return []; } }
  function setFollows(a) { store(KEY, JSON.stringify(a)); }
  function follow(slug) { var a = follows(); if (a.indexOf(slug) < 0) { a.push(slug); setFollows(a); } }
  function unfollow(slug) { setFollows(follows().filter(function (s) { return s !== slug; })); }
  function isFollowed(slug) { return follows().indexOf(slug) >= 0; }
  function units() { var u = store(UNITS); if (u === 'c' || u === 'f') return u; return /^en-US/.test(navigator.language || '') ? 'f' : 'c'; }
  function setUnits(u) { store(UNITS, u); }
  function temp(c) { if (c == null || !isFinite(c)) return '–'; return Math.round(units() === 'f' ? c * 9 / 5 + 32 : c) + '°'; }
  function rain(mm) { if (units() === 'f') { var i = mm / 25.4; return (i >= 1 ? i.toFixed(1) : i.toFixed(2)) + ' in'; } return Math.round(mm) + ' mm'; }

  // The shared data files, fetched once per page
  var BASE = '', cache = {};
  function setBase(b) { BASE = b; }
  function data(name) {
    if (!cache[name]) cache[name] = fetch(BASE + 'data/' + name + '.json').then(function (r) { if (!r.ok) throw new Error(name); return r.json(); });
    return cache[name];
  }
  function soft(name, fallback) { return data(name).catch(function () { return fallback; }); }
  function all() {
    return Promise.all([data('index'), soft('ranking', { places: [] }), soft('summary', { places: {} }), soft('news', { places: {}, top: [] }), soft('projects', { projects: [] })]).then(function (x) {
      var rk = {}; (x[1].places || []).forEach(function (p, k) { if (p && p.slug) { rk[p.slug] = p; if (!p.rank) p.rank = k + 1; } });
      var lib = {}; (x[0].places || []).forEach(function (e) { if (e && e.slug) lib[e.slug] = e; });
      return { lib: lib, list: x[0].places || [], rank: rk, rankN: (x[1].places || []).length, rankUpdated: x[1].updated, summary: x[2].places || {}, news: x[3], projects: x[4].projects || [] };
    });
  }

  // Weather codes from the World Meteorological Organization, in plain words, with a small icon
  var WMO = { 0: ['Clear', 'sun'], 1: ['Mostly clear', 'sun'], 2: ['Partly cloudy', 'part'], 3: ['Cloudy', 'cloud'], 45: ['Fog', 'fog'], 48: ['Fog', 'fog'],
    51: ['Light drizzle', 'rain'], 53: ['Drizzle', 'rain'], 55: ['Heavy drizzle', 'rain'], 56: ['Freezing drizzle', 'rain'], 57: ['Freezing drizzle', 'rain'],
    61: ['Light rain', 'rain'], 63: ['Rain', 'rain'], 65: ['Heavy rain', 'rain'], 66: ['Freezing rain', 'rain'], 67: ['Freezing rain', 'rain'],
    71: ['Light snow', 'snow'], 73: ['Snow', 'snow'], 75: ['Heavy snow', 'snow'], 77: ['Snow grains', 'snow'], 80: ['Showers', 'rain'], 81: ['Showers', 'rain'], 82: ['Violent showers', 'rain'],
    85: ['Snow showers', 'snow'], 86: ['Snow showers', 'snow'], 95: ['Thunderstorm', 'storm'], 96: ['Thunderstorm with hail', 'storm'], 99: ['Thunderstorm with hail', 'storm'] };
  var ICON = {
    sun: '<circle cx="12" cy="12" r="4.5"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    part: '<path d="M8 4.5v1.5M3.5 9H5M4.8 5.8l1 1M13 7.5a4 4 0 0 0-7.6 2"/><path d="M7 19h10a3.5 3.5 0 0 0 .3-7 5 5 0 0 0-9.6 1.3A3 3 0 0 0 7 19z"/>',
    cloud: '<path d="M6.5 19h11a4 4 0 0 0 .4-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 6.5 19z"/>',
    fog: '<path d="M4 9h16M3 13h18M5 17h14"/>',
    rain: '<path d="M6.5 15h11a4 4 0 0 0 .4-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 6.5 15z"/><path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"/>',
    snow: '<path d="M6.5 15h11a4 4 0 0 0 .4-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 6.5 15z"/><path d="M8 19h.01M12 20h.01M16 19h.01"/>',
    storm: '<path d="M6.5 15h11a4 4 0 0 0 .4-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 6.5 15z"/><path d="M12.5 15l-2 3.5h3l-2 3.5"/>' };
  function sky(code) { return WMO[code] || ['', 'cloud']; }
  function icon(code, size) { var k = sky(code)[1]; return '<svg class="wx-ico wx-' + k + '" viewBox="0 0 24 24" width="' + (size || 24) + '" height="' + (size || 24) + '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }

  var wxCache = {};
  function weather(lat, lng) {
    var k = lat.toFixed(2) + ',' + lng.toFixed(2);
    if (!wxCache[k]) wxCache[k] = fetch('https://api.open-meteo.com/v1/forecast?latitude=' + lat.toFixed(3) + '&longitude=' + lng.toFixed(3) +
      '&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m' +
      '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,uv_index_max&timezone=auto&forecast_days=7')
      .then(function (r) { if (!r.ok) throw new Error('weather'); return r.json(); });
    return wxCache[k];
  }
  function air(lat, lng) {
    return fetch('https://air-quality-api.open-meteo.com/v1/air-quality?latitude=' + lat.toFixed(3) + '&longitude=' + lng.toFixed(3) + '&current=us_aqi,pm2_5')
      .then(function (r) { if (!r.ok) throw new Error('air'); return r.json(); }).then(function (j) { return j.current || {}; });
  }
  function aqiWord(v) { return v == null ? '' : v <= 50 ? 'Good' : v <= 100 ? 'Moderate' : v <= 150 ? 'Unhealthy for some' : v <= 200 ? 'Unhealthy' : v <= 300 ? 'Very unhealthy' : 'Hazardous'; }

  // Warnings worth a glance, from the 7-day forecast: heavy rain, extreme heat, storms
  function alerts(w) {
    var d = w && w.daily, out = [];
    if (!d || !d.time) return out;
    var rain3 = 0; for (var i = 0; i < Math.min(3, d.time.length); i++) rain3 += d.precipitation_sum[i] || 0;
    if (rain3 >= 20) out.push({ kind: 'rain', text: 'Heavy rain ahead: ' + rain(rain3) + ' over the next 3 days. Low streets and drains may flood.' });
    var hot = -1; for (var j = 0; j < d.time.length; j++) if (d.temperature_2m_max[j] >= 35) { hot = j; break; }
    if (hot >= 0) out.push({ kind: 'heat', text: 'Extreme heat ' + (hot === 0 ? 'today' : 'on ' + day(d.time[hot])) + ': up to ' + temp(d.temperature_2m_max[hot]) + '. Check on older neighbours and anyone working outside.' });
    var st = -1; for (var s = 0; s < Math.min(3, d.time.length); s++) if (d.weather_code[s] >= 95) { st = s; break; }
    if (st >= 0) out.push({ kind: 'storm', text: 'Thunderstorms ' + (st === 0 ? 'today' : 'on ' + day(d.time[st])) + '.' });
    return out;
  }
  function day(iso, long) { var dt = new Date(iso + 'T12:00:00'); return dt.toLocaleDateString('en-US', { weekday: long ? 'long' : 'short' }); }

  // Plain words
  var PRESS = { heat: 'Heat', flood: 'Flooding', grey: 'Little green', crowd: 'Crowding', trees: 'Few trees', food: 'Food from far away' };
  var TOPIC = { flood: 'Flooding', heat: 'Heat', drought: 'Drought', fire: 'Fire', water: 'Rain and storms', greening: 'Green space', infrastructure: 'Infrastructure', policy: 'Policy', climate: 'Climate' };
  var TONE = { concern: 'Risk', gain: 'Progress', update: 'Update' };
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(t) { return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }
  function ndate(d) { if (!d || d.length < 8) return ''; var dt = new Date(d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6, 8) + 'T12:00:00'); return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }
  function fmtN(n) { return n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(Math.round(n)); }
  function flag(cc) { return /^[A-Za-z]{2}$/.test(cc || '') ? '<span class="fi fi-' + String(cc).toLowerCase() + ' tl-flag" aria-hidden="true"></span>' : ''; }
  function where(e) {
    var ps = String(e.display || '').split(', '), st = ps.length >= 3 ? ps[ps.length - 2] : '';
    if (/region|región/i.test(st) || st === e.name) st = '';
    return (st ? st + ', ' : '') + e.country;
  }
  function headline(it, names, ccs) {
    var tone = it.tone || (/(flood|heat|drought|fire|water)/.test(it.topic) ? 'concern' : 'update');
    return '<li class="nw2 tone-' + tone + '"><span class="nw2-tag"><b>' + (TONE[tone] || '') + '</b>' + (TOPIC[it.topic] ? ' · ' + TOPIC[it.topic] : '') + '</span>' +
      '<a class="nw2-h" translate="no" href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a>' +
      '<span class="nw2-m">' + (names && it.place ? '<a href="' + BASE + 'place/#' + esc(it.place) + '">' + flag(ccs && ccs[it.place]) + esc(names[it.place] || it.place) + '</a> · ' : '') + esc(it.source) + (it.date ? ' · ' + ndate(it.date) : '') + '</span></li>';
  }
  // Library search: names first, then anything in the address
  function matches(list, q, n) {
    var k = norm(q), a = [], b = [];
    if (!k) return [];
    list.forEach(function (e) { if (norm(e.name).indexOf(k) === 0) a.push(e); else if (norm(e.name + ' ' + e.country + ' ' + (e.display || '')).indexOf(k) >= 0) b.push(e); });
    return a.concat(b).slice(0, n || 8);
  }
  function nearest(list, lat, lng) {
    var best = null, bd = Infinity;
    list.forEach(function (e) { var dx = (e.lng - lng) * Math.cos(lat * Math.PI / 180), dy = e.lat - lat, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = e; } });
    return best ? { place: best, km: Math.sqrt(bd) * 111 } : null;
  }

  // "Back this project": counts come from the Threadlands relay; this device remembers what it backed
  var RELAY = 'https://threadlands-relay.rob41pitt.workers.dev/', BACKED = 'threadlands:backed', countsP = null;
  function backed() { try { var a = JSON.parse(store(BACKED) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
  function relayData() {
    if (!countsP) countsP = fetch(RELAY + '?counts=1').then(function (r) { if (!r.ok) throw new Error('off'); return r.json(); });
    return countsP;
  }
  function support() { return relayData().then(function (j) { return j.counts || {}; }); }

  // "Stand with" a place: the places you stand with, and how you are connected to each
  var TIES_KEY = 'threadlands:ties';
  var TIES = { live: 'I live here', from: 'I\u2019m from here', work: 'I work or study here', care: 'I care about it' };
  var TIE_SHORT = { live: 'You live here', from: 'You\u2019re from here', work: 'You work or study here', care: 'You care about it' };
  function ties() { try { var o = JSON.parse(store(TIES_KEY) || '{}'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }
  function tieOf(slug) { return ties()[slug] || null; }
  function post(body) { return fetch(RELAY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) { return r.json(); }).catch(function () { return null; }); }
  function standWith(slug, tie) {
    tie = TIES[tie] ? tie : 'care';
    var o = ties(); o[slug] = tie; store(TIES_KEY, JSON.stringify(o)); follow(slug);
    return post({ type: 'stand', place: slug, tie: tie });
  }
  function stepBack(slug) {
    var o = ties(); delete o[slug]; store(TIES_KEY, JSON.stringify(o));
    return post({ type: 'stand', place: slug, on: false });
  }
  function standers(slug) {
    return relayData().then(function (j) { var c = (j.stands || {})[slug] || {}, n = 0; Object.keys(c).forEach(function (k) { n += c[k] || 0; }); return { total: n, live: c.live || 0, from: c.from || 0, work: c.work || 0, care: c.care || 0 }; });
  }
  function backProject(id) {
    return fetch(RELAY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'back', id: id }) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || 'failed'); return j; }); })
      .then(function (j) { var a = backed(); if (a.indexOf(id) < 0) { a.push(id); store(BACKED, JSON.stringify(a)); } return j; });
  }
  function backLabel(n, mine) { return (mine ? 'Backed \u2713' : 'Back this') + (n ? ' \u00b7 ' + n : ''); }
  // Wire every [data-back] button inside root: show counts, and back on click
  function wireBacking(root) {
    var btns = root.querySelectorAll('[data-back]'); if (!btns.length) return;
    support().then(function (c) {
      var mine = backed();
      btns.forEach(function (b) {
        var id = b.dataset.back, on = mine.indexOf(id) >= 0;
        b.hidden = false; b.textContent = backLabel(c[id] || 0, on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
        var note = root.querySelector('[data-backn="' + id + '"]'); if (note) note.textContent = c[id] ? c[id] + (c[id] === 1 ? ' person backs this' : ' people back this') : '';
        b.onclick = function () {
          if (b.getAttribute('aria-pressed') === 'true') return;
          b.disabled = true;
          backProject(id).then(function (j) { c[id] = j.n; b.textContent = backLabel(j.n, true); b.setAttribute('aria-pressed', 'true'); if (note) note.textContent = j.n + (j.n === 1 ? ' person backs this' : ' people back this'); })
            .catch(function () { b.textContent = 'Try again'; }).then(function () { b.disabled = false; });
        };
      });
    }).catch(function () { /* backing not switched on yet: buttons stay hidden */ });
  }

  window.TLP = { follows: follows, follow: follow, unfollow: unfollow, isFollowed: isFollowed, setFollows: setFollows, units: units, setUnits: setUnits, temp: temp, rain: rain,
    setBase: setBase, data: data, all: all, weather: weather, air: air, aqiWord: aqiWord, alerts: alerts, sky: sky, icon: icon, day: day,
    PRESS: PRESS, TOPIC: TOPIC, TONE: TONE, esc: esc, norm: norm, ndate: ndate, fmtN: fmtN, where: where, headline: headline, flag: flag, matches: matches, nearest: nearest, support: support, relayData: relayData, TIES: TIES, TIE_SHORT: TIE_SHORT, ties: ties, tieOf: tieOf, standWith: standWith, stepBack: stepBack, standers: standers, backProject: backProject, wireBacking: wireBacking, backed: backed };
})();
