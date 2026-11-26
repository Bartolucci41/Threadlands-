"""A locator picture for each project: the project, its neighborhood and the city centre on Threadlands' land-cover data.
Used until a credited photo is added (projects.json: "photo": {"src", "credit", "date"}).
Usage: python3 -I pipeline/project_thumbs.py  -> assets/img/pj/<id>.jpg"""
import json, math, os
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'img', 'pj'); os.makedirs(OUT, exist_ok=True)
FD = '/usr/share/fonts/opentype/inter/'
F1 = ImageFont.truetype(FD + 'Inter-SemiBold.otf', 23); F2 = ImageFont.truetype(FD + 'Inter-Medium.otf', 20); F3 = ImageFont.truetype(FD + 'Inter-Medium.otf', 18); F4 = ImageFont.truetype(FD + 'Inter-Medium.otf', 16)
# Built land is kept pale so parks, farmland and water stand out
COL = {'built': (226, 221, 211), 'tree': (58, 118, 72), 'shrub': (120, 150, 92), 'grass': (150, 186, 104), 'crop': (222, 202, 120), 'bare': (214, 196, 166), 'water': (52, 128, 190), 'wetland': (78, 156, 156)}
W, H, SPAN_KM = 480, 255, 30
TOP = 46   # keep the top band clear for the status badge and caption
INK, PIN = (30, 36, 33), (196, 84, 44)

