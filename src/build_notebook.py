import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
core = open(os.path.join(HERE, 'placecore.py')).read()

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}

def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(True)}

cells = []
cells.append(md("""
# Threadlands place builder

Type any city, state, region or country, run every cell, and download a **place file** for Threadlands.

**How to use it**
1. In the menu, choose **Runtime → Run all**. The first run installs a few free tools, which takes a minute or two.
2. Change `PLACE` in the next cell and run it again for another place.
3. When it finishes, your browser downloads a file ending in `.threadlands.json`.
4. Open Threadlands and choose **Load a place file**, or drop the file onto the map.

**Where the data comes from (all free and global)**
- Place outline: OpenStreetMap, through its Nominatim search
- Land cover: ESA WorldCover 2021, 10 m, through Microsoft Planetary Computer
- Elevation: Copernicus DEM GLO-30, through Microsoft Planetary Computer
- Population: WorldPop 2020, 1 km, country files
- Rivers and canals: OpenStreetMap, through the Overpass API

Global data is coarser than local data. Treat the results as a screening view for comparing scenarios, not a forecast.
"""))

cells.append(code("""
# 1. Settings: change these, then run all cells
PLACE = "Milan, Italy"      # any city, state, region or country, e.g. "Toluca, Mexico" or "Khon Kaen, Thailand"
REGION_BUFFER_KM = None     # None picks a ring of surrounding land automatically; 0 uses only the place itself
MAX_HEXES = 2500            # more hexes give more detail but a slower page; keep it at or under 6000
"""))

cells.append(code("""
# 2. Install the free tools (only needed once per session)
!pip -q install h3 rasterio pystac-client planetary-computer shapely pycountry
"""))

cells.append(code("# 3. Core logic (the same code Threadlands is tested with)\n" + core))

