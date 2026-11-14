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

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600&display=swap">\n')
PAGES = [("", "Home"), ("explore/", "Explore"), ("library/", "Library"), ("how-it-works/", "How it works"), ("about/", "About")]


def head(base, title, desc):
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{title}</title>\n<meta name="description" content="{desc}">\n'
            f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{desc}">\n'
            + FONTS + f'<link rel="stylesheet" href="{base}assets/site.css">\n</head>\n<body>\n')


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
for name in ("home", "library", "how-it-works", "about"):
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
