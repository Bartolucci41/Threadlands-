"""This week, measured from space: the latest clear Landsat pass over each place, compared with the same
time of year in earlier years.

  python3 pipeline/now.py plan [batch_size]   -> prints chunks=[...] for GitHub Actions
  python3 pipeline/now.py build "slug1,slug2" -> writes out-now/<slug>.json
  python3 pipeline/now.py publish             -> moves out-now/ into data/now/ and rebuilds data/now/index.json
"""
import datetime, glob, json, os, sys, time, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
np = clear_mask = hex_means = to_celsius = None   # loaded only when building, so plan and publish need no extra packages


def _load():
    global np, clear_mask, hex_means, to_celsius
    import numpy
    import heatcore
    np, clear_mask, hex_means, to_celsius = numpy, heatcore.clear_mask, heatcore.hex_means, heatcore.to_celsius

PLACES = os.path.join(ROOT, "data", "places")
NOW = os.path.join(ROOT, "data", "now")
OUT = os.path.join(ROOT, "out-now")
RECENT_DAYS = 45        # how far back to look for the latest clear pass
WINDOW_DAYS = 20        # earlier years: scenes within this many days of the same date
BASE_YEARS = 6          # how many earlier years to use for "usual"
MIN_CLEAR = 0.35        # share of land hexes that must be clear to count a pass


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def slugs():
    ix = json.load(open(os.path.join(ROOT, "data", "index.json")))
    return [e["slug"] for e in ix["places"]]


def plan(size=16):
    s = slugs()
    chunks = [",".join(s[i:i + size]) for i in range(0, len(s), size)]
    print("chunks=" + json.dumps(chunks))


class Grid:
    def __init__(self, d):
        c = d["cells"]
        self.n = len(c["id"])
        self.res = d["h3_res"]
        self.idx = {h: i for i, h in enumerate(c["id"])}
        pts = np.concatenate([np.asarray(p, dtype=float) for p in c["poly"]])
        self.bbox = [float(pts[1::2].min()), float(pts[0::2].min()), float(pts[1::2].max()), float(pts[0::2].max())]
        self.land = np.asarray(c["water"], dtype=float) < 0.5
        px_m = (d["hex_km2"] / 60) ** 0.5 * 1000
        self.factor = max(3, int(round(px_m / 30)))


