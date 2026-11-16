"""Build the Threadlands website: shared styles, menu and footer, plus five pages.

  python3 src/build_site.py

Writes index.html, explore/, library/, how-it-works/, about/ and assets/site.css at the repository root.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def read(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return path


# ---- Shared styles come from the tool's template, plus a few site-wide additions
explore = read(SRC, "explore.html")
css = explore[explore.index("<style>") + len("<style>"):explore.index("</style>")]
css = ":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%;height:auto}\n" + css
css += """
  /* Site pages */
  .site-head .topnav a[aria-current="page"] { color: var(--ink); text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 6px; }
  .page-h { font-size: clamp(2.2rem, 6vw, 3.6rem); font-weight: 800; letter-spacing: -0.03em; line-height: 1.02; margin: 26px 0 12px; }
  .page-lede { margin: 0 0 26px; max-width: 44rem; font-size: 1.125rem; color: var(--ink2); text-wrap: pretty; }
  .page-lede a, .hint a, .lib-empty a { color: var(--accent); text-underline-offset: 3px; }
  .site-foot { display: grid; gap: 8px; }
  .site-foot nav { display: flex; flex-wrap: wrap; gap: 4px 16px; }
  .site-foot a { color: var(--ink2); }
  .three { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 22px 28px; margin-top: 18px; }
  .three > div { border-top: 2px solid var(--ink); padding-top: 12px; display: grid; gap: 6px; align-content: start; }
  .three .n { font: 800 2rem/1 var(--font-display); color: var(--ink); }
  .three p { margin: 0; color: var(--ink2); font-size: 0.9375rem; }
  .three a { justify-self: start; }
  .hero-copy { grid-template-columns: minmax(0, 1fr); }
  .city-card img { display: block; width: 100%; height: auto; }
  .hero-fig img { display: block; width: 100%; height: auto; border-radius: 14px; }
  .live { margin: 0; display: grid; gap: 10px; min-width: 0; }
  .live-top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
  .live-top .chip { min-height: 34px; font-size: 0.8125rem; padding: 0 12px; }
  .live-cities, .live-layers { display: flex; flex-wrap: wrap; gap: 6px; }
  .live-map { position: relative; background: var(--surface); border-radius: 14px; overflow: hidden; min-height: 320px; }
  .live-map canvas { display: block; width: 100%; }
  .live-badge { position: absolute; left: 10px; top: 10px; display: grid; padding: 8px 12px; border-radius: 10px; background: var(--surface); border: 1px solid var(--line); }
  .live-score { font: 800 2rem/1 var(--font-display); color: var(--ink); }
  .live-delta { font: 500 0.8125rem var(--font-mono); color: var(--pos); min-height: 1em; }
  .live-loading { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; color: var(--ink2); }
  .live-ctl { display: grid; gap: 6px; font-size: 0.9375rem; color: var(--ink2); }
  .live-ctl b { color: var(--ink); }
  .live-ctl input[type=range] { width: 100%; accent-color: var(--accent); min-height: 32px; }
  .live figcaption { font-size: 0.875rem; color: var(--ink2); }
  .live figcaption a { color: var(--accent); font-weight: 600; white-space: nowrap; }
  .studio-cta { margin-top: 26px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 14px 24px; padding: 18px 20px; border-radius: 14px; background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent); }
  .studio-cta h3 { margin: 2px 0 4px; font-size: 1.25rem; }
  .studio-cta p { margin: 0; max-width: 44rem; color: var(--ink2); font-size: 0.9375rem; }
  /* Studio */
  .studio-wrap { max-width: 1400px; }
  .st-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: 12px 24px; }
  .st-place { display: grid; gap: 4px; margin-bottom: 14px; }
  .st-select { min-height: 42px; padding: 0 12px; border-radius: 10px; border: 1.5px solid var(--ink); background: var(--surface); color: var(--ink); font: 500 0.9375rem var(--font-body); max-width: 20rem; }
  .st-select.small { min-height: 34px; font-size: 0.875rem; }
  .st-app { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
  @media (max-width: 900px) { .st-app { grid-template-columns: minmax(0, 1fr); } }
  .st-left { display: grid; gap: 10px; min-width: 0; }
  .st-bar { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
  .st-layers, .st-actions { display: flex; flex-wrap: wrap; gap: 6px; }
  .st-bar .chip { min-height: 36px; }
  .st-bar .chip:disabled { opacity: 0.45; cursor: default; }
  .st-map { position: relative; background: var(--surface); border-radius: 14px; overflow: hidden; min-height: 380px; }
  .st-map canvas { display: block; width: 100%; touch-action: none; cursor: crosshair; }
  .st-zoom { position: absolute; top: 10px; right: 10px; display: grid; gap: 6px; z-index: 2; }
  .st-zoom .chip { width: 40px; min-height: 40px; padding: 0; font-size: 1.25rem; background: var(--surface); box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
  .st-mode { position: absolute; left: 10px; top: 10px; z-index: 2; padding: 5px 10px; border-radius: 99px; background: var(--ink); color: var(--bg); font-size: 0.8125rem; font-weight: 600; }
  .st-attr { position: absolute; right: 0; bottom: 0; z-index: 2; padding: 2px 6px; background: var(--surface); opacity: 0.9; font-size: 0.6875rem; color: var(--ink2); border-top-left-radius: 6px; }
  .st-attr a { color: inherit; }
  .st-steps { margin: 0 0 14px; padding-left: 1.3rem; display: grid; gap: 4px; color: var(--ink2); max-width: 46rem; }
  .st-steps b { color: var(--ink); }
  .st-search { min-height: 42px; padding: 0 12px; border-radius: 10px; border: 1.5px solid var(--ink); background: var(--surface); color: var(--ink); font: 500 0.9375rem var(--font-body); width: 20rem; max-width: 100%; box-sizing: border-box; }
  .st-loading { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; color: var(--ink2); }
  .st-tip { position: absolute; pointer-events: none; padding: 6px 9px; border-radius: 8px; background: var(--ink); color: var(--bg); font-size: 0.8125rem; max-width: 260px; z-index: 2; }
  .st-time { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 12px; align-items: center; }
  .st-time input { width: 100%; accent-color: var(--accent); min-height: 32px; }
  .st-time .btn { min-height: 40px; }
  .st-yr { font: 800 1.6rem/1 var(--font-display); color: var(--ink); min-width: 3.2em; text-align: right; }
  .st-panel { display: grid; gap: 8px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }
  .st-h { font: 600 1rem var(--font-body); margin: 10px 0 2px; }
  .st-h:first-child { margin-top: 0; }
  .st-palette { display: grid; gap: 8px; }
  .st-group { display: grid; gap: 4px; }
  .st-tools { display: flex; flex-wrap: wrap; gap: 6px; }
  .st-tool { display: inline-flex; align-items: center; gap: 6px; min-height: 34px; padding: 0 10px; border-radius: 999px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); font: 500 0.8125rem var(--font-body); cursor: pointer; }
  .st-tool i { width: 12px; height: 12px; border-radius: 3px; border: 1px solid var(--ink); }
  .st-tool i.erase { background: repeating-linear-gradient(45deg, var(--surface), var(--surface) 2px, var(--ink2) 2px, var(--ink2) 3px); }
  .st-tool[aria-checked="true"] { border-color: var(--ink); box-shadow: inset 0 0 0 1.5px var(--ink); font-weight: 700; }
  .st-tooldesc { margin: 4px 0 0; font-size: 0.8125rem; color: var(--ink2); min-height: 3.2em; }
  .st-budget { display: grid; gap: 6px; }
  .st-bud-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 0.875rem; color: var(--ink2); }
  .st-bud-row b { font: 800 1.3rem var(--font-display); color: var(--ink); }
  .st-bud-row.small { font-size: 0.8125rem; }
  .st-bud-bar { height: 8px; background: var(--surface2); border-radius: 99px; overflow: hidden; }
  .st-bud-bar i { display: block; height: 100%; background: var(--accent); border-radius: 99px; transition: width .2s; }
  .st-bud-bar i.over { background: var(--neg); }
  .st-bud-bar i.done { background: var(--pos); }
  .st-score { display: grid; }
  .st-big { font: 800 2.4rem/1 var(--font-display); color: var(--ink); }
  .st-delta { font-size: 0.8125rem; color: var(--ink2); }
  .st-metrics { display: grid; gap: 6px; }
  .st-met { display: grid; grid-template-columns: 7.5em minmax(0, 1fr) 3.4em; gap: 8px; align-items: center; font-size: 0.8125rem; color: var(--ink2); }
  .st-met .st-bar { position: relative; height: 8px; background: var(--surface2); border-radius: 99px; display: block; }
  .st-met .st-bar i { position: absolute; left: 0; top: 0; bottom: 0; background: var(--ink); border-radius: 99px; }
  .st-met .st-bar b { position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--accent); }
  .st-num { text-align: right; color: var(--ink); font-family: var(--font-mono); }
  .st-num em { font-style: normal; font-size: 0.75rem; }
  .st-num em.up { color: var(--pos); } .st-num em.down { color: var(--neg); }
  .st-extra p { margin: 4px 0 0; font-size: 0.8125rem; color: var(--ink2); }
  .st-chal-t { margin: 0 0 6px; font-size: 0.875rem; color: var(--ink); font-weight: 600; }
  .now { margin: 0 0 40px; }
  .now-sub { margin: -6px 0 16px; max-width: 44rem; color: var(--ink2); font-size: 0.9375rem; }
  .now-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
  .now-card { display: grid; gap: 4px; padding: 14px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); text-decoration: none; color: var(--ink); border-top: 4px solid var(--h2); }
  .now-card.cool { border-top-color: var(--f1); }
  .now-card:hover { border-color: var(--ink2); }
  .now-v { font: 800 1.9rem/1.05 var(--font-display); }
  .now-t { font-size: 0.8125rem; color: var(--ink2); }
  .lib-tools { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 0 0 16px; }
  .lib-tools input { flex: 1 1 260px; max-width: 26rem; min-height: 44px; padding: 0 16px; border-radius: 999px; border: 1.5px solid var(--ink); background: var(--surface); color: var(--ink); font: 500 1rem var(--font-body); }
  .lib-map { background: var(--surface); border-radius: 14px; overflow: hidden; margin: 0 0 24px; position: relative; }
  .lib-map canvas { display: block; width: 100%; cursor: pointer; }
  .lib-tip { position: absolute; pointer-events: none; padding: 4px 8px; border-radius: 6px; background: var(--ink); color: var(--bg); font: 500 0.8125rem var(--font-body); transform: translate(-50%, -130%); white-space: nowrap; }
  .lib-list { columns: 3 220px; column-gap: 32px; }
  .lib-country { break-inside: avoid; margin: 0 0 14px; }
  .lib-country h3 { font: 600 0.72rem var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); margin: 0 0 4px; }
  .lib-country ul { list-style: none; margin: 0; padding: 0; }
  .lib-country li a { display: flex; justify-content: space-between; gap: 10px; padding: 3px 0; color: var(--ink); text-decoration: none; }
  .lib-country li a:hover { text-decoration: underline; }
  .lib-country li span { font: 400 0.75rem var(--font-mono); color: var(--ink2); }
  .lib-empty { color: var(--ink2); }
  .bio { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 22px; align-items: start; }
  .bio-photo { width: 160px; height: 160px; border-radius: 50%; object-fit: cover; }
  @media (max-width: 560px) { .bio { grid-template-columns: minmax(0, 1fr); } .bio-photo { width: 120px; height: 120px; } }
  .about-grid { display: grid; gap: 28px; max-width: 46rem; }
  .about-grid h2 { font-size: 1.5rem; margin: 0 0 8px; }
  .about-grid p { margin: 0 0 10px; color: var(--ink2); }
