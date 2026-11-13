# Threadlands place builder: core logic that needs only numpy.
# The notebook pastes this file in; tests run it here with synthetic data.
import math
from collections import deque
import numpy as np

# Average H3 hexagon area in km2 by resolution
H3_AREA = {3: 12393.4, 4: 1770.35, 5: 252.90, 6: 36.129, 7: 5.161, 8: 0.737, 9: 0.105}

# ESA WorldCover classes, grouped into the eight fractions Threadlands uses
WC_GROUPS = {
    10: 'tree', 20: 'shrub', 30: 'grass', 40: 'crop', 50: 'built', 60: 'bare',
    70: 'bare', 80: 'water', 90: 'wetland', 95: 'wetland', 100: 'grass',
}
FRACTIONS = ['built', 'tree', 'shrub', 'grass', 'crop', 'bare', 'water', 'wetland']


def choose_resolution(region_km2, max_cells=2500):
    """Finest H3 resolution whose hex count stays under max_cells."""
    best = 3
    for res in sorted(H3_AREA):
        if region_km2 / H3_AREA[res] <= max_cells:
            best = res
    return best


def auto_buffer_km(place_km2):
    """How much surrounding land to add so a city brings its farms, water and forest with it."""
    if place_km2 >= 20000:
        return 0.0
    if place_km2 >= 3000:
        return 10.0
    return float(min(40.0, max(12.0, 0.8 * math.sqrt(max(place_km2, 1.0)))))


def wc_fractions(labels, wc, n):
    """Share of each land cover group per hex.

    labels: int array, hex index per pixel (-1 outside every hex).
    wc: WorldCover class codes on the same grid (0 = no data).
    Hexes with no land cover data at all are treated as open water (sea outside the tiles)."""
    lab = labels.ravel()
    code = wc.ravel().astype(np.int64)
    ok = lab >= 0
    lab, code = lab[ok], code[ok]
    out = {k: np.zeros(n) for k in FRACTIONS}
    valid = code > 0
    total = np.bincount(lab[valid], minlength=n).astype(float)
    for c, g in WC_GROUPS.items():
        m = code == c
        if m.any():
            out[g] += np.bincount(lab[m], minlength=n)
    nodata = total == 0
    for k in FRACTIONS:
        with np.errstate(invalid='ignore', divide='ignore'):
            out[k] = np.where(total > 0, out[k] / np.maximum(total, 1), 0.0)
    out['water'] = np.where(nodata, 1.0, out['water'])
    return out, int(nodata.sum())


def hex_means(labels, values, n, valid_mask=None):
    """Mean of a raster per hex. Returns means and a flag for hexes with no valid pixels."""
    lab = labels.ravel()
    v = values.ravel().astype(float)
    ok = (lab >= 0) & np.isfinite(v)
    if valid_mask is not None:
        ok &= valid_mask.ravel()
    s = np.bincount(lab[ok], weights=v[ok], minlength=n)
    c = np.bincount(lab[ok], minlength=n)
    mean = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return mean, c == 0


def fill_missing(values, neighbors, missing):
    """Fill missing hex values with the mean of filled neighbours, repeating until stable."""
    v = np.array(values, dtype=float)
    miss = np.array(missing, dtype=bool)
    for _ in range(50):
        if not miss.any():
            break
        changed = False
        newv = v.copy()
        for i in np.where(miss)[0]:
            vals = [v[j] for j in neighbors[i] if not miss[j]]
            if vals:
                newv[i] = float(np.mean(vals))
                changed = True
        filled = miss & ~np.isnan(newv)
        v = newv
        miss = miss & ~filled
        if not changed:
            break
    v[np.isnan(v)] = 0.0
    return v


WATERWAY_WEIGHT = {'river': 1.0, 'canal': 0.7, 'stream': 0.5}


def waterway_hexes(ways, latlng_to_cell, idx, step_km, weight=WATERWAY_WEIGHT):
    """Mark hexes crossed by mapped rivers, canals and streams.

    ways: list of (kind, [(lat, lon), ...]) lines. latlng_to_cell: function (lat, lon) -> cell id.
    idx: dict cell id -> hex index. Each line is walked in steps of step_km so no hex is skipped.
    Returns a per-hex weight (river 1.0, canal 0.7, stream 0.5; the strongest one crossing wins)."""
    n = len(idx)
    out = np.zeros(n)
    for kind, pts in ways:
        w = weight.get(kind, 0.0)
        if w <= 0 or len(pts) < 1:
            continue
        for k in range(len(pts)):
            la0, lo0 = pts[k]
            la1, lo1 = pts[k + 1] if k + 1 < len(pts) else pts[k]
            dkm = math.hypot((la1 - la0) * 110.57, (lo1 - lo0) * 111.32 * math.cos(math.radians(la0)))
            steps = max(1, int(math.ceil(dkm / max(step_km, 1e-3))))
            for s in range(steps + 1):
                t = s / steps
                c = latlng_to_cell(la0 + (la1 - la0) * t, lo0 + (lo1 - lo0) * t)
                i = idx.get(c)
                if i is not None and w > out[i]:
                    out[i] = w
    return out


