"""Fills in missing translations for every site language with Argos Translate (free, open source, runs offline).

Each data/i18n/<lang>.json is a list lined up with data/i18n/keys.json. Lines already translated, by hand or
before, are never touched. New lines are machine-translated and recorded in data/i18n/machine.json, so they can be
checked and polished by hand later (a hand edit just replaces the line and removes it from machine.json).
Numbers in the English text appear as {0}, {1}...; a translation that loses one is skipped and stays in English.
Run: python3 pipeline/i18n_translate.py
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
DIR = os.path.join(ROOT, "data", "i18n")
LANGS = ["es", "fr", "pt", "it", "zh", "hi", "ar", "ru"]   # the site's languages besides English
PH = re.compile(r"\{\d+\}")
TAG = re.compile(r"</?\d+>")


def install(langs):
    import argostranslate.package as pkg
    pkg.update_package_index()
    avail = pkg.get_available_packages()
    for code in langs:
        p = next((p for p in avail if p.from_code == "en" and p.to_code == code), None)
        if not p:
            print("no Argos model for", code, file=sys.stderr)
            continue
        print("installing", p.from_code, "->", p.to_code, flush=True)
        pkg.install_from_path(p.download())


def translator(code):
    import argostranslate.translate as tr
    langs = tr.get_installed_languages()
    en = next((l for l in langs if l.code == "en"), None)
    to = next((l for l in langs if l.code == code), None)
    return en.get_translation(to) if en and to else None


def safe(t, text):
    """Translate keeping {0}, {1}... and <1>…</1> markers; split around them if the engine drops any."""
    want, tags = sorted(PH.findall(text)), sorted(TAG.findall(text))
    out = t.translate(text)
    if sorted(PH.findall(out)) == want and sorted(TAG.findall(out)) == tags:
        return out
    if tags:
        return None                          # sentence with styled parts: leave it for a hand translation
    parts = re.split(r"(\{\d+\})", text)     # translate the words between the numbers on their own
    res = []
    for part in parts:
        if PH.fullmatch(part) or not part.strip():
            res.append(part)
        else:
            lead, core, tail = re.match(r"^(\s*)(.*?)(\s*)$", part, re.S).groups()
            res.append(lead + t.translate(core) + tail)
    out = "".join(res)
    return out if sorted(PH.findall(out)) == want else None


def main():
    keys = json.load(open(os.path.join(DIR, "keys.json")))
    mpath = os.path.join(DIR, "machine.json")
    machine = json.load(open(mpath)) if os.path.exists(mpath) else {}
    todo = {}
    for code in LANGS:
        path = os.path.join(DIR, code + ".json")
        cur = json.load(open(path)) if os.path.exists(path) else []
        cur = cur + [None] * (len(keys) - len(cur))
        missing = [i for i, v in enumerate(cur) if not v]
        if missing:
            todo[code] = (cur, missing)
    if not todo:
        print("i18n: every language is complete")
        return
    install(list(todo))
    for code, (cur, missing) in todo.items():
        t = translator(code)
        if not t:
            continue
        done = 0
        marks = set(machine.get(code, []))
        for i in missing:
            try:
                out = safe(t, keys[i])
            except Exception as e:      # one bad line never stops the rest
                print("  skip", code, i, e, file=sys.stderr)
                out = None
            if out:
                cur[i] = out.strip()
                marks.add(i)
                done += 1
        machine[code] = sorted(marks)
        json.dump([v or "" for v in cur], open(os.path.join(DIR, code + ".json"), "w"), ensure_ascii=False, indent=0)
        print(f"i18n {code}: {done} of {len(missing)} missing lines machine-translated", flush=True)
    json.dump(machine, open(mpath, "w"), separators=(",", ":"))


if __name__ == "__main__":
    main()
