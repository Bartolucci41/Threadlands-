"""Shared land: which governments share each place's land, people and river basin.

For every place, assigns each grid cell to its state or province (Natural Earth admin-1) and,
in the United States, its county (Natural Earth admin-2), then counts people, area, city
residents and river-basin area per jurisdiction. Projects get the jurisdiction they sit in and
the people within 3 km of them, by jurisdiction, so a project that serves more than one
government shows up as a candidate joint project.

Usage: python3 -I pipeline/shared_land.py /path/to/natural-earth-vector/geojson
Writes data/shared/<slug>.json and data/shared/index.json
"""
import json, math, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/ne/natural-earth-vector/geojson'
PLACES = os.path.join(ROOT, 'data', 'places')
OUT = os.path.join(ROOT, 'data', 'shared')
os.makedirs(OUT, exist_ok=True)


def rings_of(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    return [np.asarray(r, dtype=float) for p in polys for r in p]


def load(fn, level):
    g = json.load(open(os.path.join(NE, fn)))
    feats = []
    for f in g['features']:
        p, geom = f['properties'], f['geometry']
        if not geom:
            continue
        rs = rings_of(geom)
        allpts = np.vstack(rs)
        if level == 'state':
            name = p.get('name_en') or p.get('name')
            kind = p.get('type_en') or 'State'
            country = p.get('admin')
            fid = p.get('adm1_code')
            region = None
        else:
            name = p.get('NAME_EN') or p.get('NAME')
            kind = p.get('TYPE_EN') or 'County'
            country = 'United States of America'
            fid = p.get('ADM2_CODE')
            region = p.get('REGION')
        # Common names people use, where Natural Earth uses the legal one
        if kind == 'Federal District' and country == 'Mexico':
            name = 'Mexico City'
        if kind in ('Federal District', 'District of Columbia') and name == 'Washington':
            name, kind = 'District of Columbia', 'Federal District'
        feats.append({'id': fid, 'name': name, 'type': kind, 'country': country, 'region': region, 'level': level,
                      'rings': rs, 'bbox': (allpts[:, 0].min(), allpts[:, 1].min(), allpts[:, 0].max(), allpts[:, 1].max())})
    return feats


def inside(rings, x, y):
    """Even-odd point-in-polygon over all rings (holes handled), vectorized over points and edges."""
    res = np.zeros(len(x), dtype=bool)
    for r in rings:
        a, b, c, d = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
        ok = (np.maximum(b, d) >= y.min()) & (np.minimum(b, d) <= y.max())
        a, b, c, d = a[ok], b[ok], c[ok], d[ok]
        if not len(a):
            continue
        dy = np.where(d != b, d - b, 1e-12)
        step = max(1, 4_000_000 // len(a))
        for s0 in range(0, len(x), step):
            X = x[s0:s0 + step, None]; Y = y[s0:s0 + step, None]
            cond = (b > Y) != (d > Y)
            xi = (c - a) * (Y - b) / dy + a
            res[s0:s0 + step] ^= (np.count_nonzero(cond & (X < xi), axis=1) % 2).astype(bool)
    return res


def assign(feats, lng, lat):
    out = np.full(len(lng), -1)
    bx = (lng.min(), lat.min(), lng.max(), lat.max())
    for k, f in enumerate(feats):
        b = f['bbox']
        if b[0] > bx[2] or b[2] < bx[0] or b[1] > bx[3] or b[3] < bx[1]:
            continue
        m = (lng >= b[0]) & (lng <= b[2]) & (lat >= b[1]) & (lat <= b[3]) & (out < 0)
        if not m.any():
            continue
        idx = np.where(m)[0]
        hit = inside(f['rings'], lng[idx], lat[idx])
        out[idx[hit]] = k
    return out


def main():
    states = load('ne_10m_admin_1_states_provinces.geojson', 'state')
    counties = load('ne_10m_admin_2_counties.geojson', 'county')
    projects = json.load(open(os.path.join(ROOT, 'data', 'projects.json'))).get('projects', [])
    index = {}
    for fn in sorted(os.listdir(PLACES)):
        if not fn.endswith('.json'):
            continue
        slug = fn[:-5]
        d = json.load(open(os.path.join(PLACES, fn)))
        c = d.get('cells') or {}
        if not c.get('lat'):
            continue
        lat = np.asarray(c['lat'], float); lng = np.asarray(c['lng'], float)
        pop = np.asarray([float(v or 0) for v in c['pop']]); area = np.asarray([float(v or 0) for v in c.get('area', [0] * len(lat))])
        ins = np.asarray([1 if v else 0 for v in c.get('inside', [0] * len(lat))])
        # The river basin that drains through the city, if traced
        bas = (d.get('regional') or {}).get('basin')
        bas = json.loads(bas) if isinstance(bas, str) else (bas or {})
        rr = bas.get('rings')
        rr = json.loads(rr) if isinstance(rr, str) else rr
        inbasin = np.zeros(len(lat), dtype=bool)
        if rr:
            rings = rr if isinstance(rr[0], list) else [rr]
            for ring in rings:
                pts = np.asarray(ring, float).reshape(-1, 2)          # lat, lng pairs
                poly = np.column_stack([pts[:, 1], pts[:, 0]])
                if len(poly) >= 3:
                    poly = np.vstack([poly, poly[:1]])
                    inbasin |= inside([poly], lng, lat)
        levels = [('state', states, assign(states, lng, lat))]
        if (d.get('country_code') or '').upper() == 'US':
            levels.append(('county', counties, assign(counties, lng, lat)))
        out = {'slug': slug, 'name': d.get('name'), 'basin_km2': round(float(bas.get('area_km2') or 0)) or None, 'levels': {}}
        for lvl, feats, ix in levels:
            rows = []
            for k in sorted(set(ix.tolist()) - {-1}):
                m = ix == k
                f = feats[k]
                rows.append({'id': f['id'], 'name': f['name'], 'type': f['type'], 'country': f['country'], 'region': f['region'],
                             'pop': int(pop[m].sum()), 'km2': round(float(area[m].sum())), 'city_pop': int(pop[m & (ins == 1)].sum()),
                             'basin_km2': round(float(area[m & inbasin].sum())) if inbasin.any() else None})
            rows.sort(key=lambda r: -r['pop'])
            tot = sum(r['pop'] for r in rows) or 1
            rows = [r for r in rows if r['pop'] / tot >= 0.002 or r['km2'] >= 50]
            out['levels'][lvl] = rows
        # Projects: where each sits, and who lives within 3 km, by jurisdiction
        pj = []
        lvl, feats, ix = levels[-1]
        for p in projects:
            if p.get('place') != slug or p.get('lat') is None:
                continue
            ky = 111.32; kx = 111.32 * math.cos(math.radians(p['lat']))
            dist = np.hypot((lat - p['lat']) * ky, (lng - p['lng']) * kx)
            near = dist <= 3
            home = int(ix[np.argmin(dist)]) if len(dist) else -1
            serves = []
            for k in sorted(set(ix[near].tolist()) - {-1}):
                n = int(pop[near & (ix == k)].sum())
                if n > 0:
                    serves.append({'name': feats[k]['name'], 'type': feats[k]['type'], 'pop': n})
            serves.sort(key=lambda r: -r['pop'])
            pj.append({'id': p['id'], 'in': feats[home]['name'] if home >= 0 else None, 'level': lvl, 'serves': serves})
        out['projects'] = pj
        json.dump(out, open(os.path.join(OUT, slug + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        top = out['levels'].get('county') or out['levels'].get('state') or []
        index[slug] = {'states': len(out['levels'].get('state') or []), 'counties': len(out['levels'].get('county') or []) or None,
                       'basin_states': len([r for r in (out['levels'].get('state') or []) if r.get('basin_km2')]),
                       'top': [r['name'] for r in top[:3]]}
        print(slug, index[slug])
    json.dump({'source': 'Natural Earth 10m admin-1 and admin-2 (US counties)', 'places': index},
              open(os.path.join(OUT, 'index.json'), 'w'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
