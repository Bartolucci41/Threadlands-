// Threadlands offline support: pages and data you have opened keep working without a connection.
// Pages and data: network first, so updates show at once; the saved copy is used only when offline.
// Styles, scripts and images: served from the saved copy, refreshed in the background.
var VERSION = 'tl-v103';
var CORE = ['/', '/explore/', '/studio/', '/places/', '/place/', '/lab/', '/involved/', '/assets/public.js', '/data/summary.json', '/data/ranking.json', '/how-it-works/', '/about/', '/assets/site.css',
  '/data/index.json', '/data/price-levels.json', '/data/materials.json', '/data/trees.json', '/manifest.webmanifest'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return Promise.all(CORE.map(function (u) { return c.add(u).catch(function () {}); })); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== VERSION; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;   // map tiles, fonts and live services go straight to the network
  var fresh = r.mode === 'navigate' || /\.(json|html)$/.test(u.pathname) || u.pathname.slice(-1) === '/';
  if (fresh) {
    // no-cache: always check with the server, so a new version shows on the next visit instead of up to 10 minutes later
    e.respondWith(fetch(r, { cache: 'no-cache' }).then(function (res) {
      if (res.ok) { var cp = res.clone(); caches.open(VERSION).then(function (c) { c.put(r, cp); }); }
      return res;
    }).catch(function () {
      return caches.match(r, { ignoreSearch: true }).then(function (m) { return m || (r.mode === 'navigate' ? caches.match('/') : Response.error()); });
    }));
    return;
  }
  e.respondWith(caches.match(r).then(function (m) {
    var net = fetch(r).then(function (res) { if (res.ok) { var cp = res.clone(); caches.open(VERSION).then(function (c) { c.put(r, cp); }); } return res; }).catch(function () { return m; });
    return m || net;
  }));
});
