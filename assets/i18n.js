/* Threadlands languages: swaps the page's text in place, live, with no reload.
   English is the source. data/i18n/keys.json lists English strings, with numbers written as {0}, {1}...;
   data/i18n/<lang>.json holds the translations in the same order. Anything not yet translated stays in English.
   Text that the page adds later (Studio panels, Explore results) is translated as it appears. */
(function () {
  var LANGS = [
    ['en', 'English'], ['zh', '中文'], ['hi', 'हिन्दी'], ['es', 'Español'], ['ar', 'العربية'],
    ['fr', 'Français'], ['pt', 'Português'], ['ru', 'Русский'], ['it', 'Italiano']
  ];
  // Languages appear in the menu once their translation file is in data/i18n
  var READY = ['en', 'es', 'it'];   // the others are kept up to date in data/i18n; add a code here to show it
  LANGS = LANGS.filter(function (l) { return READY.indexOf(l[0]) >= 0; });
  var RTL = { ar: 1 };
  var FONTS = { zh: 'Noto+Sans+SC:wght@400;600;800', hi: 'Noto+Sans+Devanagari:wght@400;600;800',
    ar: 'Noto+Sans+Arabic:wght@400;600;800' };
  var NUM = /[-−+]?[$€£]?\d[\d,]*(?:\.\d+)?(?:\s?[KMB%])?/g;
  var base = (document.currentScript && document.currentScript.src.replace(/assets\/i18n\.js.*$/, '')) || '/';
  var KEYS = null, DICT = null, lang = 'en', ORIG = new WeakMap(), SET = new WeakMap(), AORIG = new WeakMap(), REGIONS = null;
  var ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
  try { lang = localStorage.getItem('threadlands:lang') || 'en'; } catch (e) { /* ignore */ }
  if (!LANGS.some(function (l) { return l[0] === lang; })) lang = 'en';

  function skip(el) {
    for (var p = el; p && p.nodeType === 1; p = p.parentElement) {
      if (/^(SCRIPT|STYLE|CODE|TEXTAREA|NOSCRIPT)$/.test(p.tagName) || p.hasAttribute('data-tr') || p.getAttribute('translate') === 'no' || (p.classList && p.classList.contains('notranslate'))) return true;
    }
    return false;
  }
  // Countries come translated by the browser itself
  function regionMap() {
    if (REGIONS || !window.Intl || !Intl.DisplayNames) return REGIONS;
    REGIONS = {};
    try {
      var en = new Intl.DisplayNames(['en'], { type: 'region' }), A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      for (var i = 0; i < 26; i++) for (var j = 0; j < 26; j++) { var c = A[i] + A[j], n = en.of(c); if (n && n !== c) REGIONS[n] = c; }
      REGIONS['United States'] = 'US'; REGIONS['USA'] = 'US'; REGIONS['Czechia'] = 'CZ'; REGIONS['Turkey'] = 'TR';
    } catch (e) { /* ignore */ }
    return REGIONS;
  }
  function tr(s) {
    if (lang === 'en' || !DICT) return s;
    var m = s.match(/^(\s*)([\s\S]*?)(\s*)$/), core = m[2].replace(/\s+/g, ' ');
    if (!core) return s;
    var vals = [], key = core.replace(NUM, function (v) { vals.push(v); return '{' + (vals.length - 1) + '}'; });
    var t = DICT[key];
    if (t != null && COMMA[lang]) vals = vals.map(lnum);
    if (t == null) {
      // English dates ("Nov 27", "November 27, 2026", "Friday, November 27") are written in the reader's language
      var dates = [], dcore = core.replace(DATE, function () { dates.push(ldate.apply(null, arguments)); return '\u0000'; })
        .replace(WDAY, function (w) { dates.push(lwday(w)); return '\u0000'; });
      if (dates.length) {
        var dv = [], dkey = dcore.replace(NUM, function (v) { dv.push(v); return '{' + (dv.length - 1) + '}'; }).replace(/\u0000/g, '{date}');
        var dt = DICT[dkey], di = 0; if (COMMA[lang]) dv = dv.map(lnum);
        if (dt != null) return m[1] + dt.replace(/\{(\d+|date)\}/g, function (_, i) { return i === 'date' ? (dates[di++] || '') : (dv[+i] != null ? dv[+i] : ''); }) + m[3];
        di = 0; return m[1] + dcore.replace(/\u0000/g, function () { return dates[di++]; }) + m[3];
      }
      // A number on its own ("1,365", "13.6") is written the reader's way
      if (COMMA[lang] && !/[A-Za-z]/.test(key)) return m[1] + core.replace(NUM, lnum) + m[3];
      var R = regionMap(), c = R && R[core];
      if (c) { try { t = new Intl.DisplayNames([lang], { type: 'region' }).of(c); } catch (e) { t = null; } }
      if (t == null) return s;
      return m[1] + t + m[3];
    }
    return m[1] + t.replace(/\{(\d+)\}/g, function (_, i) { return vals[+i] != null ? vals[+i] : ''; }) + m[3];
  }
  // Languages that write 1.365 and 13,6 where English writes 1,365 and 13.6
  var COMMA = { it: 1, fr: 1, pt: 1 };
  function lnum(v) {
    var t = v.match(/^([\s\S]*?)(,*)$/), n = t[1];
    if (!/\d[,.]\d/.test(n)) return v;
    var sep = lang === 'fr' ? '\u202f' : '.';
    return n.replace(/[,.]/g, function (c) { return c === ',' ? '\u0001' : ','; }).replace(/\u0001/g, sep) + t[2];
  }
  var WDAY = /\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/g;
  function lwday(w) {
    var i = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].indexOf(w);
    try { return new Date(2024, 0, 1 + i, 12).toLocaleDateString(lang, { weekday: 'long' }); } catch (e) { return w; }
  }
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DATE = /\b(?:(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? )?(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?(?: (\d{1,2})(?!\d))?(?:,? (\d{4}))?\b/g;
  function ldate(all, wd, mo, d, y) {
    if (!d && !y) return all;                       // a month word alone ("in May") is left as it is
    var o = { month: mo.length > 4 ? 'long' : 'short' };
    if (d) o.day = 'numeric'; if (y) o.year = 'numeric'; if (wd) o.weekday = 'long';
    try { return new Date(y ? +y : new Date().getFullYear(), MON.indexOf(mo.slice(0, 3)), d ? +d : 1, 12).toLocaleDateString(lang, o); } catch (e) { return all; }
  }
  function doText(n) {
    var cur = n.nodeValue;
    if (SET.get(n) !== cur) ORIG.set(n, cur);       // the page changed this text itself: that is the new English
    var o = ORIG.get(n), v = tr(o);
    if (v !== cur) { n.nodeValue = v; }
    SET.set(n, v);
  }
  function doAttrs(el) {
    var a = AORIG.get(el); if (!a) { a = {}; AORIG.set(el, a); }
    ATTRS.forEach(function (k) {
      if (!el.hasAttribute(k)) return;
      var cur = el.getAttribute(k);
      if (a['_' + k] !== cur) a[k] = cur;
      var v = tr(a[k]); if (v !== cur) el.setAttribute(k, v); a['_' + k] = v;
    });
  }
  // Whole sentences (data-tr): translated as one string, so word order can change. In the translation,
  // <1>…</1>, <2>…</2> stand for the element's 1st, 2nd… child elements, which keep their styling.
  var WORIG = new WeakMap();
  function esc(t) { return t.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function doWhole(el) {
    var o = WORIG.get(el);
    if (!o) { o = { html: el.innerHTML, key: el.textContent.trim().replace(/\s+/g, ' ') }; WORIG.set(el, o); }
    var t = lang !== 'en' && DICT ? DICT[o.key] : null;
    if (!t) { if (el.innerHTML !== o.html) el.innerHTML = o.html; return; }
    var tmp = document.createElement('div'); tmp.innerHTML = o.html;
    var kids = tmp.children, out = '', re = /<(\d+)>([\s\S]*?)<\/\1>/g, last = 0, m;
    while ((m = re.exec(t))) {
      out += esc(t.slice(last, m.index));
      var k = kids[+m[1] - 1];
      if (k) { var c = k.cloneNode(false); c.textContent = m[2]; out += c.outerHTML; } else out += esc(m[2]);
      last = re.lastIndex;
    }
    el.innerHTML = out + esc(t.slice(last));
  }
  function walk(root) {
    if (root.nodeType === 1) {
      if (root.hasAttribute && root.hasAttribute('data-tr')) doWhole(root);
      if (root.querySelectorAll) root.querySelectorAll('[data-tr]').forEach(doWhole);
    }
    if (root.nodeType === 3) { if (root.parentElement && !skip(root.parentElement)) doText(root); return; }
    if (root.nodeType !== 1 || skip(root)) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: function (n) { if (n.nodeType === 1) return skip(n) ? 2 : 1; return n.nodeValue.trim() ? 1 : 3; }
    });
    var n = root; do { if (n.nodeType === 3) doText(n); else doAttrs(n); } while ((n = w.nextNode()));
  }
  var pending = [], scheduled = false;
  function flush() {
    scheduled = false; obs.disconnect();
    var list = pending; pending = [];
    list.forEach(function (n) { if (n.isConnected) walk(n); });
    observe();
  }
  var obs = new MutationObserver(function (ms) {
    ms.forEach(function (m) {
      if (m.type === 'characterData') pending.push(m.target);
      else if (m.type === 'attributes') pending.push(m.target);
      else m.addedNodes.forEach(function (n) { pending.push(n); });
    });
    if (!scheduled && pending.length) { scheduled = true; (window.requestAnimationFrame || setTimeout)(flush); }
  });
  function observe() { obs.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS }); }

  function font(l) {
    if (!FONTS[l] || document.getElementById('tl-font-' + l)) return;
    var k = document.createElement('link'); k.id = 'tl-font-' + l; k.rel = 'stylesheet';
    k.href = 'https://fonts.googleapis.com/css2?family=' + FONTS[l] + '&display=swap'; document.head.appendChild(k);
  }
  function load(l) {
    if (l === 'en') return Promise.resolve(null);
    var k = KEYS ? Promise.resolve(KEYS) : fetch(base + 'data/i18n/keys.json').then(function (r) { return r.json(); }).then(function (j) { KEYS = j; return j; });
    return Promise.all([k, fetch(base + 'data/i18n/' + l + '.json').then(function (r) { return r.ok ? r.json() : []; })]).then(function (a) {
      var d = {}; a[0].forEach(function (key, i) { if (a[1][i]) d[key] = a[1][i]; }); return d;
    });
  }
  function setLang(l, save) {
    lang = l; if (l === 'en') note(l);
    if (save) { try { localStorage.setItem('threadlands:lang', l); } catch (e) { /* ignore */ } }
    var h = document.documentElement; h.lang = l; h.dir = RTL[l] ? 'rtl' : 'ltr'; h.dataset.lang = l;
    font(l);
    var sel = document.getElementById('lang'); if (sel) sel.value = l;
    return load(l).then(function (d) {
      DICT = d; obs.disconnect(); note(l); walk(document.body);
      document.title = tr(TITLE);
      observe();
      document.dispatchEvent(new CustomEvent('threadlands:lang', { detail: l }));
    }).catch(function () { /* keep English */ });
  }
  // Every translation is machine-made until a person has reviewed it, and says so
  var NOTE = {
    es: 'Traducción hecha con IA, todavía sin revisar por una persona.',
    it: 'Traduzione fatta con l’IA, non ancora rivista da una persona.',
    fr: 'Traduction automatique, pas encore relue par une personne.',
    pt: 'Tradução automática, ainda não revista por uma pessoa.',
    ru: 'Машинный перевод, ещё не проверенный человеком.',
    zh: '机器翻译，尚未经过人工审校。',
    hi: 'मशीन अनुवाद, अभी किसी व्यक्ति ने जाँचा नहीं है।',
    ar: 'ترجمة آلية، لم يراجعها شخص بعد.'
  };
  function note(l) {
    var old = document.getElementById('tl-mt'); if (old) old.remove();
    if (l === 'en' || !NOTE[l]) return;
    var p = document.createElement('p'); p.id = 'tl-mt'; p.className = 'tl-mt'; p.setAttribute('translate', 'no'); p.lang = l; p.textContent = NOTE[l];
    var hd = document.querySelector('.site-head'); if (hd && hd.parentNode) hd.parentNode.insertBefore(p, hd.nextSibling); else document.body.insertBefore(p, document.body.firstChild);
  }
  var TITLE = null;
  function menu() {
    var sel = document.getElementById('lang'); if (!sel) return;
    sel.innerHTML = LANGS.map(function (l) { return '<option value="' + l[0] + '"' + (l[0] === lang ? ' selected' : '') + ' lang="' + l[0] + '">' + l[1] + '</option>'; }).join('');
    sel.addEventListener('change', function () { setLang(sel.value, true); });
  }
  function start() { TITLE = document.title; menu(); if (lang !== 'en') setLang(lang, false); else observe(); }
  window.ThreadlandsLang = { set: function (l) { return setLang(l, true); }, get: function () { return lang; }, t: tr, langs: LANGS };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
