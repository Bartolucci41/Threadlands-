"""Daily news for Threadlands: the latest flood, heat, drought, fire and city-greening headlines for each library place.

Source: Google News search feeds (RSS), in English and in the place's own language where that is Spanish, Portuguese,
Italian, French or German. Only the headline, outlet, date and link are kept; readers go to the original story.
Writes data/news.json. Run: python3 pipeline/news.py [max_places]
"""
import email.utils
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")

# Labels a headline by topic (first match wins); the search itself already asked for these topics.
TOPICS = {
    "flood": r"flood|inundac|inundaç|enchente|alagament|inondation|alluvion|hochwasser|überschwemm|storm surge|monsoon|cyclone|hurricane|typhoon|huracán|tifón",
    "heat": r"heat ?wave|extreme heat|record heat|ola de calor|onda de calor|canicule|ondata di calore|hitzewelle|calor extremo|heat island|isla de calor|îlot de chaleur",
    "drought": r"drought|water shortage|water crisis|sequía|seca\b|sécheresse|siccità|dürre|escasez de agua|falta d.água|crisis hídrica|reservoir",
    "fire": r"wildfire|forest fire|bushfire|incendio forestal|incêndio florestal|feux? de forêt|incendi boschiv|waldbrand",
    "water": r"rainfall|\brains?\b|lluvias?|chuvas?|pioggia|landslide|deslave|deslizamento|frana|storm|tormenta|tempesta",
    "greening": r"\bparks?\b|parque|\bparc\b|\bparco\b|wetland|humedal|zona úmida|tree planting|trees|árboles|arborização|alberi|bäume|green infrastructure|sponge city|reforest|urban forest|verde urbano|stadtgrün|river restoration",
}
# Headlines that match the words but are not about the city's climate or land
NOISE = r"flood(ing|ed)? (the |international |global )?(market|inbox|zone)|flooded with|stock|shares|crypto|tokyo cement|box office|\bnba\b|\bnfl\b|football|soccer|fútbol|futebol|calcio"
# Crowds that "flood" a place are not floods
NOISE += r"|\b(participants|fans|crowds?|people|tourists|visitors|thousands|runners|shoppers|buyers|orders|calls|messages) (flood|flooded)"
# Places whose name is shared with somewhere else: how to search for them, and headlines that mean the other place
SEARCH_AS = {"washington-dc": "Washington DC"}
NOT_HERE = {"washington-dc": r"washington (state|coast)|oregon|seattle|spokane", "porto": r"porto (murtinho|alegre|velho|seguro|rico|nacional)",
            "santiago": r"santiago de (compostela|cuba|los caballeros|queretaro)", "cordoba": r"cordoba,? spain|andaluc"}
SKIP_SOURCES = {"facebook", "youtube", "instagram", "x", "tiktok", "reddit", "linkedin"}
PRIORITY = {"flood": 5, "heat": 5, "fire": 4, "drought": 4, "greening": 3, "water": 3, "climate": 1}

# Search words per language, and the Google News edition to ask (hl, ceid language)
TERMS = {
    "en": '(flood OR flooding OR heatwave OR "heat wave" OR drought OR wildfire OR "water shortage" OR wetland OR "urban park" OR "green infrastructure" OR "tree planting")',
    "es": '(inundación OR inundaciones OR "ola de calor" OR sequía OR "incendio forestal" OR "escasez de agua" OR humedal OR "nuevo parque" OR arbolado)',
    "pt": '(enchente OR inundação OR alagamento OR "onda de calor" OR seca OR "incêndio florestal" OR "falta de água" OR "novo parque" OR arborização)',
    "it": '(alluvione OR "ondata di calore" OR siccità OR "incendio boschivo" OR "nuovo parco" OR "verde urbano" OR forestazione)',
    "fr": '(inondation OR canicule OR sécheresse OR "feu de forêt" OR "nouveau parc" OR "îlot de chaleur" OR végétalisation)',
    "de": '(Hochwasser OR Hitzewelle OR Dürre OR Waldbrand OR "neuer Park" OR Stadtgrün OR Starkregen)',
}
LANG_OF = {}
for lang, ccs in {"es": "AR BO CL CO CU EC ES GT MX PA PE UY", "pt": "AO BR PT", "it": "IT", "fr": "FR", "de": "AT CH DE"}.items():
    for c in ccs.split():
        LANG_OF[c] = lang
