#!/usr/bin/env python3
"""The base of Sloth OS's shared knowledge, from ProtonDB's open data (ODbL, https://github.com/bdefore/protondb-data):
per game and GPU vendor, the setting the reports say it works with.

Only the machine-recorded fields are used (the Proton variant, launch flags, launch options), and from the notes
only the names of the allowed winetricks components. Only allowed settings can get out (the same as in Sloth OS's
.exe handler: sloth_exe/community.py). A game is listed only if the setting that worked most often is not the
default one (Sloth OS starts with that anyway), and at least MIN_REPORTS reports back it up.

Each entry also says how many reports back it ("reports") and the month of the newest one ("last", "2026-09"):
Sloth Center shows it as "worked for 12 players, last confirmed in September 2026".

Usage: protondb.py <reports_piiremoved.json> <output.json>
"""
import collections
import json
import re
import sys
import time

YEARS = 2            # only recent reports (Proton changes a lot)
MIN_REPORTS = 3

# ProtonDB launchFlagsUsed -> Proton environment variable
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
    """A working report's setting in our form, or None (a native Linux version / unknown)."""
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


def summarize(reports, now=None):
    """The reports -> {"umu-<appid>": {gpu: {line, profile, fixes, reports, last}}}."""
    cut = (now or time.time()) - YEARS * 365 * 86400
    counts = collections.defaultdict(collections.Counter)   # (appid, gpu) -> config -> reports
    newest = collections.defaultdict(int)                   # (appid, gpu, config) -> newest report's time
    for x in reports:
        stamp = x.get("timestamp", 0)
        if stamp < cut:
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
        for g in (gpu, "any"):
            counts[(appid, g)][cfg] += 1
            newest[(appid, g, cfg)] = max(newest[(appid, g, cfg)], int(stamp))
    games = {}
    for (appid, gpu), counter in counts.items():
        cfg, n = counter.most_common(1)[0]
        line, profile, fixes = cfg
        if n < MIN_REPORTS or cfg == ("UMU-Proton", "default", ()):
            continue
        games.setdefault(f"umu-{appid}", {})[gpu] = {
            "line": line, "profile": profile, "fixes": [list(f) for f in fixes], "reports": n,
            "last": time.strftime("%Y-%m", time.gmtime(newest[(appid, gpu, cfg)]))}
    return games


def main(src, dst):
    with open(src, encoding="utf-8") as f:
        games = summarize(json.load(f))
    out = {"source": "ProtonDB (https://www.protondb.com), Open Database License (ODbL) 1.0",
           "games": dict(sorted(games.items(), key=lambda kv: int(kv[0][4:])))}
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=None, separators=(",", ":"), sort_keys=True)
        f.write("\n")
    print(f"{len(games)} games")


if __name__ == "__main__":
    main(*sys.argv[1:3])
