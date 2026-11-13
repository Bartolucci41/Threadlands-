import json, math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import placecore as pc

ok = 0
def check(cond, msg):
    global ok
    if not cond:
        raise AssertionError(msg)
    ok += 1

# choose_resolution / auto_buffer
check(pc.choose_resolution(180 + 2 * 3.14 * 13 * 13) == 8, 'city-size region should use res 8')
check(pc.choose_resolution(513000) == 5, 'Thailand-size should use res 5')
check(pc.choose_resolution(424000) == 5, 'California-size should use res 5')
check(pc.choose_resolution(1960000) == 4, 'Mexico-size should use res 4')
check(pc.auto_buffer_km(182) == 12.0, 'small city buffer floor')
check(pc.auto_buffer_km(1500) > 25, 'mid city buffer')
check(pc.auto_buffer_km(50000) == 0.0, 'no buffer for states')

# wc_fractions on a 3-hex toy grid
labels = np.array([[0, 0, 1, 1], [0, 0, 1, 1], [2, 2, -1, -1]])
wc = np.array([[50, 50, 40, 10], [50, 10, 40, 40], [0, 0, 80, 80]])
fr, nod = pc.wc_fractions(labels, wc, 3)
check(abs(fr['built'][0] - 0.75) < 1e-9 and abs(fr['tree'][0] - 0.25) < 1e-9, 'hex 0 fractions')
check(abs(fr['crop'][1] - 0.75) < 1e-9, 'hex 1 crop')
check(fr['water'][2] == 1.0 and nod == 1, 'no-data hex becomes water')
check(all(abs(sum(fr[k][i] for k in pc.FRACTIONS) - 1) < 1e-9 for i in range(3)), 'fractions sum to 1')

# hex_means + fill_missing
vals = np.array([[10, 12, 30, 30], [10, 12, 30, 30], [np.nan, np.nan, 5, 5]])
mean, miss = pc.hex_means(labels, vals, 3)
check(abs(mean[0] - 11) < 1e-9 and miss[2], 'hex means and missing flag')
filled = pc.fill_missing(mean, [[1, 2], [0, 2], [0, 1]], miss)
check(abs(filled[2] - 20.5) < 1e-9, 'fill missing from neighbours')

# flood_weights on a line of hexes: water at 0, rising land
nb = [[1], [0, 2], [1, 3], [2, 4], [3]]
w, dkm = pc.flood_weights(nb, [True, False, False, False, False], np.array([5, 6, 9, 30, 6.0]), 1.0, reach_km=3.5)
check(w[0] == 0 and w[1] > w[2] > 0 and w[3] == 0, 'flood weight falls with height and distance: %s' % w)
check(w[4] == 0, 'beyond reach scores zero')

# pop_to_hexes conserves totals and favours built pixels
labels2 = np.array([[0, 0, 1, 1]])
built = np.array([[True, False, False, False]])
count = np.array([[100, 100, 40, 40]])
parent = np.array([[0, 0, 1, 1]])
p = pc.pop_to_hexes(labels2, built, count, parent, 2)
check(abs(p.sum() - 140) < 1e-9, 'population total conserved: %s' % p)
check(abs(p[0] - 100) < 1e-9 and abs(p[1] - 40) < 1e-9, 'per-hex totals')

# place_dict round trip through JSON with the demo-like layout, then the JS model reads it
n = 3
cells = {'id': ['a', 'b', 'c'], 'lat': [1, 1, 1], 'lng': [1, 1.01, 1.02], 'area': [0.7] * 3, 'inside': [1, 1, 0],
         'pop': [10, 20, 0], 'elev': [5, 6, 7], 'flood': [0.1, 0.2, 0], 'water_km': [0.5, 1.0, float('inf')],
         'nb': [[1], [0, 2], [1]], 'poly': [[1, 1, 1.1, 1.1]] * 3}
for k in pc.FRACTIONS:
    cells[k] = fr[k]
d = pc.place_dict('Toy', 'toy', 'test', 8, cells, ['x'], [], '2026-11-13')
s = json.dumps(d)
check(json.loads(s)['cells']['water_km'][2] is None, 'infinite distance stored as null')
# waterway_hexes: a line crossing three cells of a fake 1-D grid (cell = floor(lon*100))
idx = {f'c{k}': k for k in range(5)}
ways = [('river', [(45.0, 9.000), (45.0, 9.025)]), ('stream', [(45.0, 9.041), (45.0, 9.049)])]
rv = pc.waterway_hexes(ways, lambda la, lo: f'c{int(lo * 100) - 900}', idx, 0.2)
check(list(rv[:3]) == [1.0, 1.0, 1.0] and rv[4] == 0.5 and rv[3] == 0.0, 'waterway hexes: %s' % rv)

# land hex carrying a river is flood-prone itself; open water is not
w2, _ = pc.flood_weights(nb, [True, True, False, False, False], np.array([5, 5, 6, 30, 6.0]), 1.0,
                         reach_km=3.5, open_water=[True, False, False, False, False])
check(w2[0] == 0 and w2[1] == 1.0 and w2[2] > 0, 'river-through-land source: %s' % w2)
print('placecore tests passed:', ok)
