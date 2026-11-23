"""Daily news for Threadlands: for each place and its state or region, the latest headlines on climate risks
(flood, heat, drought, fire) and on what is being built or decided (parks, infrastructure, policy).

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
    "infrastructure": r"metro\b|subway|transit|light rail|tram|bus rapid|brt\b|bike lanes?|cycle lanes?|ciclov|bridge|sewer|drenaje|drainage|water treatment|desalinat|levee|sea ?wall|\bdams?\b|\bpresa\b|flood (control|defen[cs]e|barrier)|stormwater|solar|wind farm|grid|infraestructura|infrastructure|obra",
    "policy": r"council|ordinance|\blaw\b|\bbill\b|budget|presupuesto|mayor|alcald|prefeit|sindaco|governor|gobernador|election|elecci|climate (plan|policy|action|goal|target)|plan de acci|permit|lawsuit|court|ruling|regulat|ban\b",
    "greening": r"\bparks?\b|parque|\bparc\b|\bparco\b|wetland|humedal|zona úmida|tree planting|trees|árboles|arborização|alberi|bäume|green infrastructure|sponge city|reforest|urban forest|verde urbano|stadtgrün|river restoration",
}
# Headlines that match the words but are not about the city's climate or land
NOISE = r"flood(ing|ed)? (the |international |global )?(market|inbox|zone)|flooded with|stock|shares|crypto|tokyo cement|box office|\bnba\b|\bnfl\b|football|soccer|fútbol|futebol|calcio"
# Crowds that "flood" a place are not floods
NOISE += r"|\b(participants|fans|crowds?|people|tourists|visitors|thousands|runners|shoppers|buyers|orders|calls|messages) (flood|flooded)"
# Places whose name is shared with somewhere else: how to search for them, and headlines that mean the other place
SEARCH_AS = {"washington-dc": "Washington DC"}
# The name local papers use, for the search in the local language and to recognise the city in a headline
LOCAL = {"mexico-city": ["Ciudad de México", "CDMX"], "rome": ["Roma"], "milan": ["Milano"], "naples": ["Napoli"], "turin": ["Torino"],
         "munich": ["München"], "lisbon": ["Lisboa"], "seville": ["Sevilla"], "vienna": ["Wien"], "zurich": ["Zürich"], "guatemala-city": ["Ciudad de Guatemala"],
         "panama-city": ["Ciudad de Panamá"], "havana": ["La Habana"], "marseille": ["Marseille"], "new-york": ["NYC", "New York City"],
         "washington-dc": ["D.C.", "Washington, DC"], "ho-chi-minh-city": ["Saigon"], "delhi": ["New Delhi"], "bengaluru": ["Bangalore"],
         "kolkata": ["Calcutta"], "mumbai": ["Bombay"], "copenhagen": ["København"], "prague": ["Praha"], "warsaw": ["Warszawa"]}
NOT_HERE = {"washington-dc": r"washington (state|coast)|oregon|seattle|spokane", "porto": r"porto (murtinho|alegre|velho|seguro|rico|nacional)",
            "santiago": r"santiago de (compostela|cuba|los caballeros|queretaro)", "cordoba": r"cordoba,? spain|andaluc"}
SKIP_SOURCES = {"facebook", "youtube", "instagram", "x", "tiktok", "reddit", "linkedin"}
HAZARDS = {"flood", "heat", "drought", "fire", "water"}
# Words that say something got better: a project approved, opened, finished or funded
GAIN = r"approv|aprueb|aprova|approva|opens?\b|opened|inaugur|complet|finish|conclu|funding|funded|financ|invest|plant(s|ed|ing)? |restor|launch|new park|nuevo parque|novo parque|nuovo parco|record (solar|clean)|cuts? emissions|reduc"
PRIORITY = {"policy": 3, "infrastructure": 3, "flood": 5, "heat": 5, "fire": 4, "drought": 4, "greening": 3, "water": 3, "climate": 1}

# Search words per language, and the Google News edition to ask (hl, ceid language)
TERMS = {
    "en": '(flood OR flooding OR heatwave OR "heat wave" OR drought OR wildfire OR "water shortage" OR wetland OR "urban park" OR "green infrastructure" OR "tree planting")',
    "es": '(inundación OR inundaciones OR "ola de calor" OR sequía OR "incendio forestal" OR "escasez de agua" OR humedal OR "nuevo parque" OR arbolado)',
    "pt": '(enchente OR inundação OR alagamento OR "onda de calor" OR seca OR "incêndio florestal" OR "falta de água" OR "novo parque" OR arborização)',
    "it": '(alluvione OR "ondata di calore" OR siccità OR "incendio boschivo" OR "nuovo parco" OR "verde urbano" OR forestazione)',
    "fr": '(inondation OR canicule OR sécheresse OR "feu de forêt" OR "nouveau parc" OR "îlot de chaleur" OR végétalisation)',
    "de": '(Hochwasser OR Hitzewelle OR Dürre OR Waldbrand OR "neuer Park" OR Stadtgrün OR Starkregen)',
}
BUILD = {
    "en": '("climate plan" OR "flood control" OR "green infrastructure" OR "new park" OR "bike lanes" OR "water infrastructure" OR "resilience plan" OR "heat action plan" OR "urban forest" OR "stormwater")',
    "es": '("plan climático" OR "obras hidráulicas" OR "nuevo parque" OR ciclovía OR "infraestructura verde" OR "plan de acción climática" OR drenaje OR reforestación)',
    "pt": '("plano climático" OR drenagem OR "novo parque" OR ciclovia OR "infraestrutura verde" OR "obras contra enchentes" OR arborização)',
    "it": '("piano clima" OR "nuovo parco" OR "piste ciclabili" OR "infrastrutture verdi" OR forestazione OR "rischio idrogeologico")',
    "fr": '("plan climat" OR "nouveau parc" OR "pistes cyclables" OR végétalisation OR "îlots de fraîcheur" OR "plan eau")',
    "de": '(Klimaplan OR "neuer Park" OR Radwege OR Schwammstadt OR Hochwasserschutz OR Stadtgrün)',
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


FAILS = [0]   # failed requests in a row; when Google News keeps refusing, stop asking and keep yesterday's headlines


def fetch(url, tries=3):
    if FAILS[0] >= 6:
        return b""
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Threadlands news; threadlands.org)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                FAILS[0] = 0
                return r.read()
        except Exception as e:
            print("  retry", k + 1, e, file=sys.stderr)
            time.sleep(5 * (k + 1))
    FAILS[0] += 1
    if FAILS[0] == 6:
        print("Google News is refusing requests; keeping the earlier headlines for the rest of this run", flush=True)
    return b""


def search(name, lang, cc):
    # One search covers risks and building/politics together: half the requests, so the run stays well inside its time
    q = f'"{name}" ({TERMS[lang][1:-1]} OR {BUILD[lang][1:-1]}) when:14d'
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


# Regions (state, province, county) that several places share get their own feed
REGION_CCS = {"US", "CA", "AU", "MX", "BR", "IN", "CN", "IT", "ES", "DE"}


REGION_SEARCH = {"Washington": "Washington State", "Georgia": "Georgia state", "State of Mexico": "Estado de México",
                 "Community of Madrid": "Comunidad de Madrid", "Valencian Community": "Comunitat Valenciana"}


def regions_of(p):
    """The county (US) and the state or province a place sits in, from its address, nearest first."""
    parts = [x.strip() for x in str(p.get("display") or "").split(",")][1:-1]
    if (p.get("cc") or "").upper() not in REGION_CCS:
        return []
    city = fold(p["name"].split(",")[0])
    parts = [x for x in parts if x and (city not in fold(x) or re.search(r" (county|parish)$", x, re.I)) and not re.search(r"region\b|regi[oó]n |township|district of columbia", x, re.I)]
    out = []
    county = next((x for x in parts if re.search(r" (county|parish)$", x, re.I)), None)
    if county:
        out.append(county)
    state = next((x for x in reversed(parts) if not re.search(r" (county|parish)$", x, re.I)), None)
    if state:
        out.append(state)
    return out


def gather(name, cc, slug, cutoff, seen, extra=()):
    """Headlines for one name in English and the local language: risks, then building and politics.
    Only headlines that name the place are kept, so a story about somewhere else never shows up here."""
    langs = ["en"] + ([LANG_OF[cc]] if cc in LANG_OF else [])
    found, items, fn = 0, [], fold(name)
    names = [fold(x) for x in [name] + LOCAL.get(slug, []) + list(extra)]
    for kind in ("both",):
        for lang in langs:
            arts = search(LOCAL[slug][0] if lang != "en" and slug in LOCAL else name, lang, cc)
            found += len(arts)
            for a in arts:
                if not a["title"] or not a["url"].startswith("http") or (a["date"] and a["date"] < cutoff):
                    continue
                key = re.sub(r"[^a-z0-9]", "", fold(a["title"]))[:60]
                if key in seen:
                    continue
                ft = fold(a["title"])
                if fold(a["source"]) in SKIP_SOURCES or re.search(fold(NOISE), ft) or ("new " + fn) in ft or re.search(NOT_HERE.get(slug, "$^"), ft):
                    continue
                named = any(re.search(r"(?<![a-z])" + re.escape(x) + r"(?![a-z])", ft) for x in names)
                topic = next((k for k, rx in TOPICS.items() if re.search(fold(rx), ft)), None)
                if not topic or not named:
                    continue                  # the headline itself must name the place and be about one of the topics
                seen.add(key)
                tone = "gain" if re.search(fold(GAIN), ft) else ("concern" if topic in HAZARDS else "update")
                items.append(dict(a, title=a["title"][:180], topic=topic, tone=tone, named=True))
            time.sleep(3)
    items.sort(key=lambda x: x["date"], reverse=True)
    return found, items


BUDGET = 40 * 60   # seconds; whatever is not reached today keeps yesterday's headlines and goes first tomorrow


def main():
    start = time.time()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    places = json.load(open(os.path.join(ROOT, "data", "index.json")))["places"]
    places = [p for p in places if p.get("slug") and p.get("name")]
    if limit:
        places = places[:limit]
    try:
        old = json.load(open(os.path.join(ROOT, "data", "news.json")))
    except Exception:
        old = {}
    # Start where yesterday's run stopped, so every place is refreshed even if one run cannot reach them all
    first = old.get("next", 0) % max(1, len(places))
    places = places[first:] + places[:first]
    cutoff = time.strftime("%Y%m%d", time.gmtime(time.time() - 15 * 86400))
    out = {k: [x for x in v if x.get("date", "") >= cutoff] for k, v in (old.get("places") or {}).items()}
    reg_out = {k: [x for x in v if x.get("date", "") >= cutoff] for k, v in (old.get("regions") or {}).items()}
    seen, regions, place_region, done = set(), {}, dict(old.get("place_region") or {}), 0
    for n, p in enumerate(places):
        rs = regions_of(p)
        if rs:
            place_region[p["slug"]] = rs
            for r in rs:
                regions.setdefault(r, (p.get("cc") or "").upper())
        if time.time() - start > BUDGET * 0.75:
            continue                      # out of time: keep what this place had
        name = SEARCH_AS.get(p["slug"]) or p["name"].split(",")[0].strip()
        cc = (p.get("cc") or "").upper()
        found, items = gather(name, cc, p["slug"], cutoff, seen)
        # Keep a mix: the newest concerns and the newest gains and updates
        conc = [x for x in items if x["tone"] == "concern"][:6]
        rest = [x for x in items if x["tone"] != "concern"][:6]
        mix = sorted(conc + rest, key=lambda x: x["date"], reverse=True)
        if FAILS[0] >= 6:
            continue                      # the search was refused: keep what this place had
        if mix:
            out[p["slug"]] = mix
        else:
            out.pop(p["slug"], None)
        done += 1
        print(f"{n + 1}/{len(places)} {name}: {found} found, {len(mix)} kept", flush=True)
    for k, (r, cc) in enumerate(regions.items()):
        if time.time() - start > BUDGET:
            break
        found, items = gather(REGION_SEARCH.get(r, r), cc, "", cutoff, seen, extra=[r.replace(" County", "").replace(" Parish", "")] if r != "Georgia" else [])
        if items:
            reg_out[r] = items[:8]
        print(f"region {k + 1}/{len(regions)} {r}: {found} found, {len(items[:8])} kept", flush=True)
    out = {k: v for k, v in out.items() if v}
    reg_out = {k: v for k, v in reg_out.items() if v}
    # The biggest stories across all places: the city named in the headline, newest first, hazards first; one per place
    top = [dict(it, place=slug) for slug, items in out.items() for it in items if it["named"]]
    top.sort(key=lambda x: (x["date"], PRIORITY.get(x["topic"], 0)), reverse=True)
    picked, used = [], set()
    for it in top:
        if it["place"] in used:
            continue
        used.add(it["place"])
        picked.append(it)
        if len(picked) >= 12:
            break
    data = {"updated": time.strftime("%Y-%m-%d"), "source": "Google News", "top": picked, "places": out,
            "regions": reg_out, "place_region": place_region, "next": (first + done) % max(1, len(places)) if done < len(places) else 0}
    json.dump(data, open(os.path.join(ROOT, "data", "news.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("news:", done, "places refreshed;", len(out), "places with news;", len(reg_out), "regions;", len(picked), "top stories")


if __name__ == "__main__":
    main()
