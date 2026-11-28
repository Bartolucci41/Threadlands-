// Finds every piece of English text the site shows, the way assets/i18n.js will look it up, and appends any new
// ones to data/i18n/keys.json. The list only ever grows at the end, so each language file stays lined up with it.
// Run with the built site served on a local port:  node pipeline/i18n_extract.js http://localhost:8765
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const BASE = (process.argv[2] || 'http://localhost:8765').replace(/\/$/, '');
const ROOT = path.join(__dirname, '..');
const KEYS = path.join(ROOT, 'data', 'i18n', 'keys.json');
const NUM = /[-−+]?[$€£]?\d[\d,]*(?:\.\d+)?(?:\s?[KMB%])?/g;   // same as assets/i18n.js
const ATTRS = ['placeholder', 'aria-label', 'title'];

// Place names and addresses are not translated: a city keeps its own name
const ix = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'index.json'), 'utf8'));
const PLACE = new Set();
(ix.places || []).forEach((p) => {
  [p.name, p.country, ...(String(p.display || '').split(','))].forEach((t) => { if (t && t.trim()) PLACE.add(t.trim().toLowerCase()); });
});
function isPlaceText(k) {
  const parts = k.split(/\s*[,·]\s*|\s+[-–]\s+/).map((t) => t.trim().toLowerCase()).filter(Boolean);
  return parts.length > 0 && parts.every((t) => PLACE.has(t) || /^\{\d\}( (people|million|km²?|ha))?.*$/.test(t) || /^added by a visitor$/.test(t));
}

// Pages to visit, and what to do on each so the text that appears later shows up too
const VISITS = [
  { url: '/' },
  { url: '/involved/', follow: ['mexico-city', 'bologna'] },
  { url: '/places/' },
  { url: '/place/#mexico-city' },
  { url: '/projects/' },
  { url: '/lab/' },
  { url: '/explore/#mexico-city', wait: 6000, clicks: ['#ptab-plan', '#ptab-compare', '#ptab-understand'] },
  { url: '/studio/', wait: 4000 },
  { url: '/how-it-works/' },
  { url: '/about/' },
  { url: '/map/#mexico-city', wait: 9000, clicks: ['[data-chip="0"]', '#tab-layers', '#tab-draw', '[data-tool="tree"]', '#tab-compare'] },
];

(async () => {
  const keys = JSON.parse(fs.readFileSync(KEYS, 'utf8'));
  const have = new Set(keys);
  const found = new Set();
  const browser = await chromium.launch();
  for (const v of VISITS) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    // No live weather, relay or news during extraction: those are not site text
    await page.route(/open-meteo|workers\.dev|gbif|news\.json/, (r) => r.abort());
    if (v.follow) await page.addInitScript((f) => { try { localStorage.setItem('threadlands:follows', JSON.stringify(f)); } catch (e) {} }, v.follow);
    try {
      await page.goto(BASE + v.url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(v.wait || 1500);
      for (const c of v.clicks || []) { try { await page.click(c, { timeout: 2000 }); await page.waitForTimeout(800); } catch (e) { /* not on this page */ } }
      const texts = await page.evaluate((ATTRS) => {
        const out = [];
        const skip = (el) => {
          for (let p = el; p && p.nodeType === 1; p = p.parentElement) {
            if (/^(SCRIPT|STYLE|CODE|TEXTAREA|NOSCRIPT|SELECT|OPTION)$/.test(p.tagName) || p.getAttribute('translate') === 'no' || p.classList.contains('notranslate')) return true;
            if (p.hasAttribute('data-tr')) return 'whole';
          }
          return false;
        };
        document.querySelectorAll('[data-tr]').forEach((el) => out.push(el.textContent));
        const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let n;
        while ((n = w.nextNode())) { if (n.nodeValue.trim() && !skip(n.parentElement)) out.push(n.nodeValue); }
        document.querySelectorAll('*').forEach((el) => { if (skip(el)) return; ATTRS.forEach((a) => { if (el.hasAttribute(a)) out.push(el.getAttribute(a)); }); });
        out.push(document.title.split(' | ')[0]);
        return out;
      }, ATTRS);
      texts.forEach((t) => {
        const core = String(t).trim().replace(/\s+/g, ' ');
        if (!core || !/[A-Za-z]{2}/.test(core) || core.length > 600) return;
        let i = 0;
        const key = core.replace(NUM, () => '{' + (i++) + '}');
        if (isPlaceText(key) || /^https?:/.test(key)) return;
        found.add(key);
      });
    } catch (e) {
      console.error('could not read', v.url, e.message);
    }
    await page.close();
  }
  await browser.close();
  const added = [...found].filter((k) => !have.has(k));
  if (added.length) fs.writeFileSync(KEYS, JSON.stringify(keys.concat(added), null, 0));
  console.log(`i18n: ${found.size} strings on the site, ${added.length} new, ${keys.length + added.length} in the list`);
})();
