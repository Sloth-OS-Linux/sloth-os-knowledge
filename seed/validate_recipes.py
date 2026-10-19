#!/usr/bin/env python3
"""A recipes.json ellenőrzése (a recipes Action futtatja minden változásnál, és PR-nál is).

A szabályok ugyanazok, mint a Sloth OS gépeken (sloth-os repó: files/system/usr/lib/sloth-os/common/
sloth_common/apps/recipes.py, abból másolva): csak engedélyezett mezők és értékek lehetnek benne, tetszőleges
parancs, környezeti változó, paraméter vagy DLL-betöltés nem. Ha ott változik, ezt is frissíteni kell.

  python3 seed/validate_recipes.py recipes.json
"""
import json
import re
import sys

# Ugyanazok az összetevők és kapcsolók, mint a közös tudásban (services/knowledge/src/worker.js); ha ott
# bővül, itt is kell (és a knowledge repó seed/validate_recipes.py-jában)
ALLOWED_VERBS = {
    "d3dcompiler_42", "d3dcompiler_43", "d3dcompiler_46", "d3dcompiler_47", "d3dx10", "d3dx11_42", "d3dx11_43",
    "d3dx9", "dotnet48", "gdiplus", "mf", "mfc42", "msxml3", "msxml4", "msxml6", "physx", "riched20", "vb6run",
    "vcrun2005", "vcrun2008", "vcrun2010", "vcrun2012", "vcrun2013", "vcrun2022", "xact", "xinput",
}
ALLOWED_ENV = {
    "PROTON_USE_WINED3D", "PROTON_ENABLE_NVAPI", "PROTON_HIDE_NVIDIA_GPU", "PROTON_FORCE_LARGE_ADDRESS_AWARE",
    "PROTON_HEAP_DELAY_FREE", "PROTON_NO_D3D11", "PROTON_NO_D3D10", "PROTON_OLD_GL_STRING", "PROTON_NO_WRITE_WATCH",
    "PROTON_NO_FSYNC", "PROTON_NO_ESYNC",
}
# Programparaméterek: csak a bevált, ártalmatlan kapcsolók (a böngészőmotorok GPU-ja, frissítő kihagyása)
ALLOWED_ARGS = {"--disable-gpu", "-opengl", "-SkipBuildPatchPrereq", "/runWithoutUpdating", "/deelevated",
                "--in-process-gpu", "--disable-gpu-sandbox"}
# DLL-kikapcsolás (=d) vagy a beépített változat (=b); natív DLL betöltését recept nem kérheti
_DLL = re.compile(r"^[a-z0-9_.-]{1,40}=(d|b)$")
_EXE = re.compile(r"^[a-z0-9 ._()+*?\[\]-]{1,80}$")
_ID = re.compile(r"^[a-z0-9-]{1,40}$")
_KEYS = {"id", "name", "match", "stubs", "prefer", "skip", "verbs", "env", "args", "dll_overrides", "per_exe"}
_PER_EXE_KEYS = {"verbs", "env", "args", "dll_overrides"}


def _rel_ok(path, allow_up=False):
    """Relatív út a Windows-környezeten belül (a „..” csak a kliens keresésénél, egy szinttel feljebb)."""
    if not isinstance(path, str) or not path or len(path) > 200 or path.startswith(("/", "\\")) or ":" in path:
        return False
    parts = re.split(r"[\\/]", path)
    ups = sum(1 for p in parts if p == "..")
    return (ups == 0 or (allow_up and ups <= 2 and all(p == ".." for p in parts[:ups]))) and "" not in parts


def _settings_ok(d):
    return (set(d) <= _PER_EXE_KEYS
            and set(d.get("verbs", [])) <= ALLOWED_VERBS
            and set(d.get("env", [])) <= ALLOWED_ENV
            and set(d.get("args", [])) <= ALLOWED_ARGS
            and all(isinstance(o, str) and _DLL.match(o) for o in d.get("dll_overrides", []))
            and all(isinstance(d.get(k, []), list) for k in _PER_EXE_KEYS))


def validate(recipe):
    """Igaz, ha a recept minden mezője megengedett. (A knowledge repó ellenőrzője ugyanezt nézi.)"""
    try:
        if not isinstance(recipe, dict) or not set(recipe) <= _KEYS or not _ID.match(recipe.get("id", "")):
            return False
        if not isinstance(recipe.get("name", ""), str) or len(recipe.get("name", "")) > 80:
            return False
        match = recipe.get("match") or {}
        if not set(match) <= {"dirs", "exe"} or not (match.get("dirs") or match.get("exe")):
            return False
        if not all(_rel_ok(d) for d in match.get("dirs", [])) or not all(
                isinstance(e, str) and _EXE.match(e) for e in match.get("exe", [])):
            return False
        stubs = recipe.get("stubs", {})
        if not isinstance(stubs, dict) or not all(
                _EXE.match(k.split("/")[-1]) and k.count("/") <= 1 and _rel_ok(v, allow_up=True)
                for k, v in stubs.items()):
            return False
        for key in ("prefer", "skip"):
            if not all(isinstance(e, str) and _EXE.match(e) for e in recipe.get(key, [])):
                return False
        if not _settings_ok({k: recipe[k] for k in _PER_EXE_KEYS if k in recipe}):
            return False
        per = recipe.get("per_exe", {})
        return isinstance(per, dict) and all(_EXE.match(k) and isinstance(v, dict) and _settings_ok(v)
                                             for k, v in per.items())
    except (TypeError, AttributeError):
        return False


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    errors = []
    if data.get("version") != 1 or not isinstance(data.get("recipes"), list):
        errors.append("a fájl szerkezete hibás (version: 1, recipes: [...])")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("updated", ""))):
        errors.append("hiányzik vagy hibás az updated mező (ÉÉÉÉ-HH-NN): a gépek ebből látják, melyik az újabb")
    ids = [r.get("id") for r in data.get("recipes", []) if isinstance(r, dict)]
    errors += [f"kétszer szerepel: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    errors += [f"érvénytelen recept: {r.get('id') if isinstance(r, dict) else r}"
               for r in data.get("recipes", []) if not validate(r)]
    for e in errors:
        print("HIBA:", e)
    print(f"{len(ids)} recept, {len(errors)} hiba")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "recipes.json"))
