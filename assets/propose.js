// "What would make this place better?" A short flow for proposing a simple change:
// 1 the idea, 2 where, 3 why (optional), 4 related ideas, projects and groups, then post, join or connect.
// Ideas go to the relay, which opens them for review; nothing is public until it has been checked.
(function () {
  var RELAY = 'https://threadlands-relay.rob41pitt.workers.dev/';
  var MINE = 'threadlands:proposals';   // what this visitor sent, so they can see it while it waits for review
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function norm(t) { return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // Topics, so "a grocery store" finds a food-access campaign and "más ciclovías" finds a bike-lane proposal
  var TOPICS = {
    food: ['Food', 'grocer supermarket market food farmers produce fresh vegetable fruit garden allotment community fridge kitchen bakery mercado tienda comida alimento huerto verdura fruta tianguis mercato cibo orto marche nourriture epicerie'],
    mobility: ['Getting around', 'bike ebike e-bike bicycle cycle cycling lane bus transit metro train tram sidewalk pavement crosswalk crossing walk walking pedestrian scooter parking traffic speed street ciclovia ciclista bici camion metrobus banqueta acera cruce peaton calle trafico bicicletta marciapiede velo trottoir'],
    trees: ['Trees and shade', 'tree trees shade canopy plant planting arbol arboles sombra albero alberi ombra arbre arbres ombre'],
    heat: ['Heat', 'heat hot cool cooling fountain mist calor fresco bebedero caldo chaleur'],
    water: ['Water and flooding', 'flood flooding rain rainwater drain drainage storm stormwater puddle water sewer leak inundacion inundaciones lluvia agua drenaje encharcamiento alcantarilla allagamento pioggia acqua inondation pluie eau'],
    parks: ['Parks and public space', 'park parks playground green space plaza square bench benches sports court field parque jardin juegos cancha banca parco giardino panchina parc jardin'],
    safety: ['Safety and lighting', 'light lighting streetlight lamp safe safety dark luminaria alumbrado luz seguridad oscuro illuminazione lampione sicurezza eclairage securite'],
    waste: ['Waste and recycling', 'trash litter garbage rubbish recycling recycle compost bin bins basura reciclaje composta bote rifiuti riciclo dechets'],
    air: ['Air', 'air pollution smog dust smoke aire contaminacion polvo humo aria inquinamento pollution']
  };
  var TOPIC_WORDS = {}; Object.keys(TOPICS).forEach(function (k) { TOPIC_WORDS[k] = TOPICS[k][1].split(' '); });
  function words(t) { return norm(t).replace(/[^a-z0-9\s-]/g, ' ').split(/[\s-]+/).filter(function (w) { return w.length > 2; }); }
  function topicsOf(t) {
    var ws = words(t), out = [];
    Object.keys(TOPIC_WORDS).forEach(function (k) {
      if (ws.some(function (w) { return TOPIC_WORDS[k].some(function (x) { return w === x || (x.length > 4 && w.indexOf(x) === 0) || (w.length > 4 && x.indexOf(w) === 0); }); })) out.push(k);
    });
    return out;
  }
  // A project's kind, in the same topics
  var KIND_T = { trees: ['trees', 'heat'], park: ['parks'], wetland: ['water', 'parks'], corridor: ['mobility', 'parks', 'trees'], rain: ['water'], farm: ['food'], river: ['water', 'parks'], transit: ['mobility'] };
  function km(a, b, c, d) { var r = Math.PI / 180, x = (d - b) * r * Math.cos((a + c) / 2 * r), y = (c - a) * r; return Math.sqrt(x * x + y * y) * 6371; }

  var S = {}, dlg = null, MAP = null, PIN = null;
  function $(s) { return dlg.querySelector(s); }

  function build() {
    dlg = document.createElement('dialog');
    dlg.className = 'fb-dlg pp-dlg'; dlg.setAttribute('aria-labelledby', 'pp-h');
    dlg.innerHTML =
      '<div class="fb-form">' +
      '<div class="fb-top"><h2 id="pp-h"></h2><button type="button" class="fb-x" aria-label="Close">&times;</button></div>' +
      '<ol class="pp-steps" aria-label="Steps"><li>Idea</li><li>Where</li><li>Why</li><li>Related</li></ol>' +
      '<div class="fb-body">' +
      // 1 the idea
      '<section class="pp-s" data-s="1"><label class="fb-l" for="pp-idea">Your idea, in a few words</label>' +
      '<input id="pp-idea" class="pp-in" type="text" maxlength="120" autocomplete="off" placeholder="More e-bike stations">' +
      '<p class="pp-ex">For example: <button type="button" data-ex="Shade trees on our street">Shade trees on our street</button> <button type="button" data-ex="A grocery store with fresh food">A grocery store with fresh food</button> <button type="button" data-ex="A safe crossing near the school">A safe crossing near the school</button> <button type="button" data-ex="Fix the street that floods when it rains">Fix the street that floods when it rains</button></p></section>' +
      // 2 where
      '<section class="pp-s" data-s="2" hidden><p class="fb-l">Where would it help?</p>' +
      '<div class="pp-where" role="radiogroup" aria-label="Where">' +
      '<label><input type="radio" name="ppw" value="pin"><span>Pin it on the map</span></label>' +
      '<label class="pp-w-area"><input type="radio" name="ppw" value="area"><span>Choose a neighborhood</span></label>' +
      '<label><input type="radio" name="ppw" value="city"><span>Across the whole place</span></label></div>' +
      '<div class="pp-pin" hidden><div class="pp-map" id="pp-map"></div><p class="pp-note"><span id="pp-pin-t">Tap the public spot you mean: a corner, a park, a bus stop. Not your home.</span> The pin is shown to the nearest 100 m or so.</p></div>' +
      '<div class="pp-area" hidden><label class="sr-only" for="pp-area">Neighborhood</label><select id="pp-area" class="pp-in"></select>' +
      '<input id="pp-area-o" class="pp-in" type="text" maxlength="80" placeholder="Name of the neighborhood" hidden></div></section>' +
      // 3 why
      '<section class="pp-s" data-s="3" hidden><label class="fb-l" for="pp-why">Why does it matter? <span>(optional, one sentence)</span></label>' +
      '<textarea id="pp-why" rows="3" maxlength="280" placeholder="The nearest fresh food is a 40-minute walk, so most people here buy from corner shops."></textarea>' +
      '<label class="pp-ok"><input type="checkbox" id="pp-show"><span>Show my reason on the page. Your name is never shown. If you leave this unticked, only the person reviewing ideas reads it.</span></label>' +
      '<p class="pp-note">Please don\u2019t include names, phone numbers or home addresses.</p></section>' +
      // 4 related
      '<section class="pp-s" data-s="4" hidden><p class="fb-l" id="pp-rel-h">Before you post</p><div id="pp-rel"></div><div class="pp-choice" id="pp-choice" hidden></div></section>' +
      '<p class="fb-err" id="pp-err" hidden></p></div>' +
      '<div class="fb-foot"><button type="button" class="btn ghost" id="pp-back">Back</button><button type="button" class="btn" id="pp-next">Next</button></div></div>' +
      '<div class="fb-done" id="pp-done" hidden><h2>Thank you</h2><p class="fb-next" id="pp-done-t"></p><div class="fb-foot"><button type="button" class="btn" id="pp-close">Done</button></div></div>';
    document.body.appendChild(dlg);
    $('.fb-x').addEventListener('click', function () { dlg.close(); });
    $('#pp-close').addEventListener('click', function () { dlg.close(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
    $('.pp-ex').addEventListener('click', function (e) { var b = e.target.closest('[data-ex]'); if (b) { $('#pp-idea').value = b.dataset.ex; $('#pp-idea').focus(); } });
    $('#pp-next').addEventListener('click', next);
    $('#pp-back').addEventListener('click', function () { go(S.step - 1); });
    $('#pp-idea').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); next(); } });
    $('.pp-where').addEventListener('change', where);
    $('#pp-area').addEventListener('change', function () { $('#pp-area-o').hidden = this.value !== '_other'; if (!$('#pp-area-o').hidden) $('#pp-area-o').focus(); });
    $('#pp-rel').addEventListener('click', function (e) { var b = e.target.closest('[data-pick]'); if (!b) return; var p = b.dataset.pick.split('|'); S.link = p[1] ? { mode: p[0], kind: p[1], id: p[2], name: b.dataset.name } : null; related(); });
  }

  function where() {
    var v = (dlg.querySelector('input[name=ppw]:checked') || {}).value; S.scope = v;
    $('.pp-pin').hidden = v !== 'pin'; $('.pp-area').hidden = v !== 'area';
    if (v === 'pin' && window.L) {
      if (!MAP) {
        MAP = L.map('pp-map', { zoomControl: true, attributionControl: true }).setView([S.ctx.lat, S.ctx.lng], 11);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(MAP);
        MAP.on('click', function (e) { drop(e.latlng.lat, e.latlng.lng); });
      }
      setTimeout(function () { MAP.invalidateSize(); }, 50);
    }
  }
  function drop(lat, lng) {
    S.lat = Math.round(lat * 1e3) / 1e3; S.lng = Math.round(lng * 1e3) / 1e3;   // about 100 m: enough to find the spot, not a doorstep
    if (PIN) PIN.setLatLng([S.lat, S.lng]); else PIN = L.circleMarker([S.lat, S.lng], { radius: 9, color: '#fff', weight: 3, fillColor: '#C0542C', fillOpacity: 1 }).addTo(MAP);
    $('#pp-pin-t').textContent = 'Pinned. Tap again to move it.';
  }

  function go(n) {
    S.step = Math.max(1, Math.min(4, n));
    dlg.querySelectorAll('.pp-s').forEach(function (s) { s.hidden = +s.dataset.s !== S.step; });
    dlg.querySelectorAll('.pp-steps li').forEach(function (li, i) { li.className = i + 1 < S.step ? 'done' : i + 1 === S.step ? 'on' : ''; });
    $('#pp-back').hidden = S.step === 1; $('#pp-err').hidden = true;
    $('#pp-next').textContent = S.step === 3 ? ($('#pp-why').value.trim() ? 'Next' : 'Skip') : S.step === 4 ? postLabel() : 'Next';
    if (S.step === 4) related();
    if (S.step === 2 && S.scope === 'pin' && MAP) setTimeout(function () { MAP.invalidateSize(); }, 50);
  }
  function err(t) { $('#pp-err').textContent = t; $('#pp-err').hidden = false; }
  function areaName() { var a = $('#pp-area').value; return a === '_other' ? $('#pp-area-o').value.trim() : a; }
  function next() {
    if (S.step === 1) { var t = $('#pp-idea').value.trim(); if (t.length < 4) return err('Write your idea in a few words.'); S.idea = t; return go(2); }
    if (S.step === 2) {
      if (!S.scope) return err('Choose where it would help.');
      if (S.scope === 'pin' && S.lat == null) return err('Tap the map to drop a pin, or choose a neighborhood.');
      if (S.scope === 'area' && !areaName()) return err('Choose or type a neighborhood.');
      S.area = S.scope === 'area' ? areaName() : ''; return go(3);
    }
    if (S.step === 3) { S.why = $('#pp-why').value.trim(); S.show = $('#pp-show').checked; return go(4); }
    if (S.step === 4) return post();
  }

  // Related: proposals already published here, real projects, and local groups, scored by topic, words and distance
  function related() {
    var c = S.ctx, mineT = topicsOf(S.idea + ' ' + (S.why || '')), mineW = words(S.idea);
    function score(text, topics, lat, lng, area) {
      var s = 0, tw = words(text);
      topics.forEach(function (t) { if (mineT.indexOf(t) >= 0) s += 3; });
      mineW.forEach(function (w) { if (w.length > 3 && tw.indexOf(w) >= 0) s += 2; });
      if (!s) return 0;
      if (S.scope === 'pin' && lat != null) { var d = km(S.lat, S.lng, lat, lng); s += d < 1.5 ? 2 : d < 5 ? 1 : 0; }
      if (S.area && area && norm(area).indexOf(norm(S.area)) >= 0) s += 2;
      return s;
    }
    var items = [];
    (c.proposals || []).forEach(function (p) { var sc = score(p.idea + ' ' + (p.why || ''), p.topic || topicsOf(p.idea), p.lat, p.lng, p.area); if (sc) items.push({ kind: 'proposal', id: p.id, sc: sc + 1, name: p.idea, where: p.area || (p.scope === 'city' ? 'Across ' + c.name : 'Pinned on the map'), n: (p.joined || []).length + 1 }); });
    (c.projects || []).forEach(function (p) { var sc = score(p.name + ' ' + (p.summary || ''), KIND_T[p.kind] || [], p.lat, p.lng, p.area); if (sc) items.push({ kind: 'project', id: p.id, sc: sc, name: p.name, where: p.area || '', who: p.who, url: c.base + 'place/?pj=' + encodeURIComponent(p.id) + '#' + p.place }); });
    (c.groups || []).forEach(function (g) { var sc = score(g.name + ' ' + (g.what || ''), g.topic || [], g.lat, g.lng, g.area); if (sc) items.push({ kind: 'group', id: g.id, sc: sc, name: g.name, where: g.area || '', what: g.what, url: g.url }); });
    if (S.link) items.forEach(function (it) { if (it.id === S.link.id) it.sc += 100; });
    items.sort(function (a, b) { return b.sc - a.sc; }); items = items.slice(0, 5);
    var KL = { proposal: 'An idea from people here', project: 'A project here', group: 'A local group' };
    var L = S.link;
    $('#pp-rel-h').textContent = items.length ? 'Before you post: related ' + (items.length === 1 ? 'work' : 'work') + ' in ' + c.name : 'Before you post';
    $('#pp-rel').innerHTML = (items.length ? '<p class="pp-note">Join forces where it fits. If you add yourself to an idea, the page shows you in its count and your neighborhood, never a pin.</p>' : '<p class="pp-none">Nothing similar here yet. Yours would be the first.</p>') +
      items.map(function (it) {
        var on = L && L.id === it.id, acts = it.kind === 'proposal'
          ? '<button type="button" class="pp-act' + (on && L.mode === 'join' ? ' on' : '') + '" data-pick="join|proposal|' + esc(it.id) + '" data-name="' + esc(it.name) + '">Same idea: add me</button><button type="button" class="pp-act' + (on && L.mode === 'connect' ? ' on' : '') + '" data-pick="connect|proposal|' + esc(it.id) + '" data-name="' + esc(it.name) + '">Related: connect mine</button>'
          : '<button type="button" class="pp-act' + (on ? ' on' : '') + '" data-pick="connect|' + it.kind + '|' + esc(it.id) + '" data-name="' + esc(it.name) + '">Connect my idea to this</button>';
        return '<div class="pp-rel' + (on ? ' on' : '') + '"><span class="pp-k">' + KL[it.kind] + '</span><b>' + esc(it.name) + '</b>' +
          (it.where || it.who || it.n > 1 ? '<span class="pp-m">' + [it.where, it.who ? 'Run by ' + it.who : '', it.n > 1 ? it.n + ' people asking' : ''].filter(Boolean).map(esc).join(' · ') + '</span>' : '') +
          (it.what ? '<span class="pp-m">' + esc(it.what) + '</span>' : '') + '<span class="pp-acts">' + acts + (it.url ? '<a href="' + esc(it.url) + '" target="_blank" rel="noopener">See it</a>' : '') + '</span></div>';
      }).join('') + (L ? '<p class="pp-note"><button type="button" class="linkbtn" data-pick="new">Post it as a separate idea instead</button></p>' : '');
    $('#pp-next').textContent = postLabel();
  }
  function postLabel() { var L = S.link; return !L ? 'Post my idea' : L.mode === 'join' ? 'Add me to this idea' : 'Post and connect'; }

  function post() {
    var L = S.link, b = { type: 'proposal', place: S.ctx.slug, idea: S.idea, why: S.why || '', show_why: !!(S.show && S.why), topic: topicsOf(S.idea + ' ' + (S.why || '')), scope: S.scope, area: S.area || '',
      lat: S.scope === 'pin' ? S.lat : null, lng: S.scope === 'pin' ? S.lng : null, mode: L ? L.mode : 'new', link_kind: L ? L.kind : '', link_id: L ? L.id : '' };
    $('#pp-next').disabled = true; $('#pp-next').textContent = 'Sending…';
    fetch(RELAY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || 'failed'); return j; }); })
      .then(function () {
        if (L && L.mode === 'join' && window.TLP && TLP.backProject) TLP.backProject(L.id).catch(function () {});   // counts at once; the reason and location wait for review
        var a = []; try { a = JSON.parse(store(MINE) || '[]'); } catch (e) {}
        a.push({ place: b.place, idea: b.idea, area: b.area, scope: b.scope, mode: b.mode, link: L ? L.name : '', sent: new Date().toISOString().slice(0, 10) }); store(MINE, JSON.stringify(a.slice(-20)));
        $('.fb-form').hidden = true; $('#pp-done').hidden = false;
        $('#pp-done-t').innerHTML = (L && L.mode === 'join' ? 'You\u2019re added to \u201c' + esc(L.name) + '\u201d. Your neighborhood' + (b.show_why ? ' and reason' : '') + ' will show with it' : L ? 'Your idea is sent, connected to \u201c' + esc(L.name) + '\u201d. It will appear' : 'Your idea is sent. It will appear on this page') +
          ' after a quick check, usually within a few days. It stays private until then, and you\u2019ll see it here marked as waiting.';
        if (S.ctx.onPosted) S.ctx.onPosted();
      })
      .catch(function (e) { err(e.message === 'failed' ? 'It couldn’t be sent right now. Please try again in a minute.' : e.message); })
      .then(function () { $('#pp-next').disabled = false; if (S.step === 4) $('#pp-next').textContent = postLabel(); });
  }

  function open(ctx) {
    if (!dlg) build();
    S = { ctx: ctx, step: 1, link: ctx.join ? { mode: 'join', kind: 'proposal', id: ctx.join.id, name: ctx.join.name } : null, scope: null, lat: null, lng: null };
    $('#pp-h').textContent = 'What would make ' + ctx.name + ' better?';
    $('#pp-idea').value = ctx.idea || ''; $('#pp-why').value = ''; $('#pp-show').checked = false;
    dlg.querySelectorAll('input[name=ppw]').forEach(function (i) { i.checked = false; }); $('.pp-pin').hidden = true; $('.pp-area').hidden = true;
    var A = ctx.areas || [];
    $('#pp-area').innerHTML = '<option value="">Choose…</option>' + A.map(function (a) { return '<option>' + esc(a) + '</option>'; }).join('') + '<option value="_other">' + (A.length ? 'Somewhere else' : 'Type a name') + '</option>';
    $('#pp-area-o').hidden = true; $('#pp-area-o').value = '';
    if (PIN && MAP) { MAP.removeLayer(PIN); PIN = null; } if (MAP) MAP.setView([ctx.lat, ctx.lng], 11);
    $('.fb-form').hidden = false; $('#pp-done').hidden = true;
    if (ctx.join) { S.idea = ctx.idea; $('#pp-h').textContent = 'Add yourself to \u201c' + ctx.join.name + '\u201d'; go(2); } else go(1);
    dlg.showModal(); if (!ctx.join) setTimeout(function () { $('#pp-idea').focus(); }, 30);
  }
  function mine(slug) { var a = []; try { a = JSON.parse(store(MINE) || '[]'); } catch (e) {} return a.filter(function (x) { return x.place === slug; }); }
  window.TLPropose = { open: open, topicsOf: topicsOf, TOPICS: TOPICS, mine: mine };
})();
