# 11. Regional threads: the river basin upstream of the city and the foodshed around it
from collections import defaultdict, deque
REGIONAL = None
FOOD_RADII_KM = [50, 100, 250]
WC_LETTER = {10: "t", 20: "s", 30: "g", 40: "c", 50: "b", 60: "n", 70: "n", 80: "w", 90: "e", 95: "e", 100: "g"}
try:
    # Where the city's people are: the population-weighted center of its own built-up hexes
    w_urb = POP * (FR["built"] >= 0.25) * inside
    if w_urb.sum() <= 0:
        w_urb = POP * (FR["built"] >= 0.25)
    if w_urb.sum() > 0:
        CLAT, CLNG = float(np.average(lat, weights=w_urb)), float(np.average(lng, weights=w_urb))
    else:
        CLAT, CLNG = float(PLACE_GEOM.centroid.y), float(PLACE_GEOM.centroid.x)
    reg_notes = []

    # Water thread: every river basin that drains toward the city (HydroBASINS level 8)
    BASIN = None
    try:
        import geopandas as gpd
        if CLNG < -30:
            cands = ["ar", "na"] if CLAT > 60 else (["sa", "na"] if (CLAT < 12 and CLNG > -82) else ["na", "sa"])
        elif CLNG < 60:
            cands = ["eu", "af", "si"] if CLAT >= 35 else ["af", "eu", "as"]
        else:
            cands = ["si", "as"] if CLAT > 55 else (["au", "as"] if (CLAT < -10 and CLNG > 110) else ["as", "au", "si"])
        pt = Point(CLNG, CLAT)
        gdf, start = None, None
        for code in cands:
            zpath = f"/content/hybas_{code}_lev08_v1c.zip" if os.path.isdir("/content") else f"hybas_{code}_lev08_v1c.zip"
            if not os.path.exists(zpath):
                url = f"https://data.hydrosheds.org/file/hydrobasins/standard/hybas_{code}_lev08_v1c.zip"
                print(f"  downloading river basins ({code})...")
                with requests.get(url, stream=True, timeout=600, headers=HEADERS) as r:
                    r.raise_for_status()
                    with open(zpath, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
            g = gpd.read_file(f"zip://{zpath}")
            hit = g[g.contains(pt)]
            if len(hit) == 0:
                near = g.distance(pt)
                if near.min() < 0.05:
                    hit = g.loc[[near.idxmin()]]
            if len(hit):
                gdf, start = g, int(hit.iloc[0]["HYBAS_ID"])
                break
        if gdf is None:
            raise RuntimeError("no basin found at the city center")
        ups = defaultdict(list)
        for hid, nd in zip(gdf["HYBAS_ID"].astype("int64"), gdf["NEXT_DOWN"].astype("int64")):
            ups[int(nd)].append(int(hid))
        ids, q = {start}, deque([start])
        while q:
            a = q.popleft()
            for b in ups.get(a, []):
                if b not in ids:
                    ids.add(b)
                    q.append(b)
        sel = gdf[gdf["HYBAS_ID"].astype("int64").isin(ids)]
        bgeom = unary_union(list(sel.geometry)).buffer(0)
        BASIN = {"geom": bgeom, "area_km2": float(sel["SUB_AREA"].sum()), "n": int(len(sel))}
        print(f"Water thread: {len(sel)} sub-basins drain toward the city, about {BASIN['area_km2']:,.0f} km2.")
    except Exception as e:
        reg_notes.append("The upstream river basin could not be loaded, so the water thread is missing.")
        print("Could not build the water thread:", e)

    # Area for the regional view: the 250 km foodshed circle, widened to hold the whole basin
    R = max(FOOD_RADII_KM)
    kxc = 111.32 * math.cos(math.radians(CLAT))
    ex = [CLNG - R / kxc, CLAT - R / 110.57, CLNG + R / kxc, CLAT + R / 110.57]
    if BASIN is not None:
        b = BASIN["geom"].bounds
        ex = [min(ex[0], b[0]), min(ex[1], b[1]), max(ex[2], b[2]), max(ex[3], b[3])]
    ex = [max(-180, ex[0]), max(-85, ex[1]), min(180, ex[2]), min(85, ex[3])]
    GRID, GTR, _ = coarse_landcover(tuple(ex), npx=260)
    gh, gw = GRID.shape
    xs = ex[0] + (np.arange(gw) + 0.5) * (ex[2] - ex[0]) / gw
    ys = ex[3] - (np.arange(gh) + 0.5) * (ex[3] - ex[1]) / gh
    XX, YY = np.meshgrid(xs, ys)
    DKM = np.hypot((XX - CLNG) * 111.32 * np.cos(np.radians(YY)), (YY - CLAT) * 110.57)
    PXA = ((ex[2] - ex[0]) / gw * 111.32 * np.cos(np.radians(YY))) * ((ex[3] - ex[1]) / gh * 110.57)

    # Food thread: cropland and people within each distance
    food = []
    pop_ok = False
    pop_dist, pop_vals = None, None
    if POP_PATH:
        try:
            with rasterio.open(POP_PATH) as src:
                sb = src.bounds
                ib = (max(ex[0], sb.left), max(ex[1], sb.bottom), min(ex[2], sb.right), min(ex[3], sb.top))
                if ib[0] < ib[2] and ib[1] < ib[3]:
                    win = window_from_bounds(*ib, transform=src.transform).round_offsets().round_lengths()
                    arr = src.read(1, window=win).astype(float)
                    if src.nodata is not None:
                        arr[arr == src.nodata] = 0
                    arr[~np.isfinite(arr) | (arr < 0)] = 0
                    wt = src.window_transform(win)
                    rr, cc_ = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
                    px = wt.c + (cc_ + 0.5) * wt.a
                    py = wt.f + (rr + 0.5) * wt.e
                    pop_dist = np.hypot((px - CLNG) * 111.32 * np.cos(np.radians(py)), (py - CLAT) * 110.57)
                    pop_vals = arr
                    pop_ok = True
        except Exception as e:
            print("Could not read regional population:", e)
    if not pop_ok:
        reg_notes.append("Regional population was not available, so the foodshed shows cropland only.")
    for rk in FOOD_RADII_KM:
        m = DKM <= rk
        crop = float((PXA[m & (GRID == 40)]).sum())
        people = float(pop_vals[pop_dist <= rk].sum()) if pop_ok else None
        food.append({"km": rk, "crop_km2": round(crop, 1), "pop": round(people) if people is not None else None})
    reg_notes.append("Regional population counts " + (pycountry.countries.get(alpha_3=ISO3).name if ISO3 else "one country") + " only.")
    print("Food thread: " + "; ".join(f"{f['km']} km: {f['crop_km2']:,.0f} km2 cropland" + (f", {f['pop']:,} people" if f['pop'] is not None else "") for f in food))

    # Land cover shares across the basin
    basin_out = None
    if BASIN is not None:
        bmask = rio_rasterize([(BASIN["geom"], 1)], out_shape=GRID.shape, transform=GTR, fill=0, dtype="uint8").astype(bool)
        valid = bmask & (GRID > 0)
        tot = float(PXA[valid].sum()) or 1.0
        def share(codes):
            return round(float(PXA[valid & np.isin(GRID, codes)].sum()) / tot, 3)
        shares = {"forest": share([10]), "shrub_grass": share([20, 30, 100]), "cropland": share([40]),
                  "built": share([50]), "bare": share([60, 70]), "water": share([80]), "wetland": share([90, 95])}
        simp = BASIN["geom"].simplify(max(ex[2] - ex[0], ex[3] - ex[1]) / 400)
        polys = [simp] if simp.geom_type == "Polygon" else [p for p in getattr(simp, "geoms", []) if p.geom_type == "Polygon"]
        rings = []
        for p in sorted(polys, key=lambda p: p.area, reverse=True)[:20]:
            rings.append([round(v, 4) for x, y in p.exterior.coords for v in (y, x)])
        basin_out = {"area_km2": round(BASIN["area_km2"]), "subbasins": BASIN["n"], "shares": shares, "rings": rings,
                     "source": "HydroBASINS level 8 (WWF HydroSHEDS)"}

    letters = np.full(GRID.shape, ".", dtype="<U1")
    for code, ch in WC_LETTER.items():
        letters[GRID == code] = ch
    REGIONAL = {
        "center": [round(CLAT, 5), round(CLNG, 5)],
        "grid": {"bounds": [round(v, 5) for v in ex], "w": int(gw), "h": int(gh), "codes": "".join(letters.ravel())},
        "foodshed": food, "need_km2_per_person": 0.0019, "basin": basin_out, "notes": reg_notes,
    }
except Exception as e:
    print("Could not build the regional threads:", e)
