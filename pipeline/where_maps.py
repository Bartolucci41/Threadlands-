"""A clean "where in the world" map for each place: land, sea, country borders and the place marked.
Used for the lead story on the home page. Usage: python3 -I pipeline/where_maps.py [slug ...]  -> assets/img/where/<slug>.webp"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'img', 'where'); os.makedirs(OUT, exist_ok=True)
LAND = json.load(open(os.path.join(ROOT, 'assets', 'land-50m.json')))
BORD = json.load(open(os.path.join(ROOT, 'assets', 'borders.json')))
FD = '/usr/share/fonts/opentype/inter/'
SS = 2; W, H = 960 * SS, 540 * SS; SPAN_KM = 1800
SEA, LANDC, BORDC, DOT, INK = (205, 222, 230), (246, 244, 238), (196, 191, 180), (192, 84, 44), (28, 38, 35)
F1 = ImageFont.truetype(FD + 'Inter-Bold.otf', 34 * SS); F2 = ImageFont.truetype(FD + 'Inter-Medium.otf', 22 * SS)
idx = {e['slug']: e for e in json.load(open(os.path.join(ROOT, 'data', 'index.json')))['places']}
for slug in (sys.argv[1:] or sorted(idx)):
    e = idx[slug]; lat0, lng0 = e['lat'], e['lng']; kx = math.cos(math.radians(lat0)); s = W / SPAN_KM
    P = lambda ln, la: (W / 2 + (ln - lng0) * 111.32 * kx * s, H / 2 - (la - lat0) * 110.57 * s)
    dlng = SPAN_KM / (111.32 * kx) * 0.75; dlat = SPAN_KM * H / W / 110.57 * 0.75
    im = Image.new('RGB', (W, H), SEA); dr = ImageDraw.Draw(im)
    def near(r):
        xs, ys = r[0::2], r[1::2]
        return not (max(xs) < lng0 - dlng or min(xs) > lng0 + dlng or max(ys) < lat0 - dlat or min(ys) > lat0 + dlat)
    for r in LAND:
        if len(r) >= 6 and near(r): dr.polygon([P(r[k], r[k + 1]) for k in range(0, len(r) - 1, 2)], fill=LANDC)
    for r in BORD:
        if near(r): dr.line([P(r[k], r[k + 1]) for k in range(0, len(r) - 1, 2)], fill=BORDC, width=2 * SS, joint='curve')
    # the place: a soft ring and a dot, with its name
    x, y = W / 2, H / 2
    for rr, a in ((46, 40), (30, 70)):
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); od.ellipse([x - rr * SS, y - rr * SS, x + rr * SS, y + rr * SS], fill=DOT + (a,)); im.paste(ov, (0, 0), ov)
    dr = ImageDraw.Draw(im)
    dr.ellipse([x - 13 * SS, y - 13 * SS, x + 13 * SS, y + 13 * SS], fill=(255, 255, 255)); dr.ellipse([x - 9 * SS, y - 9 * SS, x + 9 * SS, y + 9 * SS], fill=DOT)
    name, country = e['name'], e.get('country') or ''
    tw = dr.textlength(name, font=F1); right = x + 60 * SS + tw < W - 30 * SS
    tx = x + 58 * SS if right else x - 58 * SS - tw
    dr.text((tx, y - 40 * SS), name, font=F1, fill=INK, stroke_width=4 * SS, stroke_fill=LANDC)
    if country:
        cw = dr.textlength(country, font=F2); cx = tx if right else tx + tw - cw
        dr.text((cx, y + 2 * SS), country, font=F2, fill=(96, 104, 100), stroke_width=3 * SS, stroke_fill=LANDC)
    im.resize((W // SS, H // SS), Image.LANCZOS).save(os.path.join(OUT, slug + '.webp'), quality=82, method=6)
print('done', len(os.listdir(OUT)))