"""
write("assets/site.css", css.strip() + "\n")
write("assets/model.js", read(SRC, "model2.js"))

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600&display=swap">\n')
# Cloudflare Web Analytics: private visit counts for Robert, no cookies and no personal data
ANALYTICS = ("<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
             "data-cf-beacon='{\"token\": \"a92b6704e81e4aaba11a9f8a11832ae1\"}'></script><!-- End Cloudflare Web Analytics -->\n")
PAGES = [("", "Home"), ("explore/", "Explore"), ("studio/", "Studio"), ("library/", "Library"), ("how-it-works/", "How it works"), ("about/", "About")]


def head(base, title, desc):
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{title}</title>\n<meta name="description" content="{desc}">\n'
            f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{desc}">\n'
            + FONTS + f'<link rel="stylesheet" href="{base}assets/site.css">\n' + ANALYTICS + '</head>\n<body>\n')


def nav(base, here):
    links = "".join(f'<a href="{base}{p}"' + (' aria-current="page"' if p == here else "") + f'>{n}</a>'
                    for p, n in PAGES[1:])
    return (f'<header class="wrap site-head" id="top">\n  <div class="topbar">\n    <a class="wordmark" href="{base}">Threadlands</a>\n'
            f'    <nav class="topnav" aria-label="Site">{links}</nav>\n  </div>\n</header>\n')


def footer(base):
    links = "".join(f'<a href="{base}{p}">{n}</a>' for p, n in PAGES)
    return (f'<footer class="wrap site-foot">\n  <nav aria-label="Footer">{links}</nav>\n'
            '  <p style="margin:0">&copy; 2026 Robert Bartolucci. All rights reserved. Threadlands is created by Robert Bartolucci.</p>\n'
            '  <p style="margin:0">Data from OpenStreetMap, ESA WorldCover, Copernicus DEM, WorldPop, HydroBASINS and Landsat (USGS and NASA).</p>\n'
            '</footer>\n')


def page(rel, base, here, title, desc, body, script=""):
    doc = head(base, title, desc) + nav(base, here) + body + footer(base) + (f"<script>\n{script}\n</script>\n" if script else "") + "</body>\n</html>\n"
    return write(rel, doc)


# ---- Explore: the tool
m = read(SRC, "model2.js")
demo = read(SRC, "demo-place.json")
examples = json.dumps([{"id": "milan", "label": "Milan, Italy"}, {"id": "san-francisco", "label": "San Francisco"},
                       {"id": "bangkok", "label": "Bangkok, Thailand"}])
for s in (m, demo):
    assert "</script" not in s.lower()
body = explore.replace("/*MODEL*/", m).replace("/*DEMO*/", demo).replace("/*EXAMPLES*/", examples)
start = body.index("<!--NAV-->")
body = body[start:].replace("<!--NAV-->", nav("../", "explore/")).replace("<!--FOOTER-->", footer("../"))
doc = head("../", "Explore a place | Threadlands",
           "Pull the threads that tie a city to its water, farms and wild places, and see where to act first.") + body + "</body>\n</html>\n"
write("explore/index.html", doc)
for i, sc in enumerate(re.findall(r"<script>(.*?)</script>", doc, re.S)):
    write(f"src/.check/explore{i}.js", sc)

# ---- The other pages
for name in ("home", "studio", "library", "how-it-works", "about"):
    spec = read(SRC, "pages", name + ".html")
    meta = dict(re.findall(r"<!--\s*(\w+):\s*(.*?)\s*-->", spec.split("\n\n", 1)[0]))
    content = spec.split("\n\n", 1)[1]
    parts = content.split("<!--SCRIPT-->")
    rel = "index.html" if name == "home" else f"{name}/index.html"
    base = "" if name == "home" else "../"
    here = "" if name == "home" else f"{name}/"
    page(rel, base, here, meta["title"], meta["description"], parts[0].replace("{B}", base),
         parts[1].replace("{B}", base) if len(parts) > 1 else "")
    if len(parts) > 1:
        write(f"src/.check/{name}.js", parts[1])
print("built: index.html, explore/, library/, how-it-works/, about/, assets/site.css")