cells.append(code('''
# 4. Find the place and its outline
import datetime, math, os, json, requests
import numpy as np
import h3, pycountry
from shapely.geometry import shape, Point, Polygon, MultiPolygon, mapping
from shapely.ops import transform as shp_transform
from shapely.prepared import prep

import time
HEADERS = {"User-Agent": "Threadlands-place-builder/1.0 (educational prototype; https://threadlands.org)"}
def nominatim(path, params):
    """Ask OpenStreetMap's Nominatim, waiting and retrying politely if it is busy."""
    r = None
    for k in range(5):
        r = requests.get("https://nominatim.openstreetmap.org/" + path, params=params, headers=HEADERS, timeout=60)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (k + 1))
            continue
        break
    r.raise_for_status()
    time.sleep(1)   # Nominatim asks for at most one request per second
    return r.json()

COMMON = {"format": "jsonv2", "polygon_geojson": 1, "addressdetails": 1, "accept-language": "en"}
hits = []
if PLACE.lower().startswith("osm:"):
    # An exact OpenStreetMap object, such as "osm:R123456", chosen on the website
    hits = nominatim("lookup", dict(COMMON, osm_ids=PLACE[4:].split("||")[0].strip()))
    PLACE = PLACE.split("||", 1)[1] if (not hits and "||" in PLACE) else PLACE
if not hits and not PLACE.lower().startswith("osm:"):
    # PLACE may list fallbacks, best first: "City of Cape Town, South Africa || Cape Town, South Africa"
    hits = []
    for q in [x.strip() for x in PLACE.split("||") if x.strip()]:
        found = nominatim("search", dict(COMMON, q=q, limit=8))
        good = [h for h in found if (h.get("geojson") or {}).get("type") in ("Polygon", "MultiPolygon")
                and h.get("addresstype") in ("city", "town", "village", "municipality", "county", "state", "region", "province",
                                             "country", "borough", "city_district", "district", "state_district", "administrative")]
        if good:
            hits = good + [h for h in found if h not in good]
            break
        hits = found   # nothing outlined yet: keep the last (plainest) phrase's results
if not hits:
    raise SystemExit(f'No place was found for "{PLACE}". Add the country, for example "Toluca, Mexico".')
def has_outline(h):
    return (h.get("geojson") or {}).get("type") in ("Polygon", "MultiPolygon")
AREA_KINDS = {"city", "town", "village", "municipality", "county", "state", "region", "province", "country", "borough",
              "city_district", "district", "state_district", "suburb", "quarter", "neighbourhood", "postcode", "island", "administrative"}
outlined = [h for h in hits if has_outline(h)]
hit = next((h for h in outlined if h.get("addresstype") in AREA_KINDS), outlined[0] if outlined else hits[0])
NAME = hit.get("name") or PLACE
DISPLAY = hit.get("display_name", PLACE)
CC = ((hit.get("address") or {}).get("country_code") or "").upper()
NOTES = []

shape_src = hit
if not has_outline(hit) and hit.get("addresstype") != "postcode":
    # OpenStreetMap sometimes knows a city only as a point; use the city-level boundary that contains it
    try:
        # Neighborhood-level first; if that is too small to be the city, step out to the district or county
        for zoom in (10, 8):
            rev = nominatim("reverse", dict(COMMON, lat=hit["lat"], lon=hit["lon"], zoom=zoom))
            if not has_outline(rev):
                continue
            g_rev = shape(rev["geojson"])
            km2 = g_rev.area * 111.32 * 110.57 * math.cos(math.radians(float(hit["lat"])))
            shape_src = rev
            if km2 >= 40:
                break
        if shape_src is not hit:
            NOTES.append(f"OpenStreetMap has no outline for {NAME}, so the boundary of {shape_src.get('name') or 'the surrounding district'} is used.")
    except Exception as e:
        print("Could not look up a boundary around the point:", e)
geom = shape(shape_src["geojson"]) if has_outline(shape_src) else Point(float(hit["lon"]), float(hit["lat"]))
if geom.geom_type == "MultiPolygon":
    parts = sorted(geom.geoms, key=lambda g: g.area, reverse=True)
    kept = [g for g in parts if g.area >= 0.02 * parts[0].area]
    if len(kept) < len(parts):
        NOTES.append(f"Dropped {len(parts) - len(kept)} small outlying parts of the outline, such as distant islands.")
    geom = MultiPolygon(kept) if len(kept) > 1 else kept[0]

LAT0, LNG0 = geom.centroid.y, geom.centroid.x
KX, KY = 111.32 * math.cos(math.radians(LAT0)), 110.57
def to_km(x, y, z=None):
    return ((np.asarray(x) - LNG0) * KX, (np.asarray(y) - LAT0) * KY)
def to_deg(x, y, z=None):
    return (np.asarray(x) / KX + LNG0, np.asarray(y) / KY + LAT0)

place_km = shp_transform(to_km, geom)
if place_km.geom_type not in ("Polygon", "MultiPolygon"):
    place_km = place_km.buffer(5.0)
    NOTES.append("OpenStreetMap gave a point, not an outline, so the place is a 5 km circle around it.")
PLACE_KM2 = place_km.area
BUFFER_KM = auto_buffer_km(PLACE_KM2) if REGION_BUFFER_KM is None else float(REGION_BUFFER_KM)
region_km = place_km.buffer(BUFFER_KM) if BUFFER_KM > 0 else place_km
region_km = region_km.simplify(max(0.05, 0.002 * math.sqrt(region_km.area)))
REGION = shp_transform(to_deg, region_km)
PLACE_GEOM = shp_transform(to_deg, place_km)
minx, miny, maxx, maxy = REGION.bounds
if maxx - minx > 40:
    NOTES.append("This place is very wide, so detail is coarse. A state or city will give a sharper picture.")
print(f"Found: {DISPLAY}")
print(f"Place area about {PLACE_KM2:,.0f} km2, plus {BUFFER_KM:.0f} km of surrounding land; region about {region_km.area:,.0f} km2.")
'''))

