"""A clean "where in the world" map for each place: land, sea, country borders and the place marked.
Used for the lead story on the home page.
Styles: "flat" (drawn land and sea), "topo" (Natural Earth shaded relief) or "satellite" (NASA Blue Marble Next Generation),
both public domain, from the basemap-data package (github.com/matplotlib/basemap, data/basemap_data).
Usage: STYLE=topo RASTER_DIR=/path/to/jpgs python3 -I pipeline/where_maps.py [slug ...]  -> assets/img/where/<slug>.webp"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
STYLE = os.environ.get('STYLE', 'flat'); OUTD = os.environ.get('OUT')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.environ.get('OUT') or os.path.join(ROOT, 'assets', 'img', 'where'); os.makedirs(OUT, exist_ok=True)
RAS = None
if STYLE != 'flat':
    RAS = Image.open(os.path.join(os.environ.get('RASTER_DIR', '/tmp/claude-0/bm'), 'shadedrelief.jpg' if STYLE == 'topo' else 'bmng.jpg')).convert('RGB')

def crop_wrap(l0, l1, a1, a0, w, h):
    # equirectangular crop from lng l0..l1, lat a1 (top)..a0, across the date line if needed
    RW, RH = RAS.size; x0 = (l0 + 180) / 360 * RW; x1 = (l1 + 180) / 360 * RW; y0 = (90 - a1) / 180 * RH; y1 = (90 - a0) / 180 * RH
    y0 = max(0, y0); y1 = min(RH, y1)
    if x0 >= 0 and x1 <= RW: c = RAS.crop((int(x0), int(y0), int(math.ceil(x1)), int(math.ceil(y1))))
    else:
        c = Image.new('RGB', (int(math.ceil(x1 - x0)), int(math.ceil(y1 - y0))))
        for off in (-RW, 0, RW):
            a, b = max(x0, off), min(x1, off + RW)
            if b > a: c.paste(RAS.crop((int(a - off), int(y0), int(math.ceil(b - off)), int(math.ceil(y1)))), (int(a - x0), 0))
    return c.resize((w, h), Image.LANCZOS)
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
    if RAS is not None:
        hw = W / 2 / (111.32 * kx * s); hh = H / 2 / (110.57 * s)
        im = crop_wrap(lng0 - hw, lng0 + hw, lat0 + hh, lat0 - hh, W, H)
        if STYLE == 'satellite': im = Image.blend(im, Image.new('RGB', im.size, (10, 20, 30)), 0.12)
    else: im = Image.new('RGB', (W, H), SEA)
    dr = ImageDraw.Draw(im)
    def near(r):
        xs, ys = r[0::2], r[1::2]
        return not (max(xs) < lng0 - dlng or min(xs) > lng0 + dlng or max(ys) < lat0 - dlat or min(ys) > lat0 + dlat)
    for r in LAND:
        if RAS is None and len(r) >= 6 and near(r): dr.polygon([P(r[k], r[k + 1]) for k in range(0, len(r) - 1, 2)], fill=LANDC)
    for r in BORD:
        if near(r):
            if STYLE == 'satellite': ov = None
            dr.line([P(r[k], r[k + 1]) for k in range(0, len(r) - 1, 2)], fill=(BORDC if STYLE == 'flat' else (120, 110, 100) if STYLE == 'topo' else (235, 235, 225)), width=(2 if STYLE == 'flat' else 1) * SS, joint='curve')
    # the place: a soft ring and a dot, with its name
    x, y = W / 2, H / 2
    for rr, a in ((46, 40), (30, 70)):
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); od.ellipse([x - rr * SS, y - rr * SS, x + rr * SS, y + rr * SS], fill=DOT + (a,)); im.paste(ov, (0, 0), ov)
    dr = ImageDraw.Draw(im)
    dr.ellipse([x - 13 * SS, y - 13 * SS, x + 13 * SS, y + 13 * SS], fill=(255, 255, 255)); dr.ellipse([x - 9 * SS, y - 9 * SS, x + 9 * SS, y + 9 * SS], fill=DOT)
    name, country = e['name'], e.get('country') or ''
    tw = dr.textlength(name, font=F1); right = x + 60 * SS + tw < W - 30 * SS
    tx = x + 58 * SS if right else x - 58 * SS - tw
    TXT, HALO = ((255, 255, 255), (15, 25, 30)) if STYLE == 'satellite' else (INK, LANDC)
    dr.text((tx, y - 40 * SS), name, font=F1, fill=TXT, stroke_width=4 * SS, stroke_fill=HALO)
    if country:
        cw = dr.textlength(country, font=F2); cx = tx if right else tx + tw - cw
        dr.text((cx, y + 2 * SS), country, font=F2, fill=(225, 230, 228) if STYLE == 'satellite' else (70, 76, 72), stroke_width=3 * SS, stroke_fill=HALO)
    im.resize((W // SS, H // SS), Image.LANCZOS).save(os.path.join(OUT, slug + '.webp'), quality=82, method=6)
print('done', len(os.listdir(OUT)))
