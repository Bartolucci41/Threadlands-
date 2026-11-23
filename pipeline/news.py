"""Daily news for Threadlands: the latest flood, heat, drought, fire and city-greening headlines for each library place.

Source: the GDELT Project's free DOC 2.0 API (https://www.gdeltproject.org), which monitors world news in many languages.
Only the headline, outlet, date and link are kept; readers go to the original story.
Writes data/news.json. Run: python3 pipeline/news.py [max_places]
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOPICS = {
    "flood": r"flood|flooding|inundaci|inondation|alluvion|deluge|storm surge|monsoon|cyclone|hurricane|typhoon",
    "heat": r"heat ?wave|heatwave|extreme heat|record heat|ola de calor|canicule|ondata di calore|temperatures soar|scorching",
    "drought": r"drought|water shortage|water crisis|sequía|sécheresse|siccit|dry spell|reservoir",
    "fire": r"wildfire|forest fire|bushfire|incendio forestal|feux? de forêt",
    "greening": r"\bpark\b|parque|parc|wetland|humedal|tree planting|trees planted|green infrastructure|sponge city|reforest|urban forest|rain garden|river restoration",
}
TOPIC_TERMS = ('(flood OR flooding OR "heat wave" OR heatwave OR drought OR wildfire OR "water shortage" OR '
               'wetland OR "urban park" OR "green infrastructure" OR "tree planting" OR "climate adaptation")')
PRIORITY = {"flood": 5, "heat": 5, "fire": 4, "drought": 4, "greening": 3}


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Threadlands news (threadlands.org)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                txt = r.read().decode("utf-8", "replace")
            return json.loads(txt) if txt.strip().startswith("{") else {}
        except Exception as e:  # GDELT asks for gentle use; back off and retry
            print("  retry", k + 1, e, file=sys.stderr)
            time.sleep(8 * (k + 1))
    return {}


def topic_of(title):
    t = title.lower()
    for k, rx in TOPICS.items():
        if re.search(rx, t):
            return k
    return None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    places = json.load(open(os.path.join(ROOT, "data", "index.json")))["places"]
    places = [p for p in places if p.get("slug") and p.get("name")]
    if limit:
        places = places[:limit]
    out, seen = {}, set()
    for n, p in enumerate(places):
        name = p["name"].split(",")[0].strip()
        q = f'"{name}" {TOPIC_TERMS}'
        url = ("https://api.gdeltproject.org/api/v2/doc/doc?" +
               urllib.parse.urlencode({"query": q, "mode": "ArtList", "maxrecords": "40", "format": "json", "timespan": "14d", "sort": "DateDesc"}))
        arts = fetch(url).get("articles", []) or []
        items = []
        for a in arts:
            title = re.sub(r"\s+", " ", a.get("title") or "").strip()
            link = a.get("url") or ""
            if not title or not link.startswith("http"):
                continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())[:60]
            if key in seen:
                continue
            topic = topic_of(title)
            if not topic:
                continue                      # only keep headlines that are clearly about the topics
            named = name.lower() in title.lower()
            seen.add(key)
            items.append({"title": title[:180], "url": link, "source": a.get("domain") or "", "date": (a.get("seendate") or "")[:8],
                          "lang": a.get("language") or "", "topic": topic, "named": named})
        items.sort(key=lambda x: (x["named"], x["date"]), reverse=True)
        if items:
            out[p["slug"]] = items[:6]
        print(f"{n + 1}/{len(places)} {name}: {len(arts)} found, {len(items)} kept", flush=True)
        time.sleep(6)
    # The biggest stories across all places: named in the headline, most urgent topics, newest first
    top = []
    for slug, items in out.items():
        for it in items:
            if it["named"]:
                top.append(dict(it, place=slug))
    top.sort(key=lambda x: (x["date"][:8], PRIORITY.get(x["topic"], 0)), reverse=True)
    picked, per = [], {}
    for it in top:
        if per.get(it["place"], 0) >= 1:
            continue
        per[it["place"]] = 1
        picked.append(it)
        if len(picked) >= 12:
            break
    data = {"updated": time.strftime("%Y-%m-%d"), "source": "GDELT Project", "top": picked, "places": out}
    json.dump(data, open(os.path.join(ROOT, "data", "news.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("news:", len(out), "places with news;", len(picked), "top stories")


if __name__ == "__main__":
    main()
