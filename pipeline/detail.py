# Threadlands block-level detail: splits every hex inside a place into small cells (H3 resolution 10,
# about 1.5 hectares, roughly a city block) and measures each one from satellite data at full resolution.
#
#   python3 pipeline/detail.py mexico-city [bologna ...]
#
# Reads data/places/<slug>.json and writes data/detail/<slug>/index.json plus one tile file per
# H3 resolution-6 area (about 36 km2). The website loads only the tiles in view when you zoom in.
#
# Each cell gets:
#   land cover shares from ESA WorldCover (10 m pixels: about 150 per cell)
#   surface heat from Landsat 8 and 9 (30 m), as the departure from typical land that day, median over clear scenes
#   people, by sharing the parent hex's WorldPop count in proportion to built-up land
# The regional scores still run on the place's own hexes; the detail sharpens the map and where things are.
import json, math, os, sys, time, datetime, warnings
import numpy as np
import h3
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.windows import from_bounds as window_from_bounds, Window
from rasterio.enums import Resampling
from shapely.geometry import Polygon
import pyproj
import pystac_client, planetary_computer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = 10            # about 0.015 km2 per cell
TILE_RES = 6        # tiles of about 36 km2
MAX_PX = 60_000_000 # cap on the 10 m grid; coarser pixels above this
WC_GROUPS = {10: 'tree', 20: 'shrub', 30: 'grass', 40: 'crop', 50: 'built', 60: 'bare',
             70: 'bare', 80: 'water', 90: 'wetland', 95: 'wetland', 100: 'grass'}
GROUPS = ['built', 'tree', 'shrub', 'grass', 'crop', 'bare', 'water', 'wetland']
ST_SCALE, ST_OFFSET = 0.00341802, 149.0
QA_BAD = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def season_for(lat):
    if lat >= 23.5:
        return [6, 7, 8]
    if lat <= -23.5:
        return [12, 1, 2]
    return list(range(1, 13))