cells.append(code('''
# 5. Leave out open water far from land, so coastal and lakeside places spend their hexes on land
import rasterio, pystac_client, planetary_computer
from rasterio.features import shapes as rio_shapes, rasterize as rio_rasterize
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.windows import from_bounds as window_from_bounds
from rasterio.enums import Resampling
from scipy import ndimage
from shapely.ops import unary_union

CAT = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                modifier=planetary_computer.sign_inplace)

def coarse_landcover(bounds, npx=300):
    """A quick, low-detail land cover grid over the region, used only to find open water."""
    bx0, by0, bx1, by1 = bounds
    w = npx
    h = max(1, int(round(npx * ((by1 - by0) * KY) / max(1e-9, (bx1 - bx0) * KX))))
    gt = transform_from_bounds(bx0, by0, bx1, by1, w, h)
    grid = np.zeros((h, w), dtype=np.uint8)
    items = list(CAT.search(collections=["esa-worldcover"], bbox=list(bounds)).items())
    v2 = [it for it in items if str(it.properties.get("esa_worldcover:product_version", "")).startswith("2")]
    for it in (v2 or items):
        with rasterio.open(it.assets["map"].href) as src:
            sb = src.bounds
            ib = (max(bx0, sb.left), max(by0, sb.bottom), min(bx1, sb.right), min(by1, sb.top))
            if ib[0] >= ib[2] or ib[1] >= ib[3]:
                continue
            c0 = int(round((ib[0] - bx0) / (bx1 - bx0) * w)); c1 = int(round((ib[2] - bx0) / (bx1 - bx0) * w))
            r0 = int(round((by1 - ib[3]) / (by1 - by0) * h)); r1 = int(round((by1 - ib[1]) / (by1 - by0) * h))
            if c1 <= c0 or r1 <= r0:
                continue
            arr = src.read(1, window=window_from_bounds(*ib, transform=src.transform),
                           out_shape=(r1 - r0, c1 - c0), resampling=Resampling.nearest)
            sub = grid[r0:r1, c0:c1]
            ok = arr > 0
            sub[ok] = arr[ok]
    return grid, gt, (bx1 - bx0) * KX / w

WC0, GT0, PX0 = coarse_landcover(REGION.bounds)
LAND0 = (WC0 > 0) & (WC0 != 80)
INSIDE0 = rio_rasterize([(PLACE_GEOM, 1)], out_shape=WC0.shape, transform=GT0, fill=0, dtype="uint8").astype(bool)
water_share = 1 - LAND0.mean()
if water_share > 0.3 and LAND0.any():
    land_km2 = float((LAND0 & INSIDE0).sum()) * PX0 * PX0
    if REGION_BUFFER_KM is None and land_km2 > 0:
        BUFFER_KM = auto_buffer_km(land_km2)
    keep = ndimage.binary_dilation(LAND0, iterations=max(1, int(round(3.0 / PX0))))
    zone = unary_union([shape(g) for g, v in rio_shapes(keep.astype(np.uint8), mask=keep, transform=GT0) if v == 1])
    base_km = place_km.buffer(BUFFER_KM) if BUFFER_KM > 0 else place_km
    region_km = base_km.intersection(shp_transform(to_km, zone).buffer(0))
    if region_km.geom_type == "GeometryCollection":
        region_km = unary_union([g for g in region_km.geoms if g.geom_type in ("Polygon", "MultiPolygon")])
    region_km = region_km.simplify(max(0.05, 0.002 * math.sqrt(region_km.area)))
    REGION = shp_transform(to_deg, region_km)
    minx, miny, maxx, maxy = REGION.bounds
    NOTES.append("Open water more than about 3 km from land was left out, so the map spends its detail on land.")
    print(f"{water_share:.0%} of the first region was open water. Trimmed to about {region_km.area:,.0f} km2 around land, "
          f"with {BUFFER_KM:.0f} km of surrounding land.")
else:
    print(f"Open water is {water_share:.0%} of the region, so nothing was trimmed.")
'''))

