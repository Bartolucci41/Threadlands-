// Threadlands feedback: one private form, reached from "Send feedback" in every footer
// and from "Report a data issue" on the map and in ThreadLab.
// Reports go to a private queue (never published). Local knowledge belongs in "Add what you know" instead.
(function () {
  var RELAY = 'https://threadlands-relay.rob41pitt.workers.dev/';
  var KINDS = [
    ['broken', 'Something is broken'],
    ['data', 'Data or a map detail looks wrong'],
    ['unclear', 'Something was hard to understand'],
    ['idea', 'I have an idea']
  ];
  var dlg = null, CTX = {}, SHOT = '';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // What we attach on every report, so most issues can be reproduced without a technical write-up
  function pageContext() {
    var ua = navigator.userAgent, br = /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox' : /Safari\//.test(ua) ? 'Safari' : 'Other';
    var os = /iPhone|iPad/.test(ua) ? 'iOS' : /Android/.test(ua) ? 'Android' : /Mac/.test(ua) ? 'Mac' : /Windows/.test(ua) ? 'Windows' : /Linux/.test(ua) ? 'Linux' : 'Other';
    var lang = (document.getElementById('lang') || {}).value || document.documentElement.lang || 'en';
    return { Page: location.pathname + location.search + location.hash, Screen: innerWidth + ' × ' + innerHeight + ' · ' + br + ' on ' + os, Language: lang };
  }

  function build() {
    dlg = document.createElement('dialog');
    dlg.className = 'fb-dlg'; dlg.setAttribute('aria-labelledby', 'fb-h');
    dlg.innerHTML =
      '<form method="dialog" class="fb-form" novalidate>' +
      '<div class="fb-top"><h2 id="fb-h">Send feedback</h2><button type="button" class="fb-x" aria-label="Close">&times;</button></div>' +
      '<div class="fb-body">' +
      '<fieldset class="fb-kinds"><legend>What is it about?</legend>' +
      KINDS.map(function (k) { return '<label class="fb-k"><input type="radio" name="fbk" value="' + k[0] + '"><span>' + k[1] + '</span></label>'; }).join('') +
      '</fieldset>' +
      '<p class="fb-local" hidden>Seen something on the ground, like water collecting after heavy rain? That&rsquo;s local knowledge: use <b>Add what you know</b> on the map, so it can appear there for everyone. This form is for problems with the site, its data or its maps.</p>' +
      '<label class="fb-l" for="fb-t">What did you see, and what did you expect?</label>' +
      '<textarea id="fb-t" rows="4" maxlength="2000" required></textarea>' +
      '<div class="fb-ctx" hidden><p class="fb-ctx-h">We&rsquo;ll attach this, so we can see what you saw:</p><dl></dl></div>' +
      '<div class="fb-opt">' +
      '<label class="fb-l" for="fb-s">Screenshot <span>(optional)</span></label><input id="fb-s" type="file" accept="image/*"><p class="fb-shot" hidden></p>' +
      '<label class="fb-l" for="fb-e">Your email <span>(optional, only if you&rsquo;d like to hear when it&rsquo;s fixed)</span></label>' +
      '<input id="fb-e" type="email" autocomplete="email" maxlength="200" placeholder="name@example.com">' +
      '<p class="fb-priv">Reports are private. We never publish them or your email.</p></div>' +
      '<p class="fb-err" role="alert" hidden></p>' +
      '</div>' +
      '<div class="fb-foot"><button type="button" class="btn ghost fb-cancel">Cancel</button><button type="submit" class="btn fb-send">Send</button></div>' +
      '</form>' +
      '<div class="fb-done" hidden><h2>Thanks, we received your report.</h2><p class="fb-next"></p><div class="fb-foot"><button type="button" class="btn fb-close">Close</button></div></div>';
    document.body.appendChild(dlg);
    var q = function (s) { return dlg.querySelector(s); };
    function close() { if (dlg.open) dlg.close(); }
    q('.fb-x').addEventListener('click', close); q('.fb-cancel').addEventListener('click', close); q('.fb-close').addEventListener('click', close);
    dlg.addEventListener('click', function (e) { if (e.target === dlg) close(); });
    dlg.addEventListener('change', function (e) { if (e.target.name === 'fbk') kindChanged(); });
    q('#fb-s').addEventListener('change', function () { shrink(this.files && this.files[0]); });
    q('.fb-form').addEventListener('submit', function (e) { e.preventDefault(); send(); });
  }
  function kindChanged() {
    var k = (dlg.querySelector('input[name=fbk]:checked') || {}).value;
    dlg.querySelector('.fb-local').hidden = k !== 'data';
  }
  function showCtx() {
    var keys = Object.keys(CTX).filter(function (k) { return CTX[k] !== '' && CTX[k] != null; });
    dlg.querySelector('.fb-ctx dl').innerHTML = keys.map(function (k) { return '<dt>' + esc(k) + '</dt><dd>' + esc(CTX[k]) + '</dd>'; }).join('');
    dlg.querySelector('.fb-ctx').hidden = !keys.length;
  }
  // A screenshot is shrunk in the browser to a light JPEG before it is sent
  function shrink(file) {
    SHOT = ''; var note = dlg.querySelector('.fb-shot'); note.hidden = true;
    if (!file || !/^image\//.test(file.type)) return;
    var img = new Image(), url = URL.createObjectURL(file);
    img.onload = function () {
      var s = Math.min(1, 1600 / Math.max(img.width, img.height)), c = document.createElement('canvas');
      c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      var q = 0.82, d = c.toDataURL('image/jpeg', q);
      while (d.length > 2e6 && q > 0.4) { q -= 0.12; d = c.toDataURL('image/jpeg', q); }
      URL.revokeObjectURL(url);
      if (d.length > 2.1e6) { note.textContent = 'That image is too large to attach. Try a smaller screenshot.'; note.hidden = false; return; }
      SHOT = d; note.textContent = 'Screenshot attached (' + c.width + ' × ' + c.height + ').'; note.hidden = false;
    };
    img.onerror = function () { note.textContent = 'That file could not be read as an image.'; note.hidden = false; };
    img.src = url;
  }
  function send() {
    var q = function (s) { return dlg.querySelector(s); }, err = q('.fb-err');
    var kind = (q('input[name=fbk]:checked') || {}).value, text = q('#fb-t').value.trim(), email = q('#fb-e').value.trim();
    err.hidden = true;
    if (!kind) { err.textContent = 'Choose what your feedback is about.'; err.hidden = false; return; }
    if (text.length < 3) { err.textContent = 'Tell us what you saw, and what you expected.'; err.hidden = false; q('#fb-t').focus(); return; }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { err.textContent = 'That email address does not look right.'; err.hidden = false; return; }
    var b = q('.fb-send'); b.disabled = true; b.textContent = 'Sending…';
    fetch(RELAY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'feedback', kind: kind, text: text, email: email, context: CTX, shot: SHOT }) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (r) {
        if (!r.ok) throw new Error(r.j && r.j.error || 'Could not send.');
        q('.fb-form').hidden = true; q('.fb-done').hidden = false;
        q('.fb-next').textContent = email
          ? 'We read every report. We’ll write to ' + email + ' when it’s fixed or answered.'
          : 'We read every report. You didn’t leave an email, so we won’t be able to tell you when it’s fixed, but it still counts.';
        q('.fb-close').focus();
      })
      .catch(function (e) { err.textContent = (e && e.message) || 'Could not send. Check your connection and try again.'; err.hidden = false; })
      .then(function () { b.disabled = false; b.textContent = 'Send'; });
  }

  // TLF.open({ kind: 'data', context: { Place: 'Mexico City', Layer: 'Heat', ... } })
  function open(opts) {
    opts = opts || {};
    if (!dlg) build();
    var q = function (s) { return dlg.querySelector(s); };
    q('.fb-form').hidden = false; q('.fb-done').hidden = true; q('.fb-err').hidden = true;
    q('#fb-t').value = ''; q('#fb-s').value = ''; q('.fb-shot').hidden = true; SHOT = '';
    dlg.querySelectorAll('input[name=fbk]').forEach(function (r) { r.checked = r.value === opts.kind; });
    q('#fb-h').textContent = opts.kind === 'data' ? 'Report a data issue' : 'Send feedback';
    CTX = Object.assign({}, opts.context || {}, pageContext());
    showCtx(); kindChanged();
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
    (opts.kind ? q('#fb-t') : dlg.querySelector('input[name=fbk]')).focus();
  }
  window.TLF = { open: open };
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-feedback]'); if (!t) return;
    e.preventDefault();
    var ctx = typeof window.TLF_CONTEXT === 'function' ? (window.TLF_CONTEXT(t) || {}) : {};
    open({ kind: t.dataset.feedback || '', context: ctx });
  });
})();
