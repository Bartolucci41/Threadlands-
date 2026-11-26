"""A small picture for each project: where it sits, in its place's Threadlands land-cover data, with a marker.
Used until a credited photo is added (projects.json: "photo": {"src", "credit", "date"}).
Usage: python3 -I pipeline/project_thumbs.py  -> assets/img/pj/<id>.jpg"""
import json, math, os
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'img', 'pj'); os.makedirs(OUT, exist_ok=True)
COL = {'built': (158, 152, 144), 'tree': (63, 110, 72), 'shrub': (128, 146, 96), 'grass': (160, 176, 112), 'crop': (214, 196, 128), 'bare': (212, 200, 176), 'water': (74, 132, 176), 'wetland': (96, 150, 150)}
W, H, SPAN_KM = 640, 340, 36
cache = {}
for p in json.load(open(os.path.join(ROOT, 'data', 'projects.json')))['projects']:
    if p.get('lat') is None: continue
    if p['place'] not in cache: cache[p['place']] = json.load(open(os.path.join(ROOT, 'data', 'places', p['place'] + '.json')))
    d = cache[p['place']]; c = d['cells']; kx = math.cos(math.radians(p['lat']))
    s = W / SPAN_KM
    im = Image.new('RGB', (W, H), (236, 233, 224)); dr = ImageDraw.Draw(im)
    r = math.sqrt(2 * float(d.get('hex_km2') or 1) / (3 * math.sqrt(3))) * s * 1.15
    for i in range(len(c['lat'])):
        x = W / 2 + (c['lng'][i] - p['lng']) * 111.32 * kx * s; y = H / 2 - (c['lat'][i] - p['lat']) * 110.57 * s
        if x < -r or x > W + r or y < -r or y > H + r: continue
        mix, tot = [0, 0, 0], 0
        for k, col in COL.items():
            v = float(c[k][i] or 0) * (1.3 if k == 'water' else 1); tot += v; mix = [m + v * cc for m, cc in zip(mix, col)]
        if tot > 0: dr.polygon([(x + r * math.cos(math.radians(60 * k + 30)), y + r * math.sin(math.radians(60 * k + 30))) for k in range(6)], fill=tuple(int(m / tot) for m in mix))
    im = im.filter(ImageFilter.GaussianBlur(1.4)); dr = ImageDraw.Draw(im)
    a = (p.get('area_km2') or 0); rr = max(9, min(120, math.sqrt(a / math.pi) * s)) if a else 9
    dr.ellipse([W/2-rr-3, H/2-rr-3, W/2+rr+3, H/2+rr+3], outline=(255, 255, 255), width=4)
    dr.ellipse([W/2-rr, H/2-rr, W/2+rr, H/2+rr], outline=(192, 96, 58), width=4)
    dr.ellipse([W/2-5, H/2-5, W/2+5, H/2+5], fill=(192, 96, 58), outline=(255, 255, 255), width=2)
    im.save(os.path.join(OUT, p['id'] + '.jpg'), quality=80, optimize=True)
print('done', len(os.listdir(OUT)))