def build(slug):
    t0 = time.time()
    place = json.load(open(os.path.join(ROOT, 'data', 'places', slug + '.json')))
    C = place['cells']
    base_res = int(place['h3_res'])
    if base_res >= RES:
        log(f'{slug}: hexes are already at resolution {base_res}; no detail needed.')
        return
    inside = [i for i, v in enumerate(C['inside']) if int(v)]
    parents = [C['id'][i] for i in inside]
    base_pop = {C['id'][i]: float(C['pop'][i] or 0) for i in inside}
    cells, parent_of = [], []
    for p in parents:
        for c in h3.cell_to_children(p, RES):
            cells.append(c); parent_of.append(p)
    n = len(cells)
    lat = np.zeros(n); lng = np.zeros(n)
    for i, c in enumerate(cells):
        lat[i], lng[i] = h3.cell_to_latlng(c)
    log(f'{slug}: {len(parents):,} hexes inside the place -> {n:,} detail cells at resolution {RES}.')

    # A pixel grid over the place, each pixel labelled with its cell
    pad = 0.002
    minx, maxx, miny, maxy = lng.min() - pad, lng.max() + pad, lat.min() - pad, lat.max() + pad
    kx = 111.32 * math.cos(math.radians((miny + maxy) / 2)); ky = 110.57
    px_km = 0.010
    W = int(math.ceil((maxx - minx) * kx / px_km)); H = int(math.ceil((maxy - miny) * ky / px_km))
    if W * H > MAX_PX:
        s = math.sqrt(W * H / MAX_PX); W, H = int(W / s), int(H / s)
    GT = transform_from_bounds(minx, miny, maxx, maxy, W, H)
    log(f'Grid {W} x {H} pixels, about {(maxx - minx) * kx / W * 1000:.0f} m each.')
    shapes = ((Polygon([(lo, la) for la, lo in h3.cell_to_boundary(c)]), i) for i, c in enumerate(cells))
    LABELS = rasterize(shapes, out_shape=(H, W), transform=GT, fill=-1, dtype='int32')

    def paint(href, dest, resampling):
        with rasterio.open(href) as src:
            sb = src.bounds
            ib = (max(minx, sb.left), max(miny, sb.bottom), min(maxx, sb.right), min(maxy, sb.top))
            if ib[0] >= ib[2] or ib[1] >= ib[3]:
                return
            c0 = int(round((ib[0] - minx) / (maxx - minx) * W)); c1 = int(round((ib[2] - minx) / (maxx - minx) * W))
            r0 = int(round((maxy - ib[3]) / (maxy - miny) * H)); r1 = int(round((maxy - ib[1]) / (maxy - miny) * H))
            if c1 <= c0 or r1 <= r0:
                return
            win = window_from_bounds(*ib, transform=src.transform)
            arr = src.read(1, window=win, out_shape=(r1 - r0, c1 - c0), resampling=resampling)
            ok = np.ones(arr.shape, dtype=bool) if src.nodata is None else arr != src.nodata
            dest[r0:r1, c0:c1][ok] = arr[ok]

    cat = pystac_client.Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=planetary_computer.sign_inplace)
    BBOX = [minx, miny, maxx, maxy]

    # Land cover
    items = list(cat.search(collections=['esa-worldcover'], bbox=BBOX).items())
    v2 = [it for it in items if str(it.properties.get('esa_worldcover:product_version', '')).startswith('2')]
    items = v2 or items
    WC = np.zeros((H, W), dtype=np.uint8)
    for it in items:
        paint(it.assets['map'].href, WC, Resampling.nearest)
    lab = LABELS.ravel(); code = WC.ravel().astype(np.int64); ok = (lab >= 0) & (code > 0)
    total = np.bincount(lab[ok], minlength=n).astype(float)
    FR = {g: np.zeros(n) for g in GROUPS}
    for cval, g in WC_GROUPS.items():
        m = ok & (code == cval)
        if m.any():
            FR[g] += np.bincount(lab[m], minlength=n)
    for g in GROUPS:
        FR[g] = np.where(total > 0, FR[g] / np.maximum(total, 1), 0.0)
    FR['water'] = np.where(total == 0, 1.0, FR['water'])
    del WC
    log(f'Land cover: {len(items)} tiles.')

    # Surface heat: Landsat thermal, each scene as departures from that day's typical land, then the median
    months = season_for(float(np.median(lat)))
    found = cat.search(collections=['landsat-c2-l2'], bbox=BBOX, datetime='2021-01-01/2025-12-31',
                       query={'eo:cloud_cover': {'lt': 25}, 'platform': {'in': ['landsat-8', 'landsat-9']}}, max_items=600)
    scenes = [it for it in found.items() if it.datetime.month in months and 'lwir11' in it.assets]

    def overlap(it):
        b = it.bbox
        w = max(0.0, min(b[2], maxx) - max(b[0], minx)); h = max(0.0, min(b[3], maxy) - max(b[1], miny))
        return w * h / max(1e-9, (maxx - minx) * (maxy - miny))
    scenes.sort(key=lambda it: it.properties.get('eo:cloud_cover', 100) - 40 * overlap(it))
    scenes = scenes[:14]
    stack = []
    land = FR['water'] < 0.5
    for k, it in enumerate(scenes, 1):
        try:
            s = planetary_computer.sign(it)
            with rasterio.open(s.assets['lwir11'].href) as src:
                tr = pyproj.Transformer.from_crs('EPSG:4326', src.crs, always_xy=True)
                xs, ys = tr.transform([minx, maxx, minx, maxx], [miny, miny, maxy, maxy])
                win = window_from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
                win = win.intersection(Window(0, 0, src.width, src.height)).round_offsets().round_lengths()
                st = src.read(1, window=win)
                wt = src.window_transform(win); crs = src.crs
            with rasterio.open(s.assets['qa_pixel'].href) as q:
                qa = q.read(1, window=win)
        except Exception as e:
            log(f'  skipped a scene: {e}')
            continue
        tc = st.astype(float) * ST_SCALE + ST_OFFSET - 273.15
        good = ((qa.astype(np.int64) & QA_BAD) == 0) & (st > 0)
        rr, cc = np.nonzero(good)
        if len(rr) < 100:
            continue
        x = wt.c + (cc + 0.5) * wt.a; y = wt.f + (rr + 0.5) * wt.e
        lon, la = pyproj.Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform(x, y)
        gc = ((np.asarray(lon) - minx) / (maxx - minx) * W).astype(np.int64)
        gr = ((maxy - np.asarray(la)) / (maxy - miny) * H).astype(np.int64)
        inb = (gc >= 0) & (gc < W) & (gr >= 0) & (gr < H)
        cell = np.full(len(rr), -1, dtype=np.int64)
        cell[inb] = LABELS[gr[inb], gc[inb]]
        m = cell >= 0
        if m.sum() < 100:
            continue
        sm = np.bincount(cell[m], weights=tc[rr[m], cc[m]], minlength=n)
        ct = np.bincount(cell[m], minlength=n)
        means = np.where(ct > 0, sm / np.maximum(ct, 1), np.nan)
        lv = means[land & np.isfinite(means)]
        if len(lv) < 50:
            continue
        stack.append(means - np.median(lv))
        log(f'  heat scene {k}/{len(scenes)} {it.datetime:%Y-%m-%d}: {int(np.isfinite(means).sum()):,} cells')
    if stack:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            HEAT = np.nanmedian(np.vstack(stack), axis=0)
    else:
        HEAT = np.full(n, np.nan)
    log(f'Heat: {len(stack)} clear scenes used.')

    # People: each parent hex's count shared by built-up land
    POP = np.zeros(n)
    by_parent = {}
    for i, p in enumerate(parent_of):
        by_parent.setdefault(p, []).append(i)
    for p, idx in by_parent.items():
        w = np.array([FR['built'][i] + 0.05 for i in idx])
        POP[idx] = base_pop.get(p, 0.0) * w / w.sum()

    # Tiles
    out_dir = os.path.join(ROOT, 'data', 'detail', slug)
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    PIDX = {h: i for i, h in enumerate(C['id'])}
    tiles = {}
    for i, c in enumerate(cells):
        tiles.setdefault(h3.cell_to_parent(c, TILE_RES), []).append(i)
    index = []
    for t, idx in sorted(tiles.items()):
        idx = np.array(idx)
        def pct(a):
            return [int(round(100 * float(v))) for v in a[idx]]
        tile = {
            'lat': [round(float(v), 5) for v in lat[idx]], 'lng': [round(float(v), 5) for v in lng[idx]],
            'built': pct(FR['built']), 'tree': pct(FR['tree']), 'grass': pct(FR['grass'] + FR['shrub']),
            'crop': pct(FR['crop']), 'water': pct(FR['water']), 'wetland': pct(FR['wetland']), 'bare': pct(FR['bare']),
            'heat': [round(float(v), 1) if np.isfinite(v) else None for v in HEAT[idx]],
            'pop': [int(round(float(v))) for v in POP[idx]],
            'parent': [PIDX[parent_of[i]] for i in idx],   # index of the place hex each cell sits in
        }
        with open(os.path.join(out_dir, t + '.json'), 'w') as f:
            json.dump(tile, f, separators=(',', ':'))
        index.append({'id': t, 'n': int(len(idx)), 'bbox': [round(float(lng[idx].min()), 5), round(float(lat[idx].min()), 5),
                                                         round(float(lng[idx].max()), 5), round(float(lat[idx].max()), 5)]})
    meta = {'slug': slug, 'res': RES, 'cell_km2': round(h3.average_hexagon_area(RES, unit='km^2'), 4), 'cells': n,
            'heat_scenes': len(stack), 'built': datetime.date.today().isoformat(), 'tiles': index,
            'sources': ['Land cover: ESA WorldCover 2021 v200 10 m (CC BY 4.0), via Microsoft Planetary Computer',
                        'Surface temperature: Landsat 8-9 Collection 2 (USGS/NASA), via Microsoft Planetary Computer',
                        'People: WorldPop 2020 per hex, shared by built-up land']}
    with open(os.path.join(out_dir, 'index.json'), 'w') as f:
        json.dump(meta, f, separators=(',', ':'))
    log(f'{slug}: {n:,} cells in {len(index)} tiles, {time.time() - t0:.0f} s.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['all']:
        idx = json.load(open(os.path.join(ROOT, 'data', 'index.json')))
        args = [p['slug'] for p in sorted(idx['places'], key=lambda p: -(p.get('pop') or 0))
                if not os.path.exists(os.path.join(ROOT, 'data', 'detail', p['slug'], 'index.json'))]
        log(f'{len(args)} places without detail yet.')
    failed = []
    for s in args:
        try:
            build(s)
        except Exception as e:   # one bad place should not stop the rest
            log(f'{s}: FAILED: {e}')
            failed.append(s)
    if failed:
        log('Failed: ' + ', '.join(failed))