def flood_weights(neighbors, water_mask, elev, spacing_km, height_m=10.0, reach_km=None, open_water=None):
    """How flood-prone each hex is, from 0 to 1.

    A hex scores high when it is close to water (river, lake or sea hexes) and not much higher
    than that water. Uses a breadth-first search outward from every water hex, so each land hex
    is compared with the nearest water hex. This is a screening measure, not a flood model.
    open_water marks hexes that are mostly water; a source hex that is mostly land (a narrow
    river through a neighbourhood) is itself flood-prone and scores 1."""
    n = len(neighbors)
    if reach_km is None:
        reach_km = max(3.0, 2.5 * spacing_km)
    dist = np.full(n, -1, dtype=int)
    src_elev = np.zeros(n)
    q = deque()
    for i in range(n):
        if water_mask[i]:
            dist[i] = 0
            src_elev[i] = elev[i]
            q.append(i)
    while q:
        a = q.popleft()
        for j in neighbors[a]:
            if dist[j] < 0:
                dist[j] = dist[a] + 1
                src_elev[j] = src_elev[a]
                q.append(j)
    w = np.zeros(n)
    dist_km = np.full(n, np.inf)
    for i in range(n):
        if dist[i] < 0:
            continue
        dist_km[i] = dist[i] * spacing_km
        if water_mask[i]:
            if open_water is not None and not open_water[i]:
                w[i] = 1.0
            continue
        rel = elev[i] - src_elev[i]
        f_h = min(1.0, max(0.0, (height_m - rel) / height_m))
        f_d = min(1.0, max(0.0, 1.0 - dist_km[i] / reach_km))
        w[i] = f_h * f_d
    return w, dist_km


def pop_to_hexes(labels, built_px, count_on_target, parent_id, n):
    """Spread each population pixel over the finer pixels inside it, favouring built-up pixels,
    then add the result up per hex. Keeps every population pixel's total.

    labels: hex index per target pixel. built_px: True where WorldCover says built-up.
    count_on_target: the parent population pixel's count, repeated on each target pixel inside it.
    parent_id: an id for the parent population pixel of each target pixel (-1 where none)."""
    lab = labels.ravel()
    cnt = np.nan_to_num(count_on_target.ravel().astype(float), nan=0.0)
    cnt[cnt < 0] = 0.0
    par = parent_id.ravel()
    w = np.where(built_px.ravel(), 1.0, 0.1)
    ok = par >= 0
    m = int(par[ok].max()) + 1 if ok.any() else 1
    wsum = np.bincount(par[ok], weights=w[ok], minlength=m)
    share = np.zeros_like(w)
    share[ok] = w[ok] / np.maximum(wsum[par[ok]], 1e-12)
    pop_px = cnt * share
    keep = lab >= 0
    return np.bincount(lab[keep], weights=pop_px[keep], minlength=n)


def place_dict(name, query, kind, res, cells, sources, notes, generated):
    """Assemble the version-1 place file."""
    def rnd(a, d):
        return [round(float(x), d) for x in a]
    c = {
        'id': list(cells['id']),
        'lat': rnd(cells['lat'], 6), 'lng': rnd(cells['lng'], 6),
        'area': rnd(cells['area'], 4), 'inside': [int(bool(x)) for x in cells['inside']],
        'pop': [int(round(float(x))) for x in cells['pop']],
        'elev': rnd(cells['elev'], 1), 'flood': rnd(cells['flood'], 3),
        'water_km': [round(float(x), 2) if np.isfinite(x) else None for x in cells['water_km']],
        'nb': [list(map(int, l)) for l in cells['nb']],
        'poly': [[round(float(v), 6) for v in p] for p in cells['poly']],
    }
    for k in FRACTIONS:
        c[k] = rnd(cells[k], 3)
    if 'river' in cells:
        c['river'] = rnd(cells['river'], 2)
    return {
        'format': 'threadlands-place', 'version': 1,
        'name': name, 'query': query, 'kind': kind,
        'generated': generated, 'h3_res': res,
        'hex_km2': round(float(np.mean(cells['area'])), 4),
        'sources': sources, 'notes': notes, 'cells': c,
    }
