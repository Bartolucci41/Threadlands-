/* Threadlands languages: swaps the page's text in place, live, with no reload.
   English is the source. data/i18n/keys.json lists English strings, with numbers written as {0}, {1}...;
   data/i18n/<lang>.json holds the translations in the same order. Anything not yet translated stays in English.
   Text that the page adds later (Studio panels, Explore results) is translated as it appears. */
(function () {
  var LANGS = [
    ['en', 'English'], ['zh', '中文'], ['hi', 'हिन्दी'], ['es', 'Español'], ['ar', 'العربية'],
    ['fr', 'Français'], ['bn', 'বাংলা'], ['pt', 'Português'], ['ru', 'Русский'], ['ur', 'اردو']
  ];
  // Languages appear in the menu once their translation file is in data/i18n
  var READY = ['en', 'zh', 'es', 'fr', 'pt', 'ru'];
  LANGS = LANGS.filter(function (l) { return READY.indexOf(l[0]) >= 0; });
  var RTL = { ar: 1, ur: 1 };
  var FONTS = { zh: 'Noto+Sans+SC:wght@400;600;800', hi: 'Noto+Sans+Devanagari:wght@400;600;800', bn: 'Noto+Sans+Bengali:wght@400;600;800',
    ar: 'Noto+Sans+Arabic:wght@400;600;800', ur: 'Noto+Nastaliq+Urdu:wght@400;600' };
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
    if (t == null) {
      var R = regionMap(), c = R && R[core];
      if (c) { try { t = new Intl.DisplayNames([lang], { type: 'region' }).of(c); } catch (e) { t = null; } }
      if (t == null) return s;
      return m[1] + t + m[3];
    }
    return m[1] + t.replace(/\{(\d+)\}/g, function (_, i) { return vals[+i] != null ? vals[+i] : ''; }) + m[3];
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
    lang = l;
    if (save) { try { localStorage.setItem('threadlands:lang', l); } catch (e) { /* ignore */ } }
    var h = document.documentElement; h.lang = l; h.dir = RTL[l] ? 'rtl' : 'ltr'; h.dataset.lang = l;
    font(l);
    var sel = document.getElementById('lang'); if (sel) sel.value = l;
    return load(l).then(function (d) {
      DICT = d; obs.disconnect(); walk(document.body);
      document.title = tr(TITLE);
      observe();
      document.dispatchEvent(new CustomEvent('threadlands:lang', { detail: l }));
    }).catch(function () { /* keep English */ });
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
