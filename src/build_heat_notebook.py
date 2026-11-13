import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
core = open(os.path.join(HERE, 'heatcore.py')).read()

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}

def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(True)}

cells = []
cells.append(md("""
# Threadlands satellite heat check

Adds measured surface temperature from space to a Threadlands **place file**, so the page can check its heat estimates against reality.

**How to use it**
1. In the menu, choose **Runtime → Run all**.
2. When asked, choose a place file you already have (a file ending in `.threadlands.json`).
3. It takes about 3 to 10 minutes. Your browser then downloads the same file with `-heat` added to its name.
4. Open Threadlands and load the new file, or send it over to be built into the site.

**Where the data comes from**
Landsat 8 and 9 Collection 2 surface temperature (USGS and NASA), 2021 to 2025, through Microsoft Planetary Computer.
Only clear-sky pixels are used. Outside the tropics it uses the three hottest months; inside the tropics, the whole year.
Each scene is compared with its own typical land temperature, so scenes from cooler and hotter days can be pooled.
"""))

cells.append(code("""
# 1. Install the free tools (only needed once per session)
!pip -q install h3 rasterio pystac-client planetary-computer pyproj
"""))

cells.append(code("# 2. Core logic (the same code Threadlands is tested with)\n" + core))

cells.append(code('''
# 3. Choose your place file
import json, os, time, datetime
import numpy as np
PLACE_FILE = None   # or a path such as "milan.threadlands.json"
if PLACE_FILE is None:
    try:
        from google.colab import files
        up = files.upload()
        PLACE_FILE = next(iter(up))
    except ImportError:
        raise SystemExit("Set PLACE_FILE to the path of your place file.")
place = json.load(open(PLACE_FILE))
C = place["cells"]
N, RES = len(C["id"]), place["h3_res"]
IDX = {h: i for i, h in enumerate(C["id"])}
pts = np.concatenate([np.asarray(p, dtype=float) for p in C["poly"]])
plat, plng = pts[0::2], pts[1::2]
BBOX = [float(plng.min()), float(plat.min()), float(plng.max()), float(plat.max())]
MONTHS, SEASON = season_for(float(np.median(C["lat"])))
print(f"{place['name']}: {N:,} hexes; season used: {SEASON}")
'''))

cells.append(code('''
# 4. Find clear Landsat 8 and 9 scenes over the place
import pystac_client, planetary_computer
MAX_SCENES = 20
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
found = cat.search(collections=["landsat-c2-l2"], bbox=BBOX, datetime="2021-01-01/2025-12-31",
                   query={"eo:cloud_cover": {"lt": 30}, "platform": {"in": ["landsat-8", "landsat-9"]}}, max_items=800)
items = [it for it in found.items() if it.datetime.month in MONTHS and "lwir11" in it.assets]
def overlap(it):
    b = it.bbox
    w = max(0.0, min(b[2], BBOX[2]) - max(b[0], BBOX[0])); h = max(0.0, min(b[3], BBOX[3]) - max(b[1], BBOX[1]))
    return w * h / max(1e-9, (BBOX[2] - BBOX[0]) * (BBOX[3] - BBOX[1]))
items.sort(key=lambda it: (it.properties.get("eo:cloud_cover", 100) - 40 * overlap(it)))
items = items[:MAX_SCENES]
print(f"Using {len(items)} scenes:", ", ".join(sorted(it.datetime.strftime("%Y-%m-%d") for it in items)))
'''))

