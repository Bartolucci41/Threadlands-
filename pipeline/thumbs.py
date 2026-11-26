"""Small land-cover pictures of each place, from its own Threadlands cells, for news and listings.
Usage: python3 -I pipeline/thumbs.py   -> assets/img/thumb/<slug>.jpg"""
import json, math, os
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'img', 'thumb'); os.makedirs(OUT, exist_ok=True)
COL = {'built': (118, 116, 112), 'tree': (63, 110, 72), 'shrub': (128, 146, 96), 'grass': (160, 176, 112), 'crop': (214, 196, 128), 'bare': (212, 200, 176), 'water': (74, 132, 176), 'wetland': (96, 150, 150)}
W, H = 640, 400
for fn in sorted(os.listdir(os.path.join(ROOT, 'data', 'places'))):
    if not fn.endswith('.json'): continue
    d = json.load(open(os.path.join(ROOT, 'data', 'places', fn))); c = d.get('cells') or {}
    if not c.get('lat'): continue
    la, ln = c['lat'], c['lng']; lat0 = sum(la) / len(la); kx = math.cos(math.radians(lat0))
    # frame on where people live: population-weighted center, a window a bit wider than the city
    P = [max(0, p or 0) for p in c['pop']]; tp = sum(P) or 1
    cy = sum(a * p for a, p in zip(la, P)) / tp; cx = sum(b * p for b, p in zip(ln, P)) / tp
    span = (max(ln) - min(ln)) * kx * 0.62
    sx = W / span; sy = sx
    im = Image.new('RGB', (W, H), (236, 233, 224)); dr = ImageDraw.Draw(im)
    r = math.sqrt(2 * float(d.get('hex_km2') or 1) / (3 * math.sqrt(3))) / 111.32 * sx * 1.15
    for i in range(len(la)):
        x = W / 2 + (ln[i] - cx) * kx * sx; y = H / 2 - (la[i] - cy) * sy
        if x < -r or x > W + r or y < -r or y > H + r: continue
        mix = [0, 0, 0]; tot = 0
        for k, col in COL.items():
            v = float(c[k][i] or 0)
            if k == 'water': v *= 1.3
            tot += v; mix = [m + v * cc for m, cc in zip(mix, col)]
        if tot <= 0: continue
        fill = tuple(int(m / tot) for m in mix)
        dr.polygon([(x + r * math.cos(math.radians(60 * k + 30)), y + r * math.sin(math.radians(60 * k + 30))) for k in range(6)], fill=fill)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(os.path.join(OUT, fn[:-5] + '.jpg'), quality=78, optimize=True)
print('done', len(os.listdir(OUT)))