def read_scene(item, g):
    """Mean clear-sky surface temperature (deg C) per hex for one Landsat scene, or None."""
    import h3, planetary_computer, pyproj, rasterio
    from affine import Affine
    from rasterio.enums import Resampling
    from rasterio.windows import Window, from_bounds
    signed = planetary_computer.sign(item)
    with rasterio.open(signed.assets["lwir11"].href) as src:
        to_crs = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        b = g.bbox
        xs, ys = to_crs.transform([b[0], b[2], b[0], b[2]], [b[1], b[1], b[3], b[3]])
        win = from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
        win = win.intersection(Window(0, 0, src.width, src.height)).round_offsets().round_lengths()
        oh, ow = max(1, int(win.height // g.factor)), max(1, int(win.width // g.factor))
        st = src.read(1, window=win, out_shape=(oh, ow), resampling=Resampling.nearest)
        wt = src.window_transform(win) * Affine.scale(win.width / ow, win.height / oh)
        crs = src.crs
    with rasterio.open(signed.assets["qa_pixel"].href) as q:
        qa = q.read(1, window=win, out_shape=(oh, ow), resampling=Resampling.nearest)
    lst = to_celsius(st)
    ok = clear_mask(qa) & np.isfinite(lst)
    rr, cc = np.mgrid[0:oh, 0:ow]
    x = wt.c + (cc + 0.5) * wt.a
    y = wt.f + (rr + 0.5) * wt.e
    lon, la = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(x.ravel(), y.ravel())
    b = g.bbox
    inb = (lon >= b[0]) & (lon <= b[2]) & (la >= b[1]) & (la <= b[3]) & ok.ravel()
    hx = np.full(lon.shape, -1, dtype=np.int64)
    for j in np.flatnonzero(inb):
        hx[j] = g.idx.get(h3.latlng_to_cell(la[j], lon[j], g.res), -1)
    return hex_means(hx, lst, ok, g.n)


def search(cat, bbox, start, end, max_cloud):
    found = cat.search(collections=["landsat-c2-l2"], bbox=bbox, datetime=f"{start:%Y-%m-%d}/{end:%Y-%m-%d}",
                       query={"eo:cloud_cover": {"lt": max_cloud}, "platform": {"in": ["landsat-8", "landsat-9"]}}, max_items=200)
    return [it for it in found.items() if "lwir11" in it.assets]


def overlap(it, bbox):
    b = it.bbox
    w = max(0.0, min(b[2], bbox[2]) - max(b[0], bbox[0]))
    h = max(0.0, min(b[3], bbox[3]) - max(b[1], bbox[1]))
    return w * h / max(1e-9, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))


def build_one(slug, cat):
    d = json.load(open(os.path.join(PLACES, slug + ".json")))
    g = Grid(d)
    today = utcnow().date()
    land_n = max(1, int(g.land.sum()))
    # 1. The latest pass that saw enough of the place through the clouds
    recent = search(cat, g.bbox, today - datetime.timedelta(days=RECENT_DAYS), today, 40)
    recent = [it for it in recent if overlap(it, g.bbox) > 0.3]
    recent.sort(key=lambda it: it.datetime, reverse=True)
    now, when, scene = None, None, None
    for it in recent[:6]:
        m = read_scene(it, g)
        if np.isfinite(m[g.land]).sum() >= MIN_CLEAR * land_n:
            now, when, scene = m, it.datetime, it.id
            break
    if now is None:
        return {"slug": slug, "status": "no clear pass", "checked": today.isoformat(), "scenes_tried": min(6, len(recent))}
    # 2. Usual: passes within a few weeks of the same date in earlier years
    stack, used = [], []
    for k in range(1, BASE_YEARS + 1):
        try:
            mid = when.date().replace(year=when.year - k)
        except ValueError:   # 29 February
            mid = when.date().replace(year=when.year - k, day=28)
        cands = [it for it in search(cat, g.bbox, mid - datetime.timedelta(days=WINDOW_DAYS), mid + datetime.timedelta(days=WINDOW_DAYS), 25)
                 if overlap(it, g.bbox) > 0.3]
        cands.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
        for it in cands[:2]:
            try:
                m = read_scene(it, g)
            except Exception as e:
                print("  skipped", it.id, e)
                continue
            if np.isfinite(m[g.land]).sum() >= 0.2 * land_n:
                stack.append(m)
                used.append(it.datetime.strftime("%Y-%m-%d"))
    if len(stack) < 2:
        return {"slug": slug, "status": "not enough past passes", "checked": today.isoformat(), "date": when.strftime("%Y-%m-%d")}
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        usual = np.nanmedian(np.vstack(stack), axis=0)
        nobs = np.sum(np.isfinite(np.vstack(stack)), axis=0)
    anom = now - usual
    anom[nobs < 2] = np.nan
    land_ok = g.land & np.isfinite(anom)
    built = np.asarray(d["cells"]["built"], dtype=float) >= 0.25
    def med(mask):
        v = anom[mask]
        return round(float(np.median(v)), 2) if len(v) >= 5 else None
    rnd = lambda a, k: [round(float(v), k) if np.isfinite(v) else None for v in a]
    return {
        "slug": slug, "status": "ok", "checked": today.isoformat(), "date": when.strftime("%Y-%m-%d"), "scene": scene,
        "usual_dates": used, "usual_scenes": len(used),
        "land_anom": med(land_ok), "built_anom": med(land_ok & built), "land_now": round(float(np.nanmedian(now[land_ok])), 1),
        "clear_share": round(float(land_ok.sum()) / land_n, 2),
        # Thin cloud, fog or haze that slips past the cloud mask reads as cold ground, so flag readings that look off
        "uncertain": bool(med(land_ok) is None or abs(med(land_ok)) > 10 or float(land_ok.sum()) / land_n < 0.5 or len(used) < 4),
        "cells": {"now": rnd(now, 1), "anom": rnd(anom, 1)},
        "source": "Landsat 8-9 Collection 2 surface temperature (USGS/NASA), via Microsoft Planetary Computer",
    }


def build(chunk):
    _load()
    import planetary_computer, pystac_client
    os.makedirs(OUT, exist_ok=True)
    os.environ.update({"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "4", "GDAL_HTTP_RETRY_DELAY": "2"})
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    for slug in [s for s in chunk.split(",") if s]:
        t0 = time.time()
        try:
            r = build_one(slug, cat)
        except Exception as e:
            traceback.print_exc()
            r = {"slug": slug, "status": "failed", "error": repr(e)[:300], "checked": utcnow().date().isoformat()}
        json.dump(r, open(os.path.join(OUT, slug + ".json"), "w"), separators=(",", ":"))
        print(f"{slug}: {r['status']} {r.get('date', '')} land {r.get('land_anom')} in {(time.time() - t0) / 60:.1f} min", flush=True)


def publish():
    os.makedirs(NOW, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "**", "*.json"), recursive=True):
        r = json.load(open(f))
        dest = os.path.join(NOW, r["slug"] + ".json")
        if r.get("status") == "ok":
            json.dump(r, open(dest, "w"), separators=(",", ":"))
        elif os.path.exists(dest):
            # Keep the last good reading, but note that this week's check found nothing new
            old = json.load(open(dest))
            old["last_check"] = {"checked": r.get("checked"), "status": r.get("status")}
            json.dump(old, open(dest, "w"), separators=(",", ":"))
    names = {e["slug"]: e for e in json.load(open(os.path.join(ROOT, "data", "index.json")))["places"]}
    rows = []
    for f in sorted(glob.glob(os.path.join(NOW, "*.json"))):
        if f.endswith("index.json"):
            continue
        r = json.load(open(f))
        e = names.get(r["slug"])
        if not e or r.get("status") != "ok":
            continue
        rows.append({"slug": r["slug"], "name": e["name"], "country": e["country"], "date": r["date"],
                     "land_anom": r.get("land_anom"), "built_anom": r.get("built_anom"), "land_now": r.get("land_now"),
                     "uncertain": bool(r.get("uncertain"))})
    json.dump({"format": "threadlands-now", "updated": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "places": rows},
              open(os.path.join(NOW, "index.json"), "w"), separators=(",", ":"))
    print(f"now index has {len(rows)} places")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        plan(int(sys.argv[2]) if len(sys.argv) > 2 else 16)
    elif cmd == "build":
        build(sys.argv[2])
    elif cmd == "publish":
        publish()