cells.append(code('''
# 6. Cut the region into hexes
def cells_for(g, res):
    try:
        return list(h3.geo_to_cells(mapping(g), res))
    except Exception:
        out = set()
        for p in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
            outer = [(y, x) for x, y in p.exterior.coords]
            holes = [[(y, x) for x, y in r.coords] for r in p.interiors]
            out |= set(h3.polygon_to_cells(h3.LatLngPoly(outer, *holes), res))
        return list(out)

RES = choose_resolution(region_km.area, MAX_HEXES)
HEXES = cells_for(REGION, RES)
while len(HEXES) > MAX_HEXES and RES > 3:
    RES -= 1
    HEXES = cells_for(REGION, RES)
while len(HEXES) < MAX_HEXES / 7 and RES < 9:
    finer = cells_for(REGION, RES + 1)
    if len(finer) > MAX_HEXES:
        break
    RES, HEXES = RES + 1, finer
if len(HEXES) < 20:
    raise SystemExit("The region is too small for a useful map. Set REGION_BUFFER_KM to 10 or more and run again.")
HEXES.sort()
N = len(HEXES)
IDX = {c: i for i, c in enumerate(HEXES)}
lat = np.zeros(N); lng = np.zeros(N); area = np.zeros(N)
poly, nb, inside = [], [], np.zeros(N, dtype=bool)
place_prep = prep(PLACE_GEOM)
for i, c in enumerate(HEXES):
    lat[i], lng[i] = h3.cell_to_latlng(c)
    area[i] = h3.cell_area(c, unit="km^2")
    b = h3.cell_to_boundary(c)
    poly.append([v for pt in b for v in pt])
    nb.append([IDX[x] for x in h3.grid_ring(c, 1) if x in IDX])
    inside[i] = place_prep.contains(Point(lng[i], lat[i]))
EDGE_KM = h3.average_hexagon_edge_length(RES, unit="km")
SPACING_KM = EDGE_KM * math.sqrt(3)
print(f"{N} hexes at H3 resolution {RES}, about {area.mean():.2f} km2 each; {int(inside.sum())} inside {NAME}.")
'''))

cells.append(code('''
# 7. A common pixel grid, with each pixel labelled by the hex it falls in
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds as transform_from_bounds, rowcol
from rasterio.windows import from_bounds as window_from_bounds
from rasterio.enums import Resampling

px_km = max(0.012, EDGE_KM / 6)
W = int(math.ceil((maxx - minx) * KX / px_km)); H = int(math.ceil((maxy - miny) * KY / px_km))
CAP = 9_000_000
if W * H > CAP:
    s = math.sqrt(W * H / CAP); W, H = max(1, int(W / s)), max(1, int(H / s))
GT = transform_from_bounds(minx, miny, maxx, maxy, W, H)
shapes = [(Polygon([(p[k + 1], p[k]) for k in range(0, len(p), 2)]), i) for i, p in enumerate(poly)]
LABELS = rasterize(shapes, out_shape=(H, W), transform=GT, fill=-1, dtype="int32")
have = np.bincount(LABELS[LABELS >= 0], minlength=N)
for i in np.where(have == 0)[0]:
    r, c = rowcol(GT, lng[i], lat[i])
    if 0 <= r < H and 0 <= c < W:
        LABELS[r, c] = i
print(f"Pixel grid {W} x {H}, about {px_km * 1000:.0f} m per pixel.")

def paint(href, dest, resampling):
    """Read the part of a cloud raster that overlaps the region into dest, at the grid's resolution."""
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
        ok = np.isfinite(arr) if arr.dtype.kind == "f" else np.ones(arr.shape, dtype=bool)
        if src.nodata is not None:
            ok &= arr != src.nodata
        sub = dest[r0:r1, c0:c1]
        sub[ok] = arr[ok]
'''))

