"""Reference data the website needs alongside the places.

  python3 pipeline/refdata.py            -> tag places with country codes and refresh price levels
  python3 pipeline/refdata.py tag        -> only add missing country codes to data/places/*.json

Price levels: World Bank indicator PA.NUS.PPPC.RF, the price level ratio of the PPP conversion factor (GDP) to the
market exchange rate. It says how expensive a country is compared with the United States (US = 1.0).
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


def price_levels():
    import requests
    url = "https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PPPC.RF"
    rows, page = [], 1
    while True:
        r = requests.get(url, params={"format": "json", "mrnev": 1, "per_page": 400, "page": page}, timeout=60)
        r.raise_for_status()
        meta, data = r.json()
        rows += data or []
        if page >= meta.get("pages", 1):
            break
        page += 1
    out = {}
    for x in rows:
        iso3, v = x.get("countryiso3code"), x.get("value")
        if not iso3 or v is None:
            continue
        try:
            import pycountry
            c = pycountry.countries.get(alpha_3=iso3)
        except Exception:
            c = None
        if not c:
            continue   # regions and income groups
        out[c.alpha_2] = {"ratio": round(float(v), 3), "year": int(x["date"]), "name": x["country"]["value"]}
    us = out.get("US", {}).get("ratio") or 1.0
    for k in out:
        out[k]["factor"] = round(out[k]["ratio"] / us, 3)
    json.dump({"source": "World Bank, price level ratio of PPP conversion factor (GDP) to market exchange rate (PA.NUS.PPPC.RF)",
               "countries": out}, open(os.path.join(ROOT, "data", "price-levels.json"), "w"), separators=(",", ":"), sort_keys=True)
    print(f"price levels for {len(out)} countries; US ratio {us}")


if __name__ == "__main__":
    tag_places()
    if len(sys.argv) < 2 or sys.argv[1] != "tag":
        price_levels()
