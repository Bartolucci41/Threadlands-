"""Reference data the website needs alongside the places.

  python3 pipeline/refdata.py            -> tag places with country codes and refresh price levels
  python3 pipeline/refdata.py tag        -> only add missing country codes to data/places/*.json

Price levels: the World Bank PPP conversion factor (PA.NUS.PPP) divided by the official exchange rate (PA.NUS.FCRF).
It says how expensive a country is compared with the United States (US = 1.0).
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = os.path.join(ROOT, "data", "places")

# Country names as OpenStreetMap writes them in English, where they differ from ISO names
NAME_FIX = {
    "united states": "US", "usa": "US", "united kingdom": "GB", "russia": "RU", "south korea": "KR", "north korea": "KP",
    "iran": "IR", "vietnam": "VN", "taiwan": "TW", "democratic republic of the congo": "CD", "congo-brazzaville": "CG",
    "republic of the congo": "CG", "tanzania": "TZ", "bolivia": "BO", "venezuela": "VE", "turkey": "TR", "türkiye": "TR",
    "czechia": "CZ", "czech republic": "CZ", "laos": "LA", "syria": "SY", "moldova": "MD", "palestinian territories": "PS",
    "ivory coast": "CI", "côte d'ivoire": "CI", "hong kong": "HK", "macau": "MO", "the netherlands": "NL", "netherlands": "NL",
    "the bahamas": "BS", "the gambia": "GM", "cape verde": "CV", "east timor": "TL", "eswatini": "SZ", "brunei": "BN",
    "micronesia": "FM", "kosovo": "XK",
}


def country_code(name):
    n = (name or "").strip()
    if not n:
        return None
    if n.lower() in NAME_FIX:
        return NAME_FIX[n.lower()]
    try:
        import pycountry
        return pycountry.countries.lookup(n).alpha_2
    except Exception:
        try:
            import pycountry
            return pycountry.countries.search_fuzzy(n)[0].alpha_2
        except Exception:
            return None


def tag_places():
    changed = 0
    for f in glob.glob(os.path.join(PLACES, "*.json")):
        d = json.load(open(f))
        if d.get("country_code"):
            continue
        name = (d.get("display_name") or "").split(",")[-1].strip()
        if name.lower() in ("hong kong", "macau") or d.get("name", "").lower() == "hong kong":
            cc = "HK"
        else:
            cc = country_code(name)
        if cc:
            d["country_code"] = cc
            json.dump(d, open(f, "w"), separators=(",", ":"))
            changed += 1
        else:
            print("no country code for", os.path.basename(f), repr(name))
    print(f"tagged {changed} places with country codes")


def wb_latest(indicator):
    """Latest value per country (ISO3) for one World Bank indicator, with patient retries."""
    import time, requests
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    rows, page = [], 1
    while True:
        r = None
        for attempt in range(5):
            try:
                r = requests.get(url, params={"format": "json", "date": "2018:2025", "per_page": 1000, "page": page}, timeout=180)
                if r.status_code < 500:
                    break
            except requests.RequestException as e:
                print("World Bank busy, retrying:", e)
            time.sleep(20 * (attempt + 1))
        if r is None:
            raise SystemExit("World Bank did not answer")
        r.raise_for_status()
        j = r.json()
        if not isinstance(j, list) or len(j) < 2:
            raise SystemExit(f"Unexpected World Bank response for {indicator}: {str(j)[:300]}")
        rows += j[1] or []
        if page >= int(j[0].get("pages", 1)):
            break
        page += 1
    latest = {}
    for x in rows:
        k = x.get("countryiso3code")
        if x.get("value") is None or not k:
            continue
        if k not in latest or int(x["date"]) > int(latest[k]["date"]):
            latest[k] = x
    return latest


def price_levels():
    # Price level = PPP conversion factor (local currency per international dollar) / market exchange rate (local currency per US dollar)
    ppp = wb_latest("PA.NUS.PPP")
    fx = wb_latest("PA.NUS.FCRF")
    import pycountry
    euro = {"AUT", "BEL", "HRV", "CYP", "EST", "FIN", "FRA", "DEU", "GRC", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "PRT", "SVK", "SVN", "ESP"}
    emu = fx.get("EMU")
    out = {}
    for iso3, p in ppp.items():
        c = pycountry.countries.get(alpha_3=iso3)
        if not c:
            continue   # regions and income groups
        f = fx.get(iso3) or (emu if iso3 in euro else None)
        if not f or not f.get("value"):
            continue
        ratio = float(p["value"]) / float(f["value"])
        out[c.alpha_2] = {"ratio": round(ratio, 3), "year": int(p["date"]), "name": p["country"]["value"]}
    us = out.get("US", {}).get("ratio") or 1.0
    for k in out:
        out[k]["factor"] = round(out[k]["ratio"] / us, 3)
    json.dump({"source": "World Bank: PPP conversion factor, GDP (PA.NUS.PPP) divided by official exchange rate (PA.NUS.FCRF)",
               "countries": out}, open(os.path.join(ROOT, "data", "price-levels.json"), "w"), separators=(",", ":"), sort_keys=True)
    print(f"price levels for {len(out)} countries; US ratio {us}; e.g. MX {out.get('MX')}, NG {out.get('NG')}, IT {out.get('IT')}")


def grid_intensity():
    """Carbon intensity of electricity by country (g CO2e per kWh), latest year, from Ember via Our World in Data."""
    import csv, io, time, requests, pycountry
    url = "https://ourworldindata.org/grapher/carbon-intensity-electricity.csv?v=1&csvType=full&useColumnShortNames=true"
    r = None
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120, headers={"User-Agent": "threadlands.org reference data"})
            if r.status_code == 200:
                break
        except requests.RequestException as e:
            print("Our World in Data busy, retrying:", e)
        time.sleep(15 * (attempt + 1))
    if r is None or r.status_code != 200:
        raise SystemExit("Could not fetch grid carbon intensity")
    rows = list(csv.reader(io.StringIO(r.text)))
    head = rows[0]
    ci, yi, vi = head.index("Code") if "Code" in head else 1, head.index("Year") if "Year" in head else 2, len(head) - 1
    latest = {}
    for row in rows[1:]:
        try:
            code, year, val = row[ci], int(row[yi]), float(row[vi])
        except (ValueError, IndexError):
            continue
        if not code or code.startswith("OWID"):
            if row[0] == "World":
                latest["WORLD"] = max(latest.get("WORLD", (0, 0)), (year, val))
            continue
        c = pycountry.countries.get(alpha_3=code)
        if c and (c.alpha_2 not in latest or year > latest[c.alpha_2][0]):
            latest[c.alpha_2] = (year, val)
    out = {k: {"g_per_kwh": round(v[1]), "year": v[0]} for k, v in latest.items()}
    json.dump({"source": "Ember, via Our World in Data: carbon intensity of electricity generation (g CO2e per kWh)", "countries": out},
              open(os.path.join(ROOT, "data", "grid-intensity.json"), "w"), separators=(",", ":"), sort_keys=True)
    print(f"grid intensity for {len(out)} countries; world {out.get('WORLD')}, MX {out.get('MX')}, US {out.get('US')}")


if __name__ == "__main__":
    tag_places()
    if len(sys.argv) < 2 or sys.argv[1] != "tag":
        try:
            price_levels()
        except BaseException as e:   # keep last month's prices and still save the country codes
            print("Price levels not refreshed this time:", repr(e)[:300])
        try:
            grid_intensity()
        except BaseException as e:   # keep last month's figures
            print("Grid intensity not refreshed this time:", repr(e)[:300])
