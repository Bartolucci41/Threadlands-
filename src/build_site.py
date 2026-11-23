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
  .st-shape:not([hidden]) { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .st-shape .chip[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
  .st-opts:not([hidden]) { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: -4px 0 12px; }
  .st-opts input { width: 5rem; min-height: 36px; padding: 0 8px; border-radius: 8px; border: 1.5px solid var(--ink); background: var(--surface); color: var(--ink); font: 500 0.9375rem var(--font-body); }
  .st-opts [hidden] { display: none; }
  .st-zoom .st-3d { font-size: 0.875rem; font-weight: 700; }
  .st-zoom .st-3d[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
  .st-guide3d { position: absolute; left: 10px; top: 46px; z-index: 3; width: min(340px, calc(100% - 80px)); padding: 12px 14px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); box-shadow: 0 6px 20px rgba(0,0,0,0.18); font-size: 0.875rem; color: var(--ink); }
  .st-guide3d p { margin: 0 0 6px; } .st-guide3d ul { margin: 0 0 8px; padding-left: 1.1rem; display: grid; gap: 4px; color: var(--ink2); } .st-guide3d ul b { color: var(--ink); }
  .st-g3-row { display: flex; gap: 6px; flex-wrap: wrap; margin: 0 !important; }
  .st-legend3d:not([hidden]) { position: absolute; left: 10px; bottom: 26px; z-index: 2; display: flex; flex-wrap: wrap; gap: 4px 10px; max-width: calc(100% - 20px); padding: 6px 10px; border-radius: 10px; background: var(--surface); opacity: 0.95; font-size: 0.75rem; color: var(--ink); }
  .st-legend3d span { display: inline-flex; align-items: center; gap: 5px; } .st-legend3d i { width: 11px; height: 11px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.3); }
  .st-banner:not([hidden]) { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0; padding: 10px 12px; border-radius: 12px; background: var(--surface); border: 1px solid var(--accent); font-size: 0.9375rem; }
  .st-linkbox { flex: 1 1 260px; min-height: 34px; padding: 0 8px; border-radius: 8px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); font: 0.8125rem var(--font-mono); }
  .st-wsbar:not([hidden]) { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px; border-radius: 14px; background: var(--ink); color: var(--bg); }
  .st-wsbar .chip { background: transparent; color: var(--bg); border-color: rgba(255,255,255,0.35); }
  .st-teams { display: flex; flex-wrap: wrap; gap: 6px; }
  .st-teamchip { min-height: 38px; padding: 0 14px; border-radius: 999px; border: 2px solid var(--tc); background: transparent; color: var(--bg); font: 600 0.875rem var(--font-body); cursor: pointer; }
  .st-teamchip[aria-checked="true"] { background: var(--tc); }
  .st-timer { font: 600 0.9375rem var(--font-mono); margin-left: auto; }
  .st-dialog { border: 0; border-radius: 16px; padding: 22px; max-width: 460px; width: calc(100% - 32px); background: var(--surface); color: var(--ink); box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
  .st-dialog::backdrop { background: rgba(10,20,16,0.45); }
  .st-dialog h2 { margin: 0 0 6px; font-size: 1.35rem; } .st-dialog p { color: var(--ink2); }
  .st-dialog input { min-height: 38px; padding: 0 10px; border-radius: 8px; border: 1.5px solid var(--ink); background: var(--bg); color: var(--ink); font: 500 0.9375rem var(--font-body); }
  .st-wsrow { display: flex; gap: 8px; align-items: center; margin: 6px 0; } .st-wsrow label { min-width: 4.5rem; color: var(--ink); }
  .st-tdot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
  .studio-wrap:fullscreen { background: var(--bg); overflow: auto; padding: 16px; max-width: none; }
  .do-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 12px; }
  @media (max-width: 800px) { .do-grid { grid-template-columns: minmax(0, 1fr); } }
  .do-card { display: grid; gap: 8px; align-content: start; padding: 20px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); color: var(--ink); text-decoration: none; transition: border-color .15s, transform .15s; }
  .do-card:hover, .do-card:focus-visible { border-color: var(--ink); transform: translateY(-2px); }
  .do-card b { font: 700 1.25rem/1.2 var(--font-display); } .do-card > span { color: var(--ink2); }
  .do-card .do-go { color: var(--accent); font-weight: 600; margin-top: 4px; }
  .do-ico { width: 48px; height: 48px; border-radius: 12px; display: grid; place-items: center; background: var(--bg); color: var(--accent); }
  .short-list { display: grid; gap: 8px; max-width: 46rem; padding-left: 1.2rem; color: var(--ink2); } .short-list b { color: var(--ink); }
  section.story:has(> .how-sec) { margin-top: 0; padding-top: 0; border-top: 0; }
  .how-sec { border-top: 1px solid var(--line); padding: 6px 0; }
  .how-sec[open] { padding-bottom: 28px; }
  #do-h { max-width: none; }
  .how-sec > summary { cursor: pointer; list-style: none; display: grid; gap: 2px; padding: 10px 0; }
  .how-sec > summary::-webkit-details-marker { display: none; }
  .how-sec > summary h2 { display: inline; margin: 0; } .how-sec > summary h2::after { content: " +"; color: var(--accent); }
  .how-sec[open] > summary h2::after { content: " −"; }
  .how-sec > summary span { color: var(--ink2); }
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
  .st-catwrap { position: relative; }
  .st-cats { display: grid; grid-template-columns: repeat(9, minmax(0, 1fr)); gap: 6px; }
  @media (max-width: 760px) { .st-cats { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
  .st-cat { display: grid; justify-items: center; gap: 4px; padding: 8px 4px; min-height: 64px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font: 600 0.75rem/1.15 var(--font-body); cursor: pointer; text-align: center; }
  .st-cat:hover { border-color: var(--ink2); }
  .st-cat.on { border-color: var(--ink); box-shadow: inset 0 0 0 1.5px var(--ink); }
  .st-cat[aria-expanded="true"] { background: var(--ink); color: var(--bg); }
  .st-menu { position: absolute; top: calc(100% + 6px); z-index: 5; width: min(380px, 100%); padding: 8px; border-radius: 14px; background: var(--surface); border: 1px solid var(--line); box-shadow: 0 10px 30px rgba(0,0,0,0.18); display: grid; gap: 4px; }
  .st-menu-h { margin: 2px 6px 4px; font: 600 0.75rem var(--font-mono); letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink2); }
  .st-item { display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; gap: 10px; align-items: center; text-align: left; padding: 10px; border-radius: 10px; border: 1px solid transparent; background: none; color: var(--ink); cursor: pointer; font: 400 0.875rem var(--font-body); }
  .st-item:hover, .st-item:focus-visible { background: var(--bg); border-color: var(--line); }
  .st-item[aria-checked="true"] { border-color: var(--ink); }
  .st-item i, .st-current i { width: 14px; height: 14px; border-radius: 4px; border: 1px solid var(--ink); }
  .st-current i.erase { background: repeating-linear-gradient(45deg, var(--surface), var(--surface) 2px, var(--ink2) 2px, var(--ink2) 3px); }
  .st-item-t { display: grid; gap: 2px; } .st-item-t span { color: var(--ink2); font-size: 0.8125rem; }
  .st-carb { font-size: 0.75rem !important; color: var(--accent) !important; }
  .st-bom { margin: 10px 0 4px; border: 1px solid var(--line); border-radius: 12px; padding: 8px 12px; background: var(--surface); }
.topright { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 18px; }
.lang-sel { font: 500 0.8125rem var(--font-body); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: 6px 10px; min-height: 34px; cursor: pointer; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
html[data-lang="zh"] { --font-body: 'Noto Sans SC', system-ui, sans-serif; --font-display: 'Noto Sans SC', system-ui, sans-serif; }
html[data-lang="hi"] { --font-body: 'Noto Sans Devanagari', system-ui, sans-serif; --font-display: 'Noto Sans Devanagari', system-ui, sans-serif; }
html[data-lang="bn"] { --font-body: 'Noto Sans Bengali', system-ui, sans-serif; --font-display: 'Noto Sans Bengali', system-ui, sans-serif; }
html[data-lang="ar"] { --font-body: 'Noto Sans Arabic', system-ui, sans-serif; --font-display: 'Noto Sans Arabic', system-ui, sans-serif; }
html[data-lang="ur"] { --font-body: 'Noto Nastaliq Urdu', 'Noto Sans Arabic', system-ui, sans-serif; --font-display: 'Noto Nastaliq Urdu', 'Noto Sans Arabic', system-ui, sans-serif; line-height: 1.9; }
html[dir="rtl"] .st-bom th, html[dir="rtl"] .st-bom td, html[dir="rtl"] .st-sp-o { text-align: right; }
html[dir="rtl"] .st-bom th:nth-child(n+2), html[dir="rtl"] .st-bom td:nth-child(n+2) { text-align: left; }
.st-bom { min-width: 0; max-width: 100%; box-sizing: border-box; overflow-wrap: anywhere; }
.st-bom table { table-layout: auto; }
.st-bom-tbl { overflow-x: auto; max-width: 100%; }
.st-bom td:nth-child(2) { white-space: normal !important; }
.st-sp-o { width: 100%; box-sizing: border-box; white-space: normal; }
.st-sp [role="radiogroup"] { display: grid; gap: 4px; max-height: 260px; overflow-y: auto; }
.st-sp-o { text-align: left; padding: 6px 8px; border-radius: 10px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); font: inherit; font-size: 0.85rem; cursor: pointer; }
.st-sp-o i { color: var(--ink2); font-size: 0.75rem; }
.st-sp-o span { display: block; color: var(--ink2); font-size: 0.75rem; font-family: var(--font-mono); }
.st-sp-o[aria-checked="true"] { border: 1.5px solid var(--ink); background: var(--surface2); }
.st-optrow { min-height: 44px; display: flex; align-items: center; margin: 2px 0 6px; }
.st-dims, .st-selbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 0.9rem; }
.st-dims[hidden], .st-selbar[hidden] { display: none; }
.st-dims input, .st-selbar input { width: 76px; padding: 5px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--ink); font: inherit; }
.st-dims-note { color: var(--ink2); font-size: 0.8rem; }
.st-tool { display: inline-flex; align-items: center; gap: 6px; }
.st-tool svg { flex: none; }
.st-bom summary { cursor: pointer; font-weight: 600; font-size: 0.95rem; }
.st-bom-opts { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 4px; }
.st-bom-opts [aria-checked="true"] { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.st-bom-note { font-size: 0.85rem; color: var(--ink2); margin: 6px 0; }
.st-bom table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.st-bom th, .st-bom td { text-align: left; padding: 3px 4px; border-bottom: 1px solid var(--line); vertical-align: top; }
.st-bom th:nth-child(n+2), .st-bom td:nth-child(n+2) { text-align: right; white-space: nowrap; }
.st-bom tfoot td { font-weight: 700; border-bottom: 0; }
.st-carbon { display: block; padding: 8px 10px; border-radius: 10px; background: var(--bg); }
  .st-price { font: 500 0.75rem var(--font-mono); color: var(--ink2); white-space: nowrap; }
  .st-current { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
  .st-current b { font-size: 1.0625rem; }
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
  .lib-map canvas { display: block; width: 100%; }
  .lib-zoom { position: absolute; top: 10px; right: 10px; display: grid; gap: 6px; }
  .lib-zoom .chip { width: 40px; min-height: 40px; padding: 0; font-size: 1.15rem; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
  .lib-zoom .chip:disabled { opacity: 0.45; }
  .lib-tip a { color: var(--bg); text-decoration: underline; }
  .lib-tip { position: absolute; pointer-events: none; padding: 4px 8px; border-radius: 6px; background: var(--ink); color: var(--bg); font: 500 0.8125rem var(--font-body); transform: translate(-50%, -130%); white-space: nowrap; }
  .hero-eyebrow { margin: 0 0 14px; font: 600 0.8rem var(--font-body, system-ui); letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
  .hero-h.hero-h2 { font-size: clamp(2.2rem, 4.6vw, 3.7rem); line-height: 1.04; letter-spacing: -0.03em; max-width: 15ch; }
  .live-goals { display: flex; flex-wrap: wrap; gap: 6px; }
  .live-goals .chip[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink, #fff); border-color: var(--accent); }
  .rank { margin: 56px 0 8px; }
  .rank-head { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: end; justify-content: space-between; margin-bottom: 18px; }
  .rank-sub { margin: 6px 0 0; color: var(--ink2); max-width: 62ch; }
  .rank-find input { min-height: 44px; padding: 8px 16px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font: inherit; width: 220px; }
  .rank-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px 40px; }
  .rank-cols h3 { margin: 0 0 6px; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }
  .rank-list { list-style: none; margin: 0; padding: 0; }
  .rank-list a { display: grid; grid-template-columns: 2.2em minmax(0, 1fr) 90px 2.2em; gap: 10px; align-items: center; padding: 9px 2px; border-bottom: 1px solid var(--line); color: var(--ink); text-decoration: none; }
  .rank-list a:hover { background: var(--surface); }
  .rk-n { font: 500 0.8rem var(--font-mono); color: var(--ink2); text-align: right; }
  .rk-c { display: grid; min-width: 0; } .rk-c b { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .rk-c span { font-size: 0.8rem; color: var(--ink2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rk-bar { height: 6px; border-radius: 3px; background: var(--line); overflow: hidden; } .rk-bar i { display: block; height: 100%; background: var(--accent); border-radius: 3px; }
  .rk-v { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
  .rank-all { margin-top: 14px; } .rank-all summary { cursor: pointer; font-weight: 600; color: var(--accent); padding: 8px 0; }
  .rank-all .rank-list { columns: 2 320px; column-gap: 40px; } .rank-all .rank-list li { break-inside: avoid; }
  .rk-none { padding: 10px 0; color: var(--ink2); }
  .rank-note a { color: var(--accent); }
  .rank-note { margin: 14px 0 0; font-size: 0.82rem; color: var(--ink2); max-width: 80ch; line-height: 1.5; }
  .who-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px 32px; margin-top: 8px; }
  .who h3 { margin: 0 0 6px; font-size: 1.05rem; } .who p { margin: 0; color: var(--ink2); line-height: 1.5; }
  .viewsw { display: flex; align-items: center; justify-content: flex-end; gap: 6px; font-size: 0.8rem; color: var(--ink2); margin: 0 0 4px; }
  .viewsw .chip { min-height: 32px; padding: 4px 12px; font-size: 0.8rem; }
  body.simple .adv { display: none !important; }
  .lib-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 24px; }
  .lib-chips .chip span { opacity: 0.6; margin-left: 4px; font-size: 0.8em; }
  .lib-chips .chip.on { background: #123B38; color: #fff; border-color: #123B38; }
  .lib-region { margin: 0 0 32px; }
  .lib-region h2 { font: 700 1.5rem/1.1 var(--font-display); color: #123B38; margin: 0 0 12px; display: flex; align-items: baseline; gap: 10px; }
  .lib-region h2 span { font: 500 0.8rem var(--font-mono); color: var(--ink2); }
  .lib-cards { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
  .lib-cards a { display: flex; flex-direction: column; gap: 3px; height: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 12px; background: var(--surface); color: var(--ink); text-decoration: none; border: 1px solid transparent; transition: border-color .15s, transform .15s; }
  .lib-cards a:hover { border-color: #123B38; transform: translateY(-1px); }
  .lib-cards strong { font: 650 1.05rem/1.2 var(--font-display); }
  .lib-cty { font: 600 0.68rem var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }
  .lib-pop { font: 400 0.78rem var(--font-body); color: var(--ink2); margin-top: 4px; }
  .lib-cards li.vis a { background: transparent; border: 1.5px dashed #123B38; }
  .lib-vis { align-self: flex-start; margin-top: 6px; font: 600 0.68rem var(--font-body); padding: 2px 8px; border-radius: 999px; background: #F3E3C4; color: #6B4510; }
  .lib-chips .chip-vis { border-style: dashed; }
  .lib-empty { color: var(--ink2); }
  .bio { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 22px; align-items: start; }
  .bio-photo { width: 160px; height: 160px; border-radius: 50%; object-fit: cover; }
  @media (max-width: 560px) { .bio { grid-template-columns: minmax(0, 1fr); } .bio-photo { width: 120px; height: 120px; } }
  .about-grid { display: grid; gap: 28px; max-width: 46rem; }
  .about-grid h2 { font-size: 1.5rem; margin: 0 0 8px; }
  .about-grid p { margin: 0 0 10px; color: var(--ink2); }
  .about-grid .page-h { margin: 4px 0 14px; }
  .about-list { margin: 0; padding-left: 1.2rem; display: grid; gap: 8px; color: var(--ink2); }
  .about-list b { color: var(--ink); }
  .about-grid a:not(.btn) { color: var(--accent); text-underline-offset: 2px; }
  .contact-box { padding: 20px 22px; border-radius: 14px; background: var(--surface); border: 1px solid var(--line); scroll-margin-top: 20px; }
"""
write("assets/site.css", css.strip() + "\n")
write("assets/model.js", read(SRC, "model2.js"))

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Nunito:wght@700&family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600&display=swap">\n')
# Cloudflare Web Analytics: private visit counts for Robert, no cookies and no personal data
ANALYTICS = ("<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
             "data-cf-beacon='{\"token\": \"a92b6704e81e4aaba11a9f8a11832ae1\"}'></script><!-- End Cloudflare Web Analytics -->\n")
PAGES = [("", "Home"), ("explore/", "Explore"), ("studio/", "Studio"), ("library/", "Library"), ("how-it-works/", "How it works"), ("about/", "About")]


def APP(base):
    # Installable app: icon, manifest and offline support
    return (f'<script src="{base}assets/i18n.js" defer></script>\n'
            f'<link rel="manifest" href="{base}manifest.webmanifest">\n'
            '<meta name="theme-color" content="#E8EDE6" media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="#0D1613" media="(prefers-color-scheme: dark)">\n'
            f'<link rel="icon" type="image/png" sizes="32x32" href="{base}assets/icons/favicon-32.png">\n'
            f'<link rel="apple-touch-icon" href="{base}assets/icons/apple-touch-icon.png">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n'
            '<meta name="apple-mobile-web-app-title" content="Threadlands">\n<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
            "<script>if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () {}); });</script>\n")


# Where the heavy map data lives (Cloudflare R2). Empty: served from this site's own data/ folder.
DATA_URL = "https://pub-5cc2f5116c6c462596fbf16596585b83.r2.dev"


def head(base, title, desc):
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{title}</title>\n<meta name="description" content="{desc}">\n'
            f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{desc}">\n'
            + FONTS + f'<link rel="stylesheet" href="{base}assets/site.css?v=7">\n' + APP(base) + f'<script>window.TL_DATA = "{DATA_URL}";</script>\n' + ANALYTICS + '</head>\n<body>\n')


def nav(base, here):
    links = "".join(f'<a href="{base}{p}"' + (' aria-current="page"' if p == here else "") + f'>{n}</a>'
                    for p, n in PAGES[1:])
    return (f'<header class="wrap site-head" id="top">\n  <div class="topbar">\n    <a class="wordmark" href="{base}" translate="no"><svg class="wm-sym" viewBox="0 0 48 48" width="28" height="28" fill="none" stroke-width="4" stroke-linecap="round" aria-hidden="true"><path d="M4 8C14 8 18 24 28 24H35" stroke="#2E6E8E"/><path d="M4 24H28" stroke="#4C9A5B"/><path d="M4 40C14 40 18 24 28 24" stroke="#C0603A"/><circle cx="40" cy="24" r="5" fill="#123B38" stroke="none"/></svg><span>Threadlands</span></a>\n'
            f'    <div class="topright"><nav class="topnav" aria-label="Site">{links}</nav>'
            '<label class="lang-l"><span class="sr-only">Language</span><select id="lang" class="lang-sel" translate="no" aria-label="Language"><option value="en">English</option></select></label></div>\n  </div>\n</header>\n')


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
examples = json.dumps([{"id": "san-francisco", "label": "San Francisco"}, {"id": "mexico-city", "label": "Mexico City"},
                       {"id": "montreal", "label": "Montreal"}, {"id": "bologna", "label": "Bologna"}, {"id": "bangkok", "label": "Bangkok"}])
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
