#!/usr/bin/env python3
"""A ProtonDB nyílt adataiból (ODbL, https://github.com/bdefore/protondb-data) a Sloth OS közös tudásának
alapja: játékonként és GPU-gyártónként az a beállítás, amivel a beszámolók szerint működik.

Csak a gépileg rögzített mezőket használjuk (Proton-változat, indítási kapcsolók, indítási beállítások),
és a jegyzetekből csak az engedélyezett winetricks-összetevők nevét. Csak az engedélyezett beállítások
kerülhetnek ki (ugyanazok, mint a Sloth OS .exe kezelőjében: sloth_exe/community.py).
Csak akkor veszünk fel egy játékot, ha a legtöbbször bevált beállítás nem az alapértelmezett
(különben a Sloth OS amúgy is azzal kezd), és legalább MIN_REPORTS beszámoló támasztja alá.

Használat: protondb.py <reports_piiremoved.json> <kimenet.json>
"""
import collections
import json
import re
import sys
import time

YEARS = 2            # csak a friss beszámolók (a Proton sokat változik)
MIN_REPORTS = 3

# ProtonDB launchFlagsUsed -> Proton környezeti változó
FLAG_ENV = {
    "enableNvapi": "PROTON_ENABLE_NVAPI", "hideNvidia": "PROTON_HIDE_NVIDIA_GPU",
    "largeAddressAware": "PROTON_FORCE_LARGE_ADDRESS_AWARE", "heapDelayFree": "PROTON_HEAP_DELAY_FREE",
    "disableD3d11": "PROTON_NO_D3D11", "disableD3d10": "PROTON_NO_D3D10", "oldGlString": "PROTON_OLD_GL_STRING",
    "noWriteWatch": "PROTON_NO_WRITE_WATCH",
}
ALLOWED_ENV = set(FLAG_ENV.values())
VERBS = {"d3dcompiler_42", "d3dcompiler_43", "d3dcompiler_46", "d3dcompiler_47", "d3dx10", "d3dx11_42",
         "d3dx11_43", "d3dx9", "dotnet48", "gdiplus", "mf", "mfc42", "msxml3", "msxml4", "msxml6", "physx",
         "riched20", "vb6run", "vcrun2005", "vcrun2008", "vcrun2010", "vcrun2012", "vcrun2013", "vcrun2022",
         "xact", "xinput"}
VERB_ALIASES = {"vcrun2015": "vcrun2022", "vcrun2017": "vcrun2022", "vcrun2019": "vcrun2022",
                **{f"dotnet{v}": "dotnet48" for v in ("45", "452", "46", "461", "462", "47", "471", "472", "48")}}
_VERB_RE = re.compile(r"\b(" + "|".join(sorted(VERBS | set(VERB_ALIASES), key=len, reverse=True)) + r")\b", re.I)
_ENV_RE = re.compile(r"\b(PROTON_[A-Z0-9_]+)=1\b")


def gpu_vendor(text):
    t = (text or "").lower()
    if any(k in t for k in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        return "nvidia"
    if any(k in t for k in ("amd", "radeon", "ati ", "vega")):
        return "amd"
    if "intel" in t:
        return "intel"
    return "other"


def config(r):
    """Egy működő beszámoló beállítása a mi formánkban, vagy None (natív Linux / ismeretlen)."""
    variant = r.get("variant")
    if variant == "native" or not variant:
        return None
    line = "GE-Proton" if variant == "ge" else "UMU-Proton"
    flags = {k for k, v in (r.get("launchFlagsUsed") or {}).items() if v}
    options = r.get("launchOptions") or ""
    env_on = set(_ENV_RE.findall(options))
    if "useWineD3d11" in flags or "PROTON_USE_WINED3D" in env_on:
        profile = "wined3d"
    elif {"disableEsync", "disableFsync"} & flags or {"PROTON_NO_ESYNC", "PROTON_NO_FSYNC"} & env_on:
        profile = "nofsync"
    else:
        profile = "default"
    fixes = {("env", FLAG_ENV[f]) for f in flags if f in FLAG_ENV}
    fixes |= {("env", e) for e in env_on if e in ALLOWED_ENV}
    custom = r.get("customizationsUsed") or {}
    if custom.get("winetricks") or custom.get("protontricks"):
        notes = " ".join(str(v) for v in (r.get("notes") or {}).values()) + " " + str(r.get("concludingNotes") or "")
        for m in _VERB_RE.findall(notes):
            m = m.lower()
            fixes.add(("verb", VERB_ALIASES.get(m, m)))
    return line, profile, tuple(sorted(fixes))


def main(src, dst):
    cut = time.time() - YEARS * 365 * 86400
    with open(src, encoding="utf-8") as f:
        reports = json.load(f)
    counts = collections.defaultdict(collections.Counter)   # (appid, gpu) -> config -> beszámolók
    for x in reports:
        if x.get("timestamp", 0) < cut:
            continue
        r = x.get("responses") or {}
        if r.get("verdict") != "yes" or r.get("startsPlay") == "no":
            continue
        appid = str((x.get("app") or {}).get("steam", {}).get("appId") or "")
        if not appid.isdigit():
            continue
        cfg = config(r)
        if not cfg:
            continue
        gpu = gpu_vendor((x.get("systemInfo") or {}).get("gpu"))
        counts[(appid, gpu)][cfg] += 1
        counts[(appid, "any")][cfg] += 1
    games = {}
    for (appid, gpu), counter in counts.items():
        (line, profile, fixes), n = counter.most_common(1)[0]
        if n < MIN_REPORTS or (line, profile, fixes) == ("UMU-Proton", "default", ()):
            continue
        games.setdefault(f"umu-{appid}", {})[gpu] = {
            "line": line, "profile": profile, "fixes": [list(f) for f in fixes], "reports": n}
    out = {"source": "ProtonDB (https://www.protondb.com), Open Database License (ODbL) 1.0",
           "games": dict(sorted(games.items(), key=lambda kv: int(kv[0][4:])))}
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=None, separators=(",", ":"), sort_keys=True)
        f.write("\n")
    print(f"{len(games)} játék")


if __name__ == "__main__":
    main(*sys.argv[1:3])