cells.append(code('''
# 8. Land cover and elevation from Microsoft Planetary Computer
import pystac_client, planetary_computer
CAT = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                modifier=planetary_computer.sign_inplace)
BBOX = [minx, miny, maxx, maxy]

wc_items = list(CAT.search(collections=["esa-worldcover"], bbox=BBOX).items())
v2 = [it for it in wc_items if str(it.properties.get("esa_worldcover:product_version", "")).startswith("2")]
wc_items = v2 or wc_items
WC = np.zeros((H, W), dtype=np.uint8)
for k, it in enumerate(wc_items, 1):
    paint(it.assets["map"].href, WC, Resampling.nearest)
    print(f"  land cover tile {k}/{len(wc_items)}", end="\\r")
FR, NODATA_HEX = wc_fractions(LABELS, WC, N)
print(f"Land cover: {len(wc_items)} tiles; {NODATA_HEX} hexes had no land data and count as water (usually sea).")

dem_items = list(CAT.search(collections=["cop-dem-glo-30"], bbox=BBOX).items())
DEM = np.full((H, W), np.nan, dtype=np.float32)
for k, it in enumerate(dem_items, 1):
    paint(it.assets["data"].href, DEM, Resampling.average)
    print(f"  elevation tile {k}/{len(dem_items)}", end="\\r")
# Average elevation over land pixels only, so a coastal hex is not pulled down by the sea beside it
elev_land, miss_land = hex_means(LABELS, DEM, N, valid_mask=(WC != 80))
elev_all, miss_all = hex_means(LABELS, DEM, N)
elev = np.where(~miss_land, elev_land, elev_all)
elev_missing = miss_land & miss_all
sea = elev_missing & (FR["water"] >= 0.99)
elev[sea] = 0.0
elev_missing &= ~sea
ELEV = fill_missing(elev, nb, elev_missing)
print(f"Elevation: {len(dem_items)} tiles; range {np.nanmin(ELEV):.0f} to {np.nanmax(ELEV):.0f} m.")
'''))

cells.append(code('''
# 9. Population from WorldPop (country file, 2020, 1 km)
POP = None
POP_SOURCE = None
POP_PATH = None
try:
    ISO3 = pycountry.countries.get(alpha_2=CC).alpha_3 if CC else None
except Exception:
    ISO3 = None
if ISO3:
    urls = [f"https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/{ISO3}/{ISO3.lower()}_ppp_2020_1km_Aggregated_UNadj.tif",
            f"https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/{ISO3}/{ISO3.lower()}_ppp_2020_1km_Aggregated.tif"]
    for url in urls:
        try:
            path = f"/content/{ISO3.lower()}_pop.tif" if os.path.isdir("/content") else f"{ISO3.lower()}_pop.tif"
            if not os.path.exists(path):
                with requests.get(url, stream=True, timeout=300, headers=HEADERS) as r:
                    r.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
            with rasterio.open(path) as src:
                sb = src.bounds
                ib = (max(minx, sb.left), max(miny, sb.bottom), min(maxx, sb.right), min(maxy, sb.top))
                if ib[0] >= ib[2] or ib[1] >= ib[3]:
                    raise ValueError("population file does not cover the region")
                win = window_from_bounds(*ib, transform=src.transform).round_offsets().round_lengths()
                arr = src.read(1, window=win).astype(float)
                if src.nodata is not None:
                    arr[arr == src.nodata] = 0
                arr[~np.isfinite(arr) | (arr < 0)] = 0
                wt = src.window_transform(win)
            target_dx = (maxx - minx) / W
            if target_dx < abs(wt.a):
                xs = minx + (np.arange(W) + 0.5) * target_dx
                ys = maxy - (np.arange(H) + 0.5) * (maxy - miny) / H
                ncol = np.floor((xs - wt.c) / wt.a).astype(np.int64)
                nrow = np.floor((ys - wt.f) / wt.e).astype(np.int64)
                vc = (ncol >= 0) & (ncol < arr.shape[1]); vr = (nrow >= 0) & (nrow < arr.shape[0])
                cnt = arr[np.clip(nrow, 0, arr.shape[0] - 1)][:, np.clip(ncol, 0, arr.shape[1] - 1)]
                parent = nrow[:, None] * arr.shape[1] + ncol[None, :]
                valid = vr[:, None] & vc[None, :]
                cnt = np.where(valid, cnt, 0.0); parent = np.where(valid, parent, -1)
                POP = pop_to_hexes(LABELS, WC == 50, cnt, parent, N)
            else:
                rr, cc_ = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
                xs = wt.c + (cc_ + 0.5) * wt.a; ys = wt.f + (rr + 0.5) * wt.e
                tc = np.floor((xs - minx) / target_dx).astype(np.int64)
                tr = np.floor((maxy - ys) / ((maxy - miny) / H)).astype(np.int64)
                ok = (tc >= 0) & (tc < W) & (tr >= 0) & (tr < H) & (arr > 0)
                lab = LABELS[tr[ok], tc[ok]]
                keep = lab >= 0
                POP = np.bincount(lab[keep], weights=arr[ok][keep], minlength=N)
            POP_SOURCE = url
            POP_PATH = path
            break
        except Exception as e:
            print(f"Could not use {url.rsplit('/', 1)[-1]}: {e}")
if POP is None:
    POP = FR["built"] * area * 3000.0
    NOTES.append("WorldPop could not be downloaded, so population is estimated at 3,000 people per km2 of built-up land.")
    print("Population: estimated from built-up land.")
else:
    NOTES.append(f"Population covers {pycountry.countries.get(alpha_3=ISO3).name} only. Surrounding land in other countries counts as empty.")
    print(f"Population: about {POP.sum():,.0f} people in the region.")
'''))

