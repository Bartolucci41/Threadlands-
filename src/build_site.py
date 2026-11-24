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
html[data-lang="ar"] { --font-body: 'Noto Sans Arabic', system-ui, sans-serif; --font-display: 'Noto Sans Arabic', system-ui, sans-serif; }
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
  .feed { margin: 56px 0 48px; }
  .feed-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-top: 16px; }
  .feed-card { display: grid; gap: 6px; align-content: start; padding: 14px 16px; border-radius: 12px; background: var(--surface); border-top: 3px solid var(--pc); color: var(--ink); text-decoration: none; }
  .feed-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .feed-top { display: flex; justify-content: space-between; gap: 8px; font-size: 0.78rem; }
  .feed-st { font-weight: 600; color: var(--pc); } .feed-city { color: var(--ink2); }
  .feed-card b { font-size: 1.02rem; line-height: 1.3; } .feed-sum { font-size: 0.86rem; color: var(--ink2); line-height: 1.45; }
  .who-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px 32px; margin-top: 8px; }
  .who h3 { margin: 0 0 6px; font-size: 1.05rem; } .who p { margin: 0; color: var(--ink2); line-height: 1.5; }
  /* ---- Site-wide revamp: full-width bands, dark footer, page headers */
  html { overflow-x: clip; }
  .bleed { margin-inline: calc(50% - 50vw); padding-inline: max(16px, calc(50vw - 50% + 0px)); }
  .band-deep { background: var(--deep, #123B38); color: var(--deep-ink, #EAF2EE); }
  .band-deep a { color: #fff; }
  .band-white { background: var(--surface); }
  .site-foot2 { background: var(--deep, #123B38); color: #cfe0da; margin: 64px calc(50% - 50vw) -56px; padding: 48px max(16px, calc(50vw - 50%)) 40px; }
  .foot-grid { display: grid; grid-template-columns: 2fr repeat(3, 1fr); gap: 28px 40px; }
  .foot-brand p { margin: 10px 0 0; max-width: 32ch; color: #b9cfc8; line-height: 1.5; }
  .site-foot2 .foot-wm { color: #fff; font-size: 1.4rem; }
  .site-foot2 nav { display: grid; gap: 6px; align-content: start; }
  .site-foot2 nav h2 { margin: 0 0 6px; font: 600 0.75rem var(--font-body); letter-spacing: 0.1em; text-transform: uppercase; color: #8fb3a8; }
  .site-foot2 nav a { color: #eaf2ee; text-decoration: none; } .site-foot2 nav a:hover { text-decoration: underline; }
  .foot-small { margin-top: 36px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.12); display: grid; gap: 4px; font-size: 0.8rem; color: #8fb3a8; }
  .foot-small p { margin: 0; }
  @media (max-width: 720px) { .foot-grid { grid-template-columns: 1fr 1fr; } .foot-brand { grid-column: 1 / -1; } }
  .page-head { padding: 28px 0 8px; display: grid; gap: 10px; }
  .page-kicker { margin: 0; font: 600 0.8rem var(--font-body); letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent); }
  .page-head h1 { font-size: clamp(2.4rem, 6vw, 4.2rem); line-height: 1; letter-spacing: -0.035em; max-width: 18ch; }
  .page-lead { margin: 0; font-size: 1.15rem; color: var(--ink2); max-width: 60ch; line-height: 1.5; }
  .bigstats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 18px 28px; padding: 36px 0; }
  .bigstat b { display: block; font: 800 clamp(2.2rem, 5vw, 3.4rem)/1 var(--font-display); letter-spacing: -0.03em; }
  .bigstat span { display: block; margin-top: 6px; font-size: 0.92rem; opacity: 0.85; }
  .sect { padding-block: 64px; }
  .sect-top { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: end; justify-content: space-between; margin-bottom: 22px; }
  .sect-top h2 { font-size: clamp(1.9rem, 4.6vw, 2.9rem); letter-spacing: -0.03em; line-height: 1.05; max-width: 20ch; }
  .sect-top p { margin: 8px 0 0; color: var(--ink2); max-width: 56ch; }
  .band-deep .sect-top p { color: #b9cfc8; }
  .more { font-weight: 600; color: var(--accent); text-decoration: none; white-space: nowrap; } .more:hover { text-decoration: underline; }
  .band-deep .more { color: #fff; }
  .filters { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 0 0 16px; }
  .filters .chip[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink, #fff); border-color: var(--accent); }
  .filters input[type=search] { min-height: 40px; padding: 6px 16px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font: inherit; min-width: 200px; }
  .rk-count { font-size: 0.85rem; color: var(--ink2); margin-left: 8px; }
  .rk-table { list-style: none; margin: 8px 0 0; padding: 0; border-top: 2px solid var(--ink); }
  .rk-table a { display: grid; grid-template-columns: 3rem minmax(0, 2.2fr) minmax(0, 1fr) minmax(0, 1.2fr) minmax(80px, 1fr) 3rem; gap: 14px; align-items: center; padding: 14px 4px; border-bottom: 1px solid var(--line); color: var(--ink); text-decoration: none; }
  .rk-table a:hover { background: var(--surface); }
  .rt-n { font: 700 1.1rem var(--font-display); color: var(--ink2); text-align: right; font-variant-numeric: tabular-nums; }
  .rt-c { display: grid; min-width: 0; } .rt-c b { font: 700 1.15rem var(--font-display); letter-spacing: -0.01em; } .rt-c span { font-size: 0.82rem; color: var(--ink2); }
  .rt-p { font-size: 0.85rem; color: var(--ink2); }
  .rk-pj { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 99px; background: var(--accent); color: var(--accent-ink, #fff); }
  .rk-pj0 { background: transparent; color: var(--ink2); border: 1px solid var(--line); font-weight: 500; }
  .rt-bar { height: 8px; border-radius: 4px; background: var(--surface2); overflow: hidden; } .rt-bar i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
  .rt-v { font: 800 1.35rem var(--font-display); text-align: right; font-variant-numeric: tabular-nums; }
  @media (max-width: 760px) { .rk-table a { grid-template-columns: 2.2rem minmax(0, 1fr) 64px 2.4rem; } .rt-p, .rt-j { display: none; } }
  .rk-head { display: grid; grid-template-columns: 1rem minmax(0, 2.2fr) minmax(0, 1.6fr) minmax(0, 1fr); gap: 14px; padding: 18px 4px 8px; font: 600 0.72rem var(--font-body); letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink2); }
  .rk-head.cmp, .rk-table.cmp a { grid-template-columns: 3rem minmax(0, 2.2fr) minmax(0, 1fr) minmax(0, 1fr) minmax(80px, 1fr) 4.6rem; }
  .rt-v small { font-size: 0.6em; font-weight: 700; margin-left: 1px; }
  .rk-table:not(.cmp) a { grid-template-columns: 1rem minmax(0, 2.2fr) minmax(0, 1.6fr) minmax(0, 1fr); }
  .rk-cmp-note { margin: 4px 0 0; padding: 12px 16px; border-radius: 12px; background: var(--surface); color: var(--ink2); font-size: 0.9rem; line-height: 1.5; max-width: 60rem; }
  .rk-head i { font-style: normal; text-transform: none; letter-spacing: 0; font-weight: 500; display: block; }
  .rk-head + .rk-table { margin-top: 0; }
  .rt-p b { color: var(--ink); font-weight: 600; }
  @media (max-width: 760px) { .rk-head.cmp, .rk-table.cmp a { grid-template-columns: 2.2rem minmax(0, 1fr) 56px 3.6rem; } .rk-head.cmp span:nth-child(3), .rk-head.cmp span:nth-child(4), .rk-table.cmp .rt-p, .rk-table.cmp .rt-j { display: none; } .rk-head:not(.cmp), .rk-table:not(.cmp) a { grid-template-columns: 0 minmax(0, 1fr); } .rk-head:not(.cmp) span:nth-child(n+3), .rk-table:not(.cmp) .rt-j { display: none; } .rk-table:not(.cmp) .rt-p { display: block; grid-column: 2; } }
  .pfp-f { margin: -4px 0 8px; font-weight: 600; color: var(--warm, #C0603A); }
  .pfr-note { flex-basis: 100%; margin: 6px 0 0; color: var(--ink2); font-size: 0.85rem; line-height: 1.5; max-width: 44ch; }
  .pfp-sep { border: 0; border-top: 1px solid var(--line); margin: 12px 0; } .here-why .hw-f { font: inherit; font-weight: 600; }
  .pfp-map { margin: 10px 0 0; font-size: 0.92rem; } .pfp-map a { font-weight: 600; color: var(--accent); }
  .here-why { display: grid; gap: 6px; padding: 0 0 14px; margin: 0 0 12px; border-bottom: 1px solid var(--line); }
  .here-why b { font: 700 1.1rem var(--font-display); } .here-why p { margin: 0; line-height: 1.5; } .here-why .hw-n { color: var(--ink2); font-size: 0.88rem; }
  .rk-table li.vis a { background: linear-gradient(90deg, #F3E3C433, transparent 40%); }
  .rt-c .lib-vis { justify-self: start; margin-top: 4px; }
  .rt-v small { font: 500 0.72rem var(--font-body); color: var(--ink2); }
  .page-lead a { color: var(--accent); text-underline-offset: 3px; }
  .rk-method { margin-top: 56px; padding: 32px; border-radius: 18px; background: var(--surface); }
  .rk-method h2 { font-size: 1.6rem; margin-bottom: 16px; }
  .rk-m-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px 32px; }
  .rk-m-grid h3 { font-size: 1rem; margin-bottom: 6px; } .rk-m-grid p { margin: 0; color: var(--ink2); line-height: 1.55; font-size: 0.95rem; }
  .pj-layout { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 18px; align-items: start; }
  .pj-map { height: 620px; border-radius: 18px; overflow: hidden; background: var(--surface2); position: sticky; top: 12px; }
  .pj-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; max-height: 620px; overflow-y: auto; }
  .pjc { background: var(--surface); border-radius: 14px; border-left: 4px solid var(--pc); padding: 2px 0 12px; }
  .pjc.hl { outline: 2px solid var(--accent); }
  .pjc-go { display: grid; gap: 4px; width: 100%; text-align: left; background: none; border: 0; padding: 12px 16px 6px; font: inherit; color: var(--ink); cursor: pointer; }
  .pjc-top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px; font-size: 0.78rem; color: var(--ink2); } .pjc-st { font-weight: 700; color: var(--pc); }
  .pjc-go b { font: 700 1.08rem/1.3 var(--font-display); } .pjc-sum { font-size: 0.88rem; color: var(--ink2); line-height: 1.45; }
  .pjc-links { display: flex; flex-wrap: wrap; gap: 14px; padding: 0 16px; font-size: 0.85rem; } .pjc-links a { color: var(--accent); font-weight: 600; }
  .pj-add { margin-top: 40px; padding: 28px 32px; border-radius: 18px; background: var(--deep, #123B38); color: #eaf2ee; display: flex; flex-wrap: wrap; gap: 18px 32px; align-items: center; justify-content: space-between; }
  .pj-add h2 { font-size: 1.6rem; color: #fff; } .pj-add p { margin: 6px 0 0; color: #b9cfc8; max-width: 52ch; }
  .pj-add-f { display: flex; flex-wrap: wrap; gap: 8px; } .pj-add-f select { min-height: 44px; border-radius: 10px; border: 0; padding: 0 12px; font: inherit; min-width: 0; width: min(100%, 300px); } .pj-add-f label { min-width: 0; max-width: 100%; }
  .pj-add .btn { background: #fff; color: var(--deep, #123B38); border-color: #fff; }
  @media (max-width: 900px) { .pj-layout { grid-template-columns: 1fr; } .pj-map { height: 380px; position: static; } .pj-list { max-height: none; } }
  .hero3 { padding-top: 56px; padding-bottom: 8px; margin-top: 8px; }
  .hero3-in { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); gap: 32px 48px; align-items: center; }
  .hero3-kick { margin: 0 0 16px; font: 600 0.8rem var(--font-body); letter-spacing: 0.12em; text-transform: uppercase; color: #8fd3bf; }
  .hero3-h { color: #fff; font-size: clamp(2.4rem, 5vw, 4.1rem); line-height: 1.02; letter-spacing: -0.035em; max-width: 14ch; }
  .hero3-sub { margin: 20px 0 24px; font-size: 1.15rem; line-height: 1.55; color: #cfe0da; max-width: 44ch; }
  .hero3-in > * { min-width: 0; }
  .hero3 .search { display: flex; gap: 8px; max-width: 100%; }
  .hero3 .search input { background: #fff; border-color: #fff; min-width: 0; flex: 1 1 auto; }
  .hero3 .search .btn { background: #8fd3bf; color: #0b2624; border-color: #8fd3bf; }
  .hero3 .search-note, .hero3 .byline { color: #a9c6bd; } .hero3 .byline b { color: #fff; }
  .hero3 .live { background: var(--surface); color: var(--ink); border-radius: 20px; padding: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.35); }
  .hero3 .live a { color: var(--accent); }
  .hero3-stats { border-top: 1px solid rgba(255,255,255,0.14); margin-top: 48px; color: #fff; }
  .rank-cols h3 { font-size: 0.85rem; }
  .who-grid { gap: 28px 48px; }
  .band-deep .who h3 { color: #fff; font-size: 1.35rem; margin: 8px 0 8px; } .band-deep .who p { color: #cfe0da; font-size: 1.02rem; }
  .who-n { font: 800 2.6rem/1 var(--font-display); color: #8fd3bf; }
  .band-deep h2 { color: #fff; }
  .lib-line { margin: 18px 0 0; color: var(--ink2); }
  @media (max-width: 900px) { .hero3-in { grid-template-columns: 1fr; } .hero3 { padding-top: 32px; } }
  .news-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0 32px; border-top: 2px solid var(--ink); }
  .nw { display: grid; gap: 4px; padding: 16px 0; border-bottom: 1px solid var(--line); align-content: start; }
  .nw-t { font: 700 0.72rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--warm, #C0603A); }
  .nw-flood .nw-t { color: #1f5f9e; } .nw-greening .nw-t { color: #2f7a4a; } .nw-drought .nw-t { color: #a16207; }
  .nw-h { font: 700 1.08rem/1.3 var(--font-display); color: var(--ink); text-decoration: none; } .nw-h:hover { text-decoration: underline; }
  .nw-m { font-size: 0.8rem; color: var(--ink2); } .nw-m a { color: var(--accent); font-weight: 600; }
  .news-note { margin: 14px 0 0; font-size: 0.8rem; color: var(--ink2); } .news-note a { color: var(--accent); }
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

  /* ---- Two faces: the side switch in the top bar */
  .topnav .nav-home { margin-right: 5px; vertical-align: -2px; }
  .tl-flag { display: inline-block; width: 1.2em; height: 0.9em; margin-right: 0.4em; border-radius: 2px; vertical-align: -0.06em; box-shadow: 0 0 0 1px rgba(0,0,0,0.08); background-size: cover; flex: none; }
  /* ThreadLab: easy to spot, but flat and quiet, so Places stays the usual starting point */
  .topnav a.nav-lab { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; color: #fff; background: #165049; font-weight: 600; text-decoration: none; transition: background .12s ease; }
  .topnav a.nav-lab::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: #8fd3bf; }
  .topnav a.nav-lab:hover { color: #fff; background: #0f3b36; }
  .topnav a.nav-lab[aria-current="page"] { text-decoration: none; outline: 2px solid #8fd3bf; outline-offset: 2px; }
  .topnav a.nav-lab:focus-visible { outline: 3px solid #8fd3bf; outline-offset: 3px; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .topnav a.nav-lab { color: #0b2624; background: #8fd3bf; } :root:not([data-theme="light"]) .topnav a.nav-lab::before { background: #123B38; } }
  @media (max-width: 560px) {
    .site-head { position: relative; }
    .site-head .lang-l { position: absolute; top: 14px; right: 0; }
    .lang-sel { font-size: 0.78rem; padding-left: 8px; }
    .topright { width: 100%; }
    .topnav { gap: 6px 14px; font-size: 0.92rem; }
    .topnav a.nav-lab { padding: 3px 10px; }
    .lab-tabs { gap: 4px 16px; } .lab-tabs-k { display: none; }
  }
  /* Get involved */
  .inv-now { margin: 28px 0 0; }
  .inv-now-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
  .now-c { display: grid; gap: 6px; align-content: start; padding: 18px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); }
  .now-c:first-child { border: 2px solid var(--accent); }
  .now-k { font: 600 0.7rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
  .now-c b { font: 700 1.1rem/1.3 var(--font-display); } .now-m { font-size: 0.85rem; color: var(--ink2); line-height: 1.45; }
  .now-c a { font-weight: 600; color: var(--accent); font-size: 0.9rem; } .now-c .pjc-back { padding: 4px 0 0; }
  .chg { margin: 0 0 20px; padding: 18px 20px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); }
  .chg h3 { margin: 0 0 8px; font-size: 1.15rem; }
  .chg-list { list-style: none; margin: 0; padding: 0; }
  .chg-list li { display: grid; gap: 3px; padding: 10px 0; border-top: 1px solid var(--line); } .chg-list li:first-child { border-top: 0; }
  .chg-m { font-size: 0.78rem; color: var(--ink2); } .chg-t { font-weight: 600; color: var(--ink); text-decoration: none; line-height: 1.35; } a.chg-t:hover { text-decoration: underline; }
  .chg-s { font-size: 0.78rem; color: var(--ink2); } .chg-a { font-size: 0.85rem; font-weight: 600; color: var(--accent); }
  .chg-none { color: var(--ink2); font-size: 0.92rem; }
  .ladder { list-style: none; margin: 22px 0 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; counter-reset: lad; max-width: 60rem; }
  @media (max-width: 760px) { .ladder { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .ladder li { counter-increment: lad; display: grid; gap: 2px; padding: 12px 14px; border-radius: 14px; background: var(--surface); border: 1px solid var(--line); font-size: 0.88rem; color: var(--ink2); line-height: 1.4; }
  .ladder li b { font: 700 1.05rem var(--font-display); color: var(--ink); } .ladder li b::before { content: counter(lad) " "; color: var(--accent); }
  .mpc-tie { display: block; padding: 0 18px 16px; } .mpc-tie select { width: 100%; min-height: 36px; border-radius: 10px; border: 1px solid var(--line); background: var(--surface2); font: 500 0.85rem var(--font-body); color: var(--ink); padding: 0 10px; }
  .pf-tie { margin-top: 14px; padding: 14px 16px; border-radius: 14px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18); max-width: 34rem; }
  .pf-tie p { margin: 0 0 10px; color: #fff; font-weight: 600; }
  .pf-tie-opts { display: flex; flex-wrap: wrap; gap: 8px; }
  .pf-tie .chip { background: transparent; color: #fff; border-color: rgba(255,255,255,0.45); } .pf-tie .chip[aria-pressed="true"] { background: #8fd3bf; color: #0b2624; border-color: #8fd3bf; }
  .pf-tie-off { margin-top: 12px; color: #cfe0da; font-size: 0.85rem; }
  .pf-standers { margin: 12px 0 0; color: #cfe0da; font-size: 0.92rem; } .pf-standers b { color: #fff; }
  .inv-first { padding-top: 24px; }
  .inv-ways { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
  .inv-way { display: grid; gap: 6px; align-content: start; padding: 20px; border-radius: 18px; background: var(--surface); border: 1px solid var(--line); color: var(--ink); text-decoration: none; }
  a.inv-way:hover { border-color: var(--deep, #123B38); }
  .inv-way b { font: 700 1.2rem var(--font-display); } .inv-way span { color: var(--ink2); line-height: 1.5; }
  a.inv-way b::after { content: " \2192"; color: var(--accent); }
  .inv-soon { background: transparent; border-style: dashed; }
  .lab-tabs { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 20px; padding: 8px 0 10px; border-top: 1px solid var(--line); font-size: 0.9rem; }
  .lab-tabs-k { font: 600 0.7rem var(--font-body); letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink2); margin-right: 4px; }
  .lab-tabs a { color: var(--ink2); text-decoration: none; font-weight: 600; min-height: 32px; display: inline-flex; align-items: center; }
  .lab-tabs a:hover { color: var(--ink); }
  .lab-tabs a[aria-current="page"] { color: var(--ink); text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 6px; }
  .side-sw { display: inline-flex; align-items: center; min-height: 34px; padding: 0 14px; border-radius: 999px; border: 1.5px solid var(--deep, #123B38); color: var(--deep, #123B38); font: 600 0.82rem var(--font-body); text-decoration: none; white-space: nowrap; }
  .side-sw:hover { background: var(--deep, #123B38); color: #fff; }
  .side-sw .sw-s { display: none; }
  .wm-pro { margin-left: 8px; padding: 2px 8px; border-radius: 6px; background: var(--deep, #123B38); color: #fff; font: 600 0.72rem var(--font-body); letter-spacing: 0.06em; text-transform: uppercase; vertical-align: middle; }
  @media (max-width: 560px) { .side-sw .sw-l { display: none; } .side-sw .sw-s { display: inline; } .side-sw { min-height: 30px; padding: 0 10px; } .topright { gap: 4px 14px; } }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .side-sw { border-color: var(--accent); color: var(--accent); } }
  .linkbtn { background: none; border: 0; padding: 0; font: inherit; color: inherit; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
  .btn.ghost-inv { background: transparent; color: #fff; border-color: rgba(255,255,255,0.5); }
  .btn.ghost-inv:hover { border-color: #fff; }
  /* ---- My places */
  .mp-hero { padding-block: 44px 48px; }
  .mp-hero-in { max-width: 72rem; }
  .mp-h { max-width: 18ch; }
  .mp-h { color: #fff; font-size: clamp(2.1rem, 5vw, 3.4rem); line-height: 1.04; letter-spacing: -0.03em; margin: 0; }
  .mp-sub { margin: 16px 0 22px; font-size: 1.08rem; line-height: 1.55; color: #cfe0da; max-width: 52ch; }
  .doors { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 30px; }
  @media (max-width: 720px) { .doors { grid-template-columns: 1fr; gap: 12px; } }
  .door { display: grid; gap: 8px; align-content: start; padding: 26px 28px 24px; border-radius: 22px; text-decoration: none; min-height: 210px; box-sizing: border-box; transition: transform .15s, box-shadow .15s; }
  .door:hover { transform: translateY(-2px); box-shadow: 0 14px 40px rgba(0,0,0,0.28); }
  .door:focus-visible { outline: 3px solid #fff; outline-offset: 3px; }
  @media (prefers-reduced-motion: reduce) { .door, .door:hover { transition: none; transform: none; } }
  .band-deep a.door-places { background: #8fd3bf; color: #0b2624; }
  .band-deep a.door-lab { background: #F3F4EF; color: #12231E; }
  .door-k { font: 600 0.75rem var(--font-body); letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.75; }
  .door-t { font: 800 clamp(1.7rem, 3.6vw, 2.4rem)/1.05 var(--font-display); letter-spacing: -0.025em; }
  .door-d { font-size: 1rem; line-height: 1.5; opacity: 0.85; max-width: 40ch; }
  .door-go { margin-top: auto; padding-top: 10px; font: 700 1rem var(--font-body); }
  .home-search { max-width: 40rem; margin-top: 4px; } .home-search input { font-size: 1.05rem; min-height: 54px; }
  .hs-try { margin: 12px 0 0; color: #a9c6bd; font-size: 0.9rem; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
  .hs-tl { color: #fff; font-weight: 600; }
  .hs-chip { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.35); color: #fff !important; text-decoration: none; margin-right: 6px; }
  .hs-chip:hover { background: rgba(255,255,255,0.12); }
  @media (max-width: 560px) { .band-deep .doors a.door-places { display: none; } .door { min-height: 0; } }
  .q-lead { font-size: 1.05rem; padding: 14px 20px; box-shadow: 0 2px 0 rgba(15,47,87,0.18); }
  .qs-or { color: var(--ink2); font-size: 0.9rem; }
  .doors-link { margin: 16px 0 0; color: #cfe0da; font-size: 0.95rem; max-width: 60rem; } .doors-link span { color: #8fd3bf; font-size: 1.1rem; margin-right: 6px; }
  .mp-add { margin: 0 0 20px; } .mp-search { max-width: 34rem; }
  .mp-near { margin: 10px 0 0; font-size: 0.9rem; color: var(--ink2); } .mp-near .linkbtn { color: var(--accent); font-weight: 600; } .mp-near a { color: var(--accent); }
  #mine-h:focus { outline: none; }
  .mp { padding-top: 40px; }
  .mp-units { display: inline-flex; gap: 6px; } .mp-units .chip { min-height: 32px; padding: 0 12px; font-size: 0.85rem; }
  .mp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px; }
  .mpc { position: relative; background: var(--surface); border-radius: 18px; border: 1px solid var(--line); transition: border-color .15s, transform .15s; }
  .mpc:hover { border-color: var(--deep, #123B38); transform: translateY(-1px); }
  .mpc.mpc-new { animation: mpc-in .6s ease; } @keyframes mpc-in { from { box-shadow: 0 0 0 4px #8fd3bf; } to { box-shadow: 0 0 0 0 transparent; } }
  @media (prefers-reduced-motion: reduce) { .mpc, .mpc.mpc-new { transition: none; animation: none; } }
  .mpc-main { display: grid; gap: 12px; padding: 18px 18px 16px; color: var(--ink); text-decoration: none; height: 100%; box-sizing: border-box; align-content: start; }
  .mpc-top { display: flex; justify-content: space-between; gap: 12px; align-items: start; padding-right: 22px; }
  .mpc-name { display: block; font: 700 1.35rem/1.15 var(--font-display); letter-spacing: -0.015em; }
  .mpc-where { display: block; font-size: 0.8rem; color: var(--ink2); margin-top: 2px; }
  .mpc-wx { display: grid; grid-template-columns: auto auto; grid-template-rows: auto auto; column-gap: 6px; align-items: center; text-align: right; flex: none; }
  .mpc-wx .wx-ico { grid-row: 1; color: var(--ink2); }
  .mpc-t { font: 800 1.7rem/1 var(--font-display); font-variant-numeric: tabular-nums; }
  .mpc-hl { grid-column: 1 / -1; font-size: 0.75rem; color: var(--ink2); line-height: 1.3; }
  .mpc-alert { justify-self: start; font: 600 0.78rem var(--font-body); padding: 4px 10px; border-radius: 999px; background: #F3E3C4; color: #6B4510; }
  .mpc-alert.al-rain, .mpc-alert.al-storm { background: #D7E7F3; color: #17457E; }
  .mpc-alert.al-heat { background: #F7D9CB; color: #8A2E0E; }
  .mpc-stats { display: flex; gap: 18px; flex-wrap: wrap; padding-top: 12px; border-top: 1px solid var(--line); }
  .mpc-stats > span { display: grid; gap: 1px; } .mpc-stats i, .mpc-news i { font: 600 0.66rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); font-style: normal; }
  .mpc-stats b { font: 800 1.25rem/1.1 var(--font-display); } .mpc-stats b.mpc-press { font-size: 1rem; font-weight: 700; } .mpc-stats small { font-size: 0.72rem; color: var(--ink2); }
  .mpc-news { display: grid; gap: 3px; font-size: 0.88rem; line-height: 1.4; color: var(--ink); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
  .mpc-news i { display: block; }
  .mpc-x { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 50%; border: 0; background: transparent; color: var(--ink2); font-size: 1.3rem; line-height: 1; cursor: pointer; }
  .mpc-x:hover { background: var(--surface2); color: var(--ink); }
  .mp-empty { padding: 22px; border-radius: 18px; border: 1.5px dashed var(--line); color: var(--ink2); } .mp-empty p { margin: 0 0 14px; }
  .mp-pop { display: flex; flex-wrap: wrap; gap: 8px; }
  .mp-err { color: var(--ink2); }
  /* ---- Headlines with a tone: risk, progress or update */
  .nw2-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 0 28px; border-top: 2px solid var(--ink); }
  .nw2-list { list-style: none; margin: 0; padding: 0; border-top: 2px solid var(--ink); max-width: 52rem; }
  .nw2 { display: grid; gap: 5px; padding: 16px 0; border-bottom: 1px solid var(--line); align-content: start; }
  .nw2-tag { font: 500 0.72rem var(--font-body); letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink2); }
  .nw2-tag b { font-weight: 700; color: #6b7280; }
  .tone-concern .nw2-tag b { color: var(--warm, #C0603A); } .tone-gain .nw2-tag b { color: #2f7a4a; } .tone-update .nw2-tag b { color: #2E6E8E; }
  .nw2-h { font: 700 1.05rem/1.32 var(--font-display); color: var(--ink); text-decoration: none; } .nw2-h:hover { text-decoration: underline; }
  .nw2-m { font-size: 0.8rem; color: var(--ink2); } .nw2-m a { color: var(--accent); font-weight: 600; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .tone-gain .nw2-tag b { color: #7fd39b; } :root:not([data-theme="light"]) .tone-update .nw2-tag b { color: #8cc3e6; } }
  /* ---- The Lab band */
  .pro-band-in { display: flex; flex-wrap: wrap; gap: 20px 40px; align-items: end; justify-content: space-between; }
  .pro-band-in > div:first-child { max-width: 44rem; } .pro-band h2 { font-size: clamp(1.7rem, 4vw, 2.4rem); margin: 0 0 10px; }
  .pro-band p { color: #cfe0da; margin: 0; line-height: 1.55; }
  .pro-band .btn:not(.ghost-inv) { background: #8fd3bf; color: #0b2624; border-color: #8fd3bf; }
  .pro-band-go { display: flex; flex-wrap: wrap; gap: 10px; }
  /* ---- City profile */
  .pf-head { padding-block: 28px 22px; }
  .pf-head-in { display: flex; flex-wrap: wrap; gap: 24px 48px; justify-content: space-between; align-items: end; }
  .pf-back { font-size: 0.85rem; color: #a9c6bd !important; text-decoration: none; } .pf-back:hover { color: #fff !important; }
  .pf-h { color: #fff; font-size: clamp(2.4rem, 6vw, 4rem); line-height: 1; letter-spacing: -0.035em; margin: 10px 0 8px; }
  .pf-where { margin: 0 0 18px; color: #b9cfc8; }
  .pf-actions { display: flex; flex-wrap: wrap; gap: 10px; }
  .pf-actions .btn:not(.ghost-inv) { background: #8fd3bf; color: #0b2624; border-color: #8fd3bf; }
  .pf-actions .btn[aria-pressed="true"] { background: #fff; border-color: #fff; }
  .pf-now { min-width: 240px; }
  .pf-now-main { display: flex; align-items: center; gap: 10px; color: #fff; }
  .pf-temp { font: 800 clamp(3rem, 8vw, 4.4rem)/1 var(--font-display); letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
  .pf-sky { margin: 6px 0 2px; color: #fff; font-weight: 600; } .pf-meta { margin: 0 0 10px; font-size: 0.85rem; color: #b9cfc8; }
  .pf-now .mp-units .chip { background: transparent; color: #fff; border-color: rgba(255,255,255,0.4); } .pf-now .mp-units .chip[aria-pressed="true"] { background: #fff; color: #0b2624; border-color: #fff; }
  .pf-wait { color: #b9cfc8; }
  .pf-week { list-style: none; margin: 22px 0 0; padding: 14px 0 0; border-top: 1px solid rgba(255,255,255,0.18); display: grid; grid-template-columns: repeat(7, minmax(64px, 1fr)); gap: 8px; overflow-x: auto; }
  .pf-week li { display: grid; justify-items: center; gap: 4px; font-size: 0.82rem; color: #cfe0da; }
  .pf-week .pw-d { font-weight: 600; color: #fff; } .pf-week b { color: #fff; } .pf-week .pw-r { font-size: 0.72rem; color: #9cc8ec; min-height: 1em; }
  .pf-alerts { display: grid; gap: 8px; margin-top: 18px; }
  .pf-alert { margin: 0; padding: 12px 16px; border-radius: 12px; background: #F3E3C4; color: #4a3008; line-height: 1.45; }
  .pf-alert.al-rain, .pf-alert.al-storm { background: #D7E7F3; color: #0f2f57; } .pf-alert.al-heat { background: #F7D9CB; color: #5e1f08; }
  .pf-alert b { margin-right: 6px; }
  .pf-jump { display: flex; flex-wrap: wrap; gap: 6px 20px; padding: 18px 0 0; font-size: 0.88rem; }
  .pf-jump a { color: var(--ink2); text-decoration: none; font-weight: 600; } .pf-jump a:hover { color: var(--ink); text-decoration: underline; }
  .pf-sec { padding-block: 48px 8px; scroll-margin-top: 12px; }
  .pf-press, .pf-tied { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
  .pfp { background: var(--surface); border-radius: 16px; padding: 18px 20px; border-top: 4px solid var(--warm, #C0603A); }
  .pfp-k { font: 600 0.72rem var(--font-body); letter-spacing: 0.06em; text-transform: uppercase; color: var(--warm, #C0603A); }
  .pfp h3 { font-size: 1.35rem; margin: 6px 0 8px; } .pfp-what { margin: 0 0 8px; font-weight: 500; line-height: 1.5; } .pfp-who { margin: 0; color: var(--ink2); font-size: 0.92rem; line-height: 1.5; }
  .pft { background: var(--surface); border-radius: 16px; padding: 18px 20px; }
  .pft-n { display: block; font: 800 2.1rem/1.05 var(--font-display); letter-spacing: -0.02em; margin: 6px 0 8px; color: var(--deep, #123B38); }
  .pft p { margin: 0; color: var(--ink2); line-height: 1.5; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .pft-n { color: var(--accent); } }
  .pf-ready { display: grid; grid-template-columns: minmax(180px, 240px) minmax(0, 1fr); gap: 20px 40px; align-items: start; background: var(--surface); border-radius: 18px; padding: 22px; }
  @media (max-width: 640px) { .pf-ready { grid-template-columns: 1fr; } }
  .pfr-score { display: grid; gap: 4px; justify-items: start; } .pfr-score b { font: 800 4rem/1 var(--font-display); letter-spacing: -0.03em; } .pfr-score > span:not(.eyebrow):not(.rk-pj) { color: var(--ink2); }
  .pfr-bars { display: grid; gap: 12px; }
  .pf-bar { display: grid; grid-template-columns: minmax(120px, 11rem) minmax(0, 1fr) 2.5rem; gap: 12px; align-items: center; }
  .pf-bar-l { font-size: 0.92rem; } .pf-bar b { text-align: right; font-variant-numeric: tabular-nums; }
  .pf-bar-t { height: 8px; border-radius: 4px; background: var(--surface2); overflow: hidden; } .pf-bar-t i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
  .pf-proj { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .pf-proj .pjc { display: grid; gap: 6px; padding: 14px 16px; } .pf-proj .pjc b { font: 700 1.08rem/1.3 var(--font-display); } .pf-proj .pjc-links { padding: 4px 0 0; }
  .pf-add { display: flex; flex-wrap: wrap; gap: 14px 28px; align-items: center; justify-content: space-between; margin-top: 16px; padding: 18px 20px; border-radius: 16px; border: 1.5px dashed var(--line); }
  .pf-add p { margin: 0; max-width: 46rem; color: var(--ink2); line-height: 1.5; } .pf-add b { color: var(--ink); }
  .pjc-back { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 8px 16px 0; } .pf-proj .pjc-back { padding: 6px 0 0; }
  .back-btn { min-height: 36px; padding: 0 16px; font-size: 0.88rem; }
  .back-btn[aria-pressed="true"] { background: transparent; color: var(--accent); border-color: var(--accent); }
  .back-n { font-size: 0.82rem; color: var(--ink2); }
  .nx { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin: 14px 0 0; padding-top: 12px; border-top: 1px solid var(--line); font-size: 0.88rem; }
  .nx-k { font: 600 0.68rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); width: 100%; }
  .nx a { color: var(--accent); font-weight: 600; text-underline-offset: 3px; }
  .pf-tie-how { margin: 12px 0 0 !important; font-weight: 400 !important; font-size: 0.85rem; color: #cfe0da !important; line-height: 1.5; } .pf-tie-how b { color: #fff; }
  .pf-actions .btn.ghost-inv[aria-pressed="true"] { background: #8fd3bf; color: #0b2624; border-color: #8fd3bf; }
  .pfs { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px 32px; margin-top: 8px; padding-top: 20px; border-top: 1px solid var(--line); }
  @media (max-width: 760px) { .pfs { grid-template-columns: 1fr; } }
  .pfs h3 { font-size: 1rem; margin: 0 0 8px; }
  .pfs-map { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; } .pfs-map svg { flex: none; } .pfs-key { flex: 1 1 220px; }
  .btn .pf-nm { margin-left: -4px; }
  .pfs-r { fill: var(--surface2); stroke: var(--ink2); stroke-width: 1.2; } .pfs-c { fill: var(--accent); fill-opacity: 0.28; stroke: var(--accent); stroke-width: 1.5; }
  .pfs-key p { margin: 0 0 6px; font-size: 0.88rem; color: var(--ink2); line-height: 1.45; } .pfs-key b { color: var(--ink); }
  .pfs-key i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; } .k-r { background: var(--surface2); border: 1.2px solid var(--ink2); } .k-c { background: rgba(14,124,102,0.3); border: 1.5px solid var(--accent); }
  .pfs-n { font-size: 0.82rem !important; }
  .pfs-ev ul { margin: 0 0 8px; padding-left: 1.1rem; font-size: 0.88rem; color: var(--ink2); line-height: 1.5; } .pfs-ev li { margin-bottom: 4px; } .pfs-ev b { color: var(--ink); }
  .pfs-ev a { font-size: 0.88rem; font-weight: 600; color: var(--accent); }
  /* Today card and What's here? */
  .today { margin-top: 24px; padding: 20px; border-radius: 18px; background: var(--surface); border: 1px solid var(--line); }
  .today h2 { font-size: 1.4rem; margin: 0 0 12px; }
  .today-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px 24px; }
  @media (max-width: 860px) { .today-grid { grid-template-columns: 1fr; } }
  .td-k { display: block; font: 600 0.7rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); margin-bottom: 6px; }
  .td-big { margin: 0 0 8px; font-weight: 600; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .td-none { margin: 0 0 6px; color: var(--ink2); font-size: 0.9rem; }
  .td-al { margin: 0 0 8px; padding: 10px 12px; border-radius: 10px; background: #F3E3C4; color: #4a3008; font-size: 0.88rem; line-height: 1.45; }
  .td-al.al-rain, .td-al.al-storm { background: #D7E7F3; color: #0f2f57; } .td-al.al-heat { background: #F7D9CB; color: #5e1f08; }
  .td-al .linkbtn { font-weight: 700; color: inherit; }
  .td-n { margin: 0 0 10px; display: grid; gap: 2px; font-size: 0.9rem; line-height: 1.35; } .td-n a { font-weight: 600; color: var(--ink); }
  .td-t { font-size: 0.72rem; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.05em; }
  .td-n .linkbtn, .td-add { justify-self: start; color: var(--accent); font-weight: 600; font-size: 0.85rem; }
  .here-layers { margin-bottom: 12px; }
  .qs { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin: 0 0 12px; }
  .qs-k { font: 600 0.7rem var(--font-body); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }
  .q-btn { font: 600 0.95rem var(--font-body); padding: 10px 16px; border-radius: 999px; border: 0; background: #D7E7F3; color: #0f2f57; cursor: pointer; }
  .q-btn:hover, .q-btn.on { background: #2E6E8E; color: #fff; }
  .q-kick { display: flex; justify-content: space-between; gap: 8px; margin: 0 0 6px; font: 600 0.72rem var(--font-body); letter-spacing: 0.06em; text-transform: uppercase; color: #2E6E8E; }
  .q-dots { display: inline-flex; gap: 4px; } .q-dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--line); } .q-dots i.on { background: #2E6E8E; }
  .here-card p { line-height: 1.5; } .q-note { font-size: 0.8rem; color: var(--ink2); }
  .q-linelabel { background: #123B38; color: #fff; border: 0; border-radius: 8px; padding: 6px 10px; font: 500 12px/1.35 var(--font-body); max-width: 230px; white-space: normal; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
  .q-linelabel::before { border-top-color: #123B38 !important; }
  .q-primary { margin-top: 14px; padding: 14px; border-radius: 14px; background: #D7E7F3; color: #0f2f57; } .q-primary p { margin: 0 0 10px; }
  .q-primary .btn { background: #2E6E8E; border-color: #2E6E8E; color: #fff; }
  .q-tapnow { margin: 0; font-size: 0.95rem; }
  .q-more { gap: 6px 16px; } .q-more .linkbtn { color: var(--accent); font-weight: 600; font-size: 0.88rem; }
  .here-map.marking { outline: 3px solid #2E6E8E; outline-offset: -3px; cursor: crosshair; }
  .q-nav { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line); }
  .q-nav .linkbtn { color: var(--ink2); font-size: 0.85rem; }
  .here-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr); gap: 16px; align-items: start; }
  @media (max-width: 860px) { .here-grid { grid-template-columns: 1fr; } }
  .here-map { position: relative; height: 520px; border-radius: 18px; overflow: hidden; border: 1px solid var(--line); background: var(--surface2); }
  @media (max-width: 860px) { .here-map { height: 380px; } }
  .here-err { position: absolute; left: 12px; top: 12px; z-index: 500; background: var(--surface); padding: 8px 12px; border-radius: 10px; }
  .here-card { padding: 18px 20px; border-radius: 18px; background: var(--surface); border: 1px solid var(--line); }
  .here-card h3 { margin: 0 0 4px; font-size: 1.2rem; } .here-card h4 { margin: 14px 0 6px; font-size: 0.95rem; }
  .here-hint { margin: 0 0 12px; color: var(--ink2); line-height: 1.5; }
  .here-scale { margin: 0 0 10px; font-size: 0.82rem; color: var(--ink2); line-height: 1.45; }
  .here-facts { margin: 0; padding-left: 1.1rem; display: grid; gap: 6px; font-size: 0.92rem; line-height: 1.45; }
  .here-pj { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: 0.9rem; } .here-pj li { display: grid; gap: 1px; } .here-pj a { font-weight: 600; color: var(--accent); } .here-pj span { font-size: 0.8rem; color: var(--ink2); }
  .ob-k { font-weight: 600; color: var(--ink) !important; font-size: 0.85rem !important; } .ob-r { font-size: 0.75rem !important; color: #2f7a4a !important; }
  .here-none { margin: 0; color: var(--ink2); font-size: 0.9rem; }
  .here-acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; } .here-acts .btn { font-size: 0.88rem; }
  .here-form { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--line); display: grid; gap: 10px; }
  .here-fq { margin: 0; font-weight: 600; }
  .here-kinds { display: grid; gap: 4px; font-size: 0.9rem; } .here-kinds label { display: flex; gap: 8px; align-items: center; }
  .here-l { display: grid; gap: 4px; font-size: 0.85rem; color: var(--ink2); } .here-l textarea, .here-l input { font: inherit; font-size: 0.95rem; color: var(--ink); padding: 8px 10px; border-radius: 10px; border: 1px solid var(--line); background: var(--bg); }
  .here-fn { margin: 0; font-size: 0.8rem; color: var(--ink2); line-height: 1.45; }
  .here-msg { margin: 0; font-size: 0.85rem; color: var(--warm, #C0603A); } .here-ok { margin: 0; line-height: 1.5; }
  .here-key { margin-top: 8px; } .hk-bar { height: 10px; border-radius: 5px; }
  .hk-heat { background: linear-gradient(90deg, hsl(48,70%,82%), hsl(4,90%,48%)); } .hk-flood { background: linear-gradient(90deg, hsl(205,40%,86%), hsl(215,85%,42%)); } .hk-green { background: linear-gradient(90deg, hsl(90,25%,86%), hsl(130,65%,40%)); }
  .hk-l { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--ink2); margin-top: 4px; } .hk-n { margin: 6px 0 0; font-size: 0.78rem; color: var(--ink2); line-height: 1.4; }
  .pf-none { color: var(--ink2); grid-column: 1 / -1; margin: 0; }
  #pf-scope { margin-bottom: 4px; }
  .pf-missing { padding: 48px 0; }
  .pf + .site-foot2, .pf .pro-band { margin-top: 56px; }

  /* ---- The Lab overview */
  .lab-head { min-width: 0; } .lab-head h1 { max-width: 18ch; }
  .lab-search { width: 100%; box-sizing: border-box; }
  .lab-search { margin-top: 22px; max-width: 34rem; } .lab-search input { min-width: 0; flex: 1 1 auto; width: 0; }
  .lab-tools { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 36px 0 0; }
  @media (max-width: 860px) { .lab-tools { grid-template-columns: 1fr; } }
  .lab-tool { display: grid; gap: 8px; align-content: start; padding: 24px; border-radius: 20px; background: var(--surface); border: 1px solid var(--line); color: var(--ink); text-decoration: none; transition: border-color .15s, transform .15s; }
  .lab-tool:hover { border-color: var(--deep, #123B38); transform: translateY(-2px); }
  @media (prefers-reduced-motion: reduce) { .lab-tool, .lab-tool:hover { transition: none; transform: none; } }
  .lab-n { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; background: var(--deep, #123B38); color: #fff; font: 700 0.9rem var(--font-body); }
  .lab-tool b { font: 800 2rem/1.05 var(--font-display); letter-spacing: -0.02em; margin-top: 6px; }
  .lab-what { font-weight: 600; font-size: 1.05rem; }
  .lab-d { color: var(--ink2); line-height: 1.55; }
  .lab-go { margin-top: 8px; font-weight: 700; color: var(--accent); }
  .lab-path { margin: 56px 0 24px; padding: 28px; border-radius: 20px; background: var(--surface2); }
  .lab-path h2 { font-size: 1.6rem; margin: 0 0 14px; }
  .lab-path ol { margin: 0; padding-left: 1.3rem; display: grid; gap: 10px; color: var(--ink2); line-height: 1.5; max-width: 52rem; } .lab-path b { color: var(--ink); }
"""
write("assets/site.css", css.strip() + "\n")
write("assets/model.js", read(SRC, "model2.js"))

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Nunito:wght@700&family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600&display=swap">\n')
# Cloudflare Web Analytics: private visit counts for Robert, no cookies and no personal data
ANALYTICS = ("<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
             "data-cf-beacon='{\"token\": \"a92b6704e81e4aaba11a9f8a11832ae1\"}'></script><!-- End Cloudflare Web Analytics -->\n")
PAGES = [("", "Home"), ("involved/", "Get involved"), ("place/", "Place"), ("places/", "Places"), ("projects/", "Projects"), ("about/", "About"),
         ("lab/", "ThreadLab"), ("explore/", "Explore"), ("studio/", "Studio"), ("how-it-works/", "Method")]
# Two faces: everyone's side, and the professional side with the tools
NAV = [("", "Home"), ("places/", "Places"), ("involved/", "Get involved"), ("lab/", "ThreadLab")]
NAV_LAB = [("lab/", "Overview"), ("explore/", "Explore"), ("studio/", "Studio"), ("how-it-works/", "Method")]
PRO_PAGES = ("lab/", "explore/", "studio/", "how-it-works/")


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
            + FONTS + f'<link rel="stylesheet" href="{base}assets/site.css?v=17">\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css">\n' + APP(base) + f'<script>window.TL_DATA = "{DATA_URL}";</script>\n' + ANALYTICS + '</head>\n<body>\n')


def nav(base, here):
    # One top bar on every page; ThreadLab's pages add a row of tabs underneath
    lab = here in PRO_PAGES
    house = '<svg class="nav-home" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>'
    cur = "lab/" if lab else ("places/" if here == "place/" else "involved/" if here == "projects/" else here)
    links = "".join(f'<a href="{base}{p}"' + (' class="nav-lab"' if p == "lab/" else "") + (' aria-current="page"' if p == cur else "") + '>' + (house if p == "" else "") + f'{n}</a>' for p, n in NAV)
    tabs = ""
    if lab:
        tabs = ('  <nav class="lab-tabs" aria-label="ThreadLab"><span class="lab-tabs-k">ThreadLab</span>' +
                "".join(f'<a href="{base}{p}"' + (' aria-current="page"' if p == here else "") + f'>{n}</a>' for p, n in NAV_LAB) + '</nav>\n')
    return (f'<header class="wrap site-head" id="top">\n  <div class="topbar">\n    <a class="wordmark" href="{base}" translate="no"><svg class="wm-sym" viewBox="0 0 48 48" width="28" height="28" fill="none" stroke-width="4" stroke-linecap="round" aria-hidden="true"><path d="M4 8C14 8 18 24 28 24H35" stroke="#2E6E8E"/><path d="M4 24H28" stroke="#4C9A5B"/><path d="M4 40C14 40 18 24 28 24" stroke="#C0603A"/><circle cx="40" cy="24" r="5" fill="#123B38" stroke="none"/></svg><span>Threadlands</span></a>\n'
            f'    <div class="topright"><nav class="topnav" aria-label="Site">{links}</nav>'
            '<label class="lang-l"><span class="sr-only">Language</span><select id="lang" class="lang-sel" translate="no" aria-label="Language"><option value="en">English</option></select></label></div>\n  </div>\n' + tabs + '</header>\n')


def footer(base):
    col = lambda items: "".join(f'<a href="{base}{p}">{n}</a>' for p, n in items)
    return (f'<footer class="site-foot2">\n  <div class="wrap foot-grid">\n'
            f'    <div class="foot-brand"><a class="wordmark foot-wm" href="{base}" translate="no">Threadlands</a>'
            '<p>A civic climate map. See what&rsquo;s happening where you live, map what you notice, and explore what could change.</p></div>\n'
            f'    <nav aria-label="Get involved"><h2>Get involved</h2>{col([("involved/", "Places you stand with"), ("projects/", "Projects"), ("places/", "All places")])}</nav>\n'
            f'    <nav aria-label="ThreadLab"><h2>ThreadLab</h2>{col([("lab/", "Overview"), ("explore/", "Explore"), ("studio/", "Studio"), ("how-it-works/", "Method")])}</nav>\n'
            f'    <nav aria-label="About"><h2>About</h2>{col([("about/", "About Threadlands")])}</nav>\n'
            '  </div>\n  <div class="wrap foot-small">\n'
            '    <p>&copy; 2026 Robert Bartolucci. All rights reserved. Threadlands is created by Robert Bartolucci.</p>\n'
            '    <p>Data from OpenStreetMap, ESA WorldCover, Copernicus DEM, WorldPop, HydroBASINS, Landsat (USGS and NASA), Open-Meteo and GBIF.</p>\n'
            '  </div>\n</footer>\n')


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
for name in ("home", "involved", "place", "lab", "studio", "places", "projects", "how-it-works", "about"):
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
# Old addresses: Library, Rankings and Cities became Places
for old, new in (("library", "places"), ("rankings", "places"), ("cities", "places"), ("pro", "lab")):
    write(f"{old}/index.html", '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>Threadlands</title>'
          f'<link rel="canonical" href="../{new}/"><meta http-equiv="refresh" content="0; url=../{new}/">'
          f"<script>location.replace('../{new}/' + location.search + location.hash);</script></head>"
          f'<body><p><a href="../{new}/">Threadlands</a></p></body></html>\n')
print("built: index.html, explore/, library/, how-it-works/, about/, assets/site.css")
