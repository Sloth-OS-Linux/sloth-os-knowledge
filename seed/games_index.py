#!/usr/bin/env python3
"""The game list of Sloth Center's "Will it run?" check (games-index.json), made monthly from open data:

- ProtonDB (https://www.protondb.com, Open Database License 1.0; https://github.com/bdefore/protondb-data): from the
  reports of the last two years, per Steam game, how many say it works, per GPU vendor too, and how many played the
  game's own Linux version;
- AreWeAntiCheatYet (https://areweanticheatyet.com, MIT): which games' anti-cheat blocks Linux ("Denied": the makers
  do not allow it; "Broken": it does not work), also games that are not on Steam;
- sloth-tested.json (this repository, edited by hand): the games the Sloth OS team tried itself.

The rating is our own, simple and readable (Sloth Center explains it the same way):
  great  at least 85% of the reports say it works (players often mark a small fault in a game that runs well,
         so faults are not counted)
  ok     at least half say it works
  poor   fewer than half
  ""     fewer than MIN_REPORTS reports (Sloth Center says: too few reports)

Usage: games_index.py <reports_piiremoved.json> <awacy games.json> <sloth-tested.json> <output games-index.json>
"""
import collections
import json
import re
import sys
import time
import unicodedata

YEARS = 2
MIN_REPORTS = 3
VENDORS = ("amd", "nvidia", "intel")
AWACY_STATES = {"Denied": "denied", "Broken": "broken", "Supported": "supported", "Running": "running"}


def gpu_vendor(text):
    t = (text or "").lower()
    if any(k in t for k in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        return "nvidia"
    if any(k in t for k in ("amd", "radeon", "ati ", "vega")):
        return "amd"
    if "intel" in t:
        return "intel"
    return "other"


def clean_name(name):
    """Names from the reports may carry broken characters (e.g. a lost ®): those are dropped."""
    name = unicodedata.normalize("NFC", str(name or "")).replace("�", "")
    return re.sub(r"\s+", " ", name).strip()


def rating(works, total):
    if total < MIN_REPORTS:
        return ""
    if works >= 0.85 * total:
        return "great"
    return "ok" if works >= 0.5 * total else "poor"


def protondb(path, cut):
    """{appid: {"n": name, "t": reports, "w": works, "l": native, "g": {vendor: [works, total]}}}"""
    with open(path, encoding="utf-8") as f:
        reports = json.load(f)
    games = collections.defaultdict(lambda: {"n": "", "t": 0, "w": 0, "l": 0,
                                             "g": {v: [0, 0] for v in VENDORS}})
    for x in reports:
        if x.get("timestamp", 0) < cut:
            continue
        app = x.get("app") or {}
        appid = str((app.get("steam") or {}).get("appId") or "")
        if not appid.isdigit():
            continue
        r = x.get("responses") or {}
        works = r.get("verdict") == "yes" and r.get("startsPlay") != "no"
        g = games[appid]
        g["n"] = clean_name(app.get("title")) or g["n"]
        g["t"] += 1
        g["w"] += works
        g["l"] += r.get("variant") == "native"
        vendor = gpu_vendor((x.get("systemInfo") or {}).get("gpu"))
        if vendor in VENDORS:
            g["g"][vendor][0] += works
            g["g"][vendor][1] += 1
    return games


def main(reports_path, awacy_path, tested_path, out_path):
    cut = time.time() - YEARS * 365 * 86400
    stats = protondb(reports_path, cut)
    with open(awacy_path, encoding="utf-8") as f:
        awacy = json.load(f)
    try:
        with open(tested_path, encoding="utf-8") as f:
            tested = json.load(f).get("games", {})
    except FileNotFoundError:
        tested = {}

    index = {}
    for appid, s in stats.items():
        entry = {"n": s["n"], "r": rating(s["w"], s["t"]), "t": s["t"], "w": round(100 * s["w"] / s["t"])}
        if s["l"] * 2 >= s["t"]:
            entry["l"] = 1  # most players played its own Linux version
        gpus = {v: round(100 * w / t) for v, (w, t) in s["g"].items() if t >= MIN_REPORTS}
        if gpus:
            entry["g"] = gpus
        index[f"steam:{appid}"] = entry
    for game in awacy:
        state = AWACY_STATES.get(game.get("status"))
        if not state or game.get("native"):
            continue
        steam_id = str((game.get("storeIds") or {}).get("steam") or "")
        key = f"steam:{steam_id}" if steam_id.isdigit() else f"awacy:{game.get('slug')}"
        entry = index.setdefault(key, {"n": clean_name(game.get("name")), "r": "", "t": 0})
        entry["a"] = state
        anticheats = [clean_name(a) for a in game.get("anticheats") or [] if a]
        if anticheats:
            entry["ac"] = anticheats[:3]
    for key, test in tested.items():
        if not isinstance(test, dict) or test.get("result") not in ("works", "issues", "no"):
            continue
        entry = index.setdefault(key, {"n": clean_name(test.get("name")), "r": "", "t": 0})
        entry["st"] = test["result"]
        if test.get("date"):
            entry["sd"] = str(test["date"])[:10]
    index = {k: v for k, v in index.items() if v.get("n")}
    out = {"version": 1, "updated": time.strftime("%Y-%m-%d"),
           "sources": ["ProtonDB (https://www.protondb.com), Open Database License (ODbL) 1.0",
                       "AreWeAntiCheatYet (https://areweanticheatyet.com), MIT License",
                       "Sloth OS team tests (sloth-tested.json)"],
           "games": dict(sorted(index.items()))}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    by_rating = collections.Counter(v["r"] or "-" for v in index.values())
    print(f"{len(index)} games; ratings {dict(by_rating)}; anti-cheat "
          f"{dict(collections.Counter(v['a'] for v in index.values() if 'a' in v))}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