cells.append(code('''
# 10. Rivers, canals and streams from OpenStreetMap (narrow ones do not show in satellite land cover)
RIVER = np.zeros(N)
RIVERS_OK = False
try:
    kinds = "river|canal" if region_km.area > 20000 else "river|canal|stream"
    query = f'[out:json][timeout:180];way["waterway"~"^({kinds})$"]({miny},{minx},{maxy},{maxx});out geom;'
    import time
    SERVERS = ["https://overpass-api.de/api/interpreter",
               "https://overpass.kumi.systems/api/interpreter",
               "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
               "https://overpass.private.coffee/api/interpreter"]
    data, last_err = None, None
    for attempt in range(3):
        for url in SERVERS:
            host = url.split("/")[2]
            try:
                print(f"  asking {host} for waterways...")
                r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=200)
                if r.status_code in (429, 502, 503, 504):
                    raise RuntimeError(f"server busy ({r.status_code})")
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                last_err = e
                print(f"  {host} did not answer: {e}")
        if data is not None:
            break
        if attempt < 2:
            print(f"  all servers busy; waiting {45 * (attempt + 1)} seconds and trying again...")
            time.sleep(45 * (attempt + 1))
    if data is None:
        raise RuntimeError(f"no waterway server answered ({last_err})")
    ways = [(el.get("tags", {}).get("waterway"), [(p["lat"], p["lon"]) for p in el.get("geometry", [])])
            for el in data.get("elements", []) if el.get("type") == "way"]
    RIVER = waterway_hexes(ways, lambda la, lo: h3.latlng_to_cell(la, lo, RES), IDX, EDGE_KM / 2)
    RIVERS_OK = True
    print(f"Waterways: {len(ways)} mapped lines cross {int((RIVER > 0).sum())} hexes.")
except Exception as e:
    NOTES.append("Mapped rivers and canals could not be downloaded, so only water visible from space counts.")
    print("Could not get waterways from OpenStreetMap:", e)
'''))

cells.append(code(open(os.path.join(HERE, 'cell_regional.py')).read()))