HL = {("es", "ES"): "es", ("pt", "BR"): "pt-BR", ("pt", "PT"): "pt-PT", ("pt", "AO"): "pt-PT"}


def edition(lang, cc):
    if lang == "en":
        return {"hl": "en-US", "gl": "US", "ceid": "US:en"}
    hl = HL.get((lang, cc)) or ("es-419" if lang == "es" else lang)
    ce = {"pt-BR": "pt-419", "pt-PT": "pt-150"}.get(hl, hl)
    return {"hl": hl, "gl": cc, "ceid": f"{cc}:{ce}"}


def fold(t):
    return unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Threadlands news; threadlands.org)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:
            print("  retry", k + 1, e, file=sys.stderr)
            time.sleep(10 * (k + 1))
    return b""


def search(name, lang, cc):
    q = f'"{name}" {TERMS[lang]} when:14d'
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(dict(q=q, **edition(lang, cc)))
    raw = fetch(url)
    try:
        root = ET.fromstring(raw) if raw else None
    except ET.ParseError:
        root = None
    out = []
    for it in (root.iter("item") if root is not None else []):
        src = it.find("source")
        source = (src.text or "").strip() if src is not None else ""
        title = re.sub(r"\s+", " ", it.findtext("title") or "").strip()
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3].strip()
        try:
            d = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "")
            date = d.strftime("%Y%m%d")
        except Exception:
            date = ""
        out.append({"title": title, "url": (it.findtext("link") or "").strip(), "source": source, "date": date, "lang": lang})
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    places = json.load(open(os.path.join(ROOT, "data", "index.json")))["places"]
    places = [p for p in places if p.get("slug") and p.get("name")]
    if limit:
        places = places[:limit]
    cutoff = time.strftime("%Y%m%d", time.gmtime(time.time() - 15 * 86400))
    out, seen = {}, set()
    for n, p in enumerate(places):
        name = SEARCH_AS.get(p["slug"]) or p["name"].split(",")[0].strip()
        cc = (p.get("cc") or "").upper()
        langs = ["en"] + ([LANG_OF[cc]] if cc in LANG_OF else [])
        found, items = 0, []
        for lang in langs:
            arts = search(name, lang, cc)
            found += len(arts)
            for a in arts:
                if not a["title"] or not a["url"].startswith("http") or (a["date"] and a["date"] < cutoff):
                    continue
                key = re.sub(r"[^a-z0-9]", "", fold(a["title"]))[:60]
                if key in seen:
                    continue
                seen.add(key)
                ft, fn = fold(a["title"]), fold(name)
                if fold(a["source"]) in SKIP_SOURCES or re.search(fold(NOISE), ft) or ("new " + fn) in ft or re.search(NOT_HERE.get(p["slug"], "$^"), ft):
                    continue
                topic = next((k for k, rx in TOPICS.items() if re.search(fold(rx), ft)), None)
                if not topic:
                    continue                  # the headline itself must be about one of the topics
                items.append(dict(a, title=a["title"][:180], topic=topic, named=re.search(r"\b" + re.escape(fn) + r"\b", ft) is not None))
            time.sleep(2)
        items.sort(key=lambda x: (x["named"], x["topic"] != "climate", x["date"]), reverse=True)
        if items:
            out[p["slug"]] = items[:6]
        print(f"{n + 1}/{len(places)} {name}: {found} found, {len(items)} kept", flush=True)
    # The biggest stories across all places: the city named in the headline, a clear topic, newest first; one per place
    top = [dict(it, place=slug) for slug, items in out.items() for it in items if it["named"]]
    top.sort(key=lambda x: (x["topic"] != "climate", x["date"], PRIORITY.get(x["topic"], 0)), reverse=True)
    picked, used = [], set()
    for it in top:
        if it["place"] in used:
            continue
        used.add(it["place"])
        picked.append(it)
        if len(picked) >= 12:
            break
    data = {"updated": time.strftime("%Y-%m-%d"), "source": "Google News", "top": picked, "places": out}
    json.dump(data, open(os.path.join(ROOT, "data", "news.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("news:", len(out), "places with news;", len(picked), "top stories")


if __name__ == "__main__":
    main()
