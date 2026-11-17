"""City library robot: plan batches, build them, publish the results.

  python3 pipeline/library.py plan [batch_size]     -> prints chunks=[...] for GitHub Actions
  python3 pipeline/library.py build "slug1,slug2"   -> builds those places into out/
  python3 pipeline/library.py publish               -> moves out/ into data/places and rebuilds data/index.json
"""
import json, os, subprocess, sys, time, glob, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = os.path.join(ROOT, "data", "places")
OUT = os.path.join(ROOT, "out")
CACHE = os.path.join(ROOT, "cache")


def cities(name="cities.txt"):
    rows = []
    path = os.path.join(ROOT, "pipeline", name)
    if not os.path.exists(path):
        return rows
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        slug, query = [p.strip() for p in line.split("|", 1)]
        rows.append((slug, query))
    return rows


def plan(size=6):
    todo = [s for s, _ in cities() if not os.path.exists(os.path.join(PLACES, s + ".json"))]
    chunks = [",".join(todo[i:i + size]) for i in range(0, len(todo), size)]
    print("chunks=" + json.dumps(chunks))
    print(f"{len(todo)} places to build in {len(chunks)} batches", file=sys.stderr)


def build(slugs, q=None):
    q = q or dict(cities())
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    script = os.path.join(ROOT, "pipeline", "run_place.py")
    for slug in [s for s in slugs.split(",") if s]:
        dest = os.path.join(OUT, slug + ".json")
        log = os.path.join(OUT, "logs", slug + ".txt")
        t0 = time.time()
        status = "failed"
        try:
            with open(log, "w") as lf:
                lf.write(f"query: {q[slug]}\n"); lf.flush()
                r = subprocess.run([sys.executable, "-u", script, q[slug], dest], cwd=CACHE, stdout=lf, stderr=subprocess.STDOUT,
                                   timeout=60 * 60)
                lf.write(f"\nexit code: {r.returncode}\n")
            text = open(log).read()
            if os.path.exists(dest):
                status = "built with heat" if "HEAT_OK" in text else "built without heat"
        except subprocess.TimeoutExpired:
            status = "timed out"
        mins = (time.time() - t0) / 60
        print(f"{slug}: {status} in {mins:.1f} min", flush=True)
        if status != "built with heat":
            lines = open(log, errors="replace").read().splitlines()
            print(f"---- last lines of the {slug} log ----")
            print("\n".join(l[:300] for l in lines[-25:]), flush=True)
            print("----")
        json.dump({"slug": slug, "query": q[slug], "status": status, "minutes": round(mins, 1),
                   "when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                  open(os.path.join(OUT, "logs", slug + ".status.json"), "w"))
        # Clear per-place scratch files but keep shared downloads (river basins, population)
        for f in glob.glob(os.path.join(CACHE, "*.threadlands.json")):
            os.remove(f)
        time.sleep(2)


def one(slug, query):
    """Build a single requested place (from the website's "Build this place" button)."""
    import re
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", slug) or len(query) > 200 or "\n" in query:
        raise SystemExit("bad request")
    if os.path.exists(os.path.join(PLACES, slug + ".json")):
        print("already built:", slug)
        return
    req = os.path.join(ROOT, "pipeline", "requested.txt")
    known = dict(cities("requested.txt"))
    if slug not in known:
        with open(req, "a", encoding="utf-8") as f:
            f.write(f"{slug} | {query}\n")
    build(slug, {slug: query})


def summary(path, slug):
    d = json.load(open(path))
    c = d["cells"]
    n = len(c["id"])
    ins = [i for i in range(n) if c["inside"][i]] or list(range(n))
    reg = d.get("regional") or {}
    lat, lng = (reg.get("center") or [sum(c["lat"][i] for i in ins) / len(ins), sum(c["lng"][i] for i in ins) / len(ins)])
    disp = d.get("display_name") or d.get("name") or slug
    return {
        "slug": slug, "name": d.get("name") or slug, "country": disp.split(",")[-1].strip(),
        "display": disp, "lat": round(lat, 4), "lng": round(lng, 4),
        "pop": int(sum(c["pop"])), "city_pop": int(sum(p for p, i in zip(c["pop"], c.get("inside") or [1] * n) if i)), "hexes": n, "heat": "lst_rel" in c,
        "regional": bool(reg), "generated": d.get("generated"), "cc": d.get("country_code"),
        "kb": round(os.path.getsize(path) / 1024),
    }


def publish():
    os.makedirs(PLACES, exist_ok=True)
    report_path = os.path.join(ROOT, "data", "build-report.json")
    report = json.load(open(report_path)) if os.path.exists(report_path) else {}
    for f in glob.glob(os.path.join(OUT, "**", "*.status.json"), recursive=True):
        s = json.load(open(f))
        report[s["slug"]] = s
    for f in glob.glob(os.path.join(OUT, "**", "*.json"), recursive=True):
        if f.endswith(".status.json") or os.sep + "logs" + os.sep in f:
            continue
        try:
            d = json.load(open(f))
            assert d.get("format") == "threadlands-place" and len(d["cells"]["id"]) >= 20
        except Exception as e:
            print("skipping bad file", f, e)
            continue
        shutil.copyfile(f, os.path.join(PLACES, os.path.basename(f)))
    try:
        sys.path.insert(0, os.path.join(ROOT, "pipeline"))
        import refdata
        refdata.tag_places()
    except Exception as e:
        print("could not tag country codes:", e)
    names = dict(cities("requested.txt"))
    names.update(dict(cities()))
    # Library places show the familiar name from cities.txt ("Lagos", not "Lagos State")
    for slug, query in cities():
        f = os.path.join(PLACES, slug + ".json")
        label = query.split("||")[-1].split(",")[0].strip()
        if not os.path.exists(f) or not label:
            continue
        d = json.load(open(f))
        if d.get("name") != label:
            d.setdefault("osm_name", d.get("name"))
            d["name"] = label
            json.dump(d, open(f, "w"), separators=(",", ":"))
    index = []
    for f in sorted(glob.glob(os.path.join(PLACES, "*.json"))):
        slug = os.path.basename(f)[:-5]
        try:
            e = summary(f, slug)
        except Exception as ex:
            print("could not index", slug, ex)
            continue
        q = names.get(slug, e["display"])
        e["query"] = e["display"] if q.lower().startswith("osm:") else q
        e["requested"] = slug not in dict(cities())
        index.append(e)
    index.sort(key=lambda e: -e["pop"])
    json.dump({"format": "threadlands-index", "version": 1,
               "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "places": index},
              open(os.path.join(ROOT, "data", "index.json"), "w"), separators=(",", ":"))
    json.dump(report, open(report_path, "w"), indent=1, sort_keys=True)
    print(f"index has {len(index)} places")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        plan(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif cmd == "build":
        build(sys.argv[2])
    elif cmd == "one":
        one(sys.argv[2], sys.argv[3])
    elif cmd == "publish":
        publish()