cells.append(code('''
# 12. Flood screening, then save the place file
OPEN_WATER = FR["water"] >= 0.3
WATER = OPEN_WATER | (RIVER >= 1.0)   # rivers, lakes and sea; canals and streams are drawn but are not flood sources
REACH = max(2.0, min(2.0 * SPACING_KM, SPACING_KM + 6.0))
FLOOD, WATER_KM = flood_weights(nb, WATER, ELEV, SPACING_KM, height_m=5.0, reach_km=REACH, open_water=OPEN_WATER)
if RES <= 6:
    NOTES.append("Hexes are large, so floodplains are only roughly placed.")
if not WATER.any():
    NOTES.append("No river, lake or sea was found in the region, so flood exposure is zero.")

cells_out = {"id": HEXES, "lat": lat, "lng": lng, "area": area, "inside": inside, "pop": POP,
             "elev": ELEV, "flood": FLOOD, "water_km": WATER_KM, "nb": nb, "poly": poly, "river": RIVER}
cells_out.update(FR)
SOURCES = [
    "Outline: OpenStreetMap contributors, via Nominatim (ODbL)",
    "Land cover: ESA WorldCover 2021 v200, 10 m (CC BY 4.0), via Microsoft Planetary Computer",
    "Elevation: Copernicus DEM GLO-30, via Microsoft Planetary Computer",
    "Population: WorldPop 2020, 1 km (CC BY 4.0)" if POP_SOURCE else "Population: estimated from built-up land",
    "Hex grid: H3 (Uber, Apache 2.0)",
]
if RIVERS_OK:
    SOURCES.insert(1, "Rivers and canals: OpenStreetMap contributors, via the Overpass API (ODbL)")
place = place_dict(NAME, PLACE, hit.get("type") or hit.get("addresstype") or "place", RES, cells_out, SOURCES,
                   NOTES, datetime.date.today().isoformat())
place["display_name"] = DISPLAY
place["buffer_km"] = BUFFER_KM
if REGIONAL is not None:
    place["regional"] = REGIONAL
    SOURCES_EXTRA = ["River basins: HydroBASINS (WWF HydroSHEDS)"] if REGIONAL.get("basin") else []
    place["sources"] = place["sources"] + SOURCES_EXTRA
slug = "".join(ch if ch.isalnum() else "-" for ch in NAME.lower()).strip("-") or "place"
OUT = f"{slug}.threadlands.json"
with open(OUT, "w") as f:
    json.dump(place, f, separators=(",", ":"))
print(f"Saved {OUT} ({os.path.getsize(OUT) / 1024:,.0f} KB): {N} hexes, {POP.sum():,.0f} people.")
for note in NOTES:
    print(" -", note)
try:
    from google.colab import files
    files.download(OUT)
except Exception:
    print("Not running in Colab: the file is saved next to this notebook.")
'''))

cells.append(code('''
# 13. Optional quick look: land cover and flood screening
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
verts = [[(p[k + 1], p[k]) for k in range(0, len(p), 2)] for p in poly]
fig, ax = plt.subplots(1, 2, figsize=(13, 6))
for a, vals, title, cmap in [(ax[0], FR["built"], "Built-up share", "Greys"), (ax[1], FLOOD, "Flood screening", "Blues")]:
    pc_ = PolyCollection(verts, array=np.asarray(vals), cmap=cmap, edgecolors="none")
    a.add_collection(pc_); a.autoscale(); a.set_aspect(1 / math.cos(math.radians(LAT0))); a.set_title(title); a.axis("off")
plt.show()
'''))

nb = {"cells": cells, "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}
out = os.path.join(HERE, "threadlands-place-builder.ipynb")
json.dump(nb, open(out, "w"), indent=1)

# Syntax check every code cell (IPython "!" lines removed)
for i, c in enumerate(cells):
    if c["cell_type"] != "code":
        continue
    src = "".join(l for l in c["source"] if not l.lstrip().startswith("!"))
    compile(src, f"cell{i}", "exec")
print("notebook written and every code cell compiles:", out)