cells.append(code('''
# 5. Read each scene and average the clear pixels in every hex
import rasterio, h3, pyproj
from rasterio.windows import from_bounds, Window
from rasterio.enums import Resampling
from affine import Affine
os.environ.update({"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "4", "GDAL_HTTP_RETRY_DELAY": "2"})
px_m = (place["hex_km2"] / 60) ** 0.5 * 1000          # about 60 samples per hex
FACTOR = max(3, int(round(px_m / 30)))                   # Landsat thermal is about 100 m, so at least 90 m
stack, used = [], []
for k, it in enumerate(items):
    t0 = time.time()
    try:
        signed = planetary_computer.sign(it)
        with rasterio.open(signed.assets["lwir11"].href) as src:
            to_crs = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            xs, ys = to_crs.transform([BBOX[0], BBOX[2], BBOX[0], BBOX[2]], [BBOX[1], BBOX[1], BBOX[3], BBOX[3]])
            win = from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
            win = win.intersection(Window(0, 0, src.width, src.height)).round_offsets().round_lengths()
            oh, ow = max(1, int(win.height // FACTOR)), max(1, int(win.width // FACTOR))
            st = src.read(1, window=win, out_shape=(oh, ow), resampling=Resampling.nearest)
            wt = src.window_transform(win) * Affine.scale(win.width / ow, win.height / oh)
            crs = src.crs
        with rasterio.open(signed.assets["qa_pixel"].href) as q:
            qa = q.read(1, window=win, out_shape=(oh, ow), resampling=Resampling.nearest)
    except Exception as e:
        print(f"  skipped {it.id}: {e}")
        continue
    lst = to_celsius(st)
    ok = clear_mask(qa) & np.isfinite(lst)
    rr, cc = np.mgrid[0:oh, 0:ow]
    x = wt.c + (cc + 0.5) * wt.a
    y = wt.f + (rr + 0.5) * wt.e
    to_ll = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, la = to_ll.transform(x.ravel(), y.ravel())
    inb = (lon >= BBOX[0]) & (lon <= BBOX[2]) & (la >= BBOX[1]) & (la <= BBOX[3])
    hx = np.full(lon.shape, -1, dtype=np.int64)
    for j in np.flatnonzero(inb):
        hx[j] = IDX.get(h3.latlng_to_cell(la[j], lon[j], RES), -1)
    means = hex_means(hx, lst, ok, N)
    got = int(np.isfinite(means).sum())
    if got >= max(10, 0.05 * N):
        stack.append(means); used.append(it.datetime.strftime("%Y-%m-%d"))
    print(f"  {k + 1}/{len(items)} {it.datetime:%Y-%m-%d}: {got:,} hexes clear ({time.time() - t0:.0f} s)")
if not stack:
    raise SystemExit("No clear scenes covered this place. Try again later or raise MAX_SCENES.")
LAND = np.asarray(C["water"], dtype=float) < 0.5
LST, LST_REL, NOBS = combine(np.vstack(stack), LAND)
print(f"{len(stack)} scenes used; {np.isfinite(LST_REL).sum():,} of {N:,} hexes have a reading.")
'''))

cells.append(code('''
# 6. Save the place file with the heat readings added
def rnd(a, d):
    return [round(float(v), d) if np.isfinite(v) else None for v in a]
C["lst"] = rnd(LST, 1)
C["lst_rel"] = rnd(LST_REL, 2)
C["lst_n"] = [int(v) for v in NOBS]
place["heat_check"] = {
    "source": "Landsat 8-9 Collection 2 surface temperature (USGS/NASA), via Microsoft Planetary Computer",
    "season": SEASON, "years": "2021-2025", "scenes": len(used), "dates": used,
    "note": "Daytime land surface temperature, about 10:30 local time, clear skies only.",
}
place["sources"] = [s for s in place.get("sources", []) if not s.startswith("Surface temperature")] + \
    ["Surface temperature: Landsat 8-9 Collection 2 (USGS/NASA), via Microsoft Planetary Computer"]
stem = os.path.basename(PLACE_FILE).replace(".threadlands.json", "").replace(".json", "")
OUT = (stem if stem.endswith("-heat") else stem + "-heat") + ".threadlands.json"
with open(OUT, "w") as f:
    json.dump(place, f, separators=(",", ":"))
print(f"Saved {OUT}")
b = np.asarray(C["built"], float); t = np.asarray(C["tree"], float); cr = np.asarray(C["crop"], float)
for name, m in [("Mostly built-up", b >= 0.5), ("Mostly tree cover", t >= 0.5), ("Mostly cropland", cr >= 0.5)]:
    v = LST_REL[m & np.isfinite(LST_REL)]
    if len(v):
        print(f"  {name}: {np.median(v):+.1f} C compared with typical land ({len(v)} hexes)")
try:
    from google.colab import files
    files.download(OUT)
except Exception:
    print("Not running in Colab: the file is saved next to this notebook.")
'''))

nb = {"cells": cells, "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}
out = os.path.join(HERE, "threadlands-heat-check.ipynb")
json.dump(nb, open(out, "w"), indent=1)
for i, c in enumerate(cells):
    if c["cell_type"] == "code":
        compile("".join(l for l in c["source"] if not l.lstrip().startswith("!")), f"cell{i}", "exec")
print("written and compiles:", out)