BUSY = []
def hit(bx): return any(not (bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3]) for o in BUSY)
def place(dr, cands, txt, font):
    """Put a label in the first candidate spot (x, y, anchor) that stays in frame and clear of other labels."""
    w = dr.textlength(txt, font=font) + 20; h = font.size + 12; best = None
    for x, y, an in cands:
        x0 = x if an == 'l' else x - w if an == 'r' else x - w / 2
        bx = (x0, y, x0 + w, y + h)
        if x0 < 6 or x0 + w > W - 6 or y < TOP or y + h > H - 6: continue
        if not hit(bx): best = bx; break
    if best is None: return False
    BUSY.append(best); dr.rounded_rectangle(best, radius=h // 2, fill=(255, 255, 255)); dr.text((best[0] + 10, best[1] + 5), txt, font=font, fill=INK); return True

def short(a):
    a = (a or '').split(',')[0].split(';')[0].strip()
    return a if len(a) <= 40 else a[:38].rsplit(' ', 1)[0] + '…'

# A landmark people know, to orient each picture. The study-area centroid is not a city centre, so places
# without a landmark here get none rather than a misleading one.
LANDMARK = {'mexico-city': ('Zócalo', 19.4326, -99.1332), 'bangkok': ('Grand Palace', 13.7500, 100.4913), 'milan': ('Duomo', 45.4642, 9.1900),
            'montreal': ('Downtown', 45.5017, -73.5673), 'san-francisco': ('Union Square', 37.7880, -122.4075), 'bologna': ('Piazza Maggiore', 44.4938, 11.3430)}
cache = {}
for p in json.load(open(os.path.join(ROOT, 'data', 'projects.json')))['projects']:
    if p.get('lat') is None: continue
    if p['place'] not in cache: cache[p['place']] = json.load(open(os.path.join(ROOT, 'data', 'places', p['place'] + '.json')))
    d = cache[p['place']]; c = d['cells']; kx = math.cos(math.radians(p['lat'])); s = W / SPAN_KM
    xy = lambda la, ln: (W / 2 + (ln - p['lng']) * 111.32 * kx * s, H / 2 - (la - p['lat']) * 110.57 * s)
    BUSY.clear(); im = Image.new('RGB', (W, H), (238, 235, 227)); dr = ImageDraw.Draw(im)
    cov = Image.new('L', (W, H), 0); dc = ImageDraw.Draw(cov)
    r = math.sqrt(2 * float(d.get('hex_km2') or 1) / (3 * math.sqrt(3))) * s * 1.15
    for i in range(len(c['lat'])):
        x, y = xy(c['lat'][i], c['lng'][i])
        if x < -r or x > W + r or y < -r or y > H + r: continue
        mix, tot = [0, 0, 0], 0
        for k, col in COL.items():
            v = float(c[k][i] or 0) * (1.6 if k in ('water', 'wetland') else 1.2 if k == 'tree' else 1); tot += v; mix = [m + v * cc for m, cc in zip(mix, col)]
        hexp = [(x + r * math.cos(math.radians(60 * k + 30)), y + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]
        dc.polygon(hexp, fill=255)
        if tot > 0: dr.polygon(hexp, fill=tuple(int(m / tot) for m in mix))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    # Beyond the study boundary: hatched grey, so it reads as outside the map rather than as land with no detail
    out = np.asarray(cov) < 128; OUTLAB = None
    if out.mean() > 0.04:
        hat = Image.new('RGB', (W, H), (214, 216, 218)); dh = ImageDraw.Draw(hat)
        for k in range(-H, W, 12): dh.line([(k, H), (k + H, 0)], fill=(196, 199, 203), width=2)
        im.paste(hat, (0, 0), Image.fromarray((out * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.8)))
        dist = ndimage.distance_transform_edt(out); dist[:TOP + 10, :] = 0; dist[H - 50:, W - 150:] = 0
        yy, xx = np.unravel_index(np.argmax(dist), dist.shape)
        if dist[yy, xx] > 18: OUTLAB = (int(xx), int(yy))
    dr = ImageDraw.Draw(im)
    # Project footprint (if known) and pin
    a = p.get('area_km2') or 0; rr = max(0, min(130, math.sqrt(a / math.pi) * s)) if a else 0
    if rr > 14:
        dr.ellipse([W/2-rr-3, H/2-rr-3, W/2+rr+3, H/2+rr+3], outline=(255, 255, 255), width=3)
        dr.ellipse([W/2-rr, H/2-rr, W/2+rr, H/2+rr], outline=PIN, width=4)
    dr.ellipse([W/2-13, H/2-13, W/2+13, H/2+13], fill=(255, 255, 255)); dr.ellipse([W/2-9, H/2-9, W/2+9, H/2+9], fill=PIN)
    L = 5 * s; SB = (W - 42 - L, H - 44, W - 10, H - 10); KW = dr.textlength('Built-up', font=F4) + 46; KB = (10, H - 44, 10 + KW, H - 10)   # key: pale = built-up land
    BUSY.extend([SB, KB, (W/2-14, H/2-14, W/2+14, H/2+14)])
    # Landmark: marked if in frame, otherwise named at the edge with its direction and distance
    lm = LANDMARK.get(p['place'])
    if lm:
        name, cla, cln = lm
        cx, cy = xy(cla, cln); km = math.hypot((cla - p['lat']) * 110.57, (cln - p['lng']) * 111.32 * kx)
        if km < 1.5: pass
        elif 30 < cx < W - 30 and TOP + 4 < cy < H - 30:
            BUSY.append((cx-8, cy-8, cx+8, cy+8)); dr.rectangle([cx-6, cy-6, cx+6, cy+6], fill=INK, outline=(255, 255, 255), width=2)
            place(dr, [(cx + 12, cy - 15, 'l'), (cx - 12, cy - 15, 'r'), (cx, cy + 10, 'c'), (cx, cy - 42, 'c'), (cx + 12, cy + 4, 'l'), (cx - 12, cy + 4, 'r'), (cx + 12, cy - 34, 'l'), (cx - 12, cy - 34, 'r')], name, F2)
        else:
            ang = math.atan2(cy - H / 2, cx - W / 2); t = min((W / 2 - 34) / max(abs(math.cos(ang)), 1e-6), (H / 2 - 40) / max(abs(math.sin(ang)), 1e-6))
            ex, ey = W / 2 + t * math.cos(ang), H / 2 + t * math.sin(ang)
            ARW = '→↘↓↙←↖↑↗'[int(round(math.degrees(ang) / 45)) % 8]   # screen y points down
            txt = '%s %s %d km' % (ARW, name, round(km))
            place(dr, [(ex + 22, ey - 16, 'l'), (ex - 22, ey - 16, 'r'), (ex + 14, ey - 50, 'l'), (ex - 14, ey - 50, 'r'), (ex + 14, ey + 14, 'l'), (ex - 14, ey + 14, 'r'), (8, ey - 16, 'l'), (W - 8, ey - 16, 'r'), (W / 2, ey - 50, 'c')], txt, F2)
    lab = short(p.get('area')); off = (min(rr, 60) * 0.7 if rr > 14 else 0) + 20
    if lab: place(dr, [(W/2 + off, H/2 - 17, 'l'), (W/2 - off, H/2 - 17, 'r'), (W/2, H/2 + 18, 'c'), (W/2, H/2 - 52, 'c'), (W/2 + off, H/2 + 10, 'l'), (W/2 - off, H/2 + 10, 'r'), (W/2 + off, H/2 - 44, 'l'), (W/2 - off, H/2 - 44, 'r')], lab, F1)
    if OUTLAB:
        ox, oy = OUTLAB; place(dr, [(ox, oy - 16, 'c'), (ox, oy - 36, 'c'), (ox, oy + 4, 'c'), (ox - 20, oy - 16, 'r'), (ox + 20, oy - 16, 'l')], 'Outside this map', F3)
    # Scale
    dr.rounded_rectangle(KB, radius=8, fill=(255, 255, 255)); dr.rounded_rectangle([KB[0] + 10, KB[1] + 9, KB[0] + 28, KB[1] + 25], radius=3, fill=COL['built'], outline=(150, 145, 136))
    dr.text((KB[0] + 36, KB[1] + 7), 'Built-up', font=F4, fill=INK)
    X0 = W - 32 - L; dr.rounded_rectangle([X0 - 10, H - 44, W - 10, H - 10], radius=8, fill=(255, 255, 255))
    dr.line([X0, H - 18, X0 + L, H - 18], fill=INK, width=3); dr.text((X0, H - 42), '5 km', font=ImageFont.truetype(FD + 'Inter-Medium.otf', 16), fill=INK)
    im.save(os.path.join(OUT, p['id'] + '.jpg'), quality=82, optimize=True)
print('done', len(os.listdir(OUT)))
