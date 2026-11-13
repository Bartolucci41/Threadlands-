import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heatcore as hc

ok = 0
def check(c, m):
    global ok
    if not c:
        raise AssertionError(m)
    ok += 1

check(hc.season_for(45)[0] == [6, 7, 8], 'north summer')
check(hc.season_for(-34)[0] == [12, 1, 2], 'south summer')
check(len(hc.season_for(13.7)[0]) == 12, 'tropics all year')
k = (300 + 273.15 - 273.15)
dn = (30 + 273.15 - 149.0) / 0.00341802
check(abs(hc.to_celsius(np.array([dn]))[0] - 30) < 1e-6, 'DN to celsius')
check(np.isnan(hc.to_celsius(np.array([0]))[0]), 'fill is nan')
check(list(hc.clear_mask(np.array([21824, 21824 | 8, 1]))) == [True, False, False], 'qa bits')

hexes = np.array([0, 0, 0, 1, 1, 1, 2, -1])
t = np.array([30, 32, 34, 20, 22, 99, 40, 50.0])
clear = np.array([1, 1, 1, 1, 1, 0, 0, 1], bool)
m = hc.hex_means(hexes, t, clear, 4)
check(abs(m[0] - 32) < 1e-9 and abs(m[1] - 21) < 1e-9, 'hex means %s' % m)
check(np.isnan(m[2]) and np.isnan(m[3]), 'cloudy and empty hexes are nan')

rng = np.random.default_rng(1)
pattern = rng.normal(0, 3, 40)
stack = np.vstack([pattern + 25, pattern + 31, pattern + 28])
stack[1, :5] = np.nan
a, r, n = hc.combine(stack, np.ones(40, bool))
check(np.allclose(r - np.nanmedian(r), pattern - np.median(pattern), atol=1e-6), 'scene offsets removed')
check(n[0] == 2 and n[10] == 3, 'scene counts')
print('heatcore tests passed:', ok)
